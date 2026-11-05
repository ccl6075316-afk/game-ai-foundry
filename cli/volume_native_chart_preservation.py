"""Preserve accepted native mouth charts across explicit GLB layouts.

Reads the actual current GLB. A full oral chart, the complete shared lip rim and
its skin neighbourhood are mandatory even for a conservative anterior domain.
This is material preservation evidence, never shape or user acceptance.
"""
from collections import Counter, defaultdict
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    '_native_chart_glb_io', ROOT / 'resources/scripts/volume-fish/portable/glb_io.py')
_io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_io)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def path_of(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def load_bound(ref):
    path = path_of(ref['path'])
    require(sha(path) == ref['sha256'], 'Stale native-chart evidence')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _material(doc, binary, index):
    """Resolve image/sampler ownership instead of comparing texture table IDs."""
    material = copy.deepcopy(doc['materials'][index])

    def resolve(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.endswith('Texture') and isinstance(item, dict) and 'index' in item:
                    texture = doc['textures'][item['index']]
                    image = doc['images'][texture['source']]
                    require('bufferView' in image and 'uri' not in image,
                            'Native chart must embed its image')
                    view = doc['bufferViews'][image['bufferView']]
                    start = view.get('byteOffset', 0)
                    raw = binary[start:start + view['byteLength']]
                    rgba = np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA'))
                    sampler = doc.get('samplers', [])[texture['sampler']] if 'sampler' in texture else {}
                    item['index'] = {
                        'embedded_sha256': hashlib.sha256(raw).hexdigest(),
                        'RGBA_sha256': hashlib.sha256(rgba.tobytes()).hexdigest(),
                        'size': [int(rgba.shape[1]), int(rgba.shape[0])],
                        'sampler': sampler,
                        'texture_extensions': texture.get('extensions', {}),
                    }
                else:
                    resolve(item)
        elif isinstance(value, list):
            for item in value:
                resolve(item)
    resolve(material)
    require('baseColorTexture' in material.get('pbrMetallicRoughness', {}),
            'Missing native base-colour image')
    return material


def extract_chart(path):
    """Return all body/oral primitives, without a caller-selected face subset."""
    doc, binary, digest = _io.read_glb_snapshot(path_of(path))
    parts = []

    def append(part_id, role, primitive, positions, uv, faces):
        require(role in ('body_skin', 'mouth') and len(positions) == len(uv), 'Invalid body chart')
        require(np.isfinite(positions).all() and np.isfinite(uv).all(), 'Nonfinite chart')
        require(faces.size and faces.min() >= 0 and faces.max() < len(positions), 'Invalid chart faces')
        parts.append({'id': part_id, 'role': role,
                      'positions': positions.tolist(), 'uv': uv.tolist(),
                      'indices': faces.tolist(),
                      'material_signature': _material(doc, binary, primitive['material'])})

    if doc.get('extras', {}).get('geometry_parts'):
        layout = 'packed_anterior'
        require(len(doc['meshes']) == 1 and len(doc['meshes'][0]['primitives']) == 1,
                'Ambiguous packed chart ownership')
        primitive = doc['meshes'][0]['primitives'][0]
        positions = _io.arrays(doc, binary, primitive['attributes']['POSITION'])
        uv = _io.arrays(doc, binary, primitive['attributes']['TEXCOORD_0'])
        faces = _io.arrays(doc, binary, primitive['indices']).reshape(-1, 3)
        for index, part in enumerate(doc['extras']['geometry_parts']):
            if part['role'] not in ('body_skin', 'mouth'):
                continue
            lo, count = part['vertex_start'], part['vertex_count']
            start, size = part['index_start'], part['index_count']
            require(start % 3 == 0 and size % 3 == 0, 'Unaligned body ownership')
            append('part:' + str(index), part['role'], primitive,
                   positions[lo:lo + count], uv[lo:lo + count],
                   faces[start // 3:(start + size) // 3] - lo)
    else:
        layout = 'ordinary_multimesh'
        nodes = [node for node in doc['nodes'] if node.get('name') == 'Closed_body']
        require(len(nodes) == 1, 'Missing or ambiguous complete body node')
        node = nodes[0]
        require('matrix' not in node and node.get('translation', [0, 0, 0]) == [0, 0, 0]
                and node.get('rotation', [0, 0, 0, 1]) == [0, 0, 0, 1]
                and node.get('scale', [1, 1, 1]) == [1, 1, 1], 'Unsupported body transform')
        for index, primitive in enumerate(doc['meshes'][node['mesh']]['primitives']):
            name = doc['materials'][primitive['material']].get('name', '').lower()
            role = 'mouth' if 'oral' in name or 'mouth' in name else 'body_skin'
            append('surface:' + str(index), role, primitive,
                   _io.arrays(doc, binary, primitive['attributes']['POSITION']),
                   _io.arrays(doc, binary, primitive['attributes']['TEXCOORD_0']),
                   _io.arrays(doc, binary, primitive['indices']).reshape(-1, 3))
    require({part['role'] for part in parts} == {'body_skin', 'mouth'}, 'Incomplete body/oral ownership')
    require(len({part['id'] for part in parts}) == len(parts), 'Duplicate chart part')
    return {'layout': layout, 'model_sha256': digest, 'parts': parts}


def shared_rim(chart):
    edges = defaultdict(list)
    for part in chart['parts']:
        pos = np.asarray(part['positions'])
        for face_index, face in enumerate(part['indices']):
            triangle = pos[face]
            normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
            length = np.linalg.norm(normal)
            require(length > 1e-15, 'Degenerate chart triangle')
            normal /= length
            for a, b in zip(face, np.roll(face, -1)):
                key = tuple(sorted(tuple(np.rint(pos[v] * 1e7).astype(np.int64)) for v in (a, b)))
                edges[key].append({'part': part['id'], 'role': part['role'], 'face': face_index,
                                   'vertices': [int(a), int(b)], 'normal_y': float(normal[1])})
    rim, degree = [], Counter()
    for key, owners in edges.items():
        if {owner['role'] for owner in owners} != {'body_skin', 'mouth'}:
            continue
        require(len(owners) == 2 and key[0] != key[1], 'Nonmanifold skin/oral seam')
        oral = next(owner for owner in owners if owner['role'] == 'mouth')
        classification = 'upper' if oral['normal_y'] < -.05 else 'lower' if oral['normal_y'] > .05 else 'commissure'
        rim.append({'owners': owners, 'classification': classification})
        degree.update(key)
    counts = {name: sum(edge['classification'] == name for edge in rim)
              for name in ('upper', 'lower', 'commissure')}
    require(rim and counts['upper'] and counts['lower'] and all(v == 2 for v in degree.values()),
            'Incomplete closed upper/lower native lip seam')
    return rim, counts


def accepted_baseline(model, source_image, release, species):
    """Snapshot an actually installed accepted model before it is replaced."""
    chart = extract_chart(model)
    chart.update(kind='accepted_native_chart_snapshot', species=species,
                 source_sha256=sha(path_of(source_image)),
                 accepted_material_scope='complete body and integrated mouth chart',
                 release_record={'path': str(path_of(release)), 'sha256': sha(path_of(release))})
    _check_release(chart, species)
    shared_rim(chart)
    return chart


def _check_release(baseline, species):
    release = load_bound(baseline['release_record'])
    require(release.get('user_acceptance') is True or bool(release.get('user_acceptance_date')),
            'Baseline release has no user acceptance')
    rows = [row for row in release['fish'] if row['species'] == species]
    require(len(rows) == 1 and rows[0]['model']['sha256'] == baseline['model_sha256'],
            'Baseline is not the accepted release model')


def protected_domain(chart, domain):
    rim, counts = shared_rim(chart)
    faces = set()
    scope = domain['scope']
    require(scope in ('complete_body', 'complete_anterior'), 'Unknown preservation scope')
    rim_vertices = defaultdict(set)
    for edge in rim:
        for owner in edge['owners']:
            if owner['role'] == 'body_skin':
                rim_vertices[owner['part']].update(owner['vertices'])
    if scope == 'complete_anterior':
        cut = float(domain['all_vertices_x_gte'])
        oral_x = [p[0] for part in chart['parts'] if part['role'] == 'mouth' for p in part['positions']]
        require(np.isfinite(cut) and cut <= min(oral_x), 'Anterior domain excludes the oral depth')
    for part in chart['parts']:
        pos = np.asarray(part['positions'])
        for index, face in enumerate(part['indices']):
            # Every oral face and all skin triangles incident on any rim vertex
            # are protected, irrespective of the declared conservative X plane.
            if (scope == 'complete_body' or part['role'] == 'mouth'
                    or min(pos[face, 0]) >= cut or rim_vertices[part['id']].intersection(face)):
                faces.add((part['id'], index))
    vertices = {(part['id'], int(vertex)) for part in chart['parts']
                for index, face in enumerate(part['indices']) if (part['id'], index) in faces
                for vertex in face}
    return faces, vertices, rim, counts


def _cycle(vertices):
    vertices = tuple(vertices)
    return min(vertices[i:] + vertices[:i] for i in range(3))


def validate_preserved_domain(report, candidates, species):
    require(report['ok'] is True and report['species'] == species, 'Wrong preservation identity')
    current_path = path_of(candidates['model']['path'])
    require(sha(current_path) == candidates['model']['sha256'] == report['model_sha256'], 'Wrong current model')
    source = candidates['source_image']
    require(sha(path_of(source['path'])) == source['sha256'] == report['source_sha256'], 'Wrong actual source image')
    baseline = load_bound(report['baseline_native_chart'])
    require(baseline['kind'] == 'accepted_native_chart_snapshot' and baseline['species'] == species
            and baseline['source_sha256'] == report['source_sha256']
            and baseline['accepted_material_scope'] == 'complete body and integrated mouth chart', 'Wrong accepted chart')
    _check_release(baseline, species)
    current = extract_chart(current_path)
    require(current['layout'] == report['layout'] == baseline['layout'], 'Wrong explicit chart layout')
    domain = report.get('preservation_domain', {'scope': 'complete_body'})
    old_faces, old_vertices, old_rim, _ = protected_domain(baseline, domain)
    new_faces, new_vertices, new_rim, counts = protected_domain(current, domain)
    old_parts = {part['id']: part for part in baseline['parts']}
    new_parts = {part['id']: part for part in current['parts']}
    if 'vertex_correspondence' in report:
        correspondence = load_bound(report['vertex_correspondence'])
        require(correspondence['baseline_model_sha256'] == baseline['model_sha256']
                and correspondence['model_sha256'] == current['model_sha256'], 'Wrong source-row correspondence')
        rows = correspondence['pairs']
        mapping = {(a, int(b)): (c, int(d)) for a, b, c, d in rows}
        require(len(mapping) == len(rows), 'Repeated baseline identity')
    else:
        require(domain['scope'] == 'complete_body' and set(old_parts) == set(new_parts), 'Missing anterior row identity')
        mapping = {vertex: vertex for vertex in old_vertices}
    require(set(mapping) == old_vertices and set(mapping.values()) == new_vertices
            and len(mapping) == len(set(mapping.values())), 'Incomplete or noninjective protected row map')
    for (old_part, old_row), (new_part, new_row) in mapping.items():
        a, b = old_parts[old_part], new_parts[new_part]
        require(a['role'] == b['role'] and a['material_signature'] == b['material_signature'], 'Changed protected material/image')
        require(a['uv'][old_row] == b['uv'][new_row], 'Changed protected native UV')

    def triangles(chart, selected, transform):
        return Counter((part['role'], _cycle(tuple(transform((part['id'], int(v))) for v in face)))
                       for part in chart['parts'] for index, face in enumerate(part['indices'])
                       if (part['id'], index) in selected)
    require(triangles(baseline, old_faces, mapping.__getitem__) == triangles(current, new_faces, lambda v: v),
            'Changed or incomplete protected oriented face domain')

    def seam_tokens(rim, transform):
        return Counter(tuple(sorted((owner['role'], tuple(sorted(transform((owner['part'], v)) for v in owner['vertices'])))
                                    for owner in edge['owners'])) for edge in rim)
    require(seam_tokens(old_rim, mapping.__getitem__) == seam_tokens(new_rim, lambda v: v), 'Changed complete native rim ownership')
    claimed = report['actual_3d_rim_transport']
    require(claimed['upper_edges'] == counts['upper'] and claimed['lower_edges'] == counts['lower'], 'Wrong actual rim counts')
    require(report['auxiliary_color_contribution_changes'] == 0, 'Changed native lip colour ownership')
    if domain['scope'] == 'complete_body':
        require(report['complete_body_chart_preserved'] is True, 'Missing complete-body preservation declaration')
    else:
        require(report['complete_body_chart_preserved'] is False and report['complete_anterior_chart_preserved'] is True,
                'Anterior preservation mislabelled as whole-body preservation')
    return {'protected_faces': len(old_faces), 'protected_vertices': len(old_vertices), 'rim_counts': counts}


def check_preserved_domain(report, candidates, species, fail, label):
    try:
        validate_preserved_domain(report, candidates, species)
    except (AssertionError, ValueError, KeyError, OSError, TypeError, IndexError):
        fail('invalid_preserved_native_lip_chart', label)
