"""Independent Blender FBX round-trip validation; prints JSON only after imports."""
import bpy,json,sys,math
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
paths=sorted((ROOT/'output').glob('Yuan_*.fbx'))
results=[]
for path in paths:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True,automatic_bone_orientation=False)
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    r={'file':path.name,'armatures':len(rigs),'meshes':len(meshes),'bones':[len(o.data.bones) for o in rigs],'shape_keys':{},'weights':{'unweighted':0,'nonnormalized':0,'over4':0,'unknown_bones':[]},'uv_missing':[],'actions':[]}
    coords=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
    r['world_bounds_m']={str(c):[min(v[c] for v in coords),max(v[c] for v in coords)] for c in range(3)}
    r['height_m']=r['world_bounds_m']['2'][1]-r['world_bounds_m']['2'][0]
    for o in rigs:r['armature_transform']={'scale':list(o.scale),'rotation_euler':list(o.rotation_euler),'root_names':[b.name for b in o.data.bones if not b.parent]}
    valid=set(rigs[0].data.bones) if rigs else set()
    valid_names=set(b.name for b in rigs[0].data.bones) if rigs else set()
    for o in meshes:
        if not o.data.uv_layers:r['uv_missing'].append(o.name)
        if o.data.shape_keys:r['shape_keys'][o.name]=[k.name for k in o.data.shape_keys.key_blocks]
        for v in o.data.vertices:
            gs=[g for g in v.groups if g.weight>1e-7]
            r['weights']['unweighted']+=not gs
            r['weights']['nonnormalized']+=bool(gs) and abs(sum(g.weight for g in gs)-1)>1e-4
            r['weights']['over4']+=len(gs)>4
        unknown=set(o.vertex_groups.keys())-valid_names
        if unknown:r['weights']['unknown_bones'].append({'mesh':o.name,'groups':sorted(unknown)})
    for a in bpy.data.actions:
        r['actions'].append({'name':a.name,'frame_range':list(a.frame_range),'fcurves':len(a.fcurves),'max_keyframes':max((len(f.keyframe_points) for f in a.fcurves),default=0)})
    # Compare evaluated coordinates between sampled animation frames.
    scene=bpy.context.scene
    def sample(frame):
        scene.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get();out=[]
        for o in meshes:
            eo=o.evaluated_get(dg);me=eo.to_mesh();out.extend(tuple(eo.matrix_world@v.co) for v in me.vertices);eo.to_mesh_clear()
        return out
    a=sample(1);b=sample(31)
    dis=[(Vector(x)-Vector(y)).length for x,y in zip(a,b)]
    r['animation_max_vertex_displacement_m']=max(dis,default=0)
    r['animation_moving_vertices']=sum(d>1e-6 for d in dis)
    r['nonfinite_evaluated']=sum(not all(math.isfinite(v) for v in p) for p in b)
    r['pass']=len(rigs)==1 and not any([r['weights']['unweighted'],r['weights']['nonnormalized'],r['weights']['over4'],r['weights']['unknown_bones'],r['uv_missing'],r['nonfinite_evaluated']]) and 1.6<r['height_m']<2.0 and r['animation_moving_vertices']>0
    results.append(r)
print('FBX_VALIDATION_JSON_BEGIN')
print(json.dumps(results,indent=2))
print('FBX_VALIDATION_JSON_END')

(ROOT/'output'/'fbx_roundtrip_validation.json').write_text(json.dumps(results,indent=2))
if not all(r['pass'] for r in results): raise RuntimeError('FBX round-trip validation failed')
