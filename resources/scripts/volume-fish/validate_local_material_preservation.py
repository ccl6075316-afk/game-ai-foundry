"""Compare actual baseline/candidate GPU frames outside a frozen repair mask.

The baseline must be rendered from the original game with the identical scene,
camera and pose. This check does not approve the visual quality inside the ROI.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb(path):
    return np.asarray(Image.open(path).convert('RGB'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['baseline', 'candidate', 'parameters', 'output']:
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    names = ['oblique', 'front', 'side', 'bottom', 'whole-side', 'whole-top', 'whole-bottom', 'whole-oblique', 'source-canvas']
    rows = []
    for name in names:
        files = [a.baseline / (name + '-before.png'), a.candidate / (name + '-before.png'), a.candidate / (name + '-after.png'), a.candidate / (name + '-allowed.png')]
        baseline, off, candidate, mask = [rgb(f) for f in files]
        assert baseline.shape == off.shape == candidate.shape == mask.shape
        allowed = mask.min(axis=2) > 240
        disabled_diff = np.any(baseline != off, axis=2)
        changed = np.any(baseline != candidate, axis=2)
        outside = changed & ~allowed
        rows.append({'view': name, 'size': list(baseline.shape[:2][::-1]), 'baseline_vs_disabled_changed_pixels': int(disabled_diff.sum()), 'changed_pixels': int(changed.sum()), 'outside_region_changed_pixels': int(outside.sum()), 'allowed_pixels': int(allowed.sum()), 'ok': not disabled_diff.any() and not outside.any(), 'files': [{'path': str(f.resolve()), 'sha256': sha(f)} for f in files]})
    assert any(row['changed_pixels'] > 0 for row in rows), 'No effective local repair'
    report = {'schema_version': 1, 'ok': all(row['ok'] for row in rows), 'status': 'done' if all(row['ok'] for row in rows) else 'failed', 'next_action': 'human_review' if all(row['ok'] for row in rows) else 'fix_input', 'parameters_sha256': sha(a.parameters), 'baseline_capture_receipt_sha256': sha(a.baseline / 'capture.validation.json'), 'candidate_capture_receipt_sha256': sha(a.candidate / 'capture.validation.json'), 'views': rows, 'scope': 'Exact RGB equality outside the frozen GPU-rendered local lower-chin repair region, at9 captured static views. No image registration, tolerance, crop adjustment or mask dilation.', 'limits': 'Does not approve donor quality, prove all continuous camera/time samples or establish biological colors. Review the actual ROI and image comparisons.'}
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': report['ok'], 'views': len(rows), 'outside_changed_pixels': sum(row['outside_region_changed_pixels'] for row in rows)}))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
