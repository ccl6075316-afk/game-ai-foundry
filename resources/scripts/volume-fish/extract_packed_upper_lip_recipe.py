"""Identify a packed fish's actual shared upper oral-roof border for review.

Body/mouth roles must exist. Selection is restricted to the actual shared upper
rim, then its transverse center and anterior point; never the whole mesh max X.
No game file is modified and visual/Godot identity review remains required.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE / 'portable')]
from glb_io import arrays, read_glb
from rebind_repaired_upper_lip import named_skin, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--species', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / 'projects/fishing-2d/experiments') or args.output.exists():
        raise ValueError('Use a new recipe inside the declared experiment directory')
    doc, binary = read_glb(args.model)
    if len(doc['meshes']) != 1 or len(doc['meshes'][0]['primitives']) != 1:
        raise ValueError('This extractor requires an explicit packed one-surface source')
    node = next(node for node in doc['nodes'] if node.get('mesh') == 0)
    primitive = doc['meshes'][0]['primitives'][0]
    vertices = arrays(doc, binary, primitive['attributes']['POSITION'])
    uv = arrays(doc, binary, primitive['attributes']['TEXCOORD_0'])
    indices = arrays(doc, binary, primitive['indices']).reshape(-1)
    parts = doc['extras']['geometry_parts']
    skin_parts = [part for part in parts if part['role'] == 'body_skin']
    oral_parts = [part for part in parts if part['role'] == 'mouth']
    if not skin_parts or not oral_parts:
        raise ValueError('Both explicit skin and oral ownership are required')
    skin_ids = np.unique(np.concatenate([indices[p['index_start']:p['index_start'] + p['index_count']]
                                         for p in skin_parts]))
    oral_faces = np.concatenate([indices[p['index_start']:p['index_start'] + p['index_count']]
                                  for p in oral_parts]).reshape(-1, 3)
    shared = cKDTree(vertices[skin_ids]).query(vertices[oral_faces].reshape(-1, 3))[0].reshape(-1, 3) < 1e-7
    triangles = vertices[oral_faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-30)
    edges = []
    for face in np.flatnonzero(normals[:, 1] < -.1):
        for left, right in [(0, 1), (1, 2), (2, 0)]:
            if shared[face, left] and shared[face, right]:
                edges.append({'oral_triangle': int(face), 'vertex_indices': oral_faces[face, [left, right]].tolist(),
                              'positions': triangles[face, [left, right]].tolist(), 'oral_roof_normal': normals[face].tolist()})
    if not edges:
        raise ValueError('No actual upper roof/skin border identified')
    rim_ids = np.unique([index for edge in edges for index in edge['vertex_indices']])
    minimum_lateral = abs(vertices[rim_ids, 2]).min()
    center_ids = rim_ids[abs(vertices[rim_ids, 2]) <= minimum_lateral + 1e-7]
    nose = vertices[center_ids, 0].max()
    center_ids = center_ids[vertices[center_ids, 0] >= nose - 1e-7]
    positions = np.unique(np.round(vertices[center_ids], 7), axis=0)
    if len(positions) != 1:
        raise ValueError('Upper-rim center has multiple unresolved physical points')
    position = vertices[center_ids[0]]
    matching_skin = skin_ids[np.linalg.norm(vertices[skin_ids] - position, axis=1) < 1e-7]
    if not len(matching_skin):
        raise ValueError('Upper rim has no actual skin vertex')
    index = int(matching_skin[0])
    weights, joints, raw_weights = named_skin(doc, binary, node, primitive, index)
    for duplicate in matching_skin:
        if named_skin(doc, binary, node, primitive, int(duplicate))[0] != weights:
            raise ValueError('Same physical lip point has inconsistent skinning')
    report = {'kind': 'existing_skinned_upper_lip_vertex_recipe', 'species': args.species,
              'model_sha256': sha(args.model), 'mesh': node['name'], 'surface': 0, 'vertex_index': index,
              'position_native': position.tolist(), 'texcoord0': uv[index].tolist(),
              'raw_joint_indices': joints, 'raw_weights': raw_weights, 'weighted_bones': weights,
              'body_vertex_ranges': [[p['vertex_start'], p['vertex_start'] + p['vertex_count']]
                                     for p in skin_parts + oral_parts], 'binding_space': 'mesh_native',
              'semantic': 'Actually shared body-skin/upper oral-roof rim. Closest existing owned rim sample to the midline; recorded lateral offset is not assumed zero.',
              'identity_evidence': {'method': 'Explicit body/mouth roles and actual position-shared upper roof edges; closest existing lateral rim sample, with anterior tie-break only inside this upper rim. No claim that a centerline vertex exists.',
                                    'upper_roof_border_edges': edges, 'minimum_upper_rim_abs_lateral': float(minimum_lateral),
                                    'same_position_skin_indices': matching_skin.tolist(),
                                    'checker_sha256': sha(Path(__file__))},
              'scope': 'Candidate binding only; must inspect real lip marker and cold imported identity before installation.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'species': args.species, 'vertex_index': index, 'position': position.tolist(),
                      'shared_upper_border_edges': len(edges)}))


if __name__ == '__main__':
    main()
