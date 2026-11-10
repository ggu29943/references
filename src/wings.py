"""Optional layered white wings for Yuan.

Coordinates are meters, forward -Y.  Geometry is skinned by the integration
script; feather vanes, rachises and barb accents are real geometry, not alpha
cards.  Their UV0 coordinates run from quill (V=0) to tip (V=1).
"""
import math
import random
import bpy
from mathutils import Vector
from common import material, collection


class Geometry:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.uvs = []
        self.weights = []

    def vertex(self, p, uv, weights):
        n = len(self.vertices)
        self.vertices.append(tuple(p))
        self.uvs.append(uv)
        self.weights.append(weights)
        return n

    def tube(self, points, radius, weights, sides=4):
        """Small closed tapered tube, primarily for central feather rachises."""
        points = [Vector(p) for p in points]
        rows=[]
        for i,p in enumerate(points):
            d = (points[min(i+1,len(points)-1)] - points[max(0,i-1)]).normalized()
            u = d.cross(Vector((0,1,0))).normalized()
            if u.length < .1: u=Vector((1,0,0))
            v = d.cross(u).normalized()
            rr = radius*(1-.88*i/max(1,len(points)-1))
            rows.append([self.vertex(p+rr*(math.cos(j*2*math.pi/sides)*u+math.sin(j*2*math.pi/sides)*v),
                                     (j/sides,i/(len(points)-1)),weights) for j in range(sides)])
        for a,b in zip(rows[:-1],rows[1:]):
            for j in range(sides): self.faces.append((a[j],a[(j+1)%sides],b[(j+1)%sides],b[j]))
        self.faces.append(tuple(reversed(rows[0])))
        self.faces.append(tuple(rows[-1]))

    def object(self,name,mat):
        data=bpy.data.meshes.new(name+'Mesh')
        data.from_pydata(self.vertices,[],self.faces)
        data.materials.append(mat)
        data.update()
        obj=bpy.data.objects.new(name,data)
        bpy.data.collections['Wings'].objects.link(obj)
        uv=data.uv_layers.new(name='UVMap')
        for p in data.polygons:
            p.use_smooth=True
            for li in p.loop_indices: uv.data[li].uv=self.uvs[data.loops[li].vertex_index]
        names=sorted({n for weights in self.weights for n in weights})
        groups={n:obj.vertex_groups.new(name=n) for n in names}
        for i,weights in enumerate(self.weights):
            for n,w in weights.items():
                if w>0: groups[n].add([i],w,'REPLACE')
        obj['part']='optional_wings'
        obj['geometry_detail']='Closed layered feather vanes, rachises, and barb ridges'
        return obj


def _bone_weights(x,side):
    # Feathers move primarily with the skeletal segment their quill attaches to.
    if x<.39: return {'wing_01_'+side:1.0}
    if x<.49:
        t=(x-.39)/.10
        return {'wing_01_'+side:1-t,'wing_02_'+side:t}
    if x<.69: return {'wing_02_'+side:1.0}
    if x<.79:
        t=(x-.69)/.10
        return {'wing_02_'+side:1-t,'wing_03_'+side:t}
    return {'wing_03_'+side:1.0}


def _feather(vanes,rachis,barbs,root,tip,width,weights,side_sign,seed,rows=9,details=True):
    """Loft a thin closed feather, cupped transverse to its central shaft."""
    rng=random.Random(seed)
    root=Vector(root); tip=Vector(tip)
    direct=tip-root
    length=direct.length
    axis=direct.normalized()
    transverse=Vector((axis.z,0,-axis.x)).normalized()
    # Slightly asymmetric vane creates an avian shape rather than a leaf.
    asym=.88+.18*rng.random()
    bend=.009+.024*length
    def point(t,s,back=False):
        c=root+direct*t
        c.y += bend*math.sin(math.pi*t)+.012*t*t
        w=width*(math.sin(math.pi*(t**.78))**.69)*(.9+.10*math.cos(2*math.pi*t))
        w*=asym if s<0 else 1.0
        p=c+transverse*(s*w)
        # The upper feather surface lies towards viewer (-Y); sides curl away.
        p.y += (.10*width*s*s-.10*width*(1-s*s))*math.sin(math.pi*t)
        p.y += .00065 if back else -.00065
        p.x *= side_sign
        return p
    tops=[]; bottoms=[]
    for i in range(rows+1):
        t=.001+(i/rows)*.998
        tops.append([vanes.vertex(point(t,s),((s+1)/2,t),weights) for s in (-1,-.5,0,.5,1)])
        bottoms.append([vanes.vertex(point(t,s,True),((s+1)/2,t),weights) for s in (-1,0,1)])
    for i in range(rows):
        for j in range(4): vanes.faces.append((tops[i][j],tops[i+1][j],tops[i+1][j+1],tops[i][j+1]))
        for j in range(2): vanes.faces.append((bottoms[i][j+1],bottoms[i+1][j+1],bottoms[i+1][j],bottoms[i][j]))
        vanes.faces.append((tops[i][0],bottoms[i][0],bottoms[i+1][0],tops[i+1][0]))
        vanes.faces.append((tops[i][4],tops[i+1][4],bottoms[i+1][2],bottoms[i][2]))
    vanes.faces.append(tuple(tops[0]+list(reversed(bottoms[0]))))
    vanes.faces.append(tuple(list(reversed(tops[-1]))+bottoms[-1]))
    shaft=[]
    for j in range(4):
        p=point(.015+j/3*.95,0)
        p.y-=.00065
        shaft.append(p)
    rachis.tube(shaft,min(.0011,width*.036),weights,3)
    # Delicate vein-like ridges read as feather barbs at close viewing distance.
    if details:
        for j in range(1,5):
            t=.12+j*.155
            for s in (-1,1):
                p1=point(t-.07,0); p2=point(t,.55*s); p3=point(min(.96,t+.04),.96*s)
                for p in (p1,p2,p3): p.y-=.00065
                barbs.tube([p1,p3],min(.00033,width*.014),weights,3)


