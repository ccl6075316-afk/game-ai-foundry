"""Check the frozen local extension, preserved front lips and actual f32 mesh."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from extend_mouth_corner117 import field
from freeze_surface_ownership import accessor, read_glb
from inspect_lip_extent117 import inspect
from validate_oral_cdt_108 import crossing


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    a = ap.parse_args()
    reports = []
    for row in json.loads(a.plan.read_text())['items']:
        source, target = Path(row['source']), Path(row['target'])
        assert sha(source) == row['source_sha256']
        before, bb = read_glb(source)
        after, ab = read_glb(target)
        ir, png = inspect(target)
        corner = ir['posterior_corner_u'] * row['source_size'][0]
        reserve = corner - row['posterior_lip_branch_start_not_a_cut_target_source_x']
        expected = row['allowed_new_corner_source_x']
        extent_ok = expected[0] <= corner <= expected[1] and reserve >= row['minimum_remaining_source_lip_px']
        result = {'species': row['species'], 'model_sha256': sha(target),
                  'actual_corner_source_x': corner, 'remaining_source_band_px': reserve,
                  'extent_ok': extent_ok, 'common_boundary_edges': ir['common_edges']}
        if not extent_ok:
            result.update(ok=False, reason='Actual posterior opening does not match frozen short extension.')
            reports.append(result)
            continue
        for name in ('nodes', 'skins', 'animations', 'images', 'materials', 'textures', 'samplers'):
            assert before.get(name) == after.get(name), name
        assert ab[:len(bb)] == bb
        node = next(n for n in before['nodes'] if n.get('name') == row['mesh'])
        mi = node['mesh']
        for i, m in enumerate(before['meshes']):
            if i != mi:
                assert m == after['meshes'][i], 'Unrelated mesh changed'
        old_parts = before['meshes'][mi]['primitives']
        new_parts = after['meshes'][mi]['primitives']
        vertices, triangles, masks, part_reports = [], [], [], []
        pixel = np.asarray(Image.open(io.BytesIO(png)).convert('RGBA'))
        w, h = row['source_size']
        for si, (old, new) in enumerate(zip(old_parts, new_parts)):
            assert old['indices'] == new['indices'] and old['material'] == new['material']
            old_pos = accessor(before, bb, old['attributes']['POSITION'])
            new_pos = accessor(after, ab, new['attributes']['POSITION'])
            dx, jxx, jxy = field(old_pos.astype(float), row)
            moved = abs(dx) > 0
            assert np.array_equal(old_pos[:, 1:], new_pos[:, 1:])
            assert np.array_equal(old_pos[~moved], new_pos[~moved])
            front = old_pos[:, 0] + .5 >= row['front_fixed_u']
            assert front.any() and np.array_equal(old_pos[front], new_pos[front])
            assert np.max(abs((new_pos[:, 0].astype(float)-old_pos[:, 0])-dx)) < 4e-8
            old_normal = accessor(before, bb, old['attributes']['NORMAL'])
            new_normal = accessor(after, ab, new['attributes']['NORMAL'])
            expected_normal = old_normal.astype(float).copy()
            expected_normal[:, 0] = old_normal[:, 0] / jxx
            expected_normal[:, 1] = old_normal[:, 1] - old_normal[:, 0] * jxy / jxx
            expected_normal /= np.maximum(np.linalg.norm(expected_normal, axis=1)[:, None], 1e-12)
            expected_normal[~moved] = old_normal[~moved]
            assert np.isfinite(new_normal).all()
            assert np.array_equal(new_normal[~moved], old_normal[~moved])
            assert np.array_equal(new_normal, expected_normal.astype('<f4'))
            assert np.max(abs(np.linalg.norm(new_normal[moved].astype(float), axis=1) - 1)) < 1e-6
            for k, v in old['attributes'].items():
                if k in ('POSITION', 'NORMAL') or (si == row['skin_surface'] and k == 'TEXCOORD_0'):
                    continue
                assert new['attributes'][k] == v, k
            tri = accessor(before, bb, old['indices']).reshape(-1, 3)
            old_tri, new_tri = old_pos[tri].astype(float), new_pos[tri].astype(float)
            n0 = np.cross(old_tri[:, 1]-old_tri[:, 0], old_tri[:, 2]-old_tri[:, 0])
            n1 = np.cross(new_tri[:, 1]-new_tri[:, 0], new_tri[:, 2]-new_tri[:, 0])
            length0, length1 = np.linalg.norm(n0, axis=1), np.linalg.norm(n1, axis=1)
            valid = length0 > 1e-12
            orientation = (n0*n1).sum(1)[valid] / (length0[valid]*length1[valid])
            assert orientation.min() > 0 and np.all(length1[valid] > 1e-12)
            donors = None
            if si == row['skin_surface']:
                old_uv = accessor(before, bb, old['attributes']['TEXCOORD_0'])
                uv = accessor(after, ab, new['attributes']['TEXCOORD_0'])
                assert np.array_equal(uv[~moved], old_uv[~moved]) and np.array_equal(uv[:, 1], old_uv[:, 1])
                assert np.max(abs((uv[:, 0].astype(float)-old_uv[:, 0])-dx)) < 7e-8
                # Real face-interior source alpha, not just opaque vertices.
                selected = tri[moved[tri].any(1)]
                coords = []
                for s in np.linspace(0, 1, 9):
                    for t in np.linspace(0, 1-s, 9):
                        coords.append((uv[selected] * np.array([1-s-t, s, t])[None, :, None]).sum(1))
                q = np.concatenate(coords)
                xy = np.clip(np.floor(q*[w, h]).astype(int), [0, 0], [w-1, h-1])
                alpha = pixel[xy[:, 1], xy[:, 0], 3]
                assert alpha.min() >= 250, 'New outer lip donor entered transparent source'
                donors = {'samples': len(alpha), 'minimum_alpha': int(alpha.min())}
            triangles.append(tri + sum(len(v) for v in vertices))
            vertices.append(new_pos)
            masks.append(moved)
            part_reports.append({'surface': si, 'moved_vertices': int(moved.sum()),
                                 'minimum_face_normal_dot': float(orientation.min()),
                                 'minimum_area_ratio': float((length1[valid]/length0[valid]).min()),
                                 'minimum_jxx_at_vertices': float(jxx.min()), 'source_donors': donors})
        cross = crossing(np.concatenate(vertices).astype(float), np.concatenate(triangles), np.concatenate(masks))
        assert cross['proper_crossings'] == cross['coplanar_positive_area_overlap_pairs'] == 0, cross
        result.update(ok=True, parts=part_reports, float32_crossing=cross,
                      preserved='YZ/front lips/unrelated meshes/rig/animations/indices/PNG; actual interface single closed loop',
                      limits='Remaining source band is a frozen appearance allowance, not biological tissue thickness. Actual views, skin opacity, motion and fin gates remain required.')
        reports.append(result)
    ok = all(r['ok'] for r in reports)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps({'schema_version': 1, 'ok': ok,
                                  'status': 'done' if ok else 'failed',
                                  'next_action': 'human_review' if ok else 'fix_input',
                                  'records': reports, 'plan_sha256': sha(a.plan),
                                  'script_sha256': sha(__file__)}, indent=2)+'\n')
    print(json.dumps({'ok': ok, 'records': [{k: r[k] for k in ('species', 'actual_corner_source_x', 'remaining_source_band_px', 'ok')} for r in reports]}))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
