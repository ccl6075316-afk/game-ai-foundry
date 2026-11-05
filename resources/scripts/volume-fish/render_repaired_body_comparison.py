"""Draw source-bound before/raw-reference/current finite body-top comparisons.

Uses the frozen compact baseline projection and a current cold GLB. This is a
geometric diagnostic, not a render, anatomy approval, or physics validation.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import box, shape

from audit_body_projection_envelope import ROOT, body_triangles, project


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mask(geometry, width=520, height=240):
    image = Image.new('1', (width, height))
    draw = ImageDraw.Draw(image)
    polygons = [geometry] if geometry.geom_type == 'Polygon' else geometry.geoms
    def points(ring):
        return [(35 + (1 - x) * 450, 120 - z * 450) for x, z in ring.coords]
    for polygon in polygons:
        if polygon.geom_type != 'Polygon':
            continue
        draw.polygon(points(polygon.exterior), fill=1)
        for interior in polygon.interiors:
            draw.polygon(points(interior), fill=0)
    return np.asarray(image)


def panel(geometry, color):
    data = np.full((240, 520, 3), 248, dtype=np.uint8)
    data[mask(geometry)] = color
    return Image.fromarray(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not any(output.is_relative_to(ROOT / folder)
                                  for folder in ('work', 'output', 'projects/fishing-2d/experiments')):
        raise ValueError('Use a new output within a declared artifact directory')
    config = json.loads(args.config.read_text())
    interval_mode = config.get('display_interval', 'full')
    if interval_mode not in ('full', 'common'):
        raise ValueError('display_interval must be full or explicitly diagnostic common')
    baseline_path = Path(config['baseline_projection']['path'])
    if sha(baseline_path) != config['baseline_projection']['sha256']:
        raise ValueError('Frozen baseline projection changed')
    baseline = {row['species']: row for row in json.loads(baseline_path.read_text())['records']}
    canvas = Image.new('RGB', (2080, len(config['candidates']) * 310 + 85), '#f8f8f8')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=19)
    draw.text((25, 12), 'BODY TOP: original / raw artistic reference / current repair / overlap', font=font, fill='#203442')
    interval_note = 'Complete registered body outlines.' if interval_mode == 'full' else 'DIAGNOSTIC: cropped to common body interval.'
    draw.text((25, 42), 'Fins and separate eyes excluded. ' + interval_note + ' No shape or motion acceptance.', font=ImageFont.load_default(size=15), fill='#5d6d76')
    records = []
    for index, candidate in enumerate(config['candidates']):
        species = candidate['species']
        source = baseline[species]
        entry = {**source['sources']['before'], 'path': candidate['path'], 'sha256': candidate['sha256']}
        current, axis = project(body_triangles(entry), source['registration']['before'])
        before = shape(source['projected_geometry']['before'])
        reference = shape(source['projected_geometry']['reference'])
        complete_bounds = [list(item.bounds) for item in (before, reference, current)]
        if interval_mode == 'common':
            lower = max(item.bounds[0] for item in (before, reference, current))
            upper = min(item.bounds[2] for item in (before, reference, current))
            common = box(lower, -100, upper, 100)
            before, reference, current = [item.intersection(common) for item in (before, reference, current)]
        else:
            lower = min(item.bounds[0] for item in (before, reference, current))
            upper = max(item.bounds[2] for item in (before, reference, current))
        top = 85 + index * 310
        for column, (item, title, color) in enumerate([
                (before, 'original', [105, 121, 134]),
                (reference, 'raw reference', [221, 150, 55]),
                (current, candidate.get('label', 'repair'), [42, 124, 182])]):
            canvas.paste(panel(item, color), (column * 520, top + 45))
            draw.text((column * 520 + 22, top + 8), species + ' / ' + title, font=font, fill='#203442')
        ours, theirs = mask(current), mask(reference)
        data = np.full((240, 520, 3), 248, dtype=np.uint8)
        data[ours & theirs] = [175, 185, 192]
        data[ours & ~theirs] = [42, 124, 182]
        data[theirs & ~ours] = [221, 150, 55]
        canvas.paste(Image.fromarray(data), (1560, top + 45))
        draw.text((1582, top + 8), 'blue repair / orange reference', font=font, fill='#203442')
        records.append({'species': species, 'candidate': candidate, 'registration': axis,
                        'display_interval_mode': interval_mode,
                        'complete_registered_bounds': complete_bounds,
                        'display_interval': [lower, upper], 'body_ownership': entry['selection']})
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    report = {'kind': 'actual_finite_body_top_comparison_drawing', 'ok': True,
              'config_sha256': sha(args.config), 'baseline_projection_sha256': sha(baseline_path),
              'image': {'path': str(output), 'sha256': sha(output)}, 'records': records,
              'scope': 'Drawing of actual finite geometric projections only. Display interval mode is explicit; full mode retains all original/raw/current registered body endpoints. No image generation or anatomy/physical acceptance.',
              'formal_acceptance': False, 'checker_sha256': sha(Path(__file__))}
    output.with_suffix('.validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'ok': True, 'image': str(output), 'fish': len(records)}))


if __name__ == '__main__':
    main()
