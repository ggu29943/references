"""Silver-white Yuan hair: closed sculpted locks, strand details, UVs and skin weights.
All geometry is native mesh; no particle hair or render-only modifiers are required.
"""
import bpy, math, random
from mathutils import Vector
from math import sin, cos, pi


def _mat(name, color, roughness=.36):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=roughness
    bs.inputs['Metallic'].default_value=.05
    if 'Anisotropic IOR Level' in bs.inputs: bs.inputs['Anisotropic IOR Level'].default_value=.38
    return m


def _weights(z, chain):
    if chain=='head': return {'head':1.0}
    # Smoothly attach roots to the head and graduate into three secondary joints.
    levels=[1.56,1.40,1.22,1.02]
    names=['head',chain+'_01',chain+'_02',chain+'_03']
    if z>=levels[0]: return {names[0]:1.0}
    if z<=levels[-1]: return {names[-1]:1.0}
    for i in range(3):
        if levels[i]>=z>=levels[i+1]:
            t=(levels[i]-z)/(levels[i]-levels[i+1]); t=t*t*(3-2*t)
            return {names[i]:1-t,names[i+1]:t}
    return {names[-1]:1.0}


class _Batch:
    def __init__(self,name,materials):
        self.name=name;self.materials=materials;self.v=[];self.f=[];self.uv=[];self.w=[];self.mi=[]
    def vert(self,p,uv,chain):
        self.v.append(tuple(p));self.uv.append(uv);self.w.append(_weights(p[2],chain));return len(self.v)-1
    def face(self,inds,mat=0):self.f.append(tuple(inds));self.mi.append(mat)
    def finish(self,col):
        me=bpy.data.meshes.new(self.name);me.from_pydata(self.v,[],self.f);me.update()
        ob=bpy.data.objects.new(self.name,me);col.objects.link(ob)
        for m in self.materials: me.materials.append(m)
        uv=me.uv_layers.new(name='HairFlowUV')
        for poly,mi in zip(me.polygons,self.mi):
            poly.use_smooth=True;poly.material_index=mi
            for li in poly.loop_indices:uv.data[li].uv=self.uv[me.loops[li].vertex_index]
        groups={}
        for i,weights in enumerate(self.w):
            for bone,w in weights.items():
                if w<=1e-8:continue
                if bone not in groups:groups[bone]=ob.vertex_groups.new(name=bone)
                groups[bone].add([i],w,'REPLACE')
        ob['component']='Yuan sculpted hair';ob['uv_layout']='U around lock, V root to tip'
        return ob


def _spline(points, n):
    ps=[Vector(p) for p in points];out=[]
    for k in range(n):
        t=k/(n-1)*(len(ps)-1); i=min(int(t),len(ps)-2); t-=i
        p0=ps[max(0,i-1)];p1=ps[i];p2=ps[i+1];p3=ps[min(len(ps)-1,i+2)]
        out.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    return out


def _lock(batch,points,width,normal,chain,mat=0,n=28,sides=10,details=None):
    pts=_spline(points,n); nr=Vector(normal).normalized();rings=[]; frames=[]
    for i,p in enumerate(pts):
        t=i/(n-1);tan=(pts[min(n-1,i+1)]-pts[max(0,i-1)]).normalized()
        lateral=tan.cross(nr).normalized()
        outward=lateral.cross(tan).normalized()
        # Broad upper locks gently taper to individual pointed ends.
        swell=(.045+.955*sin(min(1,t/.23)*pi/2))
        taper=max(.009,(1-t)**.38)
        w=width*swell*taper
        d=w*.155
        ring=[]
        for j in range(sides):
            a=2*pi*j/sides
            p1=p+lateral*(w*cos(a))+outward*(d*sin(a))
            ring.append(batch.vert(p1,(j/sides,t),chain))
        rings.append(ring);frames.append((p,lateral,outward,w,d))
    batch.face(list(reversed(rings[0])),mat)
    for i in range(n-1):
        for j in range(sides):batch.face([rings[i][j],rings[i][(j+1)%sides],rings[i+1][(j+1)%sides],rings[i+1][j]],mat)
    batch.face(rings[-1],mat)
    if details:
        # Thin highlight strands lie just above the outward face of each lock.
        for offset in (-.48,.31):
            path=[]
            for p,lateral,outward,w,d in frames:
                path.append(p+lateral*w*offset+outward*(d*math.sqrt(1-offset*offset)+.00022))
            _strand(details,path,.00034,chain,0)


