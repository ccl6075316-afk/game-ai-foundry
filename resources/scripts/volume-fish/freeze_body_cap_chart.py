"""Freeze whole-body sections for dorsal/ventral native-source donor charts.

Does not alter the model or image. Material donors remain an artistic inference;
section freezing does not approve their appearance or establish biological color.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb, accessor


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['model', 'parameters', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    params = json.loads(a.parameters.read_text())
    model_sha = hashlib.sha256(a.model.read_bytes()).hexdigest()
    assert model_sha == params['model_sha256'], 'Stale model parameters'
    d, b = read_glb(a.model)
    mesh = next(n['mesh'] for n in d['nodes'] if n.get('name') == params['mesh'])
    primitive = d['meshes'][mesh]['primitives'][params['surface']]
    v = accessor(d, b, primitive['attributes']['POSITION'])
    triangles = v[accessor(d, b, primitive['indices']).reshape(-1, 3)]
    count = params['section_count']
    assert 2 <= count <= 128
    sections = []
    for x in np.linspace(v[:, 0].min() + .00002, v[:, 0].max() - .00002, count):
        hits = []
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            u, w = triangles[:, i], triangles[:, j]
            selected = ((u[:, 0] <= x) & (w[:, 0] > x)) | ((w[:, 0] <= x) & (u[:, 0] > x))
            u, w = u[selected], w[selected]
            t = (x - u[:, 0]) / (w[:, 0] - u[:, 0])
            hits.extend(u + t[:, None] * (w - u))
        assert hits, f'Empty body section at {x}'
        pts = np.asarray(hits)
        low, high = pts[:, 1].min(), pts[:, 1].max()
        sections.append([float(x), float((low + high) / 2), float((high - low) / 2), float(abs(pts[:, 2]).max())])
    chart = {k: params[k] for k in ['model_sha256', 'interior_margin_px', 'transverse_scale', 'blend_across', 'inference']}
    chart['cross_sections'] = sections
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(chart, indent=2) + '\n')
    print(json.dumps({'ok': True, 'status': 'done', 'next_action': 'human_review', 'model_sha256': model_sha, 'sections': count, 'output': str(a.output), 'geometry_and_source_unchanged': True}))


if __name__ == '__main__':
    main()
