#!/usr/bin/env python3
"""Read-only actual-mesh fin-root contact diagnostic; run with Blender --background.

Blender --background --python check_fin_attachment.py -- \
  --blend fish.blend --profile species.json --output attachment.validation.json

Root IDs prefer the author's foundry_fin_source_t POINT attribute. Legacy models
fall back to their unchanged source-coordinate rest vertices; that fallback must
not be used after coordinate projection. Samples rest and one native animation
loop. It never saves a Blender model or claims a visual/anatomical acceptance.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_bvh(vertices, faces):
    return BVHTree.FromPolygons([Vector(v) for v in vertices], faces)


def distance(bvh, point, cm):
    near, normal, _, d = bvh.find_nearest(point)
    return d * cm * (1 if (point - near).dot(normal) >= 0 else -1)


def summarize(values):
    return {'min_signed_distance_cm': min(values), 'max_signed_distance_cm': max(values),
            'mean_signed_distance_cm': sum(values) / len(values), 'samples': len(values)}


def source_t(obj, fin, aspect):
    attribute = obj.data.attributes.get('foundry_fin_source_t')
    if attribute is not None:
        if attribute.domain != 'POINT' or len(attribute.data) != len(obj.data.vertices):
            raise ValueError('Invalid source-t POINT attribute: ' + obj.name)
        return [item.value for item in attribute.data], 'foundry_fin_source_t POINT attribute'
    if fin.get('root_attachment'):
        raise ValueError('Projected fin requires source-t attribute: ' + obj.name)
    delta = Vector(fin['tip']) - Vector(fin['anchor'])
    values = []
    for vertex in obj.data.vertices:
        u = vertex.co.x + .5
        v = fin['anchor'][1] + ((.5 - vertex.co.z / aspect) - fin['anchor'][1]) / fin.get('vertical_scale', 1)
        values.append((Vector((u, v)) - Vector(fin['anchor'])).dot(delta) / delta.length_squared)
    return values, 'Legacy unchanged-source rest-coordinate reconstruction'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['blend', 'profile', 'output']:
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--samples', type=int, default=18)
    parser.add_argument('--tolerance-cm', type=float, default=.10)
    parser.add_argument('--require-paired-contact', action='store_true', help='Gate all authored paired proximal bands, including profiles without root_attachment.')
    parser.add_argument('--max-penetration-cm', type=float, help='Optional maximum root-band embedding; production tolerance, not biological evidence.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if args.samples < 2 or args.tolerance_cm < 0 or not math.isfinite(args.tolerance_cm):
        parser.error('At least two samples and nonnegative finite gap tolerance required')
    if args.max_penetration_cm is not None and (not math.isfinite(args.max_penetration_cm) or args.max_penetration_cm < 0):
        parser.error('Maximum penetration must be nonnegative and finite')
    profile = json.loads(args.profile.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()), use_scripts=False)
    scene = bpy.context.scene
    rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
    body = bpy.data.objects['Closed_body']
    rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    meshes = [obj for obj in scene.objects if obj.type == 'MESH' and any(m.type == 'ARMATURE' for m in obj.modifiers)]
    vertices = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
    cm = profile['real_length_cm'] / (max(v.x for v in vertices) - min(v.x for v in vertices))
    selections = {}
    for fin in profile['fins']:
        for side in ([-1, 1] if fin['paired'] else [1]):
            name = fin['name'] + ('_left' if side < 0 else '_right' if fin['paired'] else '')
            obj = bpy.data.objects[name]
            t, method = source_t(obj, fin, 1 / profile['source_aspect_ratio'])
            cutoff = fin.get('root_attachment', {}).get('root_band', .05)
            ids = [i for i, value in enumerate(t) if value <= cutoff + 1e-7]
            if not ids:
                raise ValueError('Empty proximal fin-root selection: ' + name)
            idset = set(ids)
            edges = [(edge.vertices[0], edge.vertices[1]) for edge in obj.data.edges if all(i in idset for i in edge.vertices)]
            selections[name] = {'ids': ids, 'edges': edges, 'method': method, 'cutoff': cutoff,
                                'attachment_required': bool(fin.get('root_attachment')) or (args.require_paired_contact and fin['paired']), 'paired': fin['paired'], 'explicit_baseline':bool(fin.get('source_baseline'))}
    report = {'schema_version': 1, 'command': 'volume.fin.check-attachment', 'stage': 'validate',
              'status': 'done', 'next_action': 'human_review', 'ok': True, 'failures': [],
              'blend': str(args.blend.resolve()), 'blend_sha256': sha(args.blend),
              'profile': str(args.profile.resolve()), 'profile_sha256': sha(args.profile),
              'cm_per_unit': cm, 'tolerance_cm': args.tolerance_cm,
              'require_paired_contact': args.require_paired_contact, 'max_penetration_cm': args.max_penetration_cm,
              'method': 'Exact evaluated Closed_body triangle BVH signed nearest distances. Actual proximal root vertices plus 1/4,1/2,3/4 points on edges wholly in the root band. Negative means embedded. Positive above tolerance means exposed. No whole-mesh nearest-point shortcut.',
              'scope': 'Rest + native Blender clip; Godot four-action overlays require separate runtime skin audit.',
              'fins': {name: {'source_t_method': s['method'], 'root_band': s['cutoff'],
                              'root_vertex_indices': s['ids'], 'root_edges': len(s['edges']),
                              'attachment_required': s['attachment_required'], 'root_band_anatomy_limit': 'Full authored source_baseline distance band, frozen before projection.' if s['explicit_baseline'] else ('Proximal source-t band is meaningful for authored paired attachment gates only; unpaired free edges may also have t<=.05 and their band distances must not be called root gaps.' if not s['paired'] else 'Author-specified paired proximal band'), 'native_samples': []}
                       for name, s in selections.items()}}

    def sample(label, frame):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = body.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        bvh = make_bvh([body.matrix_world @ v.co for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons])
        evaluated.to_mesh_clear()
        for name, selection in selections.items():
            obj = bpy.data.objects[name]
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            coords = [obj.matrix_world @ v.co for v in mesh.vertices]
            points = [coords[i] for i in selection['ids']]
            for a, b in selection['edges']:
                points.extend(coords[a].lerp(coords[b], k / 4) for k in [1, 2, 3])
            values = [distance(bvh, point, cm) for point in points]
            intersection = None
            if not selection['paired']:
                all_values = [distance(bvh, point, cm) for point in coords]
                intersection = {'minimum_full_membrane_signed_distance_cm': min(all_values),
                                'maximum_full_membrane_signed_distance_cm': max(all_values),
                                'has_inside_and_outside_vertices': min(all_values) < -.01 and max(all_values) > .01,
                                'meaning': 'Inside and outside vertices on one connected membrane prove a body-surface crossing; this does not certify the anatomical base curve or absence of local free-edge gaps.'}
                if name.startswith('Caudal'):
                    max_x = max(v.co.x for v in obj.data.vertices)
                    cap_ids = [v.index for v in obj.data.vertices if v.co.x >= max_x - .00001]
                    cap_values = [distance(bvh, coords[i], cm) for i in cap_ids]
                    intersection['anterior_clipped_root_cap'] = {**summarize(cap_values), 'vertex_indices': cap_ids,
                        'all_within_tolerance': max(cap_values) <= args.tolerance_cm,
                        'selector': 'Maximum source-u vertical clipping cap of alpha-traced tail ROI; original rest X IDs frozen, not anchor-tip t.'}
            evaluated.to_mesh_clear()
            result = summarize(values)
            result.update({'frame': frame, 'all_roots_within_tolerance': max(values) <= args.tolerance_cm and (args.max_penetration_cm is None or min(values) >= -args.max_penetration_cm),
                           'entire_root_band_detached': min(values) > args.tolerance_cm})
            if intersection is not None: result['unpaired_intersection_evidence'] = intersection
            if label == 'rest':
                report['fins'][name]['rest'] = result
            else:
                report['fins'][name]['native_samples'].append(result)

    sample('rest', None)
    rig.data.pose_position = 'POSE'
    for i in range(args.samples):
        frame = scene.frame_start + (scene.frame_end - scene.frame_start) * i / max(1, args.samples - 1)
        scene.frame_set(int(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        sample('pose', frame)
    for name, fin in report['fins'].items():
        samples = [fin['rest']] + fin['native_samples']
        fin['summary'] = {'anatomical_root_gate_applicable': fin['attachment_required'], 'fully_detached_samples': sum(s['entire_root_band_detached'] for s in samples),
                          'worst_max_signed_distance_cm': max(s['max_signed_distance_cm'] for s in samples),
                          'all_required_root_samples_contact': all(s['all_roots_within_tolerance'] for s in samples)}
        if fin['attachment_required'] and not fin['summary']['all_required_root_samples_contact']:
            report['failures'].append({'kind': 'validation', 'code': 'fin_root_contact_failed', 'message': name,
                                       'worst_max_signed_distance_cm': fin['summary']['worst_max_signed_distance_cm']})
    report['ok'] = not report['failures']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': report['ok'], 'output': str(args.output), 'failures': report['failures']}))


if __name__ == '__main__':
    main()
