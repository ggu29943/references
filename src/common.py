import bpy, math
from mathutils import Vector
CURRENT = None

def collection(name):
    global CURRENT
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    CURRENT=c
    return c

def link(obj):
    (CURRENT or bpy.context.scene.collection).objects.link(obj)
    return obj

def relocate(obj):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    return link(obj)

def material(name,color,metallic=0,roughness=.5):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.diffuse_color=(*color[:3],color[3] if len(color)>3 else 1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness
    return m

def smooth(obj):
    if obj.type=='MESH':
        for p in obj.data.polygons:p.use_smooth=True
    return obj

def assign(obj,bone):
    if not bone:return obj
    obj['rigid_bone']=bone
    if obj.type=='MESH':
        g=obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
        g.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    return obj

def mesh(name,verts,faces,mat,bone=None):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=link(bpy.data.objects.new(name,me));
    if mat:me.materials.append(mat)
    smooth(ob);assign(ob,bone)
    return ob

def curve(name,points,radius,mat,bone=None):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=2;c.bevel_depth=radius;c.bevel_resolution=2;c.resolution_u=8
    s=c.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
    for p,co in zip(s.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    ob=link(bpy.data.objects.new(name,c));c.materials.append(mat);assign(ob,bone)
    return ob

def uv_sphere(name,location,scale,mat,bone=None,segments=32,rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=location)
    o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    relocate(o);o.data.materials.append(mat);smooth(o);assign(o,bone);return o

def ribbon(name,rows,mat,bone=None):
    n=len(rows[0]);v=[p for row in rows for p in row];f=[]
    for i in range(len(rows)-1):
        for j in range(n-1):a=i*n+j;f.append((a,a+1,a+n+1,a+n))
    return mesh(name,v,f,mat,bone)

def weights(obj, fn):
    for v in obj.data.vertices:
        co=obj.matrix_world@v.co
        for name,w in fn(co).items():
            if w>1e-5:
                g=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name);g.add([v.index],w,'REPLACE')

def loft(name,rows,mat,bone=None,segments=48):
    verts=[];faces=[]
    for z,rx,ry,cy in rows:
        for j in range(segments):
            a=2*math.pi*j/segments;verts.append((rx*math.sin(a),cy-ry*math.cos(a),z))
    for i in range(len(rows)-1):
        for j in range(segments):a=i*segments+j;b=i*segments+(j+1)%segments;faces.append((a,b,b+segments,a+segments))
    faces.extend([tuple(range(segments-1,-1,-1)),tuple((len(rows)-1)*segments+j for j in range(segments))])
    return mesh(name,verts,faces,mat,bone)

def tube(name,points,radii,mat,bone=None,segments=12):
    verts=[];faces=[]
    for i,(co,rad) in enumerate(zip(points,radii)):
        co=Vector(co);t=Vector(points[min(len(points)-1,i+1)])-Vector(points[max(0,i-1)])
        t.normalize();a=t.cross(Vector((0,1,0)))
        if a.length<.01:a=t.cross(Vector((1,0,0)))
        a.normalize();b=t.cross(a).normalized()
        rx,ry=(rad,rad) if isinstance(rad,(int,float)) else rad
        for j in range(segments):v=co+a*rx*math.cos(2*math.pi*j/segments)+b*ry*math.sin(2*math.pi*j/segments);verts.append(tuple(v))
    for i in range(len(points)-1):
        for j in range(segments):a=i*segments+j;b=i*segments+(j+1)%segments;faces.append((a,b,b+segments,a+segments))
    faces.extend([tuple(range(segments-1,-1,-1)),tuple((len(points)-1)*segments+j for j in range(segments))])
    return mesh(name,verts,faces,mat,bone)
