"""Yuan's plain everyday layers, built in metres for skeletal FBX export.
Canonical text takes precedence over ornamental reference-image details.
All garments are real UV-mapped meshes with deform weights; no jewelry or floral embroidery.
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

def build():
    global COLL,CREATED
    CREATED=[];COLL=bpy.data.collections.new('04 · Layered silk garments');bpy.context.scene.collection.children.link(COLL)
    silk=mat('Silk • plain soft ivory',(.82,.835,.88),.62)
    under=mat('Silk • plain cool underlayer',(.75,.775,.82),.66)
    edge=mat('Silk • simple folded hem',(.87,.885,.92),.60)
    charcoal=mat('Sash • graphite woven silk',(.015,.018,.024),.48)

    # Continuous ankle-length underskirt with shallow, soft folds.
    rows=[]
    for i in range(29):
        t=i/28;z=1.105-.985*t;rx=.119+.185*t**.77;ry=.081+.145*t**.85
        row=[]
        for j in range(84):
            a=j*2*pi/84;pleat=1+.018*sin(16*a+.22*t)+.004*cos(32*a+.1*t)
            row.append((rx*sin(a)*pleat,-ry*cos(a)*pleat,z+.002*t*t*cos(16*a)))
        rows.append(row)
    grid('Silk_plain_underskirt_soft_folds',rows,under,clothweights,True,.0012)
    # One unadorned outer robe layer over the long underlayer. Its subtly
    # asymmetric hem reads as overlapping soft cloth, not ornamental scallops.
    rows=[]
    for i in range(25):
        t=i/24;row=[]
        for j in range(84):
            a=2*pi*j/84
            zb=.205+.045*(.5-.5*cos(a+.3))
            z=1.095*(1-t)+zb*t;d=(1.105-z)/.985
            rx=.119+.185*d**.77+.012*t
            ry=.081+.145*d**.85+.009*t
            fl=1+.012*sin(16*a+.15*d)+.004*sin(7*a-.4*d)
            row.append((rx*sin(a)*fl,-ry*cos(a)*fl,z))
        rows.append(row)
    grid('Plain_outer_robe_layer',rows,silk,clothweights,True,.001)
    line('Simple_rolled_outer_hem',rows[-1]+[rows[-1][0]],.0007,edge,clothweights)
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
    collar('Black_inner_lapel_R',[(-.041,-.043,1.43),(-.026,-.077,1.39),(.038,-.101,1.295)],.010,charcoal,.004)
    collar('Black_inner_lapel_L',[(.041,-.043,1.43),(.023,-.079,1.384),(-.063,-.103,1.24)],.010,charcoal,.006)
    collar('Pearl_cross_lapel_under',[(-.063,-.055,1.414),(-.040,-.097,1.35),(.070,-.108,1.17)],.034,edge,.003)
    co=collar('Pearl_cross_lapel_over',[(.065,-.055,1.414),(.044,-.100,1.346),(-.069,-.111,1.148)],.035,silk,.005)
    for idx in (0,-1):line('Lapel_rolled_edge_'+str(idx),[r[idx] for r in co],.0006,edge,lambda p:torsoweights(p[2]))

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

    # Relaxed A-pose sleeves: one plain bell sleeve and a short outer layer.
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
        for layer,end in enumerate([1.0,.80]):
            rows=[]
            for i in range(17):
                t=i/16*end;x=sgn*(.163+.202*t);z=1.352-.421*t;y=-.006*t
                row=[]
                for j in range(32):
                    a=j*2*pi/32
                    # Perpendicular in XZ gives volume; lower side is generously draped.
                    r=.043+.002*layer+(.050+.012*layer)*t**1.4
                    drape=.095*t**1.5*(.5+.5*cos(a))
                    xoff=sgn*cos(a)*r*.90;zoff=cos(a)*r*.43-drape
                    yy=y+sin(a)*(.054+.003*layer+.055*t)+.003*sin(12*a)*t
                    # A gently hanging cuff, without pointed ornamental flounces.
                    zz=z+zoff-(t/end)**6*.010*(.5+.5*cos(a))
                    row.append((x+xoff,yy,zz))
                rows.append(row)
            grid(f'Sleeve_{side}_tier_{layer+1}',rows,silk if layer else under,sw2,True,.0012)
            line(f'Sleeve_{side}_hem_{layer+1}',rows[-1]+[rows[-1][0]],.001,edge,sw2)
    # Plain, restrained black cloth belt; no cord, flowers, metal or jewelry.
    rows=[]
    for z in [1.075,1.078,1.097,1.117,1.120]:
        rx=.130+(.0015 if z in (1.075,1.120) else 0);ry=.098
        rows.append([(rx*sin(j*2*pi/80),-ry*cos(j*2*pi/80),z) for j in range(80)])
    grid('Plain_black_cloth_belt',rows,charcoal,lambda p:{'spine_01':1},True,.0015)
    # Two short tie ends retain a trace of the reference silhouette without
    # the original long ceremonial streamers or contrasting lining.
    for side,sgn in [('l',1),('r',-1)]:
        length=.30 if side=='r' else .25;rows=[]
        for i in range(21):
            t=i/20;row=[]
            for j in range(5):
                u=j/4*2-1;x=sgn*(.053+.010*t)+u*.010
                z=1.091-length*t;d=(1.105-z)/.985
                y=-.108-.145*d**.85-.002*sin(t*2*pi)-.0005*u*u
                row.append((x,y,z))
            rows.append(row)
        wfn=lambda p,side=side:blend_chain('belt_'+side+'_',p[2],1.10,.30)
        grid('Short_plain_belt_tie_'+side,rows,charcoal,wfn,False,.0012)
    return list(CREATED)