def build():
    """Build mesh objects in an optional collection named Wings."""
    collection('Wings')
    ivory=material('Wing • porcelain feather',(0.88,.90,.98,1),roughness=.49)
    pearl=material('Wing • pearl coverts',(.94,.955,1,1),roughness=.43)
    soft=material('Wing • soft feather shade',(.78,.81,.90,1),roughness=.58)
    shaftmat=material('Wing • satin rachis',(.95,.96,1,1),roughness=.37)
    barbmat=material('Wing • fine vane ridges',(.86,.88,.95,1),roughness=.57)
    out=[]
    for side,sgn in [('l',1),('r',-1)]:
        primary=Geometry(); secondary=Geometry(); coverts=Geometry(); shafts=Geometry(); barbs=Geometry()
        # Remiges: broad secondary flight feathers overlap below the upper arm.
        for j in range(17):
            t=j/16
            x=.16+.55*t
            z=1.35+.155*math.sin(t*math.pi*.82)
            root=(x,.145,z)
            tip=(x+.11+.075*t,.18,1.02-.20*t+.025*math.sin(t*math.pi))
            _feather(secondary,shafts,barbs,root,tip,.042+.009*t,_bone_weights(x,side),sgn,100+j,10)
        # Primary fan extends from wrist around the hooked distal edge.
        for j in range(15):
            t=j/14
            x=.65+.34*t
            z=1.49-.22*t*t
            root=(x,.16,z)
            tip=(.80+.39*t,.20,.81+.33*t**1.9)
            _feather(primary,shafts,barbs,root,tip,.047-.014*t,_bone_weights(x,side),sgn,200+j,11)
        # Three staggered rows of greater/median coverts, each closer to viewer.
        for row in range(3):
            for j in range(22):
                t=(j+.38*(row%2))/21.38
                x=.13+.88*t
                crest=1.325+.24*math.sin(t*math.pi*.84)-.16*t*t
                z=crest-.060*row+.0035*math.sin(j*2.3+row)
                root=(x,.125-.012*row,z)
                extent=.16+.030*row+.042*math.sin(t*math.pi)+.008*math.sin(j*1.67+row)
                tip=(x+.055+.024*t,.13-.012*row,z-extent)
                _feather(coverts,shafts,barbs,root,tip,.025+.004*row,_bone_weights(x,side),sgn,300+row*30+j,7,details=row==2)
        # Small marginal coverts define a smooth scalloped leading edge.
        for row in range(2):
            for j in range(24):
                t=(j+.42*row)/23.42
                x=.105+.885*t
                crest=1.325+.24*math.sin(t*math.pi*.84)-.16*t*t
                z=crest+.018-.036*row
                root=(x,.092-.012*row,z)
                tip=(x+.038,.102-.012*row,z-.085-.025*math.sin(t*math.pi))
                _feather(coverts,shafts,barbs,root,tip,.0175,_bone_weights(x,side),sgn,500+row*30+j,5,details=False)
        # Shoulder down feathers visually blend into the scapular attachment.
        for row in range(3):
            for j in range(5):
                x=.075+j*.020+row*.018
                z=1.36-row*.04+j*.009
                root=(x,.08-row*.005,z)
                tip=(x+.035,.085-row*.005,z-.105)
                _feather(coverts,shafts,barbs,root,tip,.017,{'wing_01_'+side:1},sgn,700+row*5+j,5,False)
        for name,g,mat in [('Primary',primary,ivory),('Secondary',secondary,soft),('Coverts',coverts,pearl),('Rachis',shafts,shaftmat),('Barbs',barbs,barbmat)]:
            obj=g.object('Wing_'+side+'_'+name,mat)
            # Resolve outward normals on the closed feather and tube islands.
            import bmesh
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            bm.to_mesh(obj.data);bm.free()
            out.append(obj)
    return out
