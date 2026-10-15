#!/usr/bin/env python3
"""Trace accepted side-art alpha into caudal polygons. Does not build or accept models.

Run with repository .venv Python (Pillow, NumPy, OpenCV). Example:
  .venv/bin/python resources/scripts/volume-fish/trace_tail_outline.py \
    --source accepted_side.png --profile base.json --output candidate.json --report trace.validation.json

This checks preservation of accepted illustration silhouettes, not real-fish morphometry.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def trace(alpha, max_u, min_v, max_v, max_vertices=128):
    height, width = alpha.shape
    mask = (alpha > 216).astype(np.uint8)
    mask[:, int(max_u * width):] = 0
    mask[:int(min_v * height), :] = 0
    mask[int(max_v * height):, :] = 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 4)
    if count < 2:
        raise ValueError('No connected tail alpha in requested region')
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    component = (labels == largest).astype(np.uint8)
    contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea)
    epsilon = .5
    while True:
        polygon = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
        if len(polygon) <= max_vertices:
            break
        epsilon += .25
        if epsilon > 8:
            raise ValueError('Tail outline cannot fit profile vertex budget')
    raster = np.zeros_like(mask)
    cv2.fillPoly(raster, [polygon], 1)
    overlap = int(np.sum((raster > 0) & (component > 0)))
    source_count = int(component.sum())
    model_count = int(raster.sum())
    preservation = overlap / source_count
    if preservation < .95:
        raise ValueError(f'Tail source silhouette coverage {preservation:.4f} < .95')
    return [[(float(x) + .5) / width, (float(y) + .5) / height] for x, y in polygon], {
        'roi': {'max_u': max_u, 'min_v': min_v, 'max_v': max_v},
        'alpha_threshold': 216, 'connected_component_pixels': source_count,
        'polygon_pixels': model_count, 'overlap_pixels': overlap,
        'source_preserved_fraction': preservation,
        'polygon_within_source_fraction': overlap / model_count,
        'polygon_vertices': len(polygon), 'simplification_epsilon_pixels': epsilon,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['source', 'profile', 'output', 'report']:
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--baseline-profile', type=Path, help='Optional old polygon comparison in identical fixed tail ROIs')
    parser.add_argument('--check-existing', action='store_true', help='Verify frozen output polygons and hashes without changing the profile')
    args = parser.parse_args()
    alpha = np.array(Image.open(args.source).convert('RGBA'))[:, :, 3]
    profile = json.loads(args.profile.read_text())
    report = {'schema_version': 1, 'command': 'volume.tail.trace-alpha', 'stage': 'validate',
              'status': 'done', 'next_action': 'human_review', 'ok': True, 'failures': [],
              'source_image': str(args.source.resolve()),
              'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
              'input_profile_sha256': hashlib.sha256(args.profile.read_bytes()).hexdigest(),
              'criterion': 'At least 95% accepted illustration alpha coverage in each explicit tail ROI; not an anatomical measurement or visual acceptance.',
              'lobes': {}}
    for name, roi in [('CaudalUpper', (.180, 0, .550)), ('CaudalLower', (.177, .535, 1))]:
        polygon, stats = trace(alpha, *roi)
        fin = next(fin for fin in profile['fins'] if fin['name'] == name)
        if args.check_existing and fin['polygon'] != polygon:
            raise ValueError('Existing tail polygon differs from current source trace: ' + name)
        fin['polygon'] = polygon
        stats['polygon_sha256'] = hashlib.sha256(json.dumps(polygon, separators=(',', ':')).encode()).hexdigest()
        report['lobes'][name] = stats
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.check_existing:
        if args.output.resolve() != args.profile.resolve():
            raise ValueError('--check-existing output must identify the same frozen profile')
    else:
        args.output.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n')
    if args.baseline_profile:
        baseline = json.loads(args.baseline_profile.read_text())
        fixed = {'baseline_profile': str(args.baseline_profile.resolve()),
                 'baseline_profile_sha256': hashlib.sha256(args.baseline_profile.read_bytes()).hexdigest(),
                 'method': 'Identical pixel-center point-in-polygon rasterization and alpha>216 for both profiles; fixed u<.16, upper v<.535, lower v>.55.', 'lobes': {}}
        height, width = alpha.shape
        for name, start, end in [('CaudalUpper', 0, .535), ('CaudalLower', .55, 1)]:
            xx, yy = np.meshgrid((np.arange(int(.16*width))+.5)/width,
                                 (np.arange(int(start*height), int(end*height))+.5)/height)
            source = alpha[int(start*height):int(end*height), :int(.16*width)] > 216
            values = {}
            for label, candidate in [('baseline', baseline), ('candidate', profile)]:
                polygon = next(f['polygon'] for f in candidate['fins'] if f['name']==name)
                inside = np.zeros_like(source, dtype=bool)
                for a,b in zip(polygon, polygon[1:]+polygon[:1]):
                    if a[1] == b[1]: continue
                    inside ^= ((a[1]>yy)!=(b[1]>yy)) & (xx<(b[0]-a[0])*(yy-a[1])/(b[1]-a[1])+a[0])
                overlap = int(np.sum(source & inside))
                values[label] = {'source_pixels': int(source.sum()), 'polygon_pixels': int(inside.sum()),
                                 'overlap_pixels': overlap, 'source_preserved_fraction': overlap/int(source.sum())}
            fixed['lobes'][name] = values
        report['fixed_roi_comparison'] = fixed
    report['freshness_verified'] = args.check_existing
    report['output_profile'] = str(args.output.resolve())
    report['output_profile_sha256'] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
