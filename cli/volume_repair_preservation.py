"""Narrow Caudal-repair evidence contracts; no physical algorithms or limits.

Accepted, unchanged domains can retain their review after historical media is
retired.  Current GLB data is still independently compared with the pre-install
accepted snapshot.  This module never treats an arbitrary report's ``ok`` as a
substitute for that comparison.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import io
import json
import re
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'resources/scripts/volume-fish/portable'))
from glb_io import arrays, read_glb

PRESERVED_STAGES = frozenset(('head', 'mouth', 'eyes', 'skin'))
TAIL_NAMES = frozenset(('Caudal', 'Caudal_mesh'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical(value):
    if isinstance(value, float):
        return 0.0 if value == 0 else value
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    return value


def digest(value):
    raw = json.dumps(_canonical(value), sort_keys=True, separators=(',', ':'),
                     allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def bound(ref):
    require(isinstance(ref, dict) and ref.get('path') and ref.get('sha256'),
            'Missing bound artifact')
    path = Path(ref['path'])
    path = path if path.is_absolute() else ROOT / path
    require(path.is_file() and sha(path) == ref['sha256'], 'Stale bound artifact: ' + str(path))
    return path


def load(ref):
    return json.loads(bound(ref).read_text(encoding='utf-8-sig'))


def _node_graph(doc):
    parents = {child: node.get('name') for node in doc['nodes']
               for child in node.get('children', [])}
    rows = []
    for index, node in enumerate(doc['nodes']):
        row = dict(name=node.get('name'), parent=parents.get(index), mesh='mesh' in node,
                   translation=node.get('translation', [0, 0, 0]),
                   rotation=node.get('rotation', [0, 0, 0, 1]),
                   scale=node.get('scale', [1, 1, 1]))
        if 'matrix' in node:
            row = dict(name=row['name'], parent=row['parent'], mesh=row['mesh'], matrix=node['matrix'])
        rows.append(row)
    # Ordinary exports legitimately use the same label for a bone and its mesh.
    # Compare the complete multiset, including parent, role and transform.
    require(all(r['name'] for r in rows), 'Named node identities required')
    return sorted(rows, key=lambda r: r['name'])


def inspect_model(path):
    """Read every actual partition, including parts not named by the contract."""
    doc, binary = read_glb(path)
    parts, sampling = {}, []
    packed = doc.get('extras', {}).get('geometry_parts')
    mesh_nodes = [n for n in doc['nodes'] if 'mesh' in n]
    if packed:
        require(len(mesh_nodes) == 1 and len(doc['meshes'][mesh_nodes[0]['mesh']]['primitives']) == 1,
                'Unsupported packed partition layout')
    for node in mesh_nodes:
        names = [doc['nodes'][j]['name'] for j in doc['skins'][node['skin']]['joints']]
        for surface, primitive in enumerate(doc['meshes'][node['mesh']]['primitives']):
            require(primitive.get('mode', 4) == 4 and not primitive.get('targets') and
                    not primitive.get('extensions') and not node.get('weights'),
                    'Unreviewed primitive/morph drawing behavior')
            require(set(primitive['attributes']) ==
                    {'POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0'},
                    'Unreviewed extra drawing attribute')
            attrs = {k: arrays(doc, binary, v) for k, v in primitive['attributes'].items()}
            require(all(k in attrs for k in ('POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0')),
                    'Incomplete static/skin streams')
            require(all(np.isfinite(v).all() for v in attrs.values()), 'Nonfinite attribute')
            weights = attrs['WEIGHTS_0']
            require((weights >= 0).all() and (abs(weights.sum(axis=1) - 1) < 1e-5).all(),
                    'Invalid skin weights')
            faces = arrays(doc, binary, primitive['indices']).reshape(-1, 3)
            require(set(faces.flat) == set(range(len(attrs['POSITION']))), 'Unreferenced/invalid vertex rows')
            if packed:
                coverage = np.zeros(len(faces), dtype=int)
                groups = []
                for part in packed:
                    start = part['index_start'] // 3
                    end = (part['index_start'] + part['index_count']) // 3
                    require(start < end <= len(faces), 'Invalid partition range')
                    coverage[start:end] += 1
                    key = (part['source_node'], int(part.get('source_surface', 0)))
                    require(key[0] not in TAIL_NAMES or part['role'] == 'fin', 'Caudal is not a fin')
                    groups.append((key, faces[start:end]))
                require((coverage == 1).all(), 'Partitions omit or overlap actual faces')
            else:
                groups = [((node['name'], surface), faces)]
            for key, selected in groups:
                require(key not in parts, 'Duplicate anatomical partition')
                rows = {}
                for index in np.unique(selected):
                    js = attrs['JOINTS_0'][index]
                    require((js >= 0).all() and (js < len(names)).all(), 'Invalid joint slots')
                    named = {}
                    for joint, weight in zip(js, weights[index]):
                        if weight > 0:
                            name = names[int(joint)]
                            named[name] = named.get(name, 0.0) + float(weight)
                    rows[int(index)] = (tuple(map(float, attrs['POSITION'][index])),
                                        tuple(map(float, attrs['NORMAL'][index])),
                                        tuple(map(float, attrs['TEXCOORD_0'][index])),
                                        tuple(sorted(named.items())))
                triangles = []
                for face in selected:
                    tri = tuple(rows[int(i)] for i in face)
                    triangles.append(min(tri, tri[1:] + tri[:1], tri[2:] + tri[:2]))
                geometry = []
                for tri in triangles:
                    tri = tuple(row[:3] for row in tri)
                    geometry.append(min(tri, tri[1:] + tri[:1], tri[2:] + tri[:2]))
                parts[key] = dict(signature=digest(sorted(triangles)),
                                  geometry=digest(sorted(geometry)), triangles=len(triangles),
                                  material=primitive.get('material', 0),
                                  stock_signature=hashlib.sha256(repr(sorted(triangles)).encode()).hexdigest())
                if key[0] not in TAIL_NAMES:
                    sampling.append((primitive.get('material', 0), attrs['TEXCOORD_0'][selected]))
    rig = [dict(joint_names=[doc['nodes'][j]['name'] for j in skin['joints']],
                inverse_bind=arrays(doc, binary, skin['inverseBindMatrices']).tolist())
           for skin in doc.get('skins', [])]
    clips = []
    for clip in doc.get('animations', []):
        channels = []
        for channel in clip['channels']:
            sampler = clip['samplers'][channel['sampler']]
            target = channel['target']
            channels.append(dict(node=doc['nodes'][target['node']]['name'], path=target['path'],
                                 interpolation=sampler.get('interpolation', 'LINEAR'),
                                 input=arrays(doc, binary, sampler['input']).tolist(),
                                 output=arrays(doc, binary, sampler['output']).tolist()))
        clips.append(dict(name=clip.get('name', ''), channels=sorted(channels, key=lambda r: (r['node'], r['path']))))
    images = []
    for image in doc.get('images', []):
        view = doc['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        images.append(np.asarray(Image.open(io.BytesIO(binary[offset:offset + view['byteLength']])).convert('RGBA')))
    return dict(doc=doc, parts=parts, sampling=sampling, images=images, graph=_node_graph(doc),
                rig=digest(rig), animation=digest(sorted(clips, key=lambda r: r['name'])))


def _materials(doc):
    result = copy.deepcopy(doc.get('materials', []))
    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.endswith('Texture') and isinstance(item, dict) and 'index' in item:
                    texture = doc['textures'][item['index']]
                    sampler = copy.deepcopy(doc.get('samplers', [])[texture['sampler']]) if 'sampler' in texture else {}
                    sampler.pop('name', None)
                    sampler.setdefault('wrapS', 10497)
                    sampler.setdefault('wrapT', 10497)
                    item['index'] = dict(image=texture['source'], sampler=sampler,
                                         texture_extensions=texture.get('extensions', {}))
                    item.setdefault('texCoord', 0)
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    for material in result:
        material.pop('name', None)
        material.setdefault('alphaMode', 'OPAQUE')
        material.setdefault('alphaCutoff', .5)
        material.setdefault('doubleSided', False)
        material.setdefault('emissiveFactor', [0, 0, 0])
        pbr = material.setdefault('pbrMetallicRoughness', {})
        for key, value in [('baseColorFactor', [1, 1, 1, 1]), ('metallicFactor', 1), ('roughnessFactor', 1)]:
            pbr.setdefault(key, value)
        visit(material)
    return result


def _texture_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith('Texture') and isinstance(item, dict) and 'index' in item:
                yield item
            else:
                yield from _texture_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _texture_refs(item)


def _touches_changed_texel(triangle, xs, ys):
    """Conservative complete nearest-texel footprint, including triangle edges."""
    low = np.floor(triangle.min(axis=0))
    high = np.floor(triangle.max(axis=0))
    selected = (xs >= low[0]) & (xs <= high[0]) & (ys >= low[1]) & (ys <= high[1])
    if not selected.any():
        return False
    centers = np.c_[xs[selected] + .5, ys[selected] + .5]
    edges = np.roll(triangle, -1, axis=0) - triangle
    axes = [np.array([1., 0.]), np.array([0., 1.]), *[np.array([-e[1], e[0]]) for e in edges]]
    overlap = np.ones(len(centers), dtype=bool)
    for axis in axes:
        projection = triangle @ axis
        radius = .5 * abs(axis).sum()
        midpoint = centers @ axis
        overlap &= (midpoint + radius >= projection.min() - 1e-9) & (midpoint - radius <= projection.max() + 1e-9)
    return bool(overlap.any())


def _pixels(snapshot, actual):
    require(len(snapshot['images']) == len(actual['images']), 'Changed image inventory')
    policy = snapshot.get('authorized_caudal_pixel_patch')
    for before, pixels in zip(snapshot['images'], actual['images']):
        current_hash = hashlib.sha256(pixels.tobytes()).hexdigest()
        if current_hash == before['rgba_sha256'] and list(pixels.shape[1::-1]) == before['size']:
            continue
        require(policy and before['index'] == policy['image_index'], 'RGBA changed outside authorized tail image')
        require(list(pixels.shape[1::-1]) == policy['permitted_size'], 'Unauthorized tail image dimensions')
        require(current_hash == policy['expected_patched_rgba_sha256'], 'Not the authorized measured tail pixel result')
        original = np.asarray(Image.open(bound(before['baseline_pixels'])).convert('RGBA'))
        require(hashlib.sha256(original.tobytes()).hexdigest() == before['rgba_sha256'], 'Wrong baseline pixels')
        require(list(original.shape[1::-1]) == policy['baseline_size'], 'Wrong baseline image size')
        padded = np.zeros_like(pixels)
        require(original.shape[0] <= pixels.shape[0] and original.shape[1] <= pixels.shape[1], 'Image was cropped')
        padded[:original.shape[0], :original.shape[1]] = original
        mask = np.asarray(Image.open(bound(policy['mask'])).convert('L')) > 0
        require(mask.shape == pixels.shape[:2] and mask.any(), 'Invalid authorized edit mask')
        x, y, width, height = policy['allowed_rectangle']
        allowed = np.zeros(mask.shape, dtype=bool)
        require(0 <= x < x + width <= mask.shape[1] and 0 <= y < y + height <= mask.shape[0], 'Invalid authorized tile')
        allowed[y:y + height, x:x + width] = True
        require(not (mask & ~allowed).any(), 'Edit mask exceeds authorized tail tile')
        changed = (pixels != padded).any(axis=2)
        require(not (changed & ~mask).any(), 'RGBA change outside measured edit mask')
        ys, xs = np.where(changed)
        doc = actual['doc']
        for material_index, triangles in actual['sampling']:
            for texture_ref in _texture_refs(doc['materials'][material_index]):
                texture = doc['textures'][texture_ref['index']]
                if texture['source'] != before['index']:
                    continue
                require(before['size'] == policy['permitted_size'], 'Shared protected texture was resized')
                sampler = doc['samplers'][texture['sampler']]
                require(texture_ref.get('texCoord', 0) == 0 and not texture_ref.get('extensions'), 'Unsupported protected UV transform')
                require(sampler.get('magFilter') == sampler.get('minFilter') == 9728, 'Changed shared atlas needs nearest sampling')
                for triangle in triangles:
                    require(((triangle >= 0) & (triangle < 1)).all(), 'Unsupported wrapped/boundary protected UV')
                    require(not _touches_changed_texel(triangle * before['size'], xs, ys), 'Tail pixels overlap actual non-tail UV sampling')


def _accepted(snapshot, species):
    release = load(snapshot['accepted_release'])
    require(bool(release.get('user_acceptance') or release.get('user_acceptance_date')), 'No prior user acceptance')
    matches = [r for r in release.get('fish', []) if r.get('species') == species
               and r.get('model', {}).get('sha256') == snapshot['baseline_model_sha256']]
    scalar = release.get('species') == species and release.get('accepted_model_sha256') == snapshot['baseline_model_sha256']
    require(len(matches) == 1 or scalar, 'Snapshot is not the accepted baseline')


def _stock_exception(contract, snapshot, actual, candidates, species):
    reference = contract.get('source_preserved_export_serialization')
    if not reference:
        return {}
    measured = load(reference)
    require(measured.get('kind') == 'ordinary_source_preserved_export_serialization' and
            measured.get('schema_version') == 1 and measured['ok'] is True,
            'Unknown/failed stock serialization measurement')
    records = [r for r in measured['records'] if r['species'] == species]
    require(len(records) == 1, 'No unique frozen stock serialization record')
    record = records[0]
    require(record['baseline_model']['sha256'] == snapshot['baseline_model_sha256'] and
            record['current_model_sha'] == sha(bound(candidates['model'])), 'Wrong stock model binding')
    identity = record['source_identity']
    source_role = contract.get('editable_source_role', 'editable_source')
    require(record['baseline_source_sha'] == snapshot['baseline_source_sha256'] and
            record['current_source_sha'] == sha(bound(candidates[source_role])), 'Wrong stock source binding')
    require(record['all_noncaudal_source_groups_exact'] is True and
            identity['baseline_mesh_signatures'] == identity['current_mesh_signatures'], 'Source groups changed')
    require(record['candidate_weights_exactly_predicted'] is True, 'Weights not independently predicted')
    allowed = {}
    for row in record['expected_encoded_part_signatures']:
        key = (row['name'], row['surface'])
        require(key in actual['parts'] and row['name'] in identity['current_mesh_signatures'], 'Unverified stock partition')
        require(actual['parts'][key]['stock_signature'] == row['sha256'], 'Weights differ from exact stock result')
        allowed[key] = row
    require(set(allowed) == {k for k in actual['parts'] if k[0] not in TAIL_NAMES}, 'Incomplete source serialization coverage')
    return allowed


def validate_preservation(reference, candidates, species, task_type):
    require(task_type == 'repair', 'Scoped inheritance is repair-only')
    contract = load(reference)
    require(contract.get('kind') == 'caudal_repair_preservation' and contract.get('species') == species,
            'Wrong scoped preservation contract')
    require(contract.get('affected_anatomical_parts') == ['Caudal'], 'Only Caudal repair is supported')
    model = bound(candidates['model'])
    source_role = contract.get('editable_source_role', 'editable_source')
    require(contract['model_sha256'] == sha(model) and contract['source_sha256'] == sha(bound(candidates[source_role])),
            'Stale scoped candidate')
    snapshot = load(contract['accepted_snapshot'])
    require(snapshot['kind'] == 'accepted_caudal_repair_protected_snapshot' and snapshot['species'] == species,
            'Wrong accepted snapshot')
    _accepted(snapshot, species)
    actual = inspect_model(model)
    before = {tuple(p['key']): p for p in snapshot['part_inventory']}
    require(before and any(p['affected_caudal'] for p in before.values()), 'Missing accepted Caudal inventory')
    require(all(p['affected_caudal'] == (k[0] in TAIL_NAMES) for k, p in before.items()), 'Self-reported protection omission')
    protected = {k for k in before if k[0] not in TAIL_NAMES}
    require(protected == {k for k in actual['parts'] if k[0] not in TAIL_NAMES}, 'Missing/extra protected partition')
    require(any(k[0] in TAIL_NAMES for k in actual['parts']), 'Current Caudal missing')
    bindings = load(contract['accepted_material_bindings'])
    require(bindings.get('kind') == 'accepted_caudal_repair_material_bindings' and
            bindings.get('species') == species and
            bindings['baseline_model_sha256'] == snapshot['baseline_model_sha256'],
            'Wrong accepted material binding snapshot')
    materials = {tuple(row['key']): row['material'] for row in bindings['part_material_bindings']}
    require(set(materials) == set(before), 'Incomplete accepted material binding inventory')
    require(all(actual['parts'][key]['material'] == materials[key] for key in protected),
            'Protected partition material binding changed')
    exceptions = _stock_exception(contract, snapshot, actual, candidates, species)
    for key in protected:
        old, current = before[key], actual['parts'][key]
        require(old['triangles'] == current['triangles'] and old['geometry_uv_normal_signature'] == current['geometry'],
                'Protected geometry/NORMAL/UV/topology changed: ' + str(key))
        require(old['canonical_directed_triangle_signature'] == current['signature'] or key in exceptions,
                'Protected effective skin changed: ' + str(key))
    require(snapshot['rig_semantic_signature'] == actual['rig'] and
            snapshot['native_animation_semantic_signature'] == actual['animation'], 'Rig/rest/bind/native clip changed')
    require(snapshot['node_graph'] == actual['graph'], 'Static node graph/transform changed')
    old_doc = {k: snapshot[k] for k in ('materials', 'textures', 'samplers')}
    require(_materials(old_doc) == _materials(actual['doc']), 'Material or semantic sampler changed')
    _pixels(snapshot, actual)
    return dict(protected_parts=len(protected), exact_source_serialization_exception_parts=len(exceptions),
                actual_fin_inventory=sorted({key[0] for key in actual['parts']
                    if re.match(r'^(Caudal|Anal|Dorsal|Adipose|Pectoral|Pelvic)(_|$)', key[0])}),
                model_sha256=sha(model), baseline_model_sha256=snapshot['baseline_model_sha256'])


def validate_tail_volume(report, candidates, species, preservation):
    """Affected tail measurements plus fresh whole-fin posed gates, never old negatives."""
    require(preservation and report.get('kind') == 'caudal_repair_current_volume', 'Missing strict repair preservation')
    require(report['species'] == species and report['model_sha256'] == candidates['model']['sha256'], 'Wrong tail volume candidate')
    raw = load(report['actual_tail_measurement'])
    source_role = report.get('editable_source_role', 'editable_source')
    require(raw['model_sha256'] == report['model_sha256'] and raw['source_sha256'] == candidates[source_role]['sha256'],
            'Wrong actual tail source/model')
    current = raw['current']
    tails = [row for row in current['fins'] if row['name'].removesuffix('_mesh') == 'Caudal']
    require(len(tails) == 1, 'Actual measurement must contain one Caudal')
    tail = tails[0]
    require(tail['missing_opposing_ray_count'] == 0 and not tail['missing_opposing_rays'] and
            tail['proximal_to_distal_median_ratio'] >= 1.5, 'Tail normal rays/taper failed')
    require(all(tail['zones'].get(k, {}).get('samples', 0) > 0 for k in ('proximal', 'middle', 'distal')), 'Missing tail thickness zone')
    correspondence = tail['final_geometry_correspondence']
    require(correspondence and correspondence['maximum_bidirectional_position_error_native'] <= 2e-6, 'Missing actual source/GLB correspondence')
    actual_correspondence = load(report['actual_geometry_correspondence'])
    require(actual_correspondence['ok'] is True and
            actual_correspondence['kind'] == 'actual_source_export_tail_position_correspondence' and
            actual_correspondence['species'] == species and
            actual_correspondence['model_sha256'] == report['model_sha256'] and
            actual_correspondence['source_sha256'] == candidates[source_role]['sha256'] and
            actual_correspondence['maximum_bidirectional_position_error_native'] <= 2e-6,
            'Missing independent actual source/GLB tail position proof')
    section = current['tail_cross_section']
    require(section['ok'] is True and section['sections'] and section['tolerance_mm'] == .4 and
            section['maximum_width_error_mm'] <= .4, 'Tail finite section failed')
    roots, membrane, completion = (load(report[k]) for k in ('root490', 'membrane490', 'root072'))
    require(roots['ok'] and membrane['ok'] and completion['ok'], 'Current root/membrane gates failed')
    require(roots['model_sha256'] == membrane['model_sha256'] == report['model_sha256'], 'Stale physical model binding')
    require(len(roots['samples']) == membrane['poses'] == 490 and roots['tolerance_cm'] == .1 and
            roots['max_penetration_cm'] == .6 and membrane['root_collar_mm'] == .5 and
            membrane['penetration_tolerance_mm'] == .02, 'Changed physical coverage/limits')
    require(set(roots['summary']) == set(membrane['summary']) and
            set(roots['summary']) == set(preservation['actual_fin_inventory']) and
            set(roots['summary']) == set(roots['coverage']['expected_fins']) and
            roots['coverage']['all_expected_fins_present_in_every_sample'] is True and
            all(v['failed_contact_samples'] == 0 for v in roots['summary'].values()) and
            all(v['failed_poses'] == 0 for v in membrane['summary'].values()), 'Incomplete complete-fin physical pass')
    require(all(set(sample['fins']) == set(preservation['actual_fin_inventory'])
                for sample in roots['samples']), 'Root poses omit an actual fin')
    require(len(membrane['samples']) == 490 and
            all(set(sample['fins']) == set(preservation['actual_fin_inventory'])
                for sample in membrane['samples']), 'Membrane poses omit an actual fin')
    checks = completion['checks']
    require(len(checks) == 1 and checks[0].get('model_sha256', report['model_sha256']) == report['model_sha256'] and
            checks[0]['report_sha256'] == sha(bound(report['root490'])), '072 does not bind the same current root report')
    if 'reused_completion_sha256' in completion:
        full = load(report['root490_completion'])
        require(completion['reused_completion_sha256'] == sha(bound(report['root490_completion'])) and
                full['ok'] and full['model_sha256'] == report['model_sha256'] and full['poses'] == 490,
                '072 reused completion is stale')
    return dict(raw_extra_static_contact_pass=raw['ok'], scope='Affected tail only; original .5mm diagnostic retained')
