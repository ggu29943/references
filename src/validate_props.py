"""Reimport independent static weapon FBX files and verify dimensions and UVs."""
from pathlib import Path
import bpy,json,math
ROOT=Path(__file__).resolve().parents[1];results=[]
for path in sorted((ROOT/'output').glob('Caiheng_*.fbx')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    coords=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
    bounds={axis:[min(v[i] for v in coords),max(v[i] for v in coords)] for i,axis in enumerate('xyz')}
    r={'file':path.name,'triangles':sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons),'bounds_m':bounds,'missing_uv':[o.name for o in meshes if not o.data.uv_layers],'finite':all(math.isfinite(c) for p in coords for c in p)}
    r['pass']=bool(meshes) and r['finite'] and not r['missing_uv'] and not any(o.type=='ARMATURE' for o in bpy.context.scene.objects)
    if 'Sword' in path.stem:
        r['blade_length_m']=bounds['z'][1]
        r['pass']=r['pass'] and abs(r['blade_length_m']-2.5/3)<.001
    results.append(r)
(ROOT/'output'/'prop_validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
if len(results)!=5 or not all(r['pass'] for r in results):raise RuntimeError('Prop validation failed')
