"""Verify inputs/evidence and prune only reproducible V3 transport intermediates."""
import argparse,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--cleanup',action='store_true');args=p.parse_args()
repo=Path(__file__).resolve().parents[3];game=repo/'projects/fishing-2d/game'
root=(game.parent/'plans/reviews/fish-volume-budget-v3').resolve()
assert root.is_relative_to((game.parent/'plans/reviews').resolve())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
config_path=repo/'resources/volume-fish/volume-budget-study-v3.json';config=load(config_path)
nav=load(root/'navigation.validation.json');smoke=load(root/'viewer-test.validation.json');local=load(root/'local-checks.validation.json')
assert nav['ok'] and smoke['ok'] and len(smoke['tests'])==4
assert nav['script_sha256']==sha(repo/'resources/runtime/godot/lowpoly-review/VolumeBudgetReview.gd')
assert sha(repo/'resources/runtime/godot/lowpoly-review/VolumeBudgetReview.gd')==sha(game/'scripts/aquarium/lowpoly_review/VolumeBudgetReview.gd')
assert sha(config_path)==sha(game/'scripts/aquarium/lowpoly_review/volume-budget-study-v3.json')
assert sha(repo/'resources/scripts/volume-fish/LowPolyFishTransport.gd')==sha(game/'scripts/aquarium/lowpoly_review/LowPolyFishTransport.gd')
observations={
 'bluegill':'289整鱼背鳍丢失多处棘尖、尾鳍和下侧轮廓折直；593改善，1196总体更接近。正/斜近景三档均有唇带与支持面不贴合、嘴角色块折叠，不能选作正式小鱼。下一批在600–1200总预算内重布嘴/鳍特征，300当前自动方案不接受。',
 'zander':'799/1598/3200整鱼纹样和主轮廓多数保留；近景下颌材质折痕均在，799轮廓最硬，增加面数并不单调消除折痕。下一批以1600–3200为修整区间，而非已证实最低质量线。',
 'great_hammerhead':'2000已保住头翼、主躯干、各鳍和尾形，4000/8000局部更细；正面头翼灰白边界呈波折，与几何/材质运输相关。保留原薄鳍/尾基限制，本轮没有修厚鳍。2000–4000值得继续局部修整，未证明整鱼可交付。',
 'whale_shark':'3998/7998/16000侧面与斜视主形、斑点和尾鳍保留较多，正面嘴缘细节与贴合仍变简；静态唇支持诊断仍有负距。4000–8000可作下一批修整区间，16000保留为较宽预算对照，不能把某张相似截图称无损。'
}
species_records=[];bindings={};lines=[]
for species,settings in config['species'].items():
    folder=root/species;source=load(folder/'source.validation.json');structure=load(folder/'structure.validation.json');render=load(folder/'render.validation.json')
    assert source['species']==structure['species']==render['species']==species
    for path,digest in source['inputs'].items():
        resolved=game/path[6:] if path.startswith('res://') else Path(path)
        assert sha(resolved)==digest,('Changed input',path)
        if path in bindings:assert bindings[path]==digest
        bindings[path]=digest
    assert source['exporter_sha256']==sha(repo/'resources/scripts/volume-fish/export_budget_source.gd')
    assert render['source_sha256']==sha(folder/'source.validation.json')
    assert render['renderer_sha256']==sha(repo/'resources/scripts/volume-fish/render_budget_study.gd')
    assert render['transport_sha256']==sha(repo/'resources/scripts/volume-fish/LowPolyFishTransport.gd')
    local_species=next(s for s in local['records'] if s['species']==species)
    assert render['candidates'][0]['triangles']==source['visible_triangles']
    for measured,rendered,check in zip(structure['candidates'],render['candidates'][1:],local_species['candidates']):
        path=folder/f"low-{measured['budget']}.json";recipe=load(path)
        assert sha(path)==measured['recipe_sha256']==rendered['recipe_sha256']==check['recipe_sha256']
        assert recipe['source_sha256']==sha(folder/'source.validation.json') and recipe['settings_sha256']==sha(config_path)
        assert recipe['builder_sha256']==sha(repo/'resources/scripts/volume-fish/build_budget_study.py')
        assert measured['actual_triangles']==rendered['triangles'] and measured['vertices']==rendered['vertices']
        assert rendered['surfaces']==render['candidates'][0]['surfaces'] and rendered['bones']==source['bone_count'] and rendered['uv_lookup_errors']==0
        assert measured['zero_area_triangles']==0 and all(c['closed_at_seam_precision'] for c in measured['body_checks'])
    for image in render['images']:assert sha(image['path'])==image['sha256']
    assert all(q['finite_bone_origins'] for q in render['pose_probes'])
    volume=sum(m['standardized_volume_m3'] for m in structure['body_measurements'])
    candidates=[c['actual_triangles'] for c in structure['candidates']]
    species_records.append({'species':species,'label':settings['label'],'real_length_cm':source['real_length_cm'],'body_volume_proxy_m3':volume,'body_volume_scope':structure['scope'],'original_triangles':source['visible_triangles'],'candidates':candidates,'observation':observations[species],'production_ready':False})
    lines.append(f"|{settings['label']}|{source['real_length_cm']:g} cm|{volume*1000:.3f} L|{source['visible_triangles']:,}|{' / '.join(format(q,',') for q in candidates)}|")
