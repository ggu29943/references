"""Export independent Unreal FBX LOD variants without modifying the .blend.

Run from any directory:
    blender -b --factory-startup --python src/export_lods.py

Each level starts from the same source.  Meshes carrying shape keys and small
facial components are preserved; other meshes receive a pre-armature Collapse
Decimate modifier.  These are generated reduction candidates requiring visual
review in Unreal, not platform-certified budgets or a preconfigured UE asset.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'output' / 'Yuan_Character.blend'
OUTPUT = ROOT / 'output'
LEVELS = [('LOD1', 0.45), ('LOD2', 0.20)]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def triangle_count(obj):
    return sum(len(poly.vertices) - 2 for poly in obj.data.polygons)


def is_wing(obj):
    return (
        obj.get('part') == 'optional_wings'
        or obj.name.lower().startswith(('wing_', 'wings_'))
        or any(group.name.lower().startswith('wing_') for group in obj.vertex_groups)
    )


def preservation_reason(obj):
    if obj.data.shape_keys:
        return 'shape_keys'
    # Preserve fine facial edges even where they have no morph target.  Hair
    # happens to be weighted to head at its crown, but is still reducible.
    group_names = {group.name for group in obj.vertex_groups}
    if group_names == {'head'} and not obj.name.lower().startswith('hair'):
        return 'face_detail'
    return None


def normalize_weights(obj, valid_bones):
    trimmed_vertices = 0
    repaired_empty_vertices = 0
    for vertex in obj.data.vertices:
        entries = [(entry.group, entry.weight) for entry in vertex.groups]
        usable = [
            (index, weight) for index, weight in entries
            if obj.vertex_groups[index].name in valid_bones
            and math.isfinite(weight) and weight > 1e-8
        ]
        usable.sort(key=lambda entry: entry[1], reverse=True)
        if len(usable) > 4:
            trimmed_vertices += 1
        keep = usable[:4]
        keep_indices = {index for index, _ in keep}
        for index, _ in entries:
            if index not in keep_indices:
                obj.vertex_groups[index].remove([vertex.index])
        total = sum(weight for _, weight in keep)
        if total > 0:
            for index, weight in keep:
                obj.vertex_groups[index].add([vertex.index], weight / total, 'REPLACE')
        else:
            group = obj.vertex_groups.get('root') or obj.vertex_groups.new(name='root')
            group.add([vertex.index], 1.0, 'REPLACE')
            repaired_empty_vertices += 1
    invalid = 0
    max_influences = 0
    for vertex in obj.data.vertices:
        influences = list(vertex.groups)
        max_influences = max(max_influences, len(influences))
        if (
            not influences or len(influences) > 4
            or any(obj.vertex_groups[g.group].name not in valid_bones for g in influences)
            or any(not math.isfinite(g.weight) or g.weight < 0 for g in influences)
            or abs(sum(g.weight for g in influences) - 1.0) > 1e-4
        ):
            invalid += 1
    return {
        'invalid_vertices': invalid,
        'max_influences': max_influences,
        'vertices_trimmed_to_four': trimmed_vertices,
        'vertices_repaired_to_root': repaired_empty_vertices,
    }


def select_export(rig, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [rig] + list(objects):
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig


def export_fbx(path, rig, objects):
    select_export(rig, objects)
    bpy.ops.export_scene.fbx(
        filepath=str(path), use_selection=True,
        object_types={'ARMATURE', 'MESH'},
        apply_unit_scale=True, global_scale=1,
        axis_forward='-Y', axis_up='Z',
        # Applied decimation is stored in base topology.  Leaving modifiers
        # disabled here preserves original morph targets and the skin binding.
        use_mesh_modifiers=False, mesh_smooth_type='FACE',
        add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
        use_armature_deform_only=True,
        bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0,
        path_mode='COPY', embed_textures=True,
    )


def build_level(snapshot, level_name, ratio):
    bpy.ops.wm.open_mainfile(filepath=str(snapshot))
    scene = bpy.context.scene
    scene.frame_set(1)
    rig = bpy.data.objects.get('Yuan_Rig')
    if rig is None or rig.type != 'ARMATURE':
        raise RuntimeError('Source must contain the armature Yuan_Rig')
    objects = sorted(
        [obj for obj in scene.objects if obj.type == 'MESH' and obj.parent == rig],
        key=lambda obj: obj.name,
    )
    if not objects:
        raise RuntimeError('No character meshes parented to Yuan_Rig')
    valid_bones = set(rig.data.bones.keys())
    report = {
        'level': level_name,
        'collapse_ratio_non_face_meshes': ratio,
        'source_triangles_base': sum(triangle_count(o) for o in objects if not is_wing(o)),
        'source_triangles_winged': sum(triangle_count(o) for o in objects),
        'bones': len(rig.data.bones),
        'animation': rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None,
        'meshes': [],
    }
    original_pose_position = rig.data.pose_position
    rig.data.pose_position = 'REST'
    try:
        for obj in objects:
            reason = preservation_reason(obj)
            original_triangles = triangle_count(obj)
            if reason is None and original_triangles > 8:
                bpy.ops.object.select_all(action='DESELECT')
                obj.hide_viewport = False
                obj.hide_set(False)
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                modifier = obj.modifiers.new('Generated ' + level_name + ' reduction', 'DECIMATE')
                modifier.decimate_type = 'COLLAPSE'
                modifier.ratio = ratio
                modifier.use_collapse_triangulate = True
                # Apply before deformation, so no animation pose is baked into
                # vertex coordinates and the armature modifier remains intact.
                while obj.modifiers[0] != modifier:
                    bpy.ops.object.modifier_move_up(modifier=modifier.name)
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            weight_report = normalize_weights(obj, valid_bones)
            if weight_report['invalid_vertices']:
                raise RuntimeError(f'Invalid LOD skin weights on {obj.name}')
            if not any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers):
                raise RuntimeError(f'Skin modifier missing on {obj.name}')
            morphs = list(obj.data.shape_keys.key_blocks.keys()) if obj.data.shape_keys else []
            report['meshes'].append({
                'name': obj.name,
                'protected_reason': reason,
                'triangles_before': original_triangles,
                'triangles_after': triangle_count(obj),
                'vertices': len(obj.data.vertices),
                'morphs': morphs,
                **weight_report,
            })
    finally:
        rig.data.pose_position = original_pose_position
    scene.frame_set(1)
    base = [obj for obj in objects if not is_wing(obj)]
    report['triangles_base'] = sum(triangle_count(obj) for obj in base)
    report['triangles_winged'] = sum(triangle_count(obj) for obj in objects)
    report['actual_ratio_base'] = report['triangles_base'] / report['source_triangles_base']
    report['actual_ratio_winged'] = report['triangles_winged'] / report['source_triangles_winged']
    report['invalid_vertices'] = sum(row['invalid_vertices'] for row in report['meshes'])
    report['protected_meshes'] = sum(row['protected_reason'] is not None for row in report['meshes'])
    report['max_influences'] = max(row['max_influences'] for row in report['meshes'])
    report['files'] = []
    for variant, parts in [('Base', base), ('Winged', objects)]:
        path = OUTPUT / f'Yuan_{variant}_{level_name}.fbx'
        export_fbx(path, rig, parts)
        report['files'].append({'name': path.name, 'bytes': path.stat().st_size})
    print('LOD_COMPLETE', json.dumps({k: v for k, v in report.items() if k != 'meshes'}), flush=True)
    return report


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f'Build the character first: {SOURCE}')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Snapshot also prevents the two LODs from reading different revisions if
    # another build replaces the source while these exports are running.
    with tempfile.TemporaryDirectory(prefix='yuan_lod_') as temporary:
        snapshot = Path(temporary) / 'Yuan_Character.blend'
        shutil.copy2(SOURCE, snapshot)
        source_hash = sha256(snapshot)
        report = {
            'blender': bpy.app.version_string,
            'source': str(SOURCE.relative_to(ROOT)),
            'source_sha256': source_hash,
            'units': 'meters; FBX unit conversion enabled',
            'status': 'automatic LOD candidates; Unreal visual and deformation review pending',
            'policy': 'preserve morph meshes and head-bound non-hair face details; collapse other meshes; normalize to <=4 influences',
            'source_blend_saved': False,
            'levels': [build_level(snapshot, name, ratio) for name, ratio in LEVELS],
        }
    report['source_matches_snapshot_at_completion'] = SOURCE.exists() and sha256(SOURCE) == source_hash
    temporary_report = OUTPUT / 'lod_validation.json.tmp'
    temporary_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary_report, OUTPUT / 'lod_validation.json')
    print('LOD_DONE', str(OUTPUT / 'lod_validation.json'), flush=True)


if __name__ == '__main__':
    main()
