"""Bounded lower-jaw retraction and source-lip UV alignment on an existing GLB.

Preserve Y/Z, upper head, eye geometry, topology, weights, fins and animation.
Only Closed_body POSITION/NORMAL/UV0 accessors are appended.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from freeze_surface_ownership import read_glb, accessor
from patch_existing_fin_meshes import write


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def smooth(t):
    t = np.clip(t, 0., 1.)
    return t * t * (3. - 2. * t)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.plan.read_text(encoding='utf8'))
    assert sha(p['source']) == p['source_sha256']
    assert sha(p['source_image']) == p['source_image_sha256']
    assert 0 < p['lower_retract_native'] <= .012 and .004 <= p['lower_blend_native'] <= .02
    assert p['start_u'] < p['end_u'] <= 1.
    d, b = read_glb(Path(p['source'])); old = copy.deepcopy(d); binary = bytearray(b)
    node = next(n for n in d['nodes'] if n.get('name') == 'Closed_body')
    assert not any(k in node for k in ['matrix', 'translation', 'rotation', 'scale'])
    prims = d['meshes'][node['mesh']]['primitives']; assert len(prims) == 2
    aspect = p['source_size'][1] / p['source_size'][0]
    path = np.asarray(p['old_slit_path']); center_v = PchipInterpolator(path[:, 0], path[:, 1], extrapolate=True)
    target = np.asarray(p['source_gap_pixels'], float)
    upper = PchipInterpolator(target[:, 0] / p['source_size'][0], target[:, 1] / p['source_size'][1])
    lower = PchipInterpolator(target[:, 0] / p['source_size'][0], target[:, 2] / p['source_size'][1])

    def deform(v):
        result = v.astype(float).copy(); u = v[:, 0] + .5
        center = (.5 - center_v(u)) * aspect
        depth = smooth((center - v[:, 1]) / p['lower_blend_native'])
        reach = smooth((u - p['start_u']) / (p['end_u'] - p['start_u']))
        result[:, 0] -= p['lower_retract_native'] * depth * reach
        return result

    def add(a, typ):
        a = np.asarray(a, dtype='<f4'); binary.extend(b'\0' * (-len(binary) % 4)); offset = len(binary); binary.extend(a.tobytes())
        view = len(d['bufferViews']); d['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': a.nbytes, 'target': 34962})
        idx = len(d['accessors']); d['accessors'].append({'bufferView': view, 'componentType': 5126, 'count': len(a), 'type': typ, 'min': a.min(0).tolist(), 'max': a.max(0).tolist()})
        return idx

    rows = []
    for surface, primitive in enumerate(prims):
        attrs = primitive['attributes']; v = accessor(old, b, attrs['POSITION']); new = deform(v).astype('<f4')
        unchanged = np.all(v == new, axis=1)
        jac = []
        for axis in range(3):
            delta = np.zeros(3); delta[axis] = .000002
            jac.append((deform(v + delta) - deform(v - delta)) / .000004)
        jac = np.stack(jac, axis=2); determinant = np.linalg.det(jac)
        assert determinant.min() > .05, 'Folded or overcompressed local deformation'
        normal = accessor(old, b, attrs['NORMAL'])
        mapped = np.linalg.solve(jac.transpose(0, 2, 1), normal[:, :, None])[:, :, 0]
        mapped /= np.maximum(np.linalg.norm(mapped, axis=1)[:, None], 1e-12)
        mapped[unchanged] = normal[unchanged]
        uv = accessor(old, b, attrs['TEXCOORD_0']).copy()
        old_uv = uv.copy()
        if surface == 0:
            u = v[:, 0] + .5; center = (.5 - center_v(u)) * aspect
            is_upper = v[:, 1] >= center
            edge_y = center + np.where(is_upper, p['old_gap_native'] / 2., -p['old_gap_native'] / 2.)
            cu = np.clip(uv[:, 0], target[0, 0] / p['source_size'][0], target[-1, 0] / p['source_size'][0])
            painted_edge = np.where(is_upper, upper(cu), lower(cu))
            amount = (1. - smooth(np.abs(v[:, 1] - edge_y) / .010)) * smooth((u - .936) / .012)
            # Both lip margins sample their own painted edge. The original
            # source image and lateral progression are preserved.
            desired_v = painted_edge + (edge_y - v[:, 1]) / aspect
            uv[:, 1] = uv[:, 1] * (1. - amount) + desired_v * amount
        attrs['POSITION'] = add(new, 'VEC3'); attrs['NORMAL'] = add(mapped, 'VEC3'); attrs['TEXCOORD_0'] = add(uv, 'VEC2')
        assert np.array_equal(new[:, 1:], v[:, 1:])
        assert np.array_equal(new[v[:, 1] >= (.5 - center_v(v[:, 0] + .5)) * aspect], v[v[:, 1] >= (.5 - center_v(v[:, 0] + .5)) * aspect])
        rows.append({'surface': surface, 'moved_vertices': int((~unchanged).sum()), 'minimum_jacobian': float(determinant.min()), 'maximum_retraction_native': float((v[:, 0] - new[:, 0]).max()), 'uv_vertices_changed': int(np.any(old_uv != uv, axis=1).sum())})
    for key in ['nodes', 'skins', 'animations', 'images', 'materials', 'textures', 'samplers']:
        assert d.get(key) == old.get(key), key
    for i, mesh in enumerate(d['meshes']):
        if i != node['mesh']: assert mesh == old['meshes'][i], 'Non-body mesh changed'
    for i, primitive in enumerate(prims):
        prior = old['meshes'][node['mesh']]['primitives'][i]
        for key in ['indices', 'mode', 'material']: assert primitive.get(key) == prior.get(key)
        for key in ['JOINTS_0', 'WEIGHTS_0', 'TEXCOORD_1']: assert primitive['attributes'].get(key) == prior['attributes'].get(key)
    assert bytes(binary[:len(b)]) == bytes(b)
    out = Path(p['target']); assert out.resolve() != Path(p['source']).resolve()
    out.parent.mkdir(parents=True, exist_ok=True); write(out, d, binary)
    report = {'schema_version': 1, 'ok': True, 'command': 'fish.retract-static-lower-jaw', 'status': 'done', 'next_action': 'human_review',
              'source_sha256': p['source_sha256'], 'model_sha256': sha(out), 'source_image_sha256': p['source_image_sha256'],
              'surfaces': rows, 'preserved': 'Y/Z and upper head, original BIN prefix, topology, weights, rig, animation, fin primitives and source image.',
              'limits': 'Local shape/material trial; actual views, eye preservation, body and full-fin gates still required.'}
    out.with_suffix('.build.validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report))


if __name__ == '__main__': main()
