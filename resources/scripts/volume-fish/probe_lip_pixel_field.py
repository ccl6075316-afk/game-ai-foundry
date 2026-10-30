"""Inspect a raster lip donor for two-dimensional, native-size brush clusters.

This is a local artistic regression probe, not fish acceptance. Input columns
represent distance along the lip; rows represent distance across its skin band.
An old nearest-scaled preview may be decoded with --native-size and --along-axis.
No painter implementation or plan flags are imported. A passing donor still
needs verification of its use in the atlas, lip joins, and actual model views.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interior_runs(line):
    """Exact palette runs, excluding the two potentially cropped edge cells."""
    cuts = np.flatnonzero(np.any(line[1:] != line[:-1], axis=1)) + 1
    return np.diff(np.r_[0, cuts, len(line)])[1:-1].tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-size', type=int, nargs=2, metavar=('WIDTH', 'HEIGHT'))
    parser.add_argument('--along-axis', choices=['x', 'y'], default='x')
    parser.add_argument('--brush-cell-px', type=int, default=6)
    parser.add_argument('--color-delta', type=int, default=12)
    parser.add_argument('--min-varying-band-fraction', type=float, default=.25)
    parser.add_argument('--evidence', type=Path, action='append', default=[])
    args = parser.parse_args()
    if args.brush_cell_px < 2:
        parser.error('--brush-cell-px must be at least 2')
    raw = np.array(Image.open(args.input).convert('RGBA'))
    field = raw
    decoded_preview = False
    if args.native_size:
        nw, nh = args.native_size
        if nw < 1 or nh < 1 or raw.shape[1] % nw or raw.shape[0] % nh:
            parser.error('Preview must be an integer nearest enlargement of native size')
        sx, sy = raw.shape[1] // nw, raw.shape[0] // nh
        field = raw[::sy, ::sx]
        if not np.array_equal(raw, field.repeat(sy, 0).repeat(sx, 1)):
            parser.error('Preview is not an exact nearest enlargement; use the native field')
        decoded_preview = True
    if args.along_axis == 'y':
        field = field.transpose(1, 0, 2)
    rgb = field[:, :, :3].astype(int)
    # A one-dimensional stripe has zero along-lip span in every across-width row.
    # Significant variation is required over part of the width, so a lone noisy
    # pixel or an isolated marker cannot rescue a repeated profile.
    along_spans = np.max(np.ptp(rgb, axis=1), axis=1)
    across_spans = np.max(np.ptp(rgb, axis=0), axis=1)
    varying_fraction = float(np.mean(along_spans >= args.color_delta))
    across_fraction = float(np.mean(across_spans >= args.color_delta))
    along_profiles = len({field[:, x].tobytes() for x in range(field.shape[1])})
    runs = {
        'along': [n for row in field for n in interior_runs(row)],
        'across': [n for column in field.transpose(1, 0, 2) for n in interior_runs(column)],
    }
    run_summary = {}
    for axis, lengths in runs.items():
        run_summary[axis] = {
            'interior_color_runs': len(lengths),
            'minimum_native_px': min(lengths) if lengths else None,
            'shorter_than_brush_cell': sum(n < args.brush_cell_px for n in lengths),
        }
    checks = {
        'opaque_donor': bool(np.all(field[:, :, 3] == 255)),
        'independent_along_lip_variation': bool(
            varying_fraction >= args.min_varying_band_fraction and along_profiles >= 3
        ),
        'across_skin_width_variation': bool(across_fraction >= .5),
        'minimum_native_brush_cells': bool(
            any(runs.values()) and all(
                n >= args.brush_cell_px for lengths in runs.values() for n in lengths
            )
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        'kind': 'lip_native_raster_cluster_regression',
        'ok': not failures,
        'status': 'passed' if not failures else 'failed',
        'formal_acceptance': False,
        'scope': 'Raster donor only; does not prove atlas application, joins, or model appearance.',
        'input': {'path': str(args.input.resolve()), 'sha256': digest(args.input)},
        'evidence': [{'path': str(p.resolve()), 'sha256': digest(p)} for p in args.evidence],
        'decoded_exact_nearest_preview': decoded_preview,
        'native_along_by_across_px': [field.shape[1], field.shape[0]],
        'thresholds': {
            'brush_cell_native_px': args.brush_cell_px,
            'significant_RGB_channel_span': args.color_delta,
            'minimum_varying_across_band_fraction': args.min_varying_band_fraction,
            'edge_runs': 'Excluded because an image may crop a partial brush cell.',
        },
        'measurements': {
            'independent_along_profiles': along_profiles,
            'band_fraction_with_significant_along_variation': varying_fraction,
            'along_fraction_with_significant_across_variation': across_fraction,
            'color_runs': run_summary,
        },
        'checks': checks,
        'failures': failures,
    }
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'ok': report['ok'], 'failures': failures, 'output': str(args.output.resolve())}))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
