"""Verify and close out the explicitly bounded low-poly experiment."""
import argparse,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);p.add_argument('--cleanup',action='store_true');args=p.parse_args()
repo=Path(__file__).resolve().parents[3];game=repo/'projects/fishing-2d/game';root=args.review.resolve()
assert root.is_relative_to((game.parent/'plans/reviews').resolve()) and root.name=='fish-lowpoly-v2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda name:json.loads((root/name).read_text(encoding='utf8'))
source=load('source.validation.json');render=load('render.validation.json');structure=load('structure.validation.json');cold=load('cold.validation.json')
for path,digest in source['inputs'].items():assert sha(game/path[6:] if path.startswith('res://') else Path(path))==digest,('Source changed',path)
for candidate,record in zip(render['candidates'],structure['records']):
    geometry=root/('low-'+str(int(candidate['budget']))+'.json');data=load(geometry.name)
    assert sha(geometry)==candidate['geometry_sha256']==record['candidate_sha256']
    assert data['source_sha256']==sha(root/'source.validation.json')
    assert data['builder_sha256']==sha(Path(__file__).parent/'build_whole_lowpoly.py')
    assert data['settings_sha256']==sha(repo/'resources/volume-fish/zander-lowpoly-study-v2.json')
    assert sha(candidate['scene'])==candidate['sha256']
assert cold['scene_sha256']==render['candidates'][1]['sha256'] and cold['visible_triangles']==2991 and cold['uv_lookup_errors']==0 and not cold['dependencies']
assert all(r['bone_pose_changed'] for r in cold['pose_checks'])
for image in render['images']:assert sha(image['path'])==image['sha256']
for name in ['source.log','render.log','cold.log']:
    text=(root/name).read_text(encoding='utf8');assert 'SCRIPT ERROR' not in text and '\nERROR:' not in text
scripts=['probe_whole_fish_lowpoly.gd','export_lowpoly_source.gd','build_whole_lowpoly.py','LowPolyFishTransport.gd','render_whole_lowpoly.gd','check_whole_lowpoly.py','cold_load_lowpoly.gd','finish_whole_lowpoly.py']
sources={str(Path(__file__).parent/name):sha(Path(__file__).parent/name) for name in scripts}
before=sum(x.stat().st_size for x in root.rglob('*') if x.is_file());removed=[]
if args.cleanup:
    targets=list(root.glob('source-*.bin'))+[root/'fish-1000.scn',root/'fish-6000.scn',root/'Ascend.png',root/'Dive.png',root/'floors.log']
    for path in targets:
        path=path.resolve();assert path.parent==root and path.is_file()
        removed.append({'path':str(path.relative_to(root)),'bytes':path.stat().st_size,'sha256':sha(path)});path.unlink()
