import bpy,sys,os,math,json,time
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import common,body,hair,garments,wings,rig,canon,wing_pose,weapon,weapon_plain
OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
model=[]
for mod in [body,hair,garments,wings]:
    print('BUILDING',mod.__name__,flush=True);model.extend(mod.build())
for o in model:
    if o.type=='CURVE':
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');common.assign(o,o.get('rigid_bone','head'))
    if o.type=='MESH':
        if o.name.startswith(('Upper lash ','Lower lid ','Outer lash flick ')):
            side=o.name.rsplit(' ',1)[-1];sg=1 if side=='l' else -1;cx=sg*.043
            o.shape_key_add(name='Basis');bk=o.shape_key_add(name='Blink_'+side.upper())
            for v in bk.data:
                t=(v.co.x-cx)/.031
                edge=1.581+sg*.002*t
                if o.name.startswith('Upper lash '):edge+=.0065*max(0,1-t*t)**.65
                elif o.name.startswith('Lower lid '):edge-=.0070*max(0,1-t*t)**.6
                else:edge=v.co.z
                thickness=max(-.001,min(.001,v.co.z-edge))
                v.co.z=1.581+sg*.002*t-.001*max(0,1-t*t)+thickness
                v.co.y=-.103+.006*min(1,abs(t))
        bpy.context.view_layer.objects.active=o
        for m in list(o.modifiers):
            if m.type!='ARMATURE':bpy.ops.object.modifier_apply(modifier=m.name)
        if not o.data.uv_layers:
            uv=o.data.uv_layers.new(name='UVMap')
            for p in o.data.polygons:
                for li in p.loop_indices:
                    v=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=((math.atan2(v.x,v.y)/(2*math.pi))%1,v.z/1.72)
        # Correct mesh orientation; loop normals are recalculated for FBX.
        if not o.data.shape_keys:
            bpy.context.view_layer.objects.active=o;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
arm=rig.build(model)
canon_report=canon.conform(model,arm)
idle_action=rig.animate(arm);idle_action.use_fake_user=True
fold_action=wing_pose.make_fold_action(arm)
props=weapon.build()
weapon.export_props(OUT)
plain_props=weapon_plain.build()
weapon_plain.export_props(OUT)
props+=plain_props
for o in props:o.hide_render=True;o.hide_set(True)
# Reference images remain packed as non-rendered image empties.
refcol=bpy.data.collections.new('REFERENCE · supplied images');scene.collection.children.link(refcol)
for fn in sorted((ROOT/'assets/reference').rglob('*.png')):
    img=bpy.data.images.load(str(fn),check_existing=True);img.pack()
    ob=bpy.data.objects.new('REF '+fn.stem,None);ob.empty_display_type='IMAGE';ob.data=img;ob.empty_display_size=1.72;ob.hide_render=True;ob.hide_viewport=True;refcol.objects.link(ob)
# Render stage excluded from export.
common.collection('STUDIO · excluded from export')
floor=common.material('Studio · blue slate',(.036,.054,.082,1),roughness=.8)
bpy.ops.mesh.primitive_plane_add(size=200);ground=bpy.context.object;ground.name='Studio floor';common.relocate(ground);ground.data.materials.append(floor);ground.location.z=-.001
world=bpy.data.worlds.new('Studio world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.40,.56,1);world.node_tree.nodes['Background'].inputs[1].default_value=.30;scene.world=world
for name,loc,power,size,color in [('Key',(1.8,-3,3.8),260,3,(1,.91,.85)),('Fill',(-2,-1.8,2),160,3,(.76,.85,1)),('Rim',(1,2,3),380,2,(.80,.88,1))]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);common.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Review Camera');cam=bpy.data.objects.new('Review Camera',camdata);common.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.lens=70
scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=24;scene.cycles.samples=40;scene.cycles.use_denoising=False;scene.cycles.max_bounces=6;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
wingobjs=[o for o in model if o.get('part')=='optional_wings' or any('wing' in g.name for g in o.vertex_groups)]
base=[o for o in model if o not in wingobjs]

def setcam(loc,target,scale,w,h):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale;scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100

