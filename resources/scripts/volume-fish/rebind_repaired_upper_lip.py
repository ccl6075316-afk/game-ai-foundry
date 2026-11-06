"""Bind an existing semantic upper lip to a repaired cold export, fail closed.

Matches the unchanged native UV, named skin weights and anterior vertical
location inside the original body surface; verifies a current shared oral-roof
edge. It never selects the most anterior or nearest head point. Writes review
artifacts only; installing a recipe/table is a separate operation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE / 'portable'))
from glb_io import arrays, read_glb


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def node_primitive(doc, name, surface):
    nodes = [node for node in doc['nodes'] if node.get('name') == name and 'mesh' in node]
    if len(nodes) != 1:
        raise ValueError('Body mesh owner is missing or ambiguous')
    node = nodes[0]
    return node, doc['meshes'][node['mesh']]['primitives'][surface]


def named_skin(doc, binary, node, primitive, vertex):
    joints = arrays(doc, binary, primitive['attributes']['JOINTS_0'])[vertex]
    weights = arrays(doc, binary, primitive['attributes']['WEIGHTS_0'])[vertex]
    names = [doc['nodes'][index]['name'] for index in doc['skins'][node['skin']]['joints']]
    result = {}
    for joint, weight in zip(joints, weights):
        if weight > 0:
            name = names[int(joint)]
            result[name] = result.get(name, 0.) + float(weight)
    return result, joints.tolist(), weights.tolist()


def skin_equal(left, right):
    return left.keys() == right.keys() and all(abs(left[name] - right[name]) < 1e-7 for name in left)


def owner_faces(doc, binary, node, oral_materials):
    primitives = doc['meshes'][node['mesh']]['primitives']
    if doc.get('extras', {}).get('geometry_parts'):
        if len(primitives) != 1:
            raise ValueError('Unsupported packed body layout')
        primitive = primitives[0]
        vertices = arrays(doc, binary, primitive['attributes']['POSITION'])
        indices = arrays(doc, binary, primitive['indices']).reshape(-1)
        skin, oral, ranges = [], [], []
        for part in doc['extras']['geometry_parts']:
            if part['role'] not in ('body_skin', 'mouth'):
                continue
            start, count = part['index_start'], part['index_count']
            faces = vertices[indices[start:start + count].reshape(-1, 3)]
            (oral if part['role'] == 'mouth' else skin).append(faces)
            ranges.append([part['vertex_start'], part['vertex_start'] + part['vertex_count']])
        return np.concatenate(skin), np.concatenate(oral), ranges
    skin, oral = [], []
    if not oral_materials:
        raise ValueError('Ordinary body requires the explicitly identified original oral material')
    for primitive in primitives:
        name = doc['materials'][primitive['material']].get('name', '')
        vertices = arrays(doc, binary, primitive['attributes']['POSITION'])
        faces = vertices[arrays(doc, binary, primitive['indices']).reshape(-1, 3)]
        # Use the reviewed original cavity identity, not a name substring.
        # All other surfaces belong to the explicitly selected body node.
        if name in oral_materials:
            oral.append(faces)
        else:
            skin.append(faces)
    if not skin or not oral:
        raise ValueError('A complete explicit body skin and oral surface are required')
    return np.concatenate(skin), np.concatenate(oral), None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ['baseline-model', 'baseline-recipe', 'candidate', 'output']:
        parser.add_argument('--' + option, type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / 'projects/fishing-2d/experiments'):
        raise ValueError('Recipe review output must be inside the experiment directory')
    if args.output.exists():
        raise ValueError('Recipe review artifact already exists')
    recipe = json.loads(args.baseline_recipe.read_text())
    if recipe['model_sha256'] != sha(args.baseline_model):
        raise ValueError('Baseline recipe is stale')
    old, ob = read_glb(args.baseline_model)
    new, nb = read_glb(args.candidate)
    old_node, old_primitive = node_primitive(old, recipe['mesh'], recipe['surface'])
    old_id = recipe['vertex_index']
    old_pos = arrays(old, ob, old_primitive['attributes']['POSITION'])[old_id]
    old_uv = arrays(old, ob, old_primitive['attributes']['TEXCOORD_0'])[old_id]
    old_skin, _, _ = named_skin(old, ob, old_node, old_primitive, old_id)
    if np.max(abs(old_pos - recipe['position_native'])) > 1e-7:
        raise ValueError('Baseline anchor position does not match its explicit index')
    if np.max(abs(old_uv - recipe['texcoord0'])) > 1e-7:
        raise ValueError('Baseline anchor UV does not match its explicit index')
    old_material = old['materials'][old_primitive['material']]['name']
    new_nodes = [node for node in new['nodes'] if node.get('name') == recipe['mesh'] and 'mesh' in node]
    if len(new_nodes) != 1:
        raise ValueError('Candidate body mesh owner changed')
    new_node = new_nodes[0]
    matches = []
    for surface, primitive in enumerate(new['meshes'][new_node['mesh']]['primitives']):
        if new['materials'][primitive['material']]['name'] != old_material:
            continue
        vertices = arrays(new, nb, primitive['attributes']['POSITION'])
        uv = arrays(new, nb, primitive['attributes']['TEXCOORD_0'])
        ids = np.flatnonzero((abs(uv - old_uv).max(axis=1) < 1e-7)
                             & (abs(vertices[:, :2] - old_pos[:2]).max(axis=1) < 1e-7))
        for index in ids:
            weights, joints, raw_weights = named_skin(new, nb, new_node, primitive, int(index))
            if skin_equal(weights, old_skin) and (abs(old_pos[2]) < 1e-7 or old_pos[2] * vertices[index, 2] > 0):
                matches.append((surface, int(index), primitive, vertices[index], uv[index], weights, joints, raw_weights))
    if len(matches) != 1:
        raise ValueError(f'Existing semantic anchor mapping is ambiguous: {len(matches)} candidates')
    surface, index, primitive, position, uv, weights, joints, raw_weights = matches[0]
    oral_materials = set()
    identity = recipe.get('identity_evidence', {})
    # The rebinder's own emitted recipes store the reviewed set in plural form.
    for material in identity.get('oral_materials', []):
        if not isinstance(material, str) or not material:
            raise ValueError('Invalid explicit original oral material identity')
        oral_materials.add(material)
    if identity.get('oral_material'):
        oral_materials.add(identity['oral_material'])
    if identity.get('oral_surface') is not None:
        old_oral = old['meshes'][old_node['mesh']]['primitives'][identity['oral_surface']]
        oral_materials.add(old['materials'][old_oral['material']]['name'])
    skin_faces, oral_faces, body_ranges = owner_faces(new, nb, new_node, oral_materials)
    skin_tree = cKDTree(skin_faces.reshape(-1, 3))
    shared = skin_tree.query(oral_faces.reshape(-1, 3))[0].reshape(-1, 3) < 1e-7
    normals = np.cross(oral_faces[:, 1] - oral_faces[:, 0], oral_faces[:, 2] - oral_faces[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-30)
    roof = normals[:, 0] < -.1 if recipe['species'] == 'blacktip_reef_shark' else normals[:, 1] < -.1
    witnesses = []
    for face_index in np.flatnonzero(roof):
        face = oral_faces[face_index]
        for left, right in [(0, 1), (1, 2), (2, 0)]:
            if shared[face_index, left] and shared[face_index, right] and min(
                    np.linalg.norm(face[left] - position), np.linalg.norm(face[right] - position)) < 1e-7:
                witnesses.append({'oral_triangle': int(face_index), 'edge': face[[left, right]].tolist(),
                                  'actual_oral_face_normal': normals[face_index].tolist()})
    if not witnesses:
        raise ValueError('Candidate anchor is not on a current shared upper oral-roof/skin edge')
    if body_ranges is None:
        body_ranges = [[0, len(arrays(new, nb, primitive['attributes']['POSITION']))]]
    if not any(start <= index < end for start, end in body_ranges):
        raise ValueError('Candidate upper lip is outside explicit body ownership')
    output = {'kind': 'existing_skinned_upper_lip_vertex_recipe', 'species': recipe['species'],
              'model_sha256': sha(args.candidate), 'mesh': recipe['mesh'], 'surface': surface,
              'vertex_index': index, 'position_native': position.tolist(), 'texcoord0': uv.tolist(),
              'raw_joint_indices': joints, 'raw_weights': raw_weights, 'weighted_bones': weights,
              'body_vertex_ranges': body_ranges, 'binding_space': 'mesh_native',
              'semantic': 'Current shared skin/oral-roof upper-lip edge; continued from explicitly identified canonical upper lip.',
              'identity_evidence': {'method': 'Unchanged native UV, named skin weights and anterior vertical position on the same named skin material; unique match required. Then current actual shared oral-roof edge independently verified.',
                                    'superseded_recipe': {'path': str(args.baseline_recipe.resolve()), 'sha256': sha(args.baseline_recipe)},
                                    'canonical_baseline_model_sha256': sha(args.baseline_model),
                                    'oral_materials': sorted(oral_materials),
                                    'shared_upper_roof_edge_witnesses': witnesses,
                                    'checker_sha256': sha(Path(__file__))},
              'scope': 'Candidate recipe only; actual Godot imported identity and hook placement still require a fresh process.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'species': recipe['species'], 'surface': surface, 'vertex_index': index,
                      'position': position.tolist(), 'shared_roof_edges': len(witnesses)}))


if __name__ == '__main__':
    main()
