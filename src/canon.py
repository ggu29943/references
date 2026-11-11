"""Enforce the explicit dimensions without leaving scaled armature transforms."""
from mathutils import Matrix, Vector

def is_wing(o):
    return o.get('part')=='optional_wings' or any(g.name.startswith('wing_') for g in o.vertex_groups)

def conform(model,arm):
    base=[o for o in model if not is_wing(o)]
    coords=[o.matrix_world@v.co for o in base for v in o.data.vertices]
    bottom=min(p.z for p in coords);top=max(p.z for p in coords)
    factor=1.70/(top-bottom);offset=-bottom*factor
    for o in model:
        o.data.transform(Matrix.Scale(factor,4),shape_keys=True)
        o.location*=factor;o.location.z+=offset
    arm.data.transform(Matrix.Translation((0,0,offset))@Matrix.Scale(factor,4))
    # Precisely place opposite feather tips 6 m apart after the body normalization.
    wings=[o for o in model if is_wing(o)]
    oldhalf=max(abs((o.matrix_world@v.co).x) for o in wings for v in o.data.vertices)
    anchor=.10*factor;stretch=(3-anchor)/(oldhalf-anchor)
    def wingx(x):return (1 if x>=0 else -1)*(anchor+(abs(x)-anchor)*stretch)
    for o in wings:
        inv=o.matrix_world.inverted()
        for v in o.data.vertices:
            p=o.matrix_world@v.co;p.x=wingx(p.x);v.co=inv@p
    # Changing only wing bone rest coordinates preserves the unchanged body scale.
    import bpy
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode='EDIT')
    for b in arm.data.edit_bones:
        if b.name.startswith('wing_'):
            b.head.x=wingx(b.head.x);b.tail.x=wingx(b.tail.x)
    bpy.ops.object.mode_set(mode='OBJECT')
    return {'character_height_m':1.70,'expanded_wingspan_m':6.0,'source_to_canon_scale':factor,'ground_offset_m':offset,'eye_catchlights':False,'clothing':'plain minimal layered daily robe','source':'docs/SOURCE_LORE.md'}
