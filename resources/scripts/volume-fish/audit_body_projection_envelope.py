"""Independent static body-envelope audit at every projected boundary breakpoint.

This reads finite triangles, excludes explicitly unowned parts, and reports the
whole top silhouette. It does not accept anatomy, a source fit, or a moving fish.
No dense mesh/pose cache is written. Registration and reference roles are inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from shapely import union_all
from shapely.geometry import LineString, Polygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE / 'portable')]
from compare_database_fish import read_obj, split_components
from glb_io import arrays, read_glb


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def body_triangles(entry):
    path = Path(entry['path']).resolve()
    if entry.get('sha256') != sha(path):
        raise ValueError(f'Input changed: {path}')
    selection = entry['selection']
    if path.suffix.lower() == '.obj':
        raw, groups = read_obj(path)
        faces = groups[selection['group']]
        if 'face_record' in selection:
            record_ref = selection['face_record']
            record_path = Path(record_ref['path'])
            if sha(record_path) != record_ref['sha256']:
                raise ValueError('Changed reference face ownership record')
            rows = json.loads(record_path.read_text())['items']
            record = next(row for row in rows if row['species'] == record_ref['species'])
            if record['reference_sha256'] != entry['sha256'] or record['group'] != selection['group']:
                raise ValueError('Reference ownership bound to another model/group')
            ids = record['face_ids_zero_based_within_group_triangulated_rows']
            if not ids or len(ids) != len(set(ids)) or min(ids) < 0 or max(ids) >= len(faces):
                raise ValueError('Invalid reference body face ownership')
            faces = faces[ids]
        elif 'component' in selection:
            faces = split_components(raw, faces)[selection['component']][0]
        vertices = np.column_stack([-raw[:, 1], raw[:, 2], raw[:, 0]])
        if entry.get('axes') != ['-Y', '+Z', '+X']:
            raise ValueError('OBJ audit requires an explicit supported axis registration')
        return vertices[faces]
    if path.suffix.lower() != '.glb':
        raise ValueError('Only GLB and explicitly registered OBJ are supported')
    doc, binary = read_glb(path)
    mode = selection['mode']
    result = []
    if mode == 'packed_roles':
        if len(doc['meshes']) != 1 or len(doc['meshes'][0]['primitives']) != 1:
            raise ValueError('Packed body ownership requires exactly one primitive')
        primitive = doc['meshes'][0]['primitives'][0]
        vertices = arrays(doc, binary, primitive['attributes']['POSITION'])
        indices = arrays(doc, binary, primitive['indices']).reshape(-1)
        parts = [p for p in doc['extras']['geometry_parts']
                 if p['role'] in selection['roles']]
        if not parts:
            raise ValueError('Empty body ownership selection')
        for part in parts:
            start, count = part['index_start'], part['index_count']
            result.append(vertices[indices[start:start + count].reshape(-1, 3)])
    elif mode == 'named_nodes':
        requested = set(selection['names'])
        found = set()
        parents = {child: parent for parent, node in enumerate(doc['nodes'])
                   for child in node.get('children', [])}
        for index, node in enumerate(doc['nodes']):
            if node.get('name') not in requested or 'mesh' not in node:
                continue
            # These authored sources have identity mesh/ancestor transforms.
            # Reject other spaces rather than silently measuring local geometry.
            current = index
            while True:
                ancestor = doc['nodes'][current]
                matrix = np.asarray(ancestor.get('matrix', np.eye(4).T.reshape(-1)))
                if not np.allclose(matrix, np.eye(4).T.reshape(-1), atol=1e-8):
                    raise ValueError('Nonidentity node matrix requires an explicit world adapter')
                for key, identity in [('translation', [0, 0, 0]),
                                      ('rotation', [0, 0, 0, 1]), ('scale', [1, 1, 1])]:
                    if not np.allclose(ancestor.get(key, identity), identity, atol=1e-8):
                        raise ValueError('Nonidentity node TRS requires an explicit world adapter')
                if current not in parents:
                    break
                current = parents[current]
            found.add(node['name'])
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                if primitive.get('mode', 4) != 4:
                    raise ValueError('Body primitive must contain triangles')
                vertices = arrays(doc, binary, primitive['attributes']['POSITION'])
                faces = arrays(doc, binary, primitive['indices']).reshape(-1, 3)
                result.append(vertices[faces])
        if found != requested:
            raise ValueError(f'Missing explicit body nodes: {requested - found}')
    else:
        raise ValueError('Unknown body ownership selector')
    return np.concatenate(result)


def project(triangles, axis=None):
    flat = triangles.reshape(-1, 3)
    if axis is None:
        nose = float(flat[:, 0].max())
        length = nose - float(flat[:, 0].min())
        axis = {'nose_x': nose, 'length': length,
                'basis': 'fin-excluded nose to posterior body cap; engineering axis'}
    nose, length = axis['nose_x'], axis['length']
    if length <= 0:
        raise ValueError('Nonpositive registration length')
    lateral_center = (flat[:, 2].min() + flat[:, 2].max()) / 2
    longitudinal_factor = axis.get('longitudinal_factor', 1.)
    if longitudinal_factor <= 0:
        raise ValueError('Nonpositive longitudinal body landmark map')
    points = np.stack([(nose - triangles[:, :, 0]) / length * longitudinal_factor,
                       (triangles[:, :, 2] - lateral_center) / length], axis=-1)
    polygons = []
    for triangle in points:
        polygon = Polygon(triangle)
        if polygon.area > 1e-16:
            polygons.append(polygon)
    if not polygons:
        raise ValueError('No nondegenerate projected body triangles')
    shape = union_all(polygons)
    if shape.is_empty or not shape.is_valid:
        raise ValueError('Invalid projected body union')
    return shape, axis


def boundary_stations(shape):
    polygons = [shape] if shape.geom_type == 'Polygon' else list(shape.geoms)
    return [float(x) for polygon in polygons
            for ring in [polygon.exterior, *polygon.interiors] for x, _ in ring.coords]


def span(shape, station):
    intersection = shape.intersection(LineString([(station, -100), (station, 100)]))
    if intersection.is_empty:
        return None
    bounds = intersection.bounds
    return float(bounds[1]), float(bounds[3])


def compare(before, candidate, reference):
    # Polygon unions include intersections of projected triangle edges. Their
    # boundary vertices contain every slope change of each outer envelope.
    lo = max(shape.bounds[0] for shape in (before, candidate, reference))
    hi = min(shape.bounds[2] for shape in (before, candidate, reference))
    if hi <= lo:
        raise ValueError('No common registered body interval')
    stations = sorted(set([lo, hi, *[x for shape in (before, candidate, reference)
                                    for x in boundary_stations(shape) if lo <= x <= hi]]))
    for lower, upper in zip(stations, stations[1:]):
        midpoint = (lower + upper) / 2
        if any(span(shape, midpoint) is None for shape in (before, candidate, reference)):
            raise ValueError(f'Empty body interval between {lower} and {upper}')
    rows = []
    for station in stations:
        spans = [span(shape, station) for shape in (before, candidate, reference)]
        if any(value is None for value in spans):
            raise ValueError(f'Empty body interval at {station}')
        widths = [upper - lower for lower, upper in spans]
        rows.append([station, *widths])
    values = np.asarray(rows)
    reference_max = float(values[:, 3].max())
    if reference_max <= 0:
        raise ValueError('Reference body has zero width')
    summary = {}
    for name, column in [('before', 1), ('candidate', 2), ('reference', 3)]:
        peak = int(np.argmax(values[:, column]))
        entry = {'Wmax_over_registered_length': float(values[peak, column]),
                 'peak_t_from_nose': float(values[peak, 0])}
        if name != 'reference':
            delta = abs(values[:, column] - values[:, 3])
            worst = int(np.argmax(delta))
            entry.update(max_abs_width_difference_over_reference_Wmax=float(delta[worst] / reference_max),
                         worst_difference_t=float(values[worst, 0]))
        summary[name] = entry
    return {'registration_overlap': [lo, hi], 'boundary_breakpoints': len(rows),
            'summary': summary,
            'columns': ['t_from_nose', 'before_W_over_L', 'candidate_W_over_L', 'reference_W_over_L'],
            'boundary_widths': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not any(output.is_relative_to(ROOT / relative)
               for relative in ('work', 'output', 'projects/fishing-2d/experiments')):
        raise ValueError('Audit output must be inside a declared artifact directory')
    config = json.loads(args.config.read_text())
    if output == args.config.resolve() or any(output == Path(config[role]['path']).resolve()
                                             for role in ['before', 'candidate', 'reference']):
        raise ValueError('Report must not overwrite an input')
    if output.exists():
        raise ValueError('Audit report already exists; use a distinct candidate revision')
    shapes, axes = {}, {}
    for role in ['before', 'candidate', 'reference']:
        triangles = body_triangles(config[role])
        shapes[role], axes[role] = project(triangles, config[role].get('axis'))
    report = {'kind': 'finite_static_whole_body_boundary_audit', 'ok': True,
              'species': config['species'], 'inputs': config,
              'checker_sha256': sha(Path(__file__)), 'registration': axes,
              **compare(shapes['before'], shapes['candidate'], shapes['reference']),
              'scope': 'Static finite geometry compared to raw declared artistic reference; no shape acceptance. '
                       'Every projected boundary slope breakpoint is included, with no dense sampling cache. '
                       'Does not judge biological identity, landmark registration, alpha coverage or motion.',
              'formal_acceptance': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['species', 'boundary_breakpoints', 'summary']}))


if __name__ == '__main__':
    main()