def render(name,loc,target,scale,w,h,winged=False):
    for o in wingobjs:o.hide_render=not winged
    setcam(loc,target,scale,w,h);scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=arm

def fbx(name,obs):
    select([arm]+obs)
    bpy.ops.export_scene.fbx(filepath=str(OUT/name),use_selection=True,object_types={'ARMATURE','MESH'},apply_unit_scale=True,global_scale=1,axis_forward='-Y',axis_up='Z',use_mesh_modifiers=False,mesh_smooth_type='FACE',add_leaf_bones=False,primary_bone_axis='Y',secondary_bone_axis='X',use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,path_mode='COPY',embed_textures=True)
print('EXPORT',flush=True)
fbx('Yuan_Base.fbx',base);fbx('Yuan_Winged.fbx',model)
arm.animation_data.action=fold_action
for pb in arm.pose.bones:
    if pb.name.startswith('wing_'):pb.rotation_mode='QUATERNION'
scene.frame_set(1);fbx('Yuan_Wings_Fold.fbx',model)
arm.animation_data.action=idle_action
for pb in arm.pose.bones:
    if pb.name.startswith('wing_'):pb.rotation_mode='QUATERNION'
scene.frame_set(1)
select([arm]+model)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Yuan_Winged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_apply=False,export_skins=True,export_morph=True)
# Counts and skin validation record.
report={'weapon_variants':['image_reference','text_plain'],'weapon_blade_length_m':weapon.BLADE_LENGTH_M,'weapon_chi_conversion_provisional':True,'blender':bpy.app.version_string,'units':'meters','target':'Unreal Engine','status':'canonical character revision; UE validation pending','canon':canon_report,'bones':len(arm.data.bones),'objects':len(model),'triangles_base':sum(len(p.vertices)-2 for o in base for p in o.data.polygons),'triangles_winged':sum(len(p.vertices)-2 for o in model for p in o.data.polygons),'materials':len(set(m.name for o in model for m in o.data.materials if m)),'skin_errors':[],'meshes':[]}
for o in model:
    if o.type!='MESH':continue
    bad=sum(1 for v in o.data.vertices if not v.groups or abs(sum(g.weight for g in v.groups)-1)>1e-4 or len(v.groups)>4)
    if bad:report['skin_errors'].append({'mesh':o.name,'bad_vertices':bad})
    report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'morphs':list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else []})
# Test evaluated idle pose and an explicit arm-lift pose.
scene.frame_set(61);dg=bpy.context.evaluated_depsgraph_get();report['nonfinite_vertices']=0
for o in model:
    me=o.evaluated_get(dg).to_mesh()
    report['nonfinite_vertices']+=sum(1 for v in me.vertices if not all(math.isfinite(c) for c in v.co))
    o.evaluated_get(dg).to_mesh_clear()
scene.frame_set(1)
# Check an explicit 20-degree upper-arm rotation affects actual skinned geometry.
arm_obj=next(o for o in model if o.name=='Arm l')
dg=bpy.context.evaluated_depsgraph_get();ev=arm_obj.evaluated_get(dg);me=ev.to_mesh();before=[v.co.copy() for v in me.vertices];ev.to_mesh_clear()
pb=arm.pose.bones['upperarm_l'];original=pb.rotation_euler.copy();pb.rotation_euler.z-=math.radians(20);bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get();ev=arm_obj.evaluated_get(dg);me=ev.to_mesh();report['arm_lift_test']={'rotation_degrees':20,'max_vertex_displacement_m':max((v.co-before[i]).length for i,v in enumerate(me.vertices)),'finite':all(math.isfinite(c) for v in me.vertices for c in v.co)};ev.to_mesh_clear();pb.rotation_euler=original;bpy.context.view_layer.update()
# Measure articulated folded geometry while retaining all bone lengths.
arm.animation_data.action=None
wing_pose.set_fold(arm,1)
dg=bpy.context.evaluated_depsgraph_get();foldcoords=[]
for o in wingobjs:
    ev=o.evaluated_get(dg);me=ev.to_mesh();foldcoords.extend(ev.matrix_world@v.co for v in me.vertices);ev.to_mesh_clear()
