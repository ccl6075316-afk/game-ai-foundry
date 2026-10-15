"""Read-only native fish cross-section audit; no mesh/handoff writes.

blender --background --python measure_anatomy.py -- --blend fish.blend --profile profile.json --output report.json
Anatomical station assignments and source ratios remain operator responsibilities.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cross_points(obj, x):
    """Plane/edge intersections in world coordinates, native rest mesh only."""
    points = []
    for edge in obj.data.edges:
        a, b = [obj.matrix_world @ obj.data.vertices[i].co for i in edge.vertices]
        if abs(a.x - x) < 1e-8:
            points.append(tuple(a))
        if (a.x - x) * (b.x - x) < 0:
            points.append(tuple(a.lerp(b, (x - a.x) / (b.x - a.x))))
    return list({tuple(round(value, 10) for value in point) for point in points})


def envelope(points, factor):
    if not points:
        return None
    return {
        'width_cm': (max(p[1] for p in points) - min(p[1] for p in points)) * factor,
        'height_cm': (max(p[2] for p in points) - min(p[2] for p in points)) * factor,
        'top_z_cm': max(p[2] for p in points) * factor,
        'bottom_z_cm': min(p[2] for p in points) * factor,
    }


def single_loop_perimeter(points, factor):
    """Only for a star-convex single body-section loop; not overlapping shells."""
    if len(points) < 3:
        return None
    cy = sum(p[1] for p in points) / len(points)
    cz = sum(p[2] for p in points) / len(points)
    ordered = sorted(points, key=lambda p: math.atan2(p[2] - cz, p[1] - cy))
    return sum(math.hypot(a[1] - b[1], a[2] - b[2]) for a, b in zip(ordered, ordered[1:] + ordered[:1])) * factor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blend', required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--stations', help='Optional comma-separated source-image u stations')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    native, profile_path = Path(args.blend).resolve(), Path(args.profile).resolve()
    profile = json.loads(profile_path.read_text())
    revision = profile.get('rest_shape_revision', {})
    try:
        station_set = {float(row[0]) for key in ['stations', 'vertical_stations'] for row in revision.get(key, [])}
        if args.stations is not None:
            values = args.stations.split(',')
            if not values or any(not value.strip() for value in values):
                parser.error('--stations must contain a nonempty comma-separated list')
            station_set.update(float(value) for value in values)
    except (ValueError, TypeError, IndexError):
        parser.error('Stations must be numeric source-image coordinates')
    if not station_set:
        station_set.update(float(row[0]) for row in profile.get('body', {}).get('sections', []))
    if not station_set or any(not math.isfinite(u) or not 0 <= u <= 1 for u in station_set):
        parser.error('At least one finite station in the source-image range [0, 1] is required')
    bpy.ops.wm.open_mainfile(filepath=str(native), use_scripts=False)
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    factor = float(profile['real_length_cm']) / (max(p.x for p in points) - min(p.x for p in points))
    hulls = [obj for obj in objects if obj.name in ['Closed_body', 'Frontal_head_overlay', 'Cephalofoil']]
    rows = []
    for u in sorted(station_set):
        combined, components = [], {}
        for obj in hulls:
            section = cross_points(obj, u - .5)
            combined.extend(section)
            data = envelope(section, factor)
            if data:
                if obj.name == 'Closed_body':
                    data['single_loop_perimeter_cm'] = single_loop_perimeter(section, factor)
                components[obj.name] = data
        row = {'u': u, 'outer_envelope_cm': envelope(combined, factor), 'components': components}
        width_row = next((r for r in revision.get('stations', []) if abs(r[0] - u) < 1e-9), None)
        vertical_row = next((r for r in revision.get('vertical_stations', []) if abs(r[0] - u) < 1e-9), None)
        targets = {}
        if width_row:
            targets['width_cm'] = 2 * width_row[2] * factor
        if vertical_row:
            targets['height_cm'] = (vertical_row[4] - vertical_row[3]) / profile['source_aspect_ratio'] * factor
        if targets and row['outer_envelope_cm']:
            row['profile_scenario_targets_cm'] = targets
            row['difference_from_profile_cm'] = {key: row['outer_envelope_cm'][key] - value for key, value in targets.items()}
        rows.append(row)
    missing = [row['u'] for row in rows if row['outer_envelope_cm'] is None]
    finite = all(math.isfinite(value) for row in rows if row['outer_envelope_cm'] is not None for value in row['outer_envelope_cm'].values())
    failures = []
    if missing:
        failures.append({'kind': 'validation', 'code': 'missing_station_intersection', 'message': 'Requested stations have no body/head cross-section: ' + ', '.join(str(u) for u in missing)})
    if not finite:
        failures.append({'kind': 'validation', 'code': 'nonfinite_section', 'message': 'Native cross-section measurement contains nonfinite values.'})
    passed = bool(rows) and not failures
    report = {
        'schema_version': 1, 'command': 'volume.anatomy.measure', 'ok': passed,
        'status': 'done' if passed else 'failed', 'next_action': 'human_review' if passed else 'fix_input',
        'blend': str(native), 'blend_sha256': sha(native), 'profile_sha256': sha(profile_path),
        'target_total_length_cm': profile['real_length_cm'], 'cm_per_unit': factor,
        'method': 'Native rest-mesh world-space edge/plane intersections at X=u-.5. Visible body/head/cephalofoil envelope; paired-fin spans excluded. Closed_body perimeter orders single star-convex contour points; no circle approximation and no mixed-shell perimeter.',
        'sections': rows, 'anatomy_acceptance': 'pending',
        'limitations': ['u is an image coordinate; it is not an anatomical landmark unless documented separately.', 'Profile targets may be published ranges, derived scenarios or artistic unknowns; a matching target is not biological acceptance.', 'Finite values and target agreement do not verify fin-root connection, silhouette or mouth anatomy.'],
        'missing_stations': missing, 'failures': failures,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': passed, 'output': str(output), 'sections': len(rows), 'missing_stations': missing}))
    if not passed:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
