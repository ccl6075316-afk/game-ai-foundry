"""Regression for the rejected pointed oral arc and repeated caudal foil peaks.

This is a finite geometric diagnostic, not biological metrology or image approval.
The prior user-rejected candidate is required as a real negative control.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / 'portable'))
from glb_io import read_glb, arrays, sha


def measure(folder):
    model = folder / 'fish.glb'
    doc, blob = read_glb(model)
    node = next(n for n in doc['nodes'] if n.get('name') == 'Caudal')
    parts = doc['meshes'][node['mesh']]['primitives']
    assert len(parts) == 1
    part = parts[0]
    vertices = arrays(doc, blob, part['attributes']['POSITION'])
    triangles = arrays(doc, blob, part['indices']).reshape(-1, 3)
    edges = np.unique(np.sort(np.concatenate([
        triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]
    ]), axis=1), axis=0)
    a, b = vertices[edges[:, 0]], vertices[edges[:, 1]]
    heights = np.linspace(vertices[:, 1].min() + 1e-6,
                          vertices[:, 1].max() - 1e-6, 601)
    widths = []
    for height in heights:
        mask = (a[:, 1] - height) * (b[:, 1] - height) < 0
        x, y = a[mask], b[mask]
        points = x + (y - x) * ((height - x[:, 1]) / (y[:, 1] - x[:, 1]))[:, None]
        assert len(points), 'Empty actual caudal section'
        widths.append(float(np.max(abs(points[:, 2]))))
    difference = np.diff(widths)
    signs = np.sign(difference[abs(difference) > 1e-8])
    peaks = int(((signs[:-1] > 0) & (signs[1:] < 0)).sum())
    mouth_report = folder / 'mouth-local.validation.json'
    mouth = json.loads(mouth_report.read_text(encoding='utf8'))
    assert mouth['ok'] and Path(mouth['source']).resolve() == (folder / 'fish.blend').resolve()
    turns = {}
    for name, row in mouth['mouth_rims'].items():
        points = np.array(row['points'])
        center = abs(points[:, 1]).argmin()
        assert 0 < center < len(points) - 1
        x, y = points[center] - points[center-1], points[center+1] - points[center]
        turns[name] = float(np.degrees(np.arccos(np.clip(
            x @ y / np.linalg.norm(x) / np.linalg.norm(y), -1, 1))))
    return dict(ok=peaks == 1 and max(turns.values()) <= 20,
                model_sha256=sha(model), editable_source_sha256=sha(folder / 'fish.blend'),
                mouth_probe_sha256=sha(mouth_report), caudal_projected_thickness_peaks=peaks,
                actual_oral_center_turn_degrees=turns,
                tail_sections=[dict(height=float(z), half_width=w) for z, w in zip(heights, widths)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--rejected', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists()
    current, rejected = measure(args.candidate.resolve()), measure(args.rejected.resolve())
    result = dict(ok=current['ok'] and not rejected['ok'],
                  kind='actual_oral_center_and_projected_caudal_foil_regression',
                  current=current, rejected=rejected, checker_sha256=sha(__file__),
                  limits='601 exact triangle-edge height sections diagnose the edge-on caudal envelope, not every free-face curvature. Actual upper/lower 3D oral center turns, not nose vertices. One caudal peak and20-degree oral turn are explicit repair criteria, not biological measurements. Both-side/oblique actual gray/textured review, mouth depth, full fin roots and posed membrane checks remain mandatory.',
                  formal_acceptance=False)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(ok=result['ok'], current_peaks=current['caudal_projected_thickness_peaks'],
                         rejected_peaks=rejected['caudal_projected_thickness_peaks'],
                         current_oral_turns=current['actual_oral_center_turn_degrees'],
                         rejected_oral_turns=rejected['actual_oral_center_turn_degrees'])))
    sys.exit(0 if result['ok'] else 1)