def _strand(batch,points,radius,chain,mat=0):
    # Four-sided very fine fibers are sufficient at character camera distances.
    n=len(points);rings=[]
    for i,p in enumerate(points):
        p=Vector(p);tan=(Vector(points[min(i+1,n-1)])-Vector(points[max(0,i-1)])).normalized()
        normal=tan.cross(Vector((0,1,0)))
        if normal.length<.05:normal=tan.cross(Vector((1,0,0)))
        normal.normalize();other=tan.cross(normal).normalized()
        taper=max(.05,sin(pi*(i/(n-1)) )**.4)
        ring=[batch.vert(p+radius*taper*(normal*cos(j*pi/2)+other*sin(j*pi/2)),(j/4,i/(n-1)),chain) for j in range(4)]
        rings.append(ring)
    for i in range(n-1):
        for j in range(4):batch.face([rings[i][j],rings[i][(j+1)%4],rings[i+1][(j+1)%4],rings[i+1][j]],mat)
    batch.face(list(reversed(rings[0])),mat);batch.face(rings[-1],mat)


def build():
    rng=random.Random(1904)
    col=bpy.data.collections.get('HAIR') or bpy.data.collections.new('HAIR')
    if col.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(col)
    white=_mat('Hair | pearl silver',(.78,.80,.88))
    pearl=_mat('Hair | frost highlight',(.90,.91,.96),.32)
    shadow=_mat('Hair | cool underlayers',(.66,.69,.79),.41)
    primary=_Batch('Hair_Long_Locks',[white,shadow,pearl]);fine=_Batch('Hair_Fine_Strands',[pearl]);cap=_Batch('Hair_Crown',[white,shadow])
    # Partial scalp, with a high front hairline hidden beneath the layered fringe.
    ntheta=17;na=80;grid=[]
    for i in range(ntheta):
        row=[]
        for j in range(na+1):
            a=2*pi*j/na
            front=(1+cos(a))/2
            maxtheta=2.02-1.00*(front**3)
            th=.015+maxtheta*i/(ntheta-1)
            relief=.00035*sin(a*45+th*7)*sin(th)
            x=(.111+relief)*sin(th)*sin(a)
            y=-(.100+relief)*sin(th)*cos(a)
            z=1.565+.153*cos(th)
            row.append(cap.vert((x,y,z),(j/na,i/(ntheta-1)),'head'))
        grid.append(row)
    for i in range(ntheta-1):
        for j in range(na):cap.face([grid[i][j],grid[i+1][j],grid[i+1][j+1],grid[i][j+1]],0)
    # Continuous inner fall fills gaps between the outer sculpted locks.
    # Its open front reveals the face and its scalloped lower edge gives a natural U silhouette.
    undergrid=[]
    for row in range(25):
        t=row/24;ring=[]
        for j in range(65):
            a=1.04+(2*pi-2.08)*j/64
            sx=sin(a);cy=-cos(a)
            taper=1-.13*t*t
            rx=(.092+.016*sin(pi*t))*taper
            ry=(.083+.020*sin(pi*t))*taper
            tip=1.035+.055*abs(sx)**2+.009*sin(9*a)
            z=1.638*(1-t)+tip*t
            rr=.0014*sin(a*34+t*4)*sin(pi*t)
            p=((rx+rr)*sx,(ry+rr)*cy+.029*t,z)
            chain=('hair_l' if sx>0 else 'hair_r') if cy<.1 else 'hair_back'
            ring.append(primary.vert(p,(j/64,t),chain))
        undergrid.append(ring)
    for i in range(24):
        for j in range(64):primary.face([undergrid[i][j],undergrid[i+1][j],undergrid[i+1][j+1],undergrid[i][j+1]],1)
    # Hair grows from the crown and falls around the back in overlapping locks.
    # Inner back layers first, then a subtly larger outer layer with offset tips.
    for layer,count in [(0,19),(1,17)]:
        for j in range(count):
            a=.77+(2*pi-1.54)*j/(count-1)+(rng.random()-.5)*.045
            sx=sin(a);cy=-cos(a);back=max(0,cy)
            r=.106+layer*.008
            tipz=1.005+rng.uniform(-.035,.045)+.07*(abs(sx)**3)
            dx=rng.uniform(-.012,.012)
            points=[
                (-.019+.016*sx,.003+.026*cy,1.711+layer*.001),
                (.078*sx,(.092 if cy<0 else .068)*cy,1.675+layer*.002),
                ((r+.005)*sx,((.120 if cy<0 else .100)+layer*.008)*cy,1.562),
                ((.126+layer*.012)*sx+dx*.5,((.138 if cy<0 else .118)+layer*.014)*cy+.019,1.414),
                ((.144+layer*.011)*sx+dx,(.132+layer*.018)*cy+.030+dx*.4,1.245),
                ((.132+layer*.018)*sx-dx*.6,(.137+layer*.02)*cy+.038,1.103),
                ((.09+layer*.02)*sx+dx,(.126+layer*.012)*cy+.034,tipz),
            ]
            # Sideward layers use side chains, while the rear fan shares a back chain.
            chain=('hair_l' if sx>0 else 'hair_r') if cy<.1 else 'hair_back'
            _lock(primary,points,.0145 if layer else .019,(sx,cy,.03),chain,0 if layer else 1,n=30,sides=10,details=fine if layer else None)
    # Gentle left part and staggered swept fringe; no mirrored curtain of bangs.
    bangs=_Batch('Hair_Face_Framing',[white,pearl,shadow])
    ends=[(-.102,1.592,.0040),(-.080,1.603,.0056),(-.058,1.611,.0064),
          (-.035,1.598,.0073),(-.014,1.579,.0078),(.010,1.586,.0079),
          (.034,1.603,.0075),(.057,1.610,.0062),(.080,1.614,.0055),(.100,1.601,.0039)]
    part=-.025
    for j,(ex,ez,width) in enumerate(ends):
        rootx=part+(j-4.5)*.00065
        sweep=.010 if ex>part else -.004
        p2x=rootx+(ex-rootx)*.32
        p3x=rootx+(ex-rootx)*.70
        points=[
            (rootx,-.009+(j-4.5)*.002,1.711),
            (p2x,-.049,1.699-abs(p2x)*.12),
            (p3x,-.088+abs(p3x)*.18,1.654-abs(p3x)*.10),
            (rootx+(ex-rootx)*.90,-.103+abs(ex)*.28,1.624+(j%3)*.0015),
            (ex,-.102+abs(ex)*.32,ez)
        ]
        _lock(bangs,points,width,(0,-1,.05),'head',0,n=20,sides=10,details=fine)
    # Three different S-curved tendrils on either cheek, with staggered tips.
    for side in (-1,1):
        for j in range(3):
            x=.097+j*.010
            wave=[.012,-.003,.021][j]*(1 if side>0 else .8)
            endz=[1.19,1.075,1.25][j]+(.018 if side<0 else 0)
            points=[
                (side*.050-.008,-.032,1.704-j*.004),
                (side*(.098+j*.004),-.060,1.646-j*.005),
                (side*(x+.003),-.062-j*.002,1.543),
                (side*(x+.012+wave*.4),-.075-j*.004,1.422),
                (side*(x+.022+wave*.5),-.088+j*.005,(1.422+endz)/2+.025),
                (side*(x+.032),-.081+j*.009,endz+.055),
                (side*(x+.022-wave*.3),-.068+j*.011,endz),
            ]
            _lock(bangs,points,[.0055,.0037,.0043][j],(side*.38,-1,.04),'hair_l' if side>0 else 'hair_r',0,n=27,sides=8,details=fine)
    # Individual flyaways vary in root position, curvature and endpoint.
    for side in (-1,1):
        for j in range(4):
            offset=[.003,.011,.006,.016][j]
            height=[1.254,1.112,1.310,1.186][j]
            points=[(side*(.032+j*.008),.009-j*.008,1.711-j*.002),
                    (side*(.100+offset),.014-j*.009,1.656+j*.004),
                    (side*(.113+offset),.024-j*.011,1.523+j*.018),
                    (side*(.139+offset),.039-j*.005,1.407+j*.006),
                    (side*(.154+offset),.054+j*.004,height+.050),
                    (side*(.135+j*.005),.065+j*.006,height)]
            _strand(fine,_spline(points,27),.00032,'hair_l' if side>0 else 'hair_r')
    result=[cap.finish(col),primary.finish(col),bangs.finish(col),fine.finish(col)]
    for ob in result: ob['reference']='User front, side, back and portrait references; canonical white waist-length hair without ornaments.'
    return result
