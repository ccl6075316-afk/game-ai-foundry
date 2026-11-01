"""Compare actual same-pose captures; pixel differences do not constitute visual approval."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--captures-dir', type=Path, help='New capture version; must be inside this experiment')
    parser.add_argument('--baseline-dir', type=Path, help='Reuse immutable baseline capture directory after hash/camera checks')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    allowed = root / 'projects/fishing-2d/experiments/nile-dorsal-route-trial/round10-material-performance'
    review = args.review.resolve()
    if review != allowed.resolve():
        raise ValueError('Explicit current experiment required')
    capture_dir = args.captures_dir.resolve() if args.captures_dir else review / 'captures'
    baseline_dir = args.baseline_dir.resolve() if args.baseline_dir else capture_dir / 'baseline9'
    if not capture_dir.is_relative_to(review) or not baseline_dir.is_relative_to(review):
        raise ValueError('Capture inputs/output must remain inside the isolated experiment')
    variants = ['baseline9', 'merged-mask', 'merged-opaque']
    captures = {}
    sources = {}
    for variant in variants:
        path = (baseline_dir if variant == 'baseline9' else capture_dir / variant) / 'capture.validation.json'
        report = json.loads(path.read_text())
        execution = json.loads(path.with_name('execution.validation.json').read_text())
        assert report['ok'] and execution['ok'] and execution['report_sha256'] == sha(path)
        for input_path, digest in execution['frozen_inputs'].items():
            assert sha(input_path) == digest, ('Stale capture dependency', input_path)
        captures[variant] = {row['name']: row for row in report['captures']}
        sources[str(path)] = sha(path)
        for row in report['captures']:
            assert sha(row['path']) == row['sha256']
    labels = list(captures['baseline9'])
    assert all(set(captures[name]) == set(labels) for name in variants)
    rows = []
    for label in labels:
        baseline = captures['baseline9'][label]
        a = np.asarray(Image.open(baseline['path']).convert('RGB')).astype(np.int16)
        for variant in variants[1:]:
            candidate = captures[variant][label]
            assert all(baseline[key] == candidate[key] for key in ('pose_sha256', 'camera_size', 'focus', 'direction'))
            b = np.asarray(Image.open(candidate['path']).convert('RGB')).astype(np.int16)
            assert a.shape == b.shape
            delta = np.abs(a - b)
            any_channel = delta.max(axis=2)
            rows.append({'label': label, 'variant': variant, 'pixels': a.shape[0] * a.shape[1], 'changed_pixels_any': int((any_channel > 0).sum()), 'changed_pixels_gt1': int((any_channel > 1).sum()), 'changed_pixels_gt8': int((any_channel > 8).sum()), 'maximum_channel_difference': int(delta.max()), 'mean_absolute_channel_difference': float(delta.mean())})
    output = capture_dir / 'comparison'
    output.mkdir(exist_ok=True)
    sheets = []
    # Same native renders, only presentation thumbnails. Originals retained.
    for pose in ('rest', 'Swim'):
        for framing in ('whole', 'head', 'fins'):
            names = [label for label in labels if label.startswith(pose + '-' + framing + '-')]
            sheet = Image.new('RGB', (1600, len(names) * 247 + 28), '#25343c')
            draw = ImageDraw.Draw(sheet)
            for column, title in enumerate(['baseline 9 surfaces', 'merged MASK', 'merged OPAQUE', 'OPAQUE vs baseline x4']):
                draw.text((column * 400 + 5, 5), title, fill='white')
            for row_index, label in enumerate(names):
                arrays = []
                for column, variant in enumerate(variants):
                    image = Image.open(captures[variant][label]['path']).convert('RGB')
                    arrays.append(np.asarray(image).astype(np.int16))
                    image.thumbnail((400, 225), Image.Resampling.NEAREST)
                    sheet.paste(image, (column * 400, 28 + row_index * 247 + 20))
                difference = Image.fromarray(np.clip(np.abs(arrays[0] - arrays[2]) * 4, 0, 255).astype(np.uint8))
                difference.thumbnail((400, 225), Image.Resampling.NEAREST)
                sheet.paste(difference, (1200, 28 + row_index * 247 + 20))
                draw.text((5, 28 + row_index * 247), label, fill='white')
            path = output / (pose + '-' + framing + '.png')
            sheet.save(path)
            sheets.append({'path': str(path), 'sha256': sha(path)})
    summary = {}
    for variant in variants[1:]:
        selected = [row for row in rows if row['variant'] == variant]
        summary[variant] = {'views': len(selected), 'changed_pixels_gt1_total': sum(row['changed_pixels_gt1'] for row in selected), 'changed_pixels_gt8_total': sum(row['changed_pixels_gt8'] for row in selected), 'maximum_channel_difference': max(row['maximum_channel_difference'] for row in selected), 'worst_views_gt8': sorted(selected, key=lambda row: row['changed_pixels_gt8'], reverse=True)[:5]}
    result = {'ok': True, 'kind': 'fish_material_same_pose_pixel_comparison', 'frozen_inputs': sources, 'summary': summary, 'rows': rows, 'sheets': sheets, 'scope': 'Verified capture hashes and exact pose/camera metadata. Counts characterize actual raster changes, not automatic visual or fish acceptance. Fourfold displayed difference is diagnostic only. All original PNGs retained.'}
    (output / 'comparison.validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': True, 'summary': summary, 'sheets': [row['path'] for row in sheets]}))


if __name__ == '__main__':
    main()
