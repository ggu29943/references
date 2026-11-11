"""Caiheng / 裁衡: a plain matte straight sword and its unmarked sheath.

The fictional world's chi has not been specified. CHI_METERS is an explicit
working conversion only; the canonical blade length is 2 chi and 5 cun.
Static prop meshes are independent of Yuan's skeletal mesh.
"""
from pathlib import Path
import math
import bpy
import bmesh
from mathutils import Matrix
from common import collection, material, mesh

CHI_METERS = 1.0 / 3.0
BLADE_LENGTH_CHI = 2.5
BLADE_LENGTH_M = BLADE_LENGTH_CHI * CHI_METERS
HILT_LENGTH_M = .18


def _mat(name, color):
    m = material(name, (*color, 1), metallic=0, roughness=.95)
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Specular IOR Level'].default_value = 0
    p.inputs['Coat Weight'].default_value = 0
    p.inputs['Emission Strength'].default_value = 0
    return m


def _section(w, d, blade=False):
    if blade:
        e = min(.00022, d*.15)
        return [(0,-d),(.70*w,-.62*d),(w,-e),(w,e),(.70*w,.62*d),
                (0,d),(-.70*w,.62*d),(-w,e),(-w,-e),(-.70*w,-.62*d)]
    # The same ten-point topology joins an oval, unwrapped grip to the blade.
    angles = [-math.pi/2,-math.pi/4,-.12,.12,math.pi/4,
              math.pi/2,3*math.pi/4,math.pi-.12,math.pi+.12,5*math.pi/4]
    return [(w*math.cos(a),d*math.sin(a)) for a in angles]


def _finish(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data); bm.free()
    uv = obj.data.uv_layers.new(name='UVMap')
    for p in obj.data.polygons:
        for li in p.loop_indices:
            v = obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv = ((math.atan2(v.y,v.x)/(2*math.pi))%1,
                             (v.z+HILT_LENGTH_M)/(BLADE_LENGTH_M+HILT_LENGTH_M))
        p.use_smooth = False
    obj['part'] = 'caiheng_prop'
    obj['variant'] = 'text_plain'
    obj['canonical_name'] = '裁衡'
    obj['blade_length_chi'] = BLADE_LENGTH_CHI
    obj['provisional_chi_meters'] = CHI_METERS
    obj['blade_length_m'] = BLADE_LENGTH_M
    obj['units_note'] = '1 chi = 1/3 metre is a provisional production conversion, not established lore.'
    obj['pivot_note'] = 'Blade/handle junction at origin; hand-grip centre is (0, 0, -0.09 m).'
    obj['surface_note'] = 'Matte frost colour, zero specular and emission; no markings or ornaments.'
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bevel=obj.modifiers.new('Minute edge softening','BEVEL')
    bevel.width=.00012; bevel.segments=2; bevel.limit_method='ANGLE'
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return obj