markdown='''# 梭鲈整鱼低面预算实验 V2

2026-10-25。用户明确十万面仍不可接受，要求认真探索几千、1–3千甚至更低。V1仅唇带减半不是目标完成。V2按整鱼预算重新处理几何接缝/材质运输，得到992、2991、6000三角面。仅独立候选，没有替换正式鱼，没有用户验收，没有宣称完整鱼门或FPS收益。

## 当前结论

|目标|实际面数|顶点|相对212360原版减少|身体闭合|退化面|
|---:|---:|---:|---:|---|---:|
|1000|992|613|99.53%|是|0|
|3000|2991|1712|98.59%|是|0|
|6000|6000|3358|97.17%|是|0|

正常展示尺度（四栏图每鱼约400像素长）多数鳞纹、配色、鱼鳍形状仍可辨。实际看过whole、head-side/front/oblique、Turn/Ascend/Dive与新进程cold-3000图。992近景下唇明显折硬；2991仍有下唇纹理/曲面折痕，6000有所改善但未消除。不能因全鱼缩小后相似就接受近景，也不能因此恢复十万面。

三千面候选在新Godot进程直接加载便携SCN：2991面、1712顶点、14 surfaces、无外部依赖；2套UV对应表逐顶点检查无错误，没有调用几何生成器。原骨骼/动画保留，Swim/Turn/Ascend/Dive均在0与1.25秒检测到骨骼姿态变化。这只是离散诊断，不是连续动作、鳍根或身体GPU透明覆盖门。

## 为什么V1减不下去，V2可以

V1保留原网格所有密集边界和独立材质分区，只尝试标准索引LOD；梭鲈唇带因此仅自动最低仍有约2822面，内口surface最低820。它们是原拓扑/算法约束，不是该部位生物形状必需这么多面。

V2从实际最终鱼导出全部可见节点（12节点、14surface）的当前几何。Blender只在几何上按1e-7焊合重复接缝，再以整鱼预算分配collapse decimation；没有删掉嘴、眼或鱼鳍。材质surface角色保留；逐surface查原始三角BVH，重心传递UV/UV2/颜色/法线/骨骼权重和原材质参考身份。4权重归一化。高分辨率纹理继续使用，几何密度独立降低。

Godot重绑所有实际VERTEX_ID路径：rest114位置/法线/UV，eye的rest/UV，mouth136逐顶点记录（保留stride），material130口内定位表。UV护栏继续启用，未靠关护栏隐藏紫色错误。原图参考坐标通过旧支持面运输，不冒称等于新的几何位置。不同鱼出现未知索引shader时必须扩展明确分支，不能盲套。

参数保存在Foundry `resources/volume-fish/zander-lowpoly-study-v2.json`，由Blender构建器实际读取。整鱼预算占比：身体66%、两唇8%、两眼6%、8个鳍合计20%。这些仅是本轮梭鲈起点，不是所有鱼的通用解剖比例。后续应根据失败区域在总预算内重新分配，限制嘴角/唇缘等特征边折叠；不能给贴图每个像素配几何。

## 已知失败与下一步

身体改为低面后，旧唇带相对其支持面改变。静止全顶点、全边中点及面心检查保持−0.00003阈值：992/2991/6000分别有79/85/51个采样超阈。具体逐surface最小距离见structure.validation.json。三个候选均未通过嘴唇接触门；没有降低容差、伪造通过或将原高模接触报告套给低模。

因此“几千面可保留主要显示内容”已经有实际证据；“可安装的三千面成品”尚未实现。下一批要把薄唇带与低密支持身体作为一套结构共同布面，保护口缘/嘴角并修正接缝UV，避免原叠层各自减面后不贴合。重新评估鳍根和眼片支持区域，补身体覆盖、动作/切换和全鳍专项，再考虑正常距离与远景LOD。普通鱼优先以1–3千面做工作目标；数百面应单独作为远景层试验，不宣称本轮已做。

仍有14surface与原复杂shader/高分辨率纹理，尚未合并材质/烘焙。SCN文件大小、顶点数和面数都不是实测显存或群体FPS。这次不能把98.6%减面解释成帧率提高70倍。近景质量、几何、批次、材质和CPU动作应分别验证。

## 执行与收尾

1. Godot实际工厂 `export_lowpoly_source.gd -- --output=<目录>`，导出当前属性二进制与source.validation.json输入哈希。
2. Blender `--background --factory-startup --python build_whole_lowpoly.py -- <目录>`，读取本鱼预算参数，输出三个low-*.json。
3. Godot实际CompatibilityGPU `render_whole_lowpoly.gd -- --output=<目录>`，材料运输、便携候选SCN和四栏多视/离散动作图。
4. Blender `check_whole_lowpoly.py -- <目录>`；Godot新进程 `cold_load_lowpoly.gd -- --output=<目录>`；最后`.venv` Python `finish_whole_lowpoly.py --review <目录> --cleanup`。

所有Godot命令传`--path`本游戏、`--script`Foundry工具绝对路径，日志均写本目录。当前CLI帮助/原素材workflow状态已检查为done/human_review；这次复用现有源图，不生新图。

首次只读LOD盘点在dummy renderer退出时出现缓存清理空material错误；计数已保存，不能当作无错渲染通过。最初export未显式释放缓存产生退出泄漏，已修复并以实际GPU重跑；冷读初次look_at在入树前调用及环境未设置ambient白色的问题也已修正。最终source/render/cold日志无ERROR。本轮失败原因保留，不把重试前日志当候选证据。

保留2991面便携SCN、三个小型参数/几何JSON、四栏整鱼与三种头部视图、一个Turn离散时刻、新进程图和结构/冷读/哈希报告。删除可重建原始属性二进制、992/6000 SCN、重复的两张动作图与失败盘点日志；原始游戏输入继续由路径和SHA绑定。详见validation-report.json的删项/字节与实际保留清单。没有提交推送。
'''
(root/'lowpoly-review.md').write_text(markdown,encoding='utf8')
result={'schema_version':1,'status':'done','next_action':'human_review','accepted':False,'production_changed':False,'created_utc':datetime.now(timezone.utc).isoformat(),
 'purpose':'Whole fish low-budget feasibility study, not a production fish delivery.', 'source_bindings_checked':len(source['inputs']),'tool_sha256':sources,
 'settings_sha256':sha(repo/'resources/volume-fish/zander-lowpoly-study-v2.json'),
 'candidates':[{'budget':r['budget'],'triangles':r['actual_triangles'],'vertices':sum(p['vertices'] for p in r['parts']),'body_closed':r['body_closed'],'zero_area':sum(p['zero_area_triangles'] for p in r['parts']),'lip_contact_failures':sum(p.get('lip_static_contact',{}).get('below_minus_3e_5',0) for p in r['parts']),'production_ready':False} for r in structure['records']],
 'cold_load_verified':cold,'visual_review':{'reviewer':'agent','user_accepted':False,'observation':'Normal displayed scale broadly retains source appearance. Lower lip is angular and UV folds remain at close views; all candidates fail sampled lip/body contact.','complete_motion_gate':False},
 'failed_attempts':['Dummy-renderer LOD probe teardown null-material error; floor counts not accepted as rendering proof.','Initial exporter teardown leaked objects; explicit cleanup added and GPU rerun clean.','Initial cold camera look_at before entering tree corrected; ambient color made same white as comparison.'],
 'cleanup':{'performed':args.cleanup,'before_bytes':before,'removed':removed}}
result['cleanup']['retained']=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':sha(x)} for x in sorted(root.rglob('*')) if x.is_file() and x.name!='validation-report.json']
(root/'validation-report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'status':'done','production_ready':False,'triangles':[992,2991,6000],'removed_bytes':sum(x['bytes'] for x in removed),'remaining_bytes':sum(x.stat().st_size for x in root.rglob('*') if x.is_file()),'report':str(root/'lowpoly-review.md')},ensure_ascii=False))
