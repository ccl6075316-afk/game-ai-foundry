#!/usr/bin/env python3
"""Blender exact BVH checks for task-only Godot CPU-skinned four-action exports.

Blender --background --python check_runtime_fin_attachment.py -- \
  --export /tmp/skin/export.validation.json --output runtime-attachment.validation.json
Does not modify models. Coordinates in exporter are carrier-local meters.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tolerance-cm', type=float, default=.10)
    parser.add_argument('--max-penetration-cm', type=float, help='Optional production limit for root-band embedding.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if not math.isfinite(args.tolerance_cm) or args.tolerance_cm < 0:
        parser.error('Gap tolerance must be nonnegative and finite')
    if args.max_penetration_cm is not None and (not math.isfinite(args.max_penetration_cm) or args.max_penetration_cm < 0):
        parser.error('Maximum penetration must be nonnegative and finite')
    export = json.loads(args.export.read_text())
    if hashlib.sha256(Path(export['model']).read_bytes()).hexdigest() != export['model_sha256']:
        raise ValueError('Runtime model changed after export')
    report = {'schema_version': 1, 'command': 'volume.fin.check-runtime-attachment', 'stage': 'validate',
              'status': 'done', 'next_action': 'human_review', 'ok': True, 'failures': [],
              'model': export['model'], 'model_sha256': export['model_sha256'],
              'export_report': str(args.export.resolve()),
              'export_report_sha256': hashlib.sha256(args.export.read_bytes()).hexdigest(),
              'root_selection': export['selection'], 'controller_source': export['controller_source'],
              'controller_sha256': export['controller_sha256'], 'exhibit_sha256': export['exhibit_sha256'],
              'motion_config_sha256': export['motion_config_sha256'], 'export_script_sha256': export['export_script_sha256'],
              'engine_version': export['engine_version'], 'sample_limit': export['sample_limit'],
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'tolerance_cm': args.tolerance_cm, 'max_penetration_cm': args.max_penetration_cm, 'body_triangles': export['body_triangles'],
              'method': 'Actual Godot exhibit four-action controller bone poses and imported GLB skin inverse-bind matrices. CPU linear-blend-skin body triangles and root vertices/edge points; exact posed body triangle BVH signed nearest distances in carrier-local meters, converted to cm. This measures root contact, not tank containment.',
              'samples': [], 'summary': {}}
    for sample in export['samples']:
        path = Path(sample['posed_mesh_json'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != sample['sha256']:
            raise ValueError('Posed export hash mismatch: ' + str(path))
        data = json.loads(path.read_text())
        if export.get('expected_fins'):
            if set(data['roots']) != set(export['expected_fins']):
                raise ValueError('Missing/extra fins in runtime sample: ' + str(path))
            if any(not r['points_m'] or r['vertex_count'] < 2 for r in data['roots'].values()):
                raise ValueError('Empty or incomplete basal selection: ' + str(path))
        vertices = [Vector(v) for v in data['body_vertices_m']]
        faces = data['body_triangles']
        signed_volume = sum(vertices[a].dot(vertices[b].cross(vertices[c])) for a, b, c in faces) / 6
        if abs(signed_volume) < 1e-9:
            raise ValueError('Posed body volume is zero; cannot orient closed surface')
        # Godot front faces use clockwise winding, opposite Blender BVH cross normals.
        # Determine actual orientation from signed closed volume rather than assume.
        if signed_volume < 0:
            faces = [[c, b, a] for a, b, c in faces]
        bvh = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
        result = {'action': sample['action'], 'seconds': sample['seconds'], 'posed_mesh_sha256': sample['sha256'], 'source_signed_body_volume_m3': signed_volume, 'body_winding_reversed_for_outward_normals': signed_volume < 0, 'fins': {}}
        for name, root in data['roots'].items():
            distances = []
            for coords in root['points_m']:
                point = Vector(coords)
                near, normal, _, distance = bvh.find_nearest(point)
                distances.append(distance * 100 * (1 if (point - near).dot(normal) >= 0 else -1))
            result['fins'][name] = {'root_vertices': root['vertex_count'], 'root_edges': root['edge_count'],
                                   'sample_points': len(distances), 'min_signed_distance_cm': min(distances),
                                   'max_signed_distance_cm': max(distances),
                                   'all_roots_within_tolerance': max(distances) <= args.tolerance_cm and (args.max_penetration_cm is None or min(distances) >= -args.max_penetration_cm),
                                   'entire_root_band_detached': min(distances) > args.tolerance_cm}
        report['samples'].append(result)
    counts = {a:sum(s['action']==a for s in report['samples']) for a in set(s['action'] for s in report['samples'])}
    expected = ({'Static':1, **{a:16 for a in ['Swim','Turn','Ascend','Dive']}, **{'Transition:'+a:4 for a in ['Swim','Turn','Ascend','Dive']}}
                if export.get('expected_fins') else {a:8 for a in ['Swim','Turn','Ascend','Dive']})
    if export.get('motion_range_revision') == 1:
        expected.update({'Range:'+a:16 for a in ['Neutral','WideSlow','WideFast','FinsOnly','BodyOnly']})
        expected.update({'RangeTransition:'+a:4 for a in ['Neutral','WideSlow','WideFast','FinsOnly']})
    if export.get('fin_membrane_revision')==1:
        expected['Native']=25
        expected.update({'Clearance:'+a:64 for a in ['MixedLow','MixedMid','Independent','MaxDense']})
        expected['Clearance:ControlSweep']=32
    if counts != expected:
        raise ValueError('Incomplete runtime pose coverage: ' + str(counts))
    report['coverage'] = {'poses':counts,'expected_fins':export.get('expected_fins'), 'all_expected_fins_present_in_every_sample':True}
    for name in report['samples'][0]['fins']:
        values = [sample['fins'][name] for sample in report['samples']]
        report['summary'][name] = {'samples': len(values), 'fully_detached_samples': sum(v['entire_root_band_detached'] for v in values),
                                   'failed_contact_samples': sum(not v['all_roots_within_tolerance'] for v in values),
                                   'minimum_signed_distance_cm': min(v['min_signed_distance_cm'] for v in values),
                                   'maximum_signed_distance_cm': max(v['max_signed_distance_cm'] for v in values)}
        if report['summary'][name]['failed_contact_samples']:
            report['failures'].append({'kind': 'validation', 'code': 'runtime_fin_root_contact_failed', 'message': name,
                                       'failed_samples': report['summary'][name]['failed_contact_samples']})
    report['ok'] = not report['failures']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': report['ok'], 'summary': report['summary'], 'output': str(args.output)}))
    if not report['ok']:
        sys.exit(1)


if __name__ == '__main__':
    main()