def build():
    """Return two unparented, unweighted static meshes; never clear the scene."""
    collection('PROPS · Caiheng')
    frost = _mat('Caiheng · quiet frost iron',(.78,.82,.85))
    white = _mat('Caiheng · plain white sheath',(.89,.90,.92))
    rows=[(-HILT_LENGTH_M,.0105,.0060,False),
          (-HILT_LENGTH_M+.004,.0120,.0070,False),
          (-.135,.0115,.0066,False),(-.045,.0115,.0066,False),
          (-.008,.0120,.0060,False),(0,.0135,.0021,True),
          (.006,.0135,.0021,True),(.36,.0129,.0019,True),
          (BLADE_LENGTH_M-.085,.0114,.0016,True),
          (BLADE_LENGTH_M-.018,.0039,.0007,True)]
    v=[]; f=[]; n=10
    for z,w,d,blade in rows:
        v.extend((x,y,z) for x,y in _section(w,d,blade))
    for i in range(len(rows)-1):
        for j in range(n):
            a=i*n+j;b=i*n+(j+1)%n;f.append((a,b,b+n,a+n))
    f.append(tuple(reversed(range(n))))
    tip=len(v);v.append((0,0,BLADE_LENGTH_M))
    for j in range(n):f.append(((len(rows)-1)*n+j,(len(rows)-1)*n+(j+1)%n,tip))
    sword=_finish(mesh('Caiheng_Sword',v,f,frost))
    sword['prop_kind']='sword'
    sword['one_piece']=True
    sword['grip_center_local_m']=(0,0,-.09)

    # Closed tip, hollow mouth and continuous walls; no throat collar or fittings.
    # The cavity is geometrically present instead of painted black.
    slen=BLADE_LENGTH_M+.015
    outer=[(0,.017,.0060),(.012,.017,.0060),
           (slen-.090,.0155,.0053),(slen-.018,.0075,.0040),
           (slen,.0020,.0020)]
    inner=[(0,.0146,.0034),(.012,.0146,.0034),
           (slen-.090,.0126,.0028),(slen-.020,.0024,.0010)]
    verts=[];faces=[];n=16
    for z,w,d in outer+inner:
        for j in range(n):
            a=2*math.pi*j/n
            # A softly rounded rectangle reads as a fitted plain scabbard.
            x=w*math.copysign(abs(math.cos(a))**.55,math.cos(a))
            y=d*math.copysign(abs(math.sin(a))**.70,math.sin(a))
            verts.append((x,y,z))
    for i in range(len(outer)-1):
        for j in range(n):
            a=i*n+j;b=i*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    offset=len(outer)*n
    for i in range(len(inner)-1):
        for j in range(n):
            a=offset+i*n+j;b=offset+i*n+(j+1)%n
            faces.append((a,a+n,b+n,b))
    for j in range(n):
        nxt=(j+1)%n;faces.append((j,offset+j,offset+nxt,nxt))
    faces.append(tuple((len(outer)-1)*n+j for j in range(n)))
    faces.append(tuple(reversed([offset+(len(inner)-1)*n+j for j in range(n)])))
    sheath=_finish(mesh('Caiheng_Sheath',verts,faces,white))
    sheath['prop_kind']='sheath';sheath['cavity_present']=True
    sheath.location.x=.075
    sword.name='Caiheng_Text_Sword';sheath.name='Caiheng_Text_Sheath'
    return [sword,sheath]


def export_props(out):
    """Export canonical local origins, then restore all scene selections/transforms."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    props=[o for o in bpy.context.scene.objects if o.get('part')=='caiheng_prop' and o.get('variant')=='text_plain']
    if not props:
        raise RuntimeError('Call weapon.build() before weapon.export_props().')
    old_selection=list(bpy.context.selected_objects)
    old_active=bpy.context.view_layer.objects.active
    matrices={o:o.matrix_world.copy() for o in props}
    hidden={o:(o.hide_viewport,o.hide_get()) for o in props}
    try:
        for obj in props:
            bpy.ops.object.select_all(action='DESELECT')
            obj.hide_viewport=False;obj.hide_set(False);obj.select_set(True)
            bpy.context.view_layer.objects.active=obj;obj.matrix_world=Matrix.Identity(4)
            name='Caiheng_Text_Sword' if obj.get('prop_kind')=='sword' else 'Caiheng_Text_Sheath'
            bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,
                object_types={'MESH'},global_scale=1,apply_unit_scale=True,
                axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,
                mesh_smooth_type='FACE',bake_anim=False,path_mode='COPY')
            bpy.ops.export_scene.gltf(filepath=str(out/(name+'.glb')),use_selection=True,
                export_format='GLB',export_animations=False,export_apply=True)
            obj.matrix_world=matrices[obj]
    finally:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in props:
            obj.matrix_world=matrices[obj]
            obj.hide_viewport,obj_hide=hidden[obj];obj.hide_set(obj_hide)
        for obj in old_selection:
            if obj.name in bpy.context.view_layer.objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=old_active
    return [out/(name+ext) for name in ('Caiheng_Text_Sword','Caiheng_Text_Sheath') for ext in ('.fbx','.glb')]