report['folded_wing_bounds_m']={axis:[min(p[i] for p in foldcoords),max(p[i] for p in foldcoords)] for i,axis in enumerate('xyz')}
report['wing_bone_length_max_error_m']=max(abs((pb.tail-pb.head).length-pb.bone.length) for pb in arm.pose.bones if pb.name.startswith('wing_'))
wing_pose.set_fold(arm,0)
arm.animation_data.action=idle_action
for pb in arm.pose.bones:
    if pb.name.startswith('wing_'):pb.rotation_mode='QUATERNION'
scene.frame_set(1)
(OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
for o in wingobjs:o.hide_render=True
setcam((2.4,-6,2.1),(0,0,.85),1.95,1000,1300)
select([arm])
arm.show_in_front=False
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_location=Vector((0,0,.9))
            area.spaces.active.region_3d.view_distance=2.8
            area.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
            area.spaces.active.region_3d.view_perspective='ORTHO'
            area.spaces.active.shading.color_type='MATERIAL'
material_manifest=[]
for m in sorted({m for o in model+props for m in o.data.materials if m},key=lambda m:m.name):
    p=m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
    material_manifest.append({'name':m.name,'base_color_linear':list(p.inputs['Base Color'].default_value) if p else list(m.diffuse_color),'roughness':p.inputs['Roughness'].default_value if p else m.roughness,'metallic':p.inputs['Metallic'].default_value if p else m.metallic,'specular_ior_level':p.inputs['Specular IOR Level'].default_value if p else None,'emission_strength':p.inputs['Emission Strength'].default_value if p else 0})
(OUT/'materials.json').write_text(json.dumps(material_manifest,ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Yuan_Character.blend'),compress=True)
if '--no-render' not in args:
    render('preview_portrait.png',(.42,-3,1.65),(0,-.02,1.51),.52,800,900)
    render('preview_front.png',(0,-5,1.04),(0,0,.87),1.90,900,1260)
    render('preview_winged.png',(1.5,-9,2.7),(0,0,1.0),6.65,1600,800,True)
    arm.animation_data.action=None;wing_pose.set_fold(arm,1)
    render('preview_folded.png',(2.6,6,2.5),(0,.4,.9),2.9,1100,1100,True)
    wing_pose.set_fold(arm,0);arm.animation_data.action=idle_action
    for pb in arm.pose.bones:
        if pb.name.startswith('wing_'):pb.rotation_mode='QUATERNION'
    scene.frame_set(1)
    render('preview_back.png',(-1.8,5,1.9),(0,0,.90),1.95,900,1260)
    # Visual diagnostics use the same scene; source and exports remain in rest/idle.
    scene.eevee.taa_render_samples=24
    for o in model:
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:
                if k.name.startswith('Blink_'):k.value=1
    render('check_blink.png',(.15,-3,1.62),(0,-.02,1.56),.36,500,550)
    for o in model:
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:
                if k.name.startswith('Blink_'):k.value=0
    arm.pose.bones['upperarm_l'].rotation_euler.z-=math.radians(20)
    render('check_arm_pose.png',(0,-5,1.04),(0,0,.87),1.90,600,840)
    for o in model:o.hide_render=True
    shown=[o for o in props if o.get('variant')=='image_reference']
    for o in shown:
        o.hide_set(False);o.hide_render=False
        if o.get('prop_kind')=='sword':o.rotation_euler=(0,math.pi,0);o.location=(-.18,0,.9)
        elif o.get('prop_kind')=='sheath':o.rotation_euler=(0,math.pi,0);o.location=(.12,.015,.9)
        else:o.rotation_euler=(0,0,0);o.location=(-.10,-.015,1.12)
    setcam((.4,-4,1.45),(0,0,.59),1.29,900,1200)
    scene.render.filepath=str(OUT/'preview_weapon.png');bpy.ops.render.render(write_still=True)
    setcam((-.1,-3,1.03),(-.12,0,1.0),.40,1000,900)
    scene.render.filepath=str(OUT/'preview_weapon_detail.png');bpy.ops.render.render(write_still=True)
print('DONE',json.dumps({k:v for k,v in report.items() if k!='meshes'}),flush=True)