assert local['checker_sha256']==sha(repo/'resources/scripts/volume-fish/check_budget_study.py')
for path in root.rglob('*.log'):
    text=path.read_text(encoding='utf-8',errors='replace')
    assert 'SCRIPT ERROR' not in text and '\nERROR:' not in text and 'Traceback (most recent call last)' not in text,('Log failure',path)
before=sum(x.stat().st_size for x in root.rglob('*') if x.is_file());removed=[]
if args.cleanup:
    targets=list(root.glob('*/source-*.bin'))+list(root.glob('*/render.console.log'))+[root/'viewer-test.console.log',root/'navigation.console.log']
    for path in targets:
        path=path.resolve();assert path.is_relative_to(root) and path.is_file()
        if path.suffix=='.bin':
            frozen=load(path.parent/'source.validation.json');assert sha(path)==frozen['binary_sha256'][path.name]
        removed.append({'path':str(path.relative_to(root)),'bytes':path.stat().st_size,'sha256':sha(path)});path.unlink()
markdown='''# 四种鱼：按标准体积与数量探索减面区间

2026-10-26。用户要求以当前游戏标准化实体的体积及预计数量来考虑预算，小鱼更严、大鱼可放松；不按屏幕像素划制作档位，也不把此前1000/1500/3000/5000当作定案。本轮已实际生成4鱼×3档候选并在Godot绘制对照，原版保持，所有候选未接受。

|鱼|游戏标准体长|当前身体网格体积近似|原版三角面|三档实际三角面|
|---|---:|---:|---:|---:|
'''+ '\n'.join(lines)+'''

体积由闭合身体重合缝按原077精度识别、统一绕向后分组件算有符号四面体体积，再乘实际游戏完整变换行列式；不是按体长立方假设。排除鳍、眼片、唇浮雕；双髻鲨头翼与主身分开求和，重叠域未做布尔并集。因此是当前制作模型的体积比较量，不是生物实测体重、净排水量或养殖密度。体长只列作身份/标准尺度说明，没有用于按长度划档。

体积帮助辨别数量档，最终仍须显式设计预计同时数量，不能仅按体积线性分面。例如以本轮593面小鱼、16000面鲸鲨作纯算术示例：10000条小鱼是593万面，3条鲸鲨是4.8万面；少量巨鱼即便放松也未必占主要几何成本。该数量组合只是演示，不是已实现的鱼群压测或建议放养数。

'''+'\n\n'.join('**'+config['species'][s]['label']+'**：'+observations[s] for s in config['species'])+'''

所有候选身体闭合、未发现当前零面积三角、原生四权重有限并归一化，节点和材质surface角色均保留；原骨骼18/19/17/21根保留，没有以删眼/嘴/鳍来达标。材料索引表已重绑，实际GPU实例的UV查找表无错误。shader不报警不等于嘴缘纹理正确；普通鱼各自减面后带与体表不匹配仍可见。局部检查保留逐档静止唇距、体积变化及最多每surface4000个原面心到候选曲面距离；这些距离不是轮廓、动态接触或视觉通过证明。

每鱼保留whole、whole-oblique、head-side、head-front、head-oblique、tail-oblique、Turn七组原版/低/中/高同机位图。实际已审阅侧/斜整鱼、正/斜头部与Turn，另外蓝鳃尾部。未审阅的图片不冒称人工看过。两个时间点的四动作确有骨骼姿态变化；没有运行完整鳍根/全鳍面/身体GPU覆盖/连续动作切换门。原有鳍厚度、尾柄连接等问题本轮保留，所以这些只是三角密度影响实验，不是修好全部结构后的最低面数保证。

游戏场景：`res://scenes/fish_volume_budget_review.tscn`。上方切换四鱼；左上原版，右上低档，左下中档，右下高档。左键旋转、右/中键或Shift+左键平移、滚轮绕指针缩放、WASD/方向键平移；可选头/尾近景、正侧俯视及Swim/Turn/Ascend/Dive。四鱼切换与四动作离散探针通过；蓝鳃实际Input.parse_input_event导航回归全部通过，渲染锚点误差0像素（这里只是操作测试度量，不是资产面数依据）。

复现：在同一生产依赖下，Godot `export_budget_source.gd -- --species=<id> --output=<本轮逐鱼目录>`；Blender `--background --factory-startup --python build_budget_study.py -- <逐鱼目录>`；Godot GPU `render_budget_study.gd -- --species=<id> --output=<逐鱼目录>`；Blender `check_budget_study.py -- <本轮根目录>`。全部工具在Foundry `resources/scripts/volume-fish/`，逐鱼档位和部位权重由`resources/volume-fish/volume-budget-study-v3.json`实际读取。实验Viewer从保留的recipe装配；没有称作已回写blend/最终GLB的正式成品。

收尾：保留12份不同面数配方、紧凑来源/结构/局部/实际渲染报告、代表性多视图、导航及四鱼切换证据和必要日志。源二进制是从保留生产依赖可重建的运输中间件，按SHA核对后删除；去掉重复控制台日志。没有删除原图、生产模型、其他实验目录，也没有生成完整游戏副本或逐帧录像。正常游戏资产未替换，未测群体FPS，未完成正式固化/冷读/整鱼最终门；后续在本轮有希望区间里共同重布嘴、身体支持域、鳍特征，再统一验收。
'''
(root/'volume-budget-review.md').write_text(markdown,encoding='utf-8')
result={'schema_version':1,'status':'done','next_action':'human_review','accepted':False,'production_ready':False,'production_assets_changed':False,'created_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Multi-species geometric density/quality experiment, no production delivery.','source_bindings_checked':len(bindings),'settings_sha256':sha(config_path),'species':species_records,'local_checks_sha256':sha(root/'local-checks.validation.json'),'navigation_sha256':sha(root/'navigation.validation.json'),'viewer_test_sha256':sha(root/'viewer-test.validation.json'),'visual_review':{'reviewer':'agent','user_accepted':False,'coverage':'All species: whole side/oblique, head front/oblique, Turn; bluegill tail oblique.','remaining':'Lip/support mismatch, head material boundaries, original fin thickness and tail connection. No production budget accepted.'},'cleanup':{'performed':args.cleanup,'before_bytes':before,'removed':removed}}
result['cleanup']['retained']=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':sha(x),'mutable_interactive_evidence':x.name.startswith('interactive')} for x in sorted(root.rglob('*')) if x.is_file() and x.name!='validation-report.json']
(root/'validation-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'done','accepted':False,'production_changed':False,'source_bindings_checked':len(bindings),'removed_bytes':sum(x['bytes'] for x in removed),'remaining_bytes':sum(x.stat().st_size for x in root.rglob('*') if x.is_file()),'report':str(root/'volume-budget-review.md')},ensure_ascii=False))
