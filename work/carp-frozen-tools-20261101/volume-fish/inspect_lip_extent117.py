"""Inspect existing skin/oral boundaries over exact embedded source pixels.

This is a source-plane diagnostic, not a classifier of painted lip anatomy or
proof of final shader attachment. Unknown topologies stay explicitly unknown.
"""
import argparse
import base64
import hashlib
import html
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from freeze_surface_ownership import accessor, read_glb


STANDARD = {
    'zander', 'sea_bass', 'grass_carp', 'bluegill', 'african_catfish',
    'carp', 'brown_trout', 'crucian', 'nile_tilapia', 'atlantic_salmon',
    'yellow_croaker', 'red_emperor', 'rainbow_trout', 'black_seabream',
    'red_seabream',
}


def key(v):
    return tuple(np.round(v.astype(float), 7))


def boundary(d, b, primitive):
    pos = accessor(d, b, primitive['attributes']['POSITION'])
    tri = accessor(d, b, primitive['indices']).reshape(-1, 3)
    edges = Counter()
    for face in tri:
        for i, j in zip(face, np.roll(face, -1)):
            a, z = key(pos[i]), key(pos[j])
            if a != z:
                edges[tuple(sorted((a, z)))] += 1
    return {edge for edge, count in edges.items() if count == 1}


def inspect(model):
    d, b = read_glb(model)
    body = next(n for n in d['nodes'] if n.get('name') == 'Closed_body')
    assert not any(k in body for k in ('matrix', 'translation', 'rotation', 'scale'))
    parts = d['meshes'][body['mesh']]['primitives']
    assert len(parts) == 2, 'Different topology requires explicit interface'
    boundaries = [boundary(d, b, p) for p in parts]
    common = boundaries[0] & boundaries[1]
    assert common and common == boundaries[0] == boundaries[1]
    graph = defaultdict(list)
    for a, z in common:
        graph[a].append(z)
        graph[z].append(a)
    assert all(len(v) == 2 for v in graph.values())
    first = min(graph)
    ordered, previous, current = [first], None, first
    while True:
        following = next(v for v in graph[current] if v != previous)
        if following == first:
            break
        assert following not in ordered
        ordered.append(following)
        previous, current = current, following
    assert len(ordered) == len(graph)
    ordered.append(first)
    skin = parts[0]
    material = d['materials'][skin['material']]
    texture = material['pbrMetallicRoughness']['baseColorTexture']['index']
    source = d['images'][d['textures'][texture]['source']]
    view = d['bufferViews'][source['bufferView']]
    raw = b[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
    w, h = Image.open(io.BytesIO(raw)).size
    pos = accessor(d, b, skin['attributes']['POSITION'])
    uv = accessor(d, b, skin['attributes']['TEXCOORD_0'])
    lookup = defaultdict(list)
    for v, t in zip(pos, uv):
        lookup[key(v)].append((t * [w, h]).tolist())
    points = np.asarray(ordered)
    xy = np.c_[(points[:, 0] + .5) * w, h * .5 - points[:, 1] * w]
    # Keep all raw UV matches rather than selecting a seemingly best chart.
    uv_matches = [lookup[v] for v in ordered]
    row = {
        'species': model.stem, 'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
        'source_png_sha256': hashlib.sha256(raw).hexdigest(), 'source_size': [w, h],
        'common_edges': len(common), 'physical_boundary_native': points.tolist(),
        'physical_boundary_source_plane_px': xy.tolist(), 'skin_boundary_uv_matches_px': uv_matches,
        'posterior_corner_u': float(points[:, 0].min() + .5),
        'painted_lower_lip_identity': 'unclassified', 'eligible_for_extension': False,
    }
    return row, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows, cards = [], []
    for model in sorted(args.models.glob('*.glb')):
        if model.stem not in STANDARD:
            rows.append({'species': model.stem, 'painted_lower_lip_identity': 'unclassified',
                         'eligible_for_extension': False, 'interface': 'special_topology_unknown'})
            continue
        row, raw = inspect(model)
        rows.append(row)
        w, h = row['source_size']
        pts = ' '.join(f'{x:.5f},{y:.5f}' for x, y in row['physical_boundary_source_plane_px'])
        data = base64.b64encode(raw).decode()
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{w*.8} {h*.24} {w*.2} {h*.6}">'
               f'<image width="{w}" height="{h}" href="data:image/png;base64,{data}"/>'
               f'<polyline class="rim" points="{pts}" fill="none" stroke="#39caff" stroke-width="1"/>'
               '</svg>')
        path = args.output / (model.stem + '.svg')
        path.write_text(svg)
        row['svg'] = str(path)
        cards.append(f'<section><h2>{html.escape(model.stem)}</h2>{svg}</section>')
    page = '''<!doctype html><meta charset="utf-8"><title>原材质 / 实体口缘</title>
<style>body{margin:0;background:#1b2e38;color:#eff8fa;font:15px system-ui}header{height:65px;padding:10px;box-sizing:border-box}h1{font-size:19px;margin:0}p{margin:3px 0}section{margin:0 10px}h2{font-size:16px;margin:4px 0}svg{display:block;width:100%;height:255px;background:#14252b}main{display:grid;grid-template-columns:1fr 1fr}.hidden{display:none}nav{position:absolute;top:12px;right:15px}button{padding:6px;margin-left:8px}.off .rim{display:none}</style>
<header><h1>原始材质与实际实体口缘（蓝线）</h1><p>原PNG像素不变；蓝线是原生XYZ的源平面投影，非唇线语义识别、非最终shader取样证明。</p><nav><span id="counter"></span><button onclick="show(page-1)">上一组</button><button onclick="show(page+1)">下一组</button><button onclick="document.body.classList.toggle('off')">开关蓝线</button></nav></header><main>'''
    page += ''.join(cards) + '''</main><script>let page=0;const cards=[...document.querySelectorAll('section')];function show(n){page=Math.max(0,Math.min(Math.ceil(cards.length/4)-1,n));cards.forEach((e,i)=>e.classList.toggle('hidden',Math.floor(i/4)!==page));document.getElementById('counter').textContent=(page+1)+'/'+Math.ceil(cards.length/4)}show(0)</script>'''
    (args.output / 'index.html').write_text(page)
    report = {'schema_version': 1, 'ok': True, 'command': 'fish.inspect-lip-extent117',
              'status': 'done', 'next_action': 'human_review', 'records': rows,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Read-only embedded PNG and actual welded interface. No model or source mutation; no anatomy classification.'}
    (args.output / 'extent.validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'ok': True, 'records': len(rows), 'measured': sum('common_edges' in r for r in rows)}))


if __name__ == '__main__':
    main()
