import bpy, math
from mathutils import Vector, Euler
from body import FINGER_POINTS
from wings import BONE_POINTS

def build(objects):
    bpy.ops.object.select_all(action='DESELECT')
    data=bpy.data.armatures.new('Yuan_Skeleton');rig=bpy.data.objects.new('Yuan_Rig',data);bpy.context.scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,head,tail,parent=None,deform=True):
        b=data.edit_bones.new(name);b.head=head;b.tail=tail;b.use_deform=deform
        if parent:b.parent=data.edit_bones[parent]
        return b
    bone('root',(0,0,0),(0,0,.15));bone('pelvis',(0,0,.88),(0,0,1.01),'root')
    bone('spine_01',(0,0,1.01),(0,0,1.15),'pelvis');bone('spine_02',(0,0,1.15),(0,0,1.27),'spine_01');bone('spine_03',(0,0,1.27),(0,0,1.39),'spine_02');bone('neck_01',(0,0,1.39),(0,0,1.465),'spine_03');bone('head',(0,0,1.465),(0,0,1.69),'neck_01')
    for s,side in [(1,'l'),(-1,'r')]:
        bone('clavicle_'+side,(0,0,1.355),(s*.17,0,1.35),'spine_03');bone('upperarm_'+side,(s*.17,0,1.35),(s*.285,-.004,1.12),'clavicle_'+side);bone('lowerarm_'+side,(s*.285,-.004,1.12),(s*.36,-.01,.925),'upperarm_'+side);bone('hand_'+side,(s*.36,-.01,.925),(s*.38,-.015,.872),'lowerarm_'+side)
        for fn in ['thumb','index','middle','ring','pinky']:
            pts=FINGER_POINTS[(fn,side)]
            for i in range(3):bone(f'{fn}_{i+1:02}_{side}',pts[i],pts[i+1],'hand_'+side if i==0 else f'{fn}_{i:02}_{side}')
        bone('thigh_'+side,(s*.075,0,.91),(s*.083,-.012,.52),'pelvis');bone('calf_'+side,(s*.083,-.012,.52),(s*.083,0,.11),'thigh_'+side);bone('foot_'+side,(s*.083,0,.11),(s*.083,-.083,.045),'calf_'+side);bone('ball_'+side,(s*.083,-.083,.045),(s*.083,-.135,.045),'foot_'+side)
        w=BONE_POINTS[side]
        for i in range(3):bone(f'wing_{i+1:02}_{side}',w[i],w[i+1],'spine_03' if i==0 else f'wing_{i:02}_{side}')
        sl=[(s*.27,0,1.16),(s*.32,0,.91),(s*.35,0,.65)]
        for i in range(2):bone(f'sleeve_{side}_{i+1:02}',sl[i],sl[i+1],'upperarm_'+side if i==0 else f'sleeve_{side}_01')
        for i,(a,b) in enumerate(zip([1.10,.80,.50],[.80,.50,.22])):bone(f'belt_{side}_{i+1:02}',(s*.075,-.12,a),(s*.075,-.12,b),'pelvis' if i==0 else f'belt_{side}_{i:02}')
    for side in ['front','back','l','r']:
        zs=[1.07,.76,.43,.12];rads=[.13,.20,.26,.31]
        def pt(i):return (rads[i] if side=='l' else (-rads[i] if side=='r' else 0),(-1 if side=='front' else 1)*[.11,.145,.19,.25][i] if side in ['front','back'] else 0,zs[i])
        for i in range(3):bone(f'skirt_{side}_{i+1:02}',pt(i),pt(i+1),'pelvis' if i==0 else f'skirt_{side}_{i:02}')
    for side,x,y in [('back',0,.10),('l',.115,-.015),('r',-.115,-.015)]:
        zs=[1.57,1.36,1.15,.96]
        for i in range(3):bone(f'hair_{side}_{i+1:02}',(x,y,zs[i]),(x,y,zs[i+1]),'head' if i==0 else f'hair_{side}_{i:02}')
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;data.display_type='STICK'
    valid=set(data.bones.keys())
    for o in objects:
        if o.type!='MESH':continue
        if not o.vertex_groups:
            name=o.get('rigid_bone','head');g=o.vertex_groups.new(name=name);g.add(list(range(len(o.data.vertices))),1,'REPLACE')
        unknown=set(o.vertex_groups.keys())-valid
        if unknown:raise ValueError(f'{o.name}: unknown bones {unknown}')
        mod=o.modifiers.new('Yuan skeletal deformation','ARMATURE');mod.object=rig;o.parent=rig
        # Normalize imported procedural weights, retain <=4 strongest influences.
        for v in o.data.vertices:
            gs=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-7],key=lambda p:-p[1])
            for idx,w in gs[4:]:o.vertex_groups[idx].remove([v.index])
            gs=gs[:4];total=sum(w for _,w in gs)
            if total>0:
                for idx,w in gs:o.vertex_groups[idx].add([v.index],w/total,'REPLACE')
            else:
                g=o.vertex_groups.get('root') or o.vertex_groups.new(name='root');g.add([v.index],1,'REPLACE')
    return rig

def animate(rig):
    scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1;scene.frame_end=121
    for b in rig.pose.bones:b.rotation_mode='QUATERNION' if b.name.startswith('wing_') else 'XYZ'
    for frame in [1,31,61,91,121]:
        t=(frame-1)/120*math.tau
        channels={'spine_02':(.008*math.sin(t),0,.005*math.sin(t)),'neck_01':(-.006*math.sin(t),.01*math.sin(t),.008*math.sin(t)),'hair_back_01':(.015*math.sin(t+.3),0,0),'hair_back_02':(.022*math.sin(t+.6),0,0)}
        for s,side in [(1,'l'),(-1,'r')]:
            channels['wing_01_'+side]=(.012*math.sin(t),0,s*.014*math.sin(t));channels['sleeve_'+side+'_01']=(.012*math.sin(t+.2),0,0)
        for name,rot in channels.items():
            b=rig.pose.bones[name]
            if name.startswith('wing_'):
                b.rotation_quaternion=Euler(rot).to_quaternion();b.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=name)
            else:
                b.rotation_euler=rot;b.keyframe_insert(data_path='rotation_euler',frame=frame,group=name)
    rig.animation_data.action.name='Yuan_Idle_4s'
    scene.frame_set(1)
    return rig.animation_data.action
