"""Read-only 2D preflight for author_front_mouth_chart's native lip transport.

Rasterize each source segment's complete outward strip into nearest-texel cells.
The footprint is conservative at cell/strip boundaries. It cannot validate the
3D rim, semantic tissue, appearance or the actual baked sample set.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strip_cells(start, end, normal, width, size):
    """Cells intersecting a strip: separating-axis test, including ties."""
    w, h = size
    quad = np.array([start, end, end + normal * width, start + normal * width])
    corners = np.rint(quad).astype(int)
    outside = (corners[:, 0] < 0) | (corners[:, 0] >= w) | (corners[:, 1] < 0) | (corners[:, 1] >= h)
    if outside.any():
        return None, quad[outside].tolist()
    lo = np.maximum(np.ceil(quad.min(0) - .5).astype(int), 0)
    hi = np.minimum(np.floor(quad.max(0) + .5).astype(int), [w - 1, h - 1])
    yy, xx = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
    cells = np.c_[xx.ravel(), yy.ravel()]
    tangent = end - start
    tangent /= np.linalg.norm(tangent)
    inside = np.ones(len(cells), bool)
    for axis in [np.array([1., 0.]), np.array([0., 1.]), tangent, normal]:
        q = quad @ axis
        c = cells @ axis
        radius = .5 * np.abs(axis).sum()
        inside &= (c + radius >= q.min() - 1e-9) & (c - radius <= q.max() + 1e-9)
    return cells[inside], []


def check(config, root=ROOT):
    source = (root / config['source']).resolve()
    if sha(source) != config['source_sha256']:
        raise ValueError('Source hash changed')
    with Image.open(source) as image:
        rgba = np.asarray(image.convert('RGBA'))
    h, w = rgba.shape[:2]
    if [w, h] != config['source_size']:
        raise ValueError('Source size differs from config')
    c = config['lip_source_transport']
    if c.get('transport_oral'):
        raise ValueError('transport_oral remaps into the cavity; this outward-lip preflight cannot approve it')
    if not 0 <= c['source_start_x'] < c['source_end_x'] < w:
        raise ValueError('Bounded native source interval required')
    domain = c['complete_native_lip']
    rows = []
    for name, sign in [('upper', -1), ('lower', 1)]:
        curve = np.asarray(config[name + '_inner_edge_px'], float)
        if curve.ndim != 2 or curve.shape[1] != 2 or not np.isfinite(curve).all():
            raise ValueError('Finite 2D donor curve required')
        curve = curve[(curve[:, 0] >= c['source_start_x']) & (curve[:, 0] <= c['source_end_x'])]
        if len(curve) < 3:
            raise ValueError('Need at least three in-domain source points, as in the author')
        outer = float(domain[name + '_width_px']) + float(domain['outer_fade_px'])
        inner = (float(c['inner_lip_return_px']) + float(c['inner_lip_fade_px'])) * float(c.get('inner_lip_source_across_scale', .5))
        width = max(outer, inner)
        if not np.isfinite(width) or min(domain[name + '_width_px'], domain['outer_fade_px'], width) <= 0:
            raise ValueError('Positive finite lip width/fade required')
        cells, outside = set(), []
        for start, end in zip(curve, curve[1:]):
            delta = end - start
            length = np.linalg.norm(delta)
            if length <= 1e-12:
                raise ValueError('Zero-length donor segment')
            normal = np.array([-delta[1], delta[0]]) / length * sign
            selected, bad = strip_cells(start, end, normal, width, (w, h))
            if bad:
                outside.append({'source_segment_px': [start.tolist(), end.tolist()], 'outside_strip_corners_px': bad})
            else:
                cells.update(map(tuple, selected.tolist()))
        pixels = np.array(sorted(cells), dtype=int).reshape(-1, 2)
        alpha = rgba[pixels[:, 1], pixels[:, 0], 3] / 255. if len(pixels) else np.array([])
        invalid = pixels[alpha < .95]
        rows.append({'lip': name, 'ok': not outside and not len(invalid), 'source_curve_points': len(curve),
                     'maximum_outward_distance_px': width, 'tested_native_texel_cells': len(pixels),
                     'invalid_alpha_count': len(invalid), 'first_invalid_alpha_pixels_xy': invalid[:12].tolist(),
                     'out_of_bounds_segment_count': len(outside), 'first_out_of_bounds_segments': outside[:3]})
    implementations = [Path(__file__).parent.parent / name for name in ['author_front_mouth_chart.py', 'rim_material_transport.py']]
    return {'ok': all(row['ok'] for row in rows), 'kind': 'native_lip_donor_2d_preflight',
            'source': {'path': str(source), 'sha256': sha(source)}, 'source_size': [w, h],
            'sampling_implementations': {str(p): sha(p) for p in implementations},
            'alpha_minimum': .95, 'sampling': 'Nearest np.rint; top-left image pixels, equivalent to author H-1-y lookup',
            'lips': rows, 'scope': 'Conservative complete outward source-strip footprint, including fade and inner return. '
            'No geometry/source/config writes. A pass does not validate tissue ownership, actual 3D phase/domain, baked texels, appearance or SOP. '
            'A boundary-only rejection needs actual sample evidence; do not weaken the author opacity/bounds guards.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    from parts import fresh_output
    out = fresh_output(args.output)
    if out.exists():
        raise ValueError('Fresh report required')
    config = json.loads(args.config.read_text(encoding='utf8'))
    report = check(config)
    report.update(config={'path': str(args.config.resolve()), 'sha256': sha(args.config)}, checker_sha256=sha(__file__))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'ok': report['ok'], 'report': str(out), 'lips': report['lips']}))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
