"""Build compact CSV/HTML views of a read-only current-runtime part inventory."""
import csv
import hashlib
import html
import json
import re
import struct
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GAME_ROOT = ROOT / 'projects/fishing-2d'
OUT = GAME_ROOT / 'plans/reviews/fish-part-inventory-20261029'
CATEGORIES = {'body':'身体','fin':'鱼鳍','eye':'眼部','mouth':'嘴颌/口角','barbel':'鱼须',
              'head_overlay':'头部覆盖层','head_structure':'头部结构','other':'其他'}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')

def csv_file(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

def main():
    report_path = OUT/'inventory.validation.json'
    report = json.loads(report_path.read_text())
    assert report['ok'] and report['engine_output_scan']['ok'] and len(report['inventory']) == 28
    summaries, parts, checks = [], [], []
    for fish in sorted(report['inventory'], key=lambda f:f['configured_length_cm']):
        species, name = fish['species'], fish['name_zh'].split('·')[0]
        model = GAME_ROOT/'game/assets/models/fish'/f'{species}.glb'
        assert sha(model) == fish['model_sha256']
        data = model.read_bytes(); magic, version, length = struct.unpack_from('<III', data)
        assert magic == 0x46546C67 and version == 2 and length == len(data)
        chunk_size, chunk_type = struct.unpack_from('<II',data,12); assert chunk_type == 0x4E4F534A
        gltf = json.loads(data[20:20+chunk_size]); source_counts = {}
        for node in gltf['nodes']:
            if 'mesh' not in node: continue
            counts=[]
            for primitive in gltf['meshes'][node['mesh']]['primitives']:
                assert primitive.get('mode',4) == 4
                count = gltf['accessors'][primitive.get('indices',primitive['attributes']['POSITION'])]['count']
                assert count % 3 == 0; counts.append(count//3)
            source_counts[node['name']] = counts
        groups=Counter(); visible=[p for p in fish['parts'] if p['visible']]
        assert sum(p['triangles'] for p in visible) == fish['totals']['triangles']
        assert sum(p['vertices'] for p in visible) == fish['totals']['vertices']
        for part in fish['parts']:
            if part['visible']:
                assert source_counts[part['name']] == [s['triangles'] for s in part['surfaces']], (species,part['name'])
                groups[part['category']] += part['triangles']
            parts.append({'鱼':name,'species':species,'游戏配置体长_cm':fish['configured_length_cm'],
                '部件':part['name'],'类别':CATEGORIES[part['category']],'可见':part['visible'],
                '三角面':part['triangles'],'顶点':part['vertices'],'占可见整鱼_%':round(part['share_of_visible_fish']*100,3),
                '材质面':len(part['surfaces']),'各材质面LOD层数':'/'.join(str(len(s['lods'])) for s in part['surfaces'])})
        totals=fish['totals']; top=visible[0]
        summaries.append({'鱼':name,'species':species,'游戏配置体长_cm':fish['configured_length_cm'],
            '可见三角面':totals['triangles'],'身体面':groups['body'],'全部鱼鳍面':groups['fin'],
            '其余部件面':totals['triangles']-groups['body']-groups['fin'],'顶点':totals['vertices'],
            '可见部件':totals['parts'],'材质面':totals['surfaces'],'骨骼':fish['bones'],
            '最大部件':top['name'],'最大部件面':top['triangles'],'隐藏面_不计入总数':totals['hidden_triangles'],
            '缩放后静止包围盒长度_cm':round(fish['visible_rest_aabb_length_m']*100,4),
            '计划同屏数量':'待定'})
        checks.append({'species':species,'source_glb_sha256':sha(model),
            'visible_part_surface_triangles_equal_raw_glb':True,'visible_parts':len(visible)})
    csv_file(OUT/'fish-summary.csv',summaries); csv_file(OUT/'fish-parts.csv',parts)
    population_sources = ['game/scripts/aquarium/HallTank3D.gd','game/scripts/aquarium/AquariumHall3D.gd',
                          'game/scripts/aquarium/fish_school/FishSchoolReview.gd','game/assets/aquascape-marine-v1/layout.json']
    marine=json.loads((GAME_ROOT/population_sources[-1]).read_text())
    population={'status':'production_per_species_counts_not_defined','planned_counts':{f['species']:None for f in report['inventory']},
      'note':'Larger fish having fewer instances is the user planning policy, not a discovered production population formula. A blank target is not zero fish.',
      'observed_examples':{'shared_28_species_exhibit':1,'hall_default_tank_totals':[8,4],
       'hall_species_cycle':['red_emperor','red_seabream','black_seabream','yellow_croaker'],
       'marine_showcase':marine['fish_species'],'school_test':'Count and roster are configurable; default cyclic allocation is not a size-based production budget.'},
      'source_sha256':{p:sha(GAME_ROOT/p) for p in population_sources}}
    save(OUT/'population-context.validation.json',population)
    save(OUT/'crosscheck.validation.json',{'ok':True,'method':'Independent GLB JSON/accessor count for every visible runtime node and surface; checks runtime sum and source model SHA.',
        'inventory_sha256':sha(report_path),'fish':checks,'summary':{'fish':len(summaries),'visible_parts':sum(s['可见部件'] for s in summaries),
        'one_of_each_base_triangles':sum(s['可见三角面'] for s in summaries)},'formal_acceptance':False})
    fields=['鱼','游戏配置体长_cm','可见三角面','身体面','全部鱼鳍面','其余部件面','顶点','骨骼','最大部件']
    header=''.join(f'<th>{html.escape(k)}</th>' for k in fields)
    body=''; detail=''
    for row in summaries:
        species=row['species']; label=html.escape(row['鱼'])
        body+='<tr data-name="'+label+' '+species+'">'+''.join('<td>'+('<a href="#'+species+'">'+label+'</a>' if k=='鱼' else f'{row[k]:,}' if isinstance(row[k],(int,float)) else html.escape(str(row[k])))+'</td>' for k in fields)+'</tr>'
        rows=[p for p in parts if p['species']==species]
        detail+='<details id="'+species+'" data-name="'+label+' '+species+'"><summary>'+label+' · '+str(row['游戏配置体长_cm'])+' cm · '+f'{row["可见三角面"]:,}'+' 三角面</summary><table><thead><tr><th>部件</th><th>类别</th><th>三角面</th><th>顶点</th><th>占比</th><th>材质面</th><th>各材质面LOD层数</th><th>可见</th></tr></thead><tbody>'
        for part in rows:
            detail+='<tr>'+''.join('<td>'+html.escape(str(part[k]))+'</td>' for k in ['部件','类别','三角面','顶点','占可见整鱼_%','材质面','各材质面LOD层数','可见'])+'</tr>'
        detail+='</tbody></table></details>'
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>28种鱼：体长与部件面数</title>
<style>body{font:15px system-ui;background:#f6f8fa;color:#17232f;margin:24px}main{max-width:1500px;margin:auto}h1{font-size:26px}p{line-height:1.7}table{border-collapse:collapse;width:100%;background:white;margin:14px 0}td,th{padding:9px;border-bottom:1px solid #dde3e9;text-align:right}td:first-child,th:first-child,td:last-child{text-align:left}th{background:#e6edf3;position:sticky;top:0}details{margin:12px 0;padding:14px;background:white;border:1px solid #dce3ea;border-radius:8px;overflow:auto}summary{font-weight:650;cursor:pointer}input,select{padding:9px;font:inherit}a{color:#075db2}.scroll{overflow:auto}.note{background:#e7f0ff;padding:14px;border-radius:8px}</style>
<main><h1>28种鱼：游戏体长与部件三角面数</h1>
<p class="note">基于当前Godot实际入口重新加载统计，未修改模型。体长来自3D游戏配置，单位厘米；按体长从小到大排列。数量预算尚待确定，可用“单鱼三角面 × 同屏数量”比较几何规模，但这不是帧率预测。</p>
<p>三角面为可见基础网格，隐藏部件不计入总数。LOD单独记录，不与基础面数相加。顶点为引擎各表面实际顶点之和，包含UV/法线接缝拆点，不是唯一空间坐标数。缩放后的静止包围盒长度在CSV另列，不能当作动作中的精确生物体长。</p>
<p><a href="fish-summary.csv">下载整鱼汇总CSV</a> · <a href="fish-parts.csv">下载全部部件CSV</a> · <a href="inventory.validation.json">原始统计报告</a></p>
<input id="q" placeholder="搜索鱼名或species"><select id="order"><option value="length">按体长</option><option value="triangles">按总面数，从多到少</option><option value="fins">按鳍面数，从多到少</option></select>
<div class="scroll"><table id="overview"><thead><tr>'''+header+'</tr></thead><tbody>'+body+'</tbody></table></div><h2>各鱼部件明细（点击展开）</h2>'+detail+'''
<p>复现：运行Foundry的inventory_fish_parts.gd（游戏--path，--headless，输出参数为本报告目录绝对路径），再运行summarize_fish_parts.py。没有做减面、焊点、加厚、材质迁移或正式资产验收。</p></main>
<script>const q=document.querySelector('#q');q.oninput=()=>{const v=q.value.toLowerCase();document.querySelectorAll('[data-name]').forEach(e=>e.hidden=!e.dataset.name.toLowerCase().includes(v))};const body=document.querySelector('#overview tbody');document.querySelector('#order').onchange=e=>{const at={length:1,triangles:2,fins:4}[e.target.value],sign=at===1?1:-1;[...body.rows].sort((a,b)=>sign*(Number(a.cells[at].textContent.replaceAll(',',''))-Number(b.cells[at].textContent.replaceAll(',','')))).forEach(r=>body.append(r))};document.querySelectorAll('a[href^="#"]').forEach(a=>a.onclick=()=>{document.getElementById(a.hash.slice(1)).open=true});</script></html>'''
    (OUT/'index.html').write_text(page)
    print(json.dumps({'fish':len(summaries),'parts':len(parts),'visible_parts':sum(s['可见部件'] for s in summaries),'triangles_one_of_each':sum(s['可见三角面'] for s in summaries)},ensure_ascii=False))

if __name__ == '__main__': main()
