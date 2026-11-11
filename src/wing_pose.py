"""Bone-only folding for the shoulder / elbow / wrist chains; no mesh shrinking."""
import bpy
from mathutils import Vector, Matrix

def set_fold(rig, amount):
    amount=max(0,min(1,amount))
    for side,sg in [('l',1),('r',-1)]:
        directions=[Vector((sg*.30,.95,-.08)),Vector((-sg*.23,-.96,-.15)),Vector((sg*.15,.94,-.30))]
        for i,direction in enumerate(directions):
            pb=rig.pose.bones[f'wing_{i+1:02}_{side}'];pb.rotation_mode='QUATERNION';rest=pb.bone
            restq=rest.matrix_local.to_quaternion()
            targetq=(rest.tail_local-rest.head_local).rotation_difference(direction)@restq
            q=restq.slerp(targetq,amount)
            if i==0:
                head=pb.parent.matrix@pb.parent.bone.matrix_local.inverted()@rest.head_local
            else:head=rig.pose.bones[f'wing_{i:02}_{side}'].tail.copy()
            matrix=q.to_matrix().to_4x4();matrix.translation=head
            pb.matrix=matrix
            bpy.context.view_layer.update()

def make_fold_action(rig):
    previous=rig.animation_data.action if rig.animation_data else None
    rig.animation_data_create();rig.animation_data.action=bpy.data.actions.new('Yuan_Wings_Fold_Open_4s')
    for frame,amount in [(1,0),(31,1),(61,1),(91,0),(121,0)]:
        bpy.context.scene.frame_set(frame)
        set_fold(rig,amount)
        for side in ['l','r']:
            for i in range(3):
                pb=rig.pose.bones[f'wing_{i+1:02}_{side}'];pb.rotation_mode='QUATERNION'
                # matrix assignment already computed the local basis, retain it across mode conversion.
                pb.rotation_quaternion=pb.matrix_basis.to_quaternion()
                pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
    action=rig.animation_data.action;action.use_fake_user=True
    rig.animation_data.action=previous
    for side in ['l','r']:
        for i in range(3):
            pb=rig.pose.bones[f'wing_{i+1:02}_{side}'];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(1,0,0,0)
    bpy.context.scene.frame_set(1)
    return action
