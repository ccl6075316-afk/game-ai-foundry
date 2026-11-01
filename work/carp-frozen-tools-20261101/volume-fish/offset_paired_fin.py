"""Move a paired fin's free membrane outward while preserving frozen full roots.

Only POSITION accessors of the named fin are appended. All original BIN
bytes, body primitives, UVs, rig and animations are preserved. The output still
requires the original absolute-root and full-membrane collision gates.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from freeze_surface_ownership import accessor
from patch_existing_fin_meshes import read, write


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--species', required=True)
    parser.add_argument('--fin', required=True)
    parser.add_argument('--offset-mm', required=True, type=float)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf8'))
    spec = next(row for row in plan['items'] if row['species'] == args.species)
    source = Path(spec['model'])
    assert sha(source) == spec['model_sha256'], 'Stale model plan'
    assert args.fin.startswith(('Pectoral_', 'Pelvic_')) and args.fin.endswith(('_left', '_right'))
    assert 0 < args.offset_mm <= .25, 'Bounded outward edit only (0, .25] mm'
    assert args.output.resolve() != source.resolve() and not args.output.exists(), 'New output required'
    document, binary = read(source)
    before = copy.deepcopy(document)
    original = bytes(binary)
    target = next(node for node in document['nodes'] if node.get('name') == args.fin and 'mesh' in node)
    assert not any(key in target for key in ['matrix', 'translation', 'rotation', 'scale']), 'Nonidentity fin node'
    roots = np.asarray(spec['fins'][args.fin]['rest_points_gltf'])
    assert roots.ndim == 2 and roots.shape[1] == 3 and len(roots) > 1, 'Empty frozen root band'
    native_offset = args.offset_mm / (spec['scale_cm'] * 10.)
    side = 1 if args.fin.endswith('_left') else -1
    records = []

    def append_vectors(source_index, rows):
        value = copy.deepcopy(document['accessors'][source_index])
        assert value['componentType'] == 5126 and value['type'] == 'VEC3' and 'sparse' not in value
        binary.extend(b'\0' * (-len(binary) % 4))
        offset = len(binary)
        binary.extend(np.asarray(rows, dtype='<f4').tobytes())
        value.update(bufferView=len(document['bufferViews']), byteOffset=0,
                     min=rows.min(axis=0).tolist(), max=rows.max(axis=0).tolist())
        document['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(rows) * 12, 'target': 34962})
        document['accessors'].append(value)
        return len(document['accessors']) - 1

    for primitive in document['meshes'][target['mesh']]['primitives']:
        positions = accessor(document, binary, primitive['attributes']['POSITION']).astype(np.float64)
        distances = np.min(np.linalg.norm(positions[:, None, :] - roots[None, :, :], axis=2), axis=1)
        root_mask = distances < spec['length_native'] * .00002
        assert root_mask.any() and (~root_mask).any(), 'Missing root/free selection'
        revised = positions.copy()
        revised[~root_mask, 2] += side * native_offset
        assert np.array_equal(revised[root_mask], positions[root_mask])
        assert np.array_equal(revised[:, :2], positions[:, :2])
        # Keep the authored shading normals. Recomputing them from the shell
        # triangulation discards the source model's custom smoothing and visibly
        # changes this otherwise microscopic clearance repair.
        primitive['attributes']['POSITION'] = append_vectors(primitive['attributes']['POSITION'], revised)
        records.append({'root_vertices_preserved': int(root_mask.sum()), 'free_vertices_moved': int((~root_mask).sum())})
    for key in ['nodes', 'skins', 'animations', 'materials', 'images', 'textures', 'samplers']:
        assert document.get(key) == before.get(key), f'Unexpected {key} change'
    for index, mesh in enumerate(document['meshes']):
        if index != target['mesh']:
            assert mesh == before['meshes'][index], 'Non-target mesh changed'
    for old, new in zip(before['meshes'][target['mesh']]['primitives'], document['meshes'][target['mesh']]['primitives']):
        expected = copy.deepcopy(old)
        for key in ['POSITION']:
            expected['attributes'][key] = new['attributes'][key]
        assert expected == new, 'Non-position fin data changed'
    assert bytes(binary[:len(original)]) == original, 'Original binary changed'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, document, binary)
    result = {'schema_version': 1, 'ok': True, 'command': 'fish.offset-paired-fin',
              'status': 'done', 'next_action': 'human_review',
              'source': str(source), 'source_sha256': sha(source), 'output': str(args.output),
              'output_sha256': sha(args.output), 'fin': args.fin, 'offset_mm': args.offset_mm,
              'native_offset': native_offset, 'records': records,
              'original_binary_prefix_preserved': True, 'body_uv_rig_animation_unchanged': True,
              'authored_normals_preserved': True,
              'root_points_unchanged': True, 'side_xy_silhouette_unchanged': True,
              'validation': 'pending; must run full roots, membranes, body and GPU views'}
    args.output.with_suffix('.repair.validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
