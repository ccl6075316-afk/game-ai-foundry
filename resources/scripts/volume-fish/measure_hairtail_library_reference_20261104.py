"""Measure the inspected LargeheadHairtail artistic rest mesh, never a fish asset.

Reuses the retained UnityPy 1.25.4 transform extraction report (the bundle has a
32-byte duplicate UnityFS prefix). This does not play animation or assert species
identity. Output is confined to this fish's experiment tree and must be new.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from audit_transverse_width import section


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(obj, transform_report, bundle, output):
    allowed = ROOT / 'projects/fishing-2d/experiments/hairtail-static-merge'
    assert output.is_relative_to(allowed) and not output.exists(), 'new hairtail output required'
    transforms = json.loads(transform_report.read_text(encoding='utf-8-sig'))
    assert transforms['bundle_sha256'] == digest(bundle)
    assert len(transforms['transforms']) == 51
    assert all(abs(v - 1) < 1e-6 for t in transforms['transforms'] for v in t['scale'].values())
    vertices, groups = [], {}
    group = 'default'
    for line in obj.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == 'v':
            vertices.append(list(map(float, words[1:4])))
        elif words[0] == 'g':
            group = words[1]
        elif words[0] == 'f':
            ids = [int(w.split('/')[0]) - 1 for w in words[1:]]
            assert len(ids) == 3
            groups.setdefault(group, []).append(ids)
    vertices = np.array(vertices)
    assert sum(map(len, groups.values())) == 3000
    faces = np.array(groups['LargeheadHairtail_0'])
    _, inverse = np.unique(np.round(vertices, 7), axis=0, return_inverse=True)
    ids = inverse[faces]
    row = np.r_[ids[:, 0], ids[:, 1], ids[:, 2]]
    col = np.r_[ids[:, 1], ids[:, 2], ids[:, 0]]
    graph = coo_matrix((np.ones(len(row)), (row, col)), shape=(inverse.max() + 1,) * 2)
    _, labels = connected_components(graph, directed=False)
    face_labels = labels[ids[:, 0]]
    components, counts = np.unique(face_labels, return_counts=True)
    body = faces[face_labels == components[np.argmax(counts)]]
    assert len(body) == 2068, 'review changed body/eye/tooth membership before reuse'
    # Anatomical interpretation was visually inspected in mesh-local projections.
    # Original local +Y is anterior-to-posterior; X transverse, Z vertical.
    positions = vertices[:, [1, 2, 0]]
    points = positions[np.unique(body)]
    low, high = points[:, 0].min(), points[:, 0].max()
    length = high - low
    stations = np.unique(np.r_[np.linspace(.001, .15, 31), np.linspace(.15, .99, 85)])
    rows = []
    for t in stations:
        cross = section(positions, body.reshape(-1), low + t * length)
        width, height = np.ptp(cross[:, 2]), np.ptp(cross[:, 1])
        rows.append(dict(s_from_anterior_axis=float(t), width_over_axis=float(width / length),
                         height_over_axis=float(height / length), width_height_ratio=float(width / height)))
    inputs = {role: {'path': str(p), 'sha256': digest(p)} for role, p in
              [('reference_obj', obj), ('transform_report', transform_report), ('bundle', bundle), ('implementation', Path(__file__))]}
    report = dict(ok=True, kind='local_library_mesh_local_artistic_reference_sections', inputs=inputs,
                  source_name='LargeheadHairtail', scientific_name=None, identity='unverified',
                  body_selection=dict(group='LargeheadHairtail_0', connected_triangles=2068,
                                      weld_coordinate_decimals=7, eyes_teeth_and_fins_excluded=True),
                  normalization=dict(axis='mesh local +Y, anterior=minY, tail=maxY', length=float(length),
                                     length_type='visible body nose-to-filament-tip engineering axis, not SL or biological TL',
                                     all_51_node_local_scales_unit=True, scene_animation_playback_verified=False),
                  sections=rows, width_peak=max(rows, key=lambda r: r['width_over_axis']),
                  limitations=['Game art, not biological measurements or identity approval.',
                               'Geometric stations are not anatomical lip/eye/gill landmarks.',
                               'Library default jaw opening is not the project target.',
                               'No source topology or production asset is authored here.'])
    output.mkdir(parents=True)
    (output / 'sections.validation.json').write_text(json.dumps(report, indent=2) + '\n')
    image = Image.new('RGB', (1600, 500), 'white')
    draw = ImageDraw.Draw(image)
    for row_index, axes in enumerate([(1, 2), (1, 0)]):
        for color, (name, triangles) in zip(['#0050a0', '#d06000', '#10a040'], groups.items()):
            for triangle in triangles:
                xy = [(int(60 + (vertices[i, axes[0]] + 1.05) * 450),
                       int(row_index * 250 + 180 - vertices[i, axes[1]] * 500)) for i in triangle]
                draw.line(xy + [xy[0]], fill=color, width=1)
        draw.text((20, row_index * 250 + 10), str(axes), fill='black')
    image.save(output / 'mesh-local-projections.png')
    return {'ok': True, 'output': str(output), 'width_peak': report['width_peak'], 'sections': len(rows)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['obj', 'transform-report', 'bundle', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(measure(args.obj.resolve(), args.transform_report.resolve(), args.bundle.resolve(), args.output.resolve())))
