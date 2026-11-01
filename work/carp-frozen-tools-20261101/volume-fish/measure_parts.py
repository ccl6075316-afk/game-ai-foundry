"""Read-only rest-shape part dimensions. No species acceptance is inferred.

blender --background --python measure_parts.py -- --blend fish.blend --profile fish.json --output parts.validation.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('blend', 'profile', 'output'):
        parser.add_argument('--' + key, required=True, type=Path)
    a = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    p = json.loads(a.profile.read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()), use_scripts=False)
    for rig in (o for o in bpy.context.scene.objects if o.type == 'ARMATURE'):
        rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    coords = {o.name: [o.matrix_world @ v.co for v in o.data.vertices] for o in objects}
    all_points = [v for points in coords.values() for v in points]
    span = max(v.x for v in all_points) - min(v.x for v in all_points)
    cm = p['real_length_cm'] / span
    parts = {}
    body = coords['Closed_body']
    nose = max(v.x for v in body)
    for o in objects:
        points = coords[o.name]
        lo = [min(v[i] for v in points) for i in range(3)]
        hi = [max(v[i] for v in points) for i in range(3)]
        parts[o.name] = {'rest_bbox_lwh_cm': [(b-a)*cm for a, b in zip(lo, hi)],
                         'source_u_range': [lo[0]+.5, hi[0]+.5], 'vertices': len(points),
                         'nose_to_anterior_x_percent_tl': (nose-hi[0])*cm/p['real_length_cm']*100}
    # Height above the actual body at each dorsal apex station, not fin bbox height.
    sys.path.insert(0, str(Path(__file__).parent))
    from measure_anatomy import cross_points
    dorsal_names = [name for name in coords if 'dorsal' in name.lower()]
    for name in dorsal_names:
        points = coords[name]
        tip = max(points, key=lambda v: v.z)
        section = cross_points(bpy.data.objects['Closed_body'], tip.x)
        if not section:
            raise ValueError('Missing body section at dorsal apex: ' + name)
        height = (tip.z-max(v[2] for v in section))*cm
        parts[name]['apex_above_local_body_cm'] = height
        parts[name]['apex_height_percent_tl'] = height/p['real_length_cm']*100
    report = {'schema_version': 1, 'command': 'volume.parts.measure', 'ok': True, 'status': 'done',
              'next_action': 'human_review', 'failures': [], 'style_visual_review': 'pending',
              'blend_sha256': sha(a.blend), 'profile_sha256': sha(a.profile), 'real_length_cm': p['real_length_cm'],
              'cm_per_unit': cm, 'parts': parts,
              'limitations': ['Bounding boxes are engineering dimensions, not anatomical lengths.',
                             'Dorsal apex above local body is a declared measurement proxy; literature fin-base definitions and tail TL convention may differ.',
                             'No inferred body-width, head-length, eye-pigment or pectoral-anterior-margin biological acceptance.']}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'output': str(a.output), 'dorsal_heights_cm': {n:parts[n]['apex_above_local_body_cm'] for n in dorsal_names}}))


if __name__ == '__main__':
    main()
