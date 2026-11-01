"""Small, explicitly bounded posterior oral-corner extension of an existing GLB.

Only the two declared body primitives move. The same C1 X field preserves the
welded interface; Y/Z, front lips, topology, rig, fins, eyes and source images
stay fixed. A frozen source-plane allowance is required before using this tool.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from freeze_surface_ownership import accessor, read_glb
from patch_existing_fin_meshes import write


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bump(q):
    inside = abs(q) < 1
    value = np.where(inside, (1 - q*q)**2, 0.)
    derivative = np.where(inside, -4*q*(1 - q*q), 0.)
    return value, derivative


def field(pos, row):
    u = pos[:, 0] + .5
    bx, dbx = bump((u - row['corner_u']) / row['radius_u'])
    distance = abs(pos[:, 1] - row['center_y'])
    span = row['radius_y'] - row['plateau_y']
    t = np.clip((distance - row['plateau_y']) / span, 0., 1.)
    by = 1 - t*t*(3 - 2*t)
    dby = np.where((distance > row['plateau_y']) & (distance < row['radius_y']),
                   -6*t*(1-t)/span*np.sign(pos[:, 1]-row['center_y']), 0.)
    dx = -row['delta_u'] * bx * by
    jxx = 1 - row['delta_u'] * dbx / row['radius_u'] * by
    jxy = -row['delta_u'] * bx * dby
    return dx, jxx, jxy


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    records = []
    for row in plan['items']:
        source, target = Path(row['source']), Path(row['target'])
        assert source.resolve() != target.resolve()
        assert sha(source) == row['source_sha256']
        assert row['painted_continuation_verified'] is True
        assert 0 < row['delta_u'] < row['radius_u'] / 2
        assert row['plateau_y'] < row['radius_y']
        # Global lower bound of this separable field, independent of mesh sampling.
        minimum_jxx = 1 - row['delta_u'] / row['radius_u'] * 8/(3*np.sqrt(3))
        assert minimum_jxx > .5
        d, b = read_glb(source)
        original = copy.deepcopy(d)
        binary = bytearray(b)
        body = next(n for n in d['nodes'] if n.get('name') == row['mesh'])
        assert not any(k in body for k in ('matrix', 'translation', 'rotation', 'scale'))
        mi = body['mesh']
        parts = d['meshes'][mi]['primitives']
        assert len(parts) == 2
        details = []

        def append_array(data, template):
            value = np.asarray(data, dtype='<f4')
            binary.extend(b'\0' * (-len(binary) % 4))
            off = len(binary)
            binary.extend(value.tobytes())
            vi = len(d['bufferViews'])
            d['bufferViews'].append({'buffer': 0, 'byteOffset': off, 'byteLength': value.nbytes, 'target': 34962})
            ac = copy.deepcopy(template)
            ac.update(bufferView=vi, byteOffset=0, componentType=5126,
                      count=len(value), min=value.min(0).tolist(), max=value.max(0).tolist())
            ai = len(d['accessors'])
            d['accessors'].append(ac)
            return ai

        for si, pr in enumerate(parts):
            attrs = pr['attributes']
            pos = accessor(original, b, attrs['POSITION']).astype(float)
            delta, jxx, jxy = field(pos, row)
            moved = abs(delta) > 0
            assert moved.any()
            changed = pos.copy()
            changed[:, 0] += delta
            normal = accessor(original, b, attrs['NORMAL']).astype(float)
            nn = normal.copy()
            nn[:, 0] = normal[:, 0] / jxx
            nn[:, 1] = normal[:, 1] - normal[:, 0] * jxy / jxx
            nn /= np.maximum(np.linalg.norm(nn, axis=1)[:, None], 1e-12)
            nn[~moved] = normal[~moved]
            for name, value in [('POSITION', changed), ('NORMAL', nn)]:
                attrs[name] = append_array(value, original['accessors'][attrs[name]])
            if si == row['skin_surface']:
                uv = accessor(original, b, attrs['TEXCOORD_0']).astype(float)
                # Existing source stays in the same native XY plane. Do not
                # stretch the painted lip together with the moved cut corner.
                uv[moved, 0] += delta[moved] * row['source_u_per_native']
                attrs['TEXCOORD_0'] = append_array(uv, original['accessors'][attrs['TEXCOORD_0']])
            details.append({'surface': si, 'moved_vertices': int(moved.sum()),
                            'max_posterior_shift_native': float(-delta.min())})
        assert binary[:len(b)] == b
        for name in ('nodes', 'skins', 'animations', 'images', 'textures', 'materials', 'samplers'):
            assert d.get(name) == original.get(name), name
        for i, m in enumerate(d['meshes']):
            if i != mi:
                assert m == original['meshes'][i]
        target.parent.mkdir(parents=True, exist_ok=True)
        write(target, d, binary)
        records.append({'species': row['species'], 'source_sha256': sha(source),
                        'model_sha256': sha(target), 'minimum_global_jxx': float(minimum_jxx),
                        'changes': details, 'candidate_only': True,
                        'source_images_rig_topology_fins_other_meshes_preserved': True})
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps({'schema_version': 1, 'ok': True, 'status': 'done',
                                  'next_action': 'human_review', 'records': records,
                                  'plan_sha256': sha(a.plan), 'script_sha256': sha(__file__)}, indent=2) + '\n')
    print(json.dumps({'ok': True, 'candidates': len(records)}))


if __name__ == '__main__':
    main()
