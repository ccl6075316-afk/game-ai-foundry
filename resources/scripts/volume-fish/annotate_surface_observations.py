"""Create vector observation overlays without changing screenshot pixels.

Input: JSON with items: species, title, screenshot, observations (label, boxes,
description). Boxes are in the original screenshot's pixel coordinates. Output
SVGs embed the exact original PNG bytes; HTML allows toggling only the vectors.
Annotations are observations, not automatically confirmed texture defects.
"""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    cards, records = [], []
    for item in plan['items']:
        source = Path(item['screenshot'])
        raw = source.read_bytes()
        with Image.open(source) as image:
            width, height = image.size
            assert image.format == 'PNG'
        data = 'data:image/png;base64,' + base64.b64encode(raw).decode()
        top, bottom = 100, 115
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height+top+bottom}" role="img">',
                 f'<title>{html.escape(item["title"])}</title>',
                 f'<rect width="{width}" height="{height+top+bottom}" fill="#142b36"/>',
                 '<g font-family="sans-serif" fill="#eff7fb">',
                 f'<text x="28" y="39" font-size="27">{html.escape(item["title"])}</text>',
                 '<text x="28" y="75" font-size="19" fill="#c6d4dc">主观观察示例：相似/镜像纹样，不是已证实的贴图断缝</text>',
                 '</g>',
                 f'<image x="0" y="{top}" width="{width}" height="{height}" href="{data}" style="image-rendering:pixelated"/>',
                 f'<g class="marks" transform="translate(0,{top})" fill="none" stroke="#ffc66d" stroke-width="3">']
        for observation in item['observations']:
            for index, box in enumerate(observation['boxes']):
                x, y, w, h = box
                assert 0 <= x < x+w <= width and 0 <= y < y+h <= height
                parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9"/>')
                label = html.escape(observation['label'] + chr(65+index))
                parts.extend([f'<rect x="{x}" y="{y-28}" width="52" height="25" rx="5" fill="#ffc66d" stroke="none"/>',
                              f'<text x="{x+8}" y="{y-9}" font-family="sans-serif" font-size="17" fill="#172b35" stroke="none">{label}</text>'])
        parts.extend(['</g>', '<g font-family="sans-serif" fill="#dce8ee" font-size="20">'])
        for index, observation in enumerate(item['observations']):
            parts.append(f'<text x="28" y="{top+height+35+index*30}">{html.escape(observation["description"])}</text>')
        parts.extend([f'<text x="28" y="{top+height+91}" fill="#a9bdc8" font-size="18">原截图逐字节嵌入；只叠加框线。当前最好版本保持不变。</text>', '</g></svg>'])
        svg = ''.join(parts)
        ElementTree.fromstring(svg)
        file = args.output / (item['species'] + '-observations.svg')
        file.write_text(svg)
        cards.append('<section>' + svg + '</section>')
        records.append({'species': item['species'], 'screenshot': str(source),
                        'source_sha256': hashlib.sha256(raw).hexdigest(),
                        'svg': str(file), 'svg_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                        'screenshot_size': [width, height], 'observations': item['observations']})
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>当前鱼背纹样：观察框与原截图</title><style>
body{margin:0;background:#0e202a;color:#e7f0f5;font:16px/1.6 system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:#122b38ef;padding:14px 24px;border-bottom:1px solid #405966}
h1{font-size:22px;margin:0 0 6px}p{margin:5px 0}main{max-width:1400px;margin:auto;padding:20px}
section{margin-bottom:24px;border:1px solid #405966;border-radius:12px;overflow:hidden}svg{display:block;width:100%;height:auto}
.hide-marks .marks{display:none}label{cursor:pointer;display:inline-flex;align-items:center;gap:8px;color:#ffc66d}
</style><header><h1>我所指的“重复/镜像感”</h1>
<p>同号 A/B 框标出相似纹样。没有发现能明确证明贴图裂缝的边界，不把它列为必须修复的问题。</p>
<label><input id="show" type="checkbox" checked> 显示观察框（关闭即可看原截图）</label></header><main>'''
    page += ''.join(cards) + '''</main><script>
document.getElementById('show').addEventListener('change',e=>document.body.classList.toggle('hide-marks',!e.target.checked));
</script></html>'''
    (args.output / 'index.html').write_text(page)
    report = {'ok': True, 'status': 'done', 'next_action': 'human_review',
              'scope': 'Vector overlays over exact, unchanged screenshots. Subjective visual observations only; no runtime/model/texture mutation.',
              'plan_sha256': hashlib.sha256(args.plan.read_bytes()).hexdigest(), 'records': records}
    (args.output / 'annotations.validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'ok': True, 'images': len(records), 'html': str(args.output/'index.html')}))


if __name__ == '__main__':
    main()
