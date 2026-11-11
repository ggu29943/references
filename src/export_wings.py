"""Export wings as separate skeletal components for runtime visibility in Unreal."""
from pathlib import Path
import bpy,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_lods import export_fbx,normalize_weights,is_wing,triangle_count
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
reports=[]
for suffix,ratio in [('',1),('_LOD1',.45),('_LOD2',.20)]:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Yuan_Character.blend'))
    rig=bpy.data.objects['Yuan_Rig'];bpy.context.scene.frame_set(1)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.parent==rig and is_wing(o)]
    for o in objects:
        o.hide_set(False)
        if ratio<1:
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
            m=o.modifiers.new('Wing LOD reduction','DECIMATE');m.ratio=ratio;m.use_collapse_triangulate=True
            while o.modifiers[0]!=m:bpy.ops.object.modifier_move_up(modifier=m.name)
            bpy.ops.object.modifier_apply(modifier=m.name)
        check=normalize_weights(o,set(rig.data.bones.keys()))
        if check['invalid_vertices']:raise RuntimeError('Invalid wing weights')
    name='Yuan_Wings_Only'+suffix+'.fbx';export_fbx(OUT/name,rig,objects)
    reports.append({'file':name,'triangles':sum(triangle_count(o) for o in objects),'bones':len(rig.data.bones)})
(OUT/'wing_components.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports))
