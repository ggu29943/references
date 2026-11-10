"""Yuan's layered silk hanfu, built in metres for skeletal FBX export.
Each garment is a real mesh with UVs and deform weights. Embroidery is geometry.
"""
import bpy, math, bmesh
from mathutils import Vector
from math import sin, cos, pi, sqrt

COLL=None
CREATED=[]

def mat(name, color, rough=.45, metallic=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metallic
    if 'Sheen Weight' in p.inputs: p.inputs['Sheen Weight'].default_value=.22
    return m

def mesh(name,vs,fs,material,weights=None):
    d=bpy.data.meshes.new(name); d.from_pydata(vs,[],fs); d.update()
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(d);bm.free()
    o=bpy.data.objects.new(name,d); COLL.objects.link(o); d.materials.append(material)
    for p in d.polygons:p.use_smooth=True
    uv=d.uv_layers.new(name='UVMap')
    for p in d.polygons:
        for li in p.loop_indices:
            co=d.vertices[d.loops[li].vertex_index].co
            uv.data[li].uv=(co.x+.5,co.z/1.72)
    if weights:
        groups={}
        for i,ws in enumerate(weights):
            for bone,w in ws.items():
                if w>1e-5:
                    g=groups.get(bone)
                    if g is None:g=groups[bone]=o.vertex_groups.new(name=bone)
                    g.add([i],w,'REPLACE')
    CREATED.append(o);return o

def blend_chain(prefix,z,top=1.07,step=.32):
    t=max(0,min(2,(top-z)/step))
    i=min(1,int(t));a=t-i
    if t>=2:return {prefix+'03':1}
    return {prefix+f'{i+1:02}':1-a,prefix+f'{i+2:02}':a}

def clothweights(p):
    x,y,z=p
    a=math.atan2(x,-y)
    # Blend adjacent cardinal cloth chains, avoiding a hard seam at quadrants.
    t=(a%(2*pi))/(pi/2);i=int(t);a=t-i
    sides=['front','l','back','r','front'];w={}
    for side,factor in [(sides[i],1-a),(sides[i+1],a)]:
        for k,v in blend_chain('skirt_'+side+'_',z).items():w[k]=w.get(k,0)+factor*v
    if z>1.07:
        a=min(1,(z-1.07)/.08);w={k:v*(1-a) for k,v in w.items()};w['spine_01']=a
    return w

def torsoweights(z):
    if z>=1.31:return {'spine_03':1}
    if z>=1.21:
        a=(z-1.21)/.10;return {'spine_02':1-a,'spine_03':a}
    a=max(0,min(1,(z-1.11)/.1));return {'spine_01':1-a,'spine_02':a}

def grid(name,rows,material,wfn,closed=False,thickness=0):
    vs=[p for row in rows for p in row];fs=[];n=len(rows[0]);m=len(rows)
    for i in range(m-1):
        for j in range(n if closed else n-1):
            k=(j+1)%n;fs.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
    ob=mesh(name,vs,fs,material,[wfn(p) for p in vs])
    if thickness:
        mod=ob.modifiers.new('Tailored fabric thickness','SOLIDIFY');mod.thickness=thickness;mod.offset=0
    return ob

def line(name,pts,radius,material,wfn):
    rows=[]
    for i,p in enumerate(pts):
        p=Vector(p);t=Vector(pts[min(len(pts)-1,i+1)])-Vector(pts[max(0,i-1)])
        t.normalize();ref=Vector((0,1,0))
        if abs(t.dot(ref))>.94:ref=Vector((1,0,0))
        a=t.cross(ref).normalized();b=t.cross(a).normalized()
        rows.append([tuple(p+radius*(cos(j*2*pi/6)*a+sin(j*2*pi/6)*b)) for j in range(6)])
    return grid(name,rows,material,wfn,True)

class Detail:
    def __init__(self):self.v=[];self.f=[];self.w=[]
    def petal(self,center,length,width,angle,y_sign=-1,wfn=clothweights):
        # Slightly convex pointed petal in XZ, stitched into the cloth.
        c=Vector(center);d=Vector((sin(angle),0,cos(angle)));ac=Vector((cos(angle),0,-sin(angle)))
        off=len(self.v);rows=6;cols=5
        self.v.append(tuple(c));self.w.append(wfn(c))
        for i in range(1,rows-1):
            t=i/(rows-1);wid=width*sin(pi*t)**.8
            for j in range(cols):
                u=2*j/(cols-1)-1
                p=c+d*(t*length)+ac*(wid*u)
                p.y+=y_sign*.0014*sin(pi*t)*(1-u*u)
                self.v.append(tuple(p));self.w.append(wfn(p))
        for j in range(cols-1):self.f.append((off,off+1+j+1,off+1+j))
        for i in range(rows-3):
            for j in range(cols-1):
                a=off+1+i*cols+j;self.f.append((a,a+1,a+1+cols,a+cols))
        tip=len(self.v);p=c+d*length;self.v.append(tuple(p));self.w.append(wfn(p))
        last=off+1+(rows-3)*cols
        for j in range(cols-1):self.f.append((last+j,last+j+1,tip))
    def flower(self,center,size,wfn=clothweights,petals=5,y_sign=-1):
        for i in range(petals):self.petal(center,size,size*.23,i*2*pi/petals+.12,y_sign,wfn)
    def finish(self,name,material):return mesh(name,self.v,self.f,material,self.w)

def build():
    global COLL,CREATED
    CREATED=[];COLL=bpy.data.collections.new('04 · Layered silk garments');bpy.context.scene.collection.children.link(COLL)
    silk=mat('Silk • pearl ivory',(.82,.835,.88),.4)
    under=mat('Silk • cool underlayer',(.70,.725,.79),.5)
    edge=mat('Silk • folded ivory edging',(.94,.95,.98),.36)
    thread=mat('Embroidery • raised pearl thread',(.91,.92,.955),.48)
    charcoal=mat('Sash • graphite woven silk',(.015,.018,.024),.48)
    trim=mat('Sash • subtle edge stitching',(.095,.105,.12),.45)
    silver=mat('Flower centre • pale gold',(.61,.53,.33),.32,.45)

    # One finely pleated continuous ankle-length underskirt.
    rows=[]
    for i in range(29):
        t=i/28;z=1.105-.985*t;rx=.119+.185*t**.77;ry=.081+.145*t**.85
        row=[]
        for j in range(84):
            a=j*2*pi/84;pleat=1+.027*sin(28*a+.1*t)+.012*cos(56*a)
            row.append((rx*sin(a)*pleat,-ry*cos(a)*pleat,z+.0025*t*t*cos(28*a)))
        rows.append(row)
    grid('Silk_underskirt_28_soft_pleats',rows,under,clothweights,True,.0012)
    # Four petal-like overlapping outer skirts. The hems descend to pointed scallops.
    for layer,(ztop,zbot,extra) in enumerate([(1.095,.32,.016),(1.095,.51,.023),(1.095,.71,.030)]):
        rows=[]
        for i in range(17):
            t=i/16;row=[]
            for j in range(84):
                a=2*pi*j/84
                # Handkerchief hem points front, back, and sides.
                zb=zbot+.115*(.5-.5*cos(4*a))
                z=ztop*(1-t)+zb*t
                d=(1.105-z)/.985
                rx=.119+.185*d**.77+extra*t;ry=.081+.145*d**.85+extra*.65*t
                fl=1+.022*sin(28*a+.1*d)
                row.append((rx*sin(a)*fl,-ry*cos(a)*fl,z))
            rows.append(row)
        grid(f'Outer_skirt_layer_{layer+1:02}',rows,silk,clothweights,True,.001)
        line(f'Rolled_hem_skirt_{layer+1:02}',rows[-1]+[rows[-1][0]],.0009,edge,clothweights)
    # Centre ornamental stole panels, with pointed hems and subtle ripples.
    for back in (False,True):
        sign=1 if back else -1
        rows=[]
        for i in range(35):
            t=i/34;row=[]
            for j in range(9):
                u=j/8*2-1;zb=.19+.048*abs(u);z=1.09*(1-t)+zb*t
                d=(1.105-z)/.985;w=.034+.007*t
                y=sign*(.081+.145*d**.85+.027+.0012*cos(2*pi*u))
                row.append((u*w,y,z))
            rows.append(row)
        grid(('Back' if back else 'Front')+'_embroidered_stole',rows,silk,clothweights,False,.0012)
        for index in (0,-1):line(('Back' if back else 'Front')+f'_stole_piping_{index}',[r[index] for r in rows],.00065,edge,clothweights)
    # Torso follows body while retaining an open neckline.
    profiles=[(1.105,.124,.086),(1.16,.128,.09),(1.24,.153,.096),(1.31,.161,.088),(1.35,.176,.075),(1.385,.121,.063),(1.425,.045,.045)]
    rows=[]
    for z,rx,ry in profiles:
        rows.append([(rx*sin(j*2*pi/64),-ry*cos(j*2*pi/64),z) for j in range(64)])
    grid('Wrap_bodice',rows,silk,lambda p:torsoweights(p[2]),True,.0015)
    # Interleaved black inner collar and broad pearl crossover collar.
    def collar(name,points,width,material,offset):
        pts=[]
        for q in range(len(points)-1):
            a=Vector(points[q]);b=Vector(points[q+1])
            for i in range(8):pts.append(a.lerp(b,i/8))
        pts.append(Vector(points[-1]));rows=[]
        for i,p in enumerate(pts):
            tangent=pts[min(len(pts)-1,i+1)]-pts[max(0,i-1)];tangent.y=0;tangent.normalize()
            across=Vector((-tangent.z,0,tangent.x))
            rows.append([tuple(p+across*(width*(j/4-.5))+Vector((0,-offset,0))) for j in range(5)])
        grid(name,rows,material,lambda p:torsoweights(p[2]),False,.0012)
        return rows
    collar('Black_inner_lapel_R',[(-.041,-.043,1.43),(-.026,-.077,1.39),(.038,-.101,1.295)],.018,charcoal,.004)
    collar('Black_inner_lapel_L',[(.041,-.043,1.43),(.023,-.079,1.384),(-.063,-.103,1.24)],.018,charcoal,.006)
    collar('Pearl_cross_lapel_under',[(-.063,-.055,1.414),(-.040,-.097,1.35),(.070,-.108,1.17)],.040,edge,.003)
    co=collar('Pearl_cross_lapel_over',[(.065,-.055,1.414),(.044,-.100,1.346),(-.069,-.111,1.148)],.043,silk,.005)
    for idx in (0,-1):line('Lapel_rolled_edge_'+str(idx),[r[idx] for r in co],.0008,thread,lambda p:torsoweights(p[2]))

    # Fitted shoulder yokes bridge the bodice and upper sleeve. The arm-root
    # circle rises above the sleeve opening; these cloth caps cover that join.
    for side,sgn in [('l',1),('r',-1)]:
        rows=[]
        for i in range(19):
            lat=-pi*.49+i/18*pi*.98
            row=[]
            for j in range(40):
                angle=j*2*pi/40
                row.append((sgn*(.158+.060*cos(lat)*sin(angle)),
                            .002+.054*cos(lat)*cos(angle),
                            1.338+.049*sin(lat)))
            rows.append(row)
        def shoulder_weights(p,side=side):
            a=max(0,min(1,(abs(p[0])-.115)/.075))
            return {'clavicle_'+side:1-a,'upperarm_'+side:a}
        grid('Fitted_silk_shoulder_yoke_'+side,rows,silk,shoulder_weights,True,.0012)

    # Relaxed A-pose sleeves with bell cuffs; two overlapping hanging flounces.
    for side,sgn in [('l',1),('r',-1)]:
        def sw(p,side=side,sgn=sgn):
            z=p[2];x=abs(p[0]);under=(x-.17)*(-2.05)+1.35
            if z<under-.055:
                return blend_chain('sleeve_'+side+'_',z,1.16,.25) if z>=.91 else {'sleeve_'+side+'_02':1}
            t=max(0,min(1,(1.20-z)/.16));return {'upperarm_'+side:1-t,'lowerarm_'+side:t}
        # The sleeve helper has only 2 secondary bones.
        def sw2(p):
            w=sw(p);bad='sleeve_'+side+'_03'
            if bad in w:w['sleeve_'+side+'_02']=w.get('sleeve_'+side+'_02',0)+w.pop(bad)
            return w
        for layer,end in enumerate([1.0,.79,.58]):
            rows=[]
            for i in range(17):
                t=i/16*end;x=sgn*(.163+.202*t);z=1.352-.421*t;y=-.006*t
                row=[]
                for j in range(32):
                    a=j*2*pi/32
                    # Perpendicular in XZ gives volume; lower side is generously draped.
                    r=.043+.002*layer+(.065+.016*layer)*t**1.4
                    drape=.12*t**1.5*(.5+.5*cos(a))
                    xoff=sgn*cos(a)*r*.90;zoff=cos(a)*r*.43-drape
                    yy=y+sin(a)*(.054+.003*layer+.055*t)+.003*sin(12*a)*t
                    # Layer hems have a softly pointed underside.
                    zz=z+zoff-(t/end)**6*.026*(.5+.5*cos(2*a))
                    row.append((x+xoff,yy,zz))
                rows.append(row)
            grid(f'Sleeve_{side}_tier_{layer+1}',rows,silk if layer else under,sw2,True,.0012)
            line(f'Sleeve_{side}_hem_{layer+1}',rows[-1]+[rows[-1][0]],.001,edge,sw2)
        # Embroidery sprays on visible front shoulder/cuff surface.
        d=Detail()
        for k,(x,z,size) in enumerate([(.205,1.235,.019),(.270,1.09,.021),(.330,.95,.017)]):
            yy=-.063-(1.35-z)*.09
            d.flower((sgn*x,yy,z),size,sw2,7)
            for h in range(2):
                d.petal((sgn*(x+.010),yy,z-.018-h*.019),.018,.003,sgn*1.1,-1,sw2)
        d.finish(f'Sleeve_{side}_pearl_embroidery',thread)

    # Sculpted wide black obi, upper/lower seam and silver waist cord.
    rows=[]
    for z in [1.063,1.067,1.097,1.130,1.134]:
        rx=.130+(.003 if z in (1.063,1.134) else 0);ry=.098
        rows.append([(rx*sin(j*2*pi/80),-ry*cos(j*2*pi/80),z) for j in range(80)])
    grid('Graphite_wide_obi',rows,charcoal,lambda p:{'spine_01':1},True,.002)
    for z in (1.069,1.128):
        line('Obi_seam_'+str(z),[(.132*sin(j*2*pi/80),-.100*cos(j*2*pi/80),z) for j in range(81)],.0009,trim,lambda p:{'spine_01':1})
    line('Ivory_waist_cord',[(.133*sin(j*2*pi/96),-.102*cos(j*2*pi/96),1.098) for j in range(97)],.0021,edge,lambda p:{'spine_01':1})
    for side,sgn in [('l',1),('r',-1)]:
        length=.78 if side=='r' else .65;rows=[]
        for i in range(39):
            t=i/38;row=[]
            for j in range(5):
                u=j/4*2-1;x=sgn*(.076+.013*t)+u*.0155
                z=1.091-length*t;d=(1.105-z)/.985;y=-.112-.145*d**.85-.003*sin(t*3*pi)-.0007*u*u
                row.append((x,y,z))
            rows.append(row)
        wfn=lambda p,side=side:blend_chain('belt_'+side+'_',p[2],1.10,.30)
        grid('Long_black_sash_'+side,rows,charcoal,wfn,False,.0015)
        for idx in (0,-1):line('Black_sash_edge_'+side+str(idx),[r[idx] for r in rows],.00065,trim,wfn)
        # White reverse tail visible beneath black sash, offset by a few millimetres.
        lining=[[tuple(Vector(p)+Vector((sgn*.005,.003,-.025))) for p in r] for r in rows]
        grid('White_sash_reverse_'+side,lining,edge,wfn,False,.0008)
    rows=[]
    for i in range(25):
        t=i/24;z=1.09-.41*t;d=(1.105-z)/.985
        rows.append([(u*.016,.106+.145*d**.85,z) for u in [-1,-.5,0,.5,1]])
    grid('Short_rear_black_sash',rows,charcoal,clothweights,False,.0015)

    # Low-relief floral vines on front/back decorative stole and skirt panels.
    details=Detail()
    for sign in (-1,1):
        for z in [.95,.82,.69,.56,.43,.30]:
            d=(1.105-z)/.985;y=sign*(.081+.145*d**.85+.030)
            details.flower((0,y,z),.022,clothweights,7,sign)
            for s in (-1,1):
                details.petal((s*.004,y,z-.028),.018,.004,s*.62,sign,clothweights)
                details.petal((s*.003,y,z-.045),.019,.004,s*.9,sign,clothweights)
        for s in (-1,1):
            for z in (.84,.64,.46):
                d=(1.105-z)/.985;rx=.119+.185*d**.77+.029;ry=.081+.145*d**.85+.020
                a=.65;details.flower((s*rx*sin(a),sign*(ry*cos(a)+.008),z),.023,clothweights,7,sign)
    details.finish('Pearl_floral_vines_on_silk',thread)
    # Five-petal waist ornaments and pendant with individual convex leaves.
    flowers=Detail();centers=[]
    for x,z,size in [(-.079,1.098,.023),(0,1.098,.015),(.079,1.098,.023),(.083,.875,.014)]:
        y=-.112 if z>1.05 else -.173
        wf=(lambda p:{'spine_01':1}) if z>1.05 else (lambda p:blend_chain('belt_l_',p[2],1.10,.30))
        flowers.flower((x,y,z),size,wf,5)
        centers.append(((x,y-.0015,z),wf))
    flowers.flower((0,.116,1.09),.023,lambda p:{'spine_01':1},5,1)
    flowers.finish('White_five_petal_waist_blossoms',edge)
    v=[];f=[];w=[]
    for c,wf in centers:
        off=len(v);v.append(c);w.append(wf(c))
        for j in range(16):
            p=(c[0]+.0027*cos(j*2*pi/16),c[1]-.001,c[2]+.0027*sin(j*2*pi/16));v.append(p);w.append(wf(p))
        for j in range(16):f.append((off,off+1+j,off+1+(j+1)%16))
    mesh('Blossom_pale_gold_centres',v,f,silver,w)
    return list(CREATED)
