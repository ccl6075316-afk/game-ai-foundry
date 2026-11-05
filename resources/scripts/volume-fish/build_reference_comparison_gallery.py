"""Compose source-faithful side/top review sheets and an offline 24-fish gallery."""
import hashlib
import html
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/fish-reference-compare-20261105'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def role_zh(reference):
    role = reference['role']
    if reference.get('reference_kind') == 'preview_only':
        return '主参考：历史模型预览（无本地网格）'
    if 'later' in role:
        return '后续比较，未据此改形'
    if 'not_selected' in role or 'not_chosen' in role:
        return '曾查看，未选为造型目标'
    if 'qualitative' in role or 'qualitative' in reference.get('used_for', '').lower():
        return '辅助形态对照'
    if 'adopted' in role or reference.get('adoption_status', '').startswith('geometric_parameters_adopted'):
        return '采用部分形体参数'
    return '实际参考，具体用途见来源记录'


def on_white(image):
    result = Image.new('RGBA', image.size, (248, 249, 250, 255))
    result.alpha_composite(image.convert('RGBA'))
    return result.convert('RGB')


def main():
    manifest_path = OUT / 'comparison-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    batch = json.loads((OUT / 'renders-batch.validation.json').read_text(encoding='utf8'))
    assert batch['ok'] and len(batch['results']) == 27
    results = {x['id']: x for x in batch['results']}
    labels = {row['species']: row['label'] for row in manifest['entries']}
    font = lambda n: ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', n)
    metrics = {}
    (OUT / 'sheets').mkdir(exist_ok=True)
    for case in manifest['pairs']:
        result = results[case['id']]
        folder = Path(result['output'])
        report = json.loads(Path(result['report']).read_text(encoding='utf8'))
        assert report['ok'] and report['source_files_unchanged'] and report['clean_rgba'] and report['transparent_background']
        assert all(v['all_fins_inside_frame'] for v in report['views'])
        for name, digest in report['files'].items():
            assert sha(folder / name) == digest, name
        reference = next(r for e in manifest['entries'] for r in e['references'] if r.get('pair_id') == case['id'])
        masks, overlays, stats = {}, {}, {}
        for view in ('side', 'top'):
            for role in ('ours', 'reference'):
                image = Image.open(folder / f'{role}-{view}-grey.png').convert('RGBA')
                masks[role] = np.asarray(image)[:, :, 3] >= 26
            ours, ref = masks['ours'], masks['reference']
            intersection = int((ours & ref).sum())
            union = int((ours | ref).sum())
            rgb = np.full((*ours.shape, 3), 248, dtype=np.uint8)
            rgb[ours & ref] = (202, 210, 217)
            rgb[ours & ~ref] = (40, 126, 182)
            rgb[ref & ~ours] = (221, 138, 38)
            for mask, color in [(ours, (25, 103, 163)), (ref, (194, 112, 19))]:
                binary = Image.fromarray((mask * 255).astype('uint8'))
                boundary = np.asarray(binary.filter(ImageFilter.MaxFilter(3))) != np.asarray(binary.filter(ImageFilter.MinFilter(3)))
                rgb[boundary] = color
            overlays[view] = Image.fromarray(rgb)
            overlays[view].save(folder / f'overlay-{view}.png')
            stats[view] = {'alpha_threshold': 26 / 255, 'ours_pixels': int(ours.sum()),
                           'reference_pixels': int(ref.sum()), 'intersection_pixels': intersection,
                           'union_pixels': union, 'intersection_over_union': intersection / union,
                           'scope': 'Visible complete-fish projection including fins, eyes and rest-pose differences. Not isolated body width, biological error or an acceptance score.'}
        metrics[case['id']] = stats
        for mode in ('grey', 'native'):
            width, height = 2400, 1240
            sheet = Image.new('RGB', (width, height), '#f8f9fa')
            draw = ImageDraw.Draw(sheet)
            title = labels[case['species']] + '  /  ' + reference['name']
            draw.text((25, 12), title, font=font(26), fill='#203242')
            draw.text((25, 52), role_zh(reference) + '  ·  ' + ('灰模' if mode == 'grey' else '原纹理') + '  ·  侧视与俯视使用同一正交取景', font=font(22), fill='#526171')
            for row, view in enumerate(('side', 'top')):
                y = 95 + row * 540
                for col, (role, label) in enumerate((('ours', '我们的当前模型'), ('reference', '实际参考模型'), ('overlay', '轮廓叠加'))):
                    image = overlays[view] if role == 'overlay' else on_white(Image.open(folder / f'{role}-{view}-{mode}.png'))
                    image = image.resize((800, 480), Image.Resampling.NEAREST)
                    sheet.paste(image, (col * 800, y + 32))
                    draw.text((col * 800 + 18, y), ('侧视' if view == 'side' else '俯视') + ' · ' + label, font=font(22), fill='#203242')
            draw.text((25, 1177), '蓝：只在我们投影内   橙：只在参考投影内   浅灰：共同区域；包括全部鳍、眼和原静息姿态。', font=font(21), fill='#203242')
            draw.text((25, 1208), '全部网格长轴等长、等比缩放并居中；未按解剖测位配准，不是生物尺寸误差。原文件未改形。', font=font(20), fill='#526171')
            sheet.save(OUT / 'sheets' / f'{case["id"]}-{mode}.png')
        reference['role_zh'] = role_zh(reference)
    for row in manifest['entries']:
        for reference in row['references']:
            reference['role_zh'] = role_zh(reference)
    data = json.dumps(manifest, ensure_ascii=False).replace('</', '<\\/')
    page = TEMPLATE.replace('__DATA__', data)
    (OUT / 'report.html').write_text(page, encoding='utf8')
    (OUT / 'projection-metrics.validation.json').write_text(json.dumps({'ok': True, 'scope': 'Pixel-set statistics of actual clean RGBA projections; not a shape acceptance score.', 'pairs': metrics}, indent=2) + '\n', encoding='utf8')
    (OUT / 'gallery.validation.json').write_text(json.dumps({'ok': True, 'fish': len(manifest['entries']), 'rendered_pairs': len(manifest['pairs']), 'raw_model_images': 216, 'comparison_sheets': 54, 'historical_preview_images': 4, 'manifest_sha256': sha(manifest_path), 'html_sha256': sha(OUT / 'report.html'), 'assets_modified': False, 'source_preview_limit': manifest['preview_only_limit']}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'ok': True, 'fish': 24, 'pairs': 27, 'html': str(OUT / 'report.html')}))


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>24鱼 · 当前模型与实际参考</title>
<style>
*{box-sizing:border-box}body{margin:0;font:16px/1.55 "Microsoft YaHei",system-ui,sans-serif;color:#243746;background:#eef2f5}button,input,select{font:inherit}aside{position:fixed;width:240px;height:100vh;background:#162b3a;color:white;padding:20px 15px;overflow:auto}aside h2{font-size:23px;margin:0 0 7px}aside p{color:#b7cad5;font-size:13px}#search{width:100%;border:1px solid #476071;background:#223e50;color:white;border-radius:7px;padding:8px}.filters{display:flex;gap:4px;margin:12px 0}.filters button{border:0;border-radius:5px;padding:5px 7px;background:#314e61;color:white;cursor:pointer}#list button{display:block;width:100%;text-align:left;border:0;border-radius:7px;background:transparent;color:#dce5eb;padding:10px 9px;cursor:pointer;margin:3px 0}#list button.active{background:#286887;color:white}#list small{float:right;opacity:.65;font-size:12px}main{margin-left:240px;padding:25px;max-width:2000px}h1{margin:0;font-size:30px}.sub{color:#617586;margin:7px 0 15px}.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0}.controls select{padding:8px;border:1px solid #c5d1da;border-radius:7px;background:white;max-width:100%}.tag{font-size:14px;background:#e0ecf1;border-radius:20px;padding:4px 12px}.tag.orange{background:#ffebcc}.purpose{background:white;border:1px solid #dce4e9;border-radius:9px;padding:12px 16px;margin-bottom:14px}.purpose p{margin:3px 0}.legend{font-size:14px;color:#536775}.blue{color:#1967a3}.orange{color:#bd7013}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0}.image{background:#f8f9fa;border:1px solid #d6e0e7;border-radius:8px;overflow:hidden}.image h3{font-size:15px;margin:0;padding:9px 12px;background:white}.image img{display:block;width:100%;height:auto;background:#f8f9fa}.preview{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.preview img{width:100%;height:380px;object-fit:contain;background:#e5ebef}.warn{background:#fff0d9;color:#6f410c;border:1px solid #e5bc76;border-radius:8px;padding:14px;margin:14px 0}a{color:#126a91}details{background:white;padding:14px 18px;border-radius:9px;margin:16px 0}summary{cursor:pointer}pre{white-space:pre-wrap;word-break:break-word;font:12px/1.6 Consolas,monospace;max-height:500px;overflow:auto}footer{font-size:13px;color:#647787;margin:20px 0 10px}.downloads{display:flex;gap:18px;margin:12px 0}.viewtitle{margin:17px 0 3px;font-size:19px}@media(max-width:1000px){aside{width:190px}main{margin-left:190px;padding:15px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.grid .image:last-child{grid-column:span 2}}@media(max-width:650px){aside{position:relative;width:100%;height:auto;max-height:300px}main{margin-left:0}.preview{grid-template-columns:1fr}}
</style>
<aside><h2>24鱼参考对照</h2><p>13条已接受成品 · 11条本批候选</p><input id="search" placeholder="搜索鱼名"><div class="filters"><button data-filter="all">全部24</button><button data-filter="accepted">成品13</button><button data-filter="candidate">候选11</button></div><nav id="list"></nav></aside>
<main><h1 id="title"></h1><p class="sub">当前文件与记录中实际使用／查看过的参考。点击图片可查看原尺寸。</p><div class="controls"><span id="category" class="tag"></span><select id="reference"></select><select id="mode"><option value="grey">灰模：看形体</option><option value="native">原纹理：看实际模型</option></select></div><section class="purpose"><p id="role"></p><p class="legend">三维图：全部网格长轴等长、等比缩放、居中；保留原静息鳍姿，没有调整形状来匹配。侧／俯视使用相同的正交取景。</p><p class="legend"><span class="blue">蓝＝只在我们投影内</span>　<span class="orange">橙＝只在参考投影内</span>　浅灰＝共同区域。包括全部鳍、眼与鱼须，不等于去鳍体厚测量。</p></section><div id="content"></div><details><summary>来源、用途与文件核对记录</summary><p>“采用参数”“只作比较”分别标记。参考的生物身份、工程归一化与未知按原记录保留。</p><p id="sourceLink"></p><pre id="provenance"></pre><p><a href="comparison-manifest.json">完整24鱼清单</a> · <a href="inputs-frozen.json">13条成品来源审核</a> · <a href="inputs-new-eleven.json">11条候选来源审核</a> · <a href="projection-metrics.validation.json">投影像素统计（含鳍，非验收分数）</a></p></details><footer>本页来自实际本地模型渲染；没有使用AI生成或修饰对比图。灰模保留原／已核对的透明规则，原Unity自定义shader未复刻。本轮未改鱼资产、未安装、未提交代码。</footer></main>
<script>
const DATA=__DATA__;let selected=decodeURIComponent(location.hash.slice(1))||DATA.entries[0].species;let category='all';
const $=id=>document.getElementById(id);const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function list(){const query=$('search').value.trim().toLowerCase();$('list').innerHTML='';for(const e of DATA.entries){if(category!=='all'&&category!==e.category)continue;if(query&&!`${e.label} ${e.species}`.toLowerCase().includes(query))continue;const b=document.createElement('button');b.innerHTML=escape(e.label)+`<small>${e.category==='accepted'?'成品':'候选'}</small>`;b.className=e.species===selected?'active':'';b.onclick=()=>select(e.species);$('list').appendChild(b)}}
function card(path,title){return `<article class="image"><h3>${escape(title)}</h3><a href="${escape(path)}" target="_blank"><img src="${escape(path)}" alt="${escape(title)}"></a></article>`}
function views(pair,mode,withOverlay=true){let h='';for(const v of ['side','top']){const name=v==='side'?'侧视':'俯视';h+=`<h2 class="viewtitle">${name}</h2><div class="grid">`+card(`renders/${pair}/ours-${v}-${mode}.png`,'我们的当前模型')+card(`renders/${pair}/reference-${v}-${mode}.png`,'实际参考模型')+(withOverlay?card(`renders/${pair}/overlay-${v}.png`,'完整投影轮廓叠加'):'')+'</div>'}return h}
function select(id){selected=id;history.replaceState(null,'','#'+encodeURIComponent(id));const e=DATA.entries.find(x=>x.species===id)||DATA.entries[0];selected=e.species;$('title').textContent=e.label;$('category').textContent=e.category==='accepted'?'原已接受成品':'本批成品候选 · 待整鱼接受';$('category').className='tag'+(e.category==='candidate'?' orange':'');$('reference').innerHTML=e.references.map((r,i)=>`<option value="${i}">${escape(r.role_zh)} · ${escape(r.name)}</option>`).join('');list();render()}
function render(){const e=DATA.entries.find(x=>x.species===selected);const r=e.references[+$('reference').value];const mode=$('mode').value;$('role').textContent='本参考用途：'+r.role_zh;$('provenance').textContent=JSON.stringify({current_model:e.current_model,reference:r},null,2);$('sourceLink').innerHTML=r.source_model_url?`<a href="${escape(r.source_model_url)}" target="_blank">打开原参考模型网页</a>`:'';if(r.pair_id){$('content').innerHTML=`<div class="downloads"><a href="sheets/${r.pair_id}-${mode}.png" target="_blank">打开当前完整对照大图</a><a href="renders/${r.pair_id}/render.validation.json" target="_blank">此对照的相机／缩放／源文件记录</a></div>`+views(r.pair_id,mode);return}const fallback=e.references.find(x=>x.pair_id);let h='<div class="warn"><strong>主参考缺少本地网格及标定侧／俯视。</strong><br>下面展示实际采用过的四张历史斜视原图，不能当作同相机正交对比，也不计算像素差。另一个下拉选项中的GiltheadBream是后来比较过的近缘模型，没有替换成当时主参考。</div>';if(fallback){h+='<h2>我们的当前模型：正交侧视／俯视</h2><div class="preview">'+card(`renders/${fallback.pair_id}/ours-side-${mode}.png`,'我们的侧视')+card(`renders/${fallback.pair_id}/ours-top-${mode}.png`,'我们的俯视')+'</div>'}h+='<h2>当时实际采用的参考预览原图</h2><div class="preview">';for(const [i,p]of r.previews.entries())h+=card(p.presentation_path,['近俯斜视','侧上斜视：全鱼','前上斜视','前下斜视'][i]+'（相机未标定）');$('content').innerHTML=h+'</div>'}
$('reference').onchange=render;$('mode').onchange=render;$('search').oninput=list;for(const b of document.querySelectorAll('[data-filter]'))b.onclick=()=>{category=b.dataset.filter;list()};select(DATA.entries.some(e=>e.species===selected)?selected:DATA.entries[0].species);
</script></html>'''


if __name__ == '__main__':
    main()
