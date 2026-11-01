"""Record the bounded zander investigation, verify bindings, prune explicit derived outputs."""
import argparse,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from PIL import Image

parser=argparse.ArgumentParser();parser.add_argument('--review',type=Path,required=True);parser.add_argument('--cleanup',action='store_true');args=parser.parse_args()
repo=Path(__file__).resolve().parents[3];game=repo/'projects/fishing-2d/game';root=args.review.resolve()
assert root.is_relative_to((game.parent/'plans/reviews').resolve()) and root.name=='fish-reduction-v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
probe=json.loads((root/'probe.validation.json').read_text());contact=json.loads((root/'contact.validation.json').read_text());render=json.loads((root/'cold-load-render.validation.json').read_text())
assert contact['probe_sha256']==sha(root/'probe.validation.json')
bindings={**probe['inputs'],**render['inputs']}
for path,digest in bindings.items():
    resolved=game/path[6:] if path.startswith('res://') else Path(path)
    assert sha(resolved)==digest,('Input changed',path)
assert not render['input_changes']
for image in render['images']:assert sha(image['path'])==image['sha256']
candidate=root/'lips-25.res';assert sha(candidate)==render['candidate_sha256']==probe['candidates'][0]['sha256']
for log in ['probe.log','render.log']:
    text=(root/log).read_text(encoding='utf8')
    assert 'SCRIPT ERROR' not in text and '\nERROR:' not in text
pixels=[]
for shot in ['whole','side','front','oblique','moving_oblique']:
    a=np.array(Image.open(root/(shot+'.png')).convert('RGB'))[24:]
    left=a[:,:768].astype(float);right=a[:,768:].astype(float)
    # A numerical raster difference only; it is not an acceptance criterion.
    pixels.append({'view':shot,'rgb_mean_absolute_difference_0_to_255':float(abs(left-right).mean()),'pixels_with_any_channel_difference_over_16':int((abs(left-right).max(2)>16).sum())})
scripts=['probe_lip_reduction.gd','check_reduced_lip_contact.py','render_lip_reduction.gd','finish_lip_reduction.py','build_native_source_lips.py','repair_lip_contact140.py','build_source_lips.py','build_eye_relief.py','closed_body_index140.py']
sources={str(Path(__file__).parent/name):sha(Path(__file__).parent/name) for name in scripts}
sources[str(repo/'resources/volume-fish/mouth-repair-139.json')]=sha(repo/'resources/volume-fish/mouth-repair-139.json')
sources[str(repo/'resources/volume-fish/whale-shark-eye-151.json')]=sha(repo/'resources/volume-fish/whale-shark-eye-151.json')
before=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
deleted=[]
if args.cleanup:
    targets=list(root.glob('*.bin'))+[root/'lips-10.res',root/'lips-3.res',root/'moving_oblique.png']
    for target in targets:
        target=target.resolve();assert target.parent==root and target.is_file()
        deleted.append({'path':str(target),'bytes':target.stat().st_size,'sha256':sha(target),'reason':'Reconstructable diagnostic geometry or failed candidate; metrics retained. Single moving head view redundant with static head; not a dynamic gate.'})
        target.unlink()
result={'schema_version':1,'command':'fish.lip-reduction-investigation','status':'done','next_action':'human_review',
 'production_changed':False,'accepted':False,'created_utc':datetime.now(timezone.utc).isoformat(),
 'original_whole_fish_triangles':212360,'candidate_whole_fish_triangles':108320,'whole_fish_reduction_percent':100*(212360-108320)/212360,
 'candidate_status':'static_contact_pass; visual_probe_only; full_dynamic_and_finalization_pending',
 'inputs_checked':len(bindings),'sources':sources,'contact':contact['records'],'pixels':pixels,
 'visual_review':{'reviewer':'agent','views':['whole','side','front','oblique'],'observation':'No obvious lip silhouette break at the captured scale. Minor raster/shading differences remain. No user acceptance. One moving head pose is insufficient for dynamic contact proof.'},
 'weight_observation':'Stored resource max weight-sum error 1.522898674e-5, identical to baseline; initial stricter 1e-5 diagnostic assertion failed. Record baseline quantization; do not claim native normalization gate passed or relax production thresholds.',
 'limits':['No production asset replacement, no full fish acceptance, no FPS improvement measured.','Uniform decimation is a probe, not an approved universal reducer.','17,340-face candidate fails static contact at four probes;4,604-face candidate fails630 probes and has zero-area triangles.','Original lips/eyes/fins/body/anatomy/continuous-time/full action gates still required after any production change.','External uploaded animal models do not establish official Planet Zoo LOD or total fur/rendering cost.'],
 'cleanup':{'before_bytes':before,'deleted':deleted,'retained_candidate':'lips-25.res','failed_candidate_disposition':'Removed if cleanup enabled; exact hashes and measured failure causes remain in probe/contact reports.','cleanup_performed':args.cleanup}}
markdown='''# 鱼类面数膨胀与第一次减面调查

2026-10-25。独立实验，未替换正式鱼、未改接受状态。所有“面”均指三角面。原梭鲈212,360面；只替换实验唇带后108,320面，减少104,040面（48.99%）。仍远非最终性能目标，未测FPS收益。

## 确认的制作原因

1. `build_native_source_lips.py:27` 硬性要求257个纵向采样、17点横向采样。端部收束，实际每片8,160面。贴图像素精度不要求每个像素对应几何面；细网格用于贴体和浅凸曲面。
2. `repair_lip_contact140.py:53–95` 找到局部面心/边中点穿入后，对整片条带统一四分，以避免T接缝；两次就是16倍。当前梭鲈两片实际8,160和130,560面，与该机制精确吻合。历史中间报告未恢复，不声称读取了已清理的原实验记录。
3. `build_source_lips.py:14,44` 对身体使用统一体素重建再按比例DECIMATE。`mouth-repair-139.json` 的梭鲈/小黄鱼体素0.001、比例0.15；比例不是最终屏幕预算。当前黑鲷身体186,040面，但不能把这两个物种的历史参数当作黑鲷的完整来源证明。
4. `build_eye_relief.py:62–65,118–122` 使用均匀环×扇区。鲸鲨151参数36环×192扇区=每眼13,632面。此为被审计版本；其他任务正在继续改鲸鲨，不能当作永恒现值。
5. 鳍根另有局部接触细分，和唇带整片四分不同。身体、唇、眼缺少整鱼经审核的近中远LOD；被拒绝的旧自动LOD不可直接恢复。

此前28鱼审计中，零面积只占总面数约0.082%。清掉坏面不能把二十万降到一万；核心是大量有效但分配过密的面。独立唇带本身不是如此高面数的必然原因，合GLB也不改变三角面数。

## 独立减面实验

通过Godot ImporterMesh.generate_lods生成索引候选；检查导入器未改非索引顶点属性，再压紧实际引用顶点，保留UV/UV2/法线/颜色/骨骼权重对应；拒绝VERTEX_ID依赖shader。只对独立候选改索引，不重画材质，不修改生产配置。比例是选择最接近的现有LOD，所以10%实际是12.5%，3%实际约3.32%。候选没有作为自动LOD装入游戏。

|唇带面数|静止贴体采样|结果|
|---:|---:|---|
|138,720原版|625,522|通过−0.00003接触阈值|
|34,680候选|157,342|通过；最小距离−0.00002148|
|17,340候选|79,312|4个采样超阈；最小−0.00004052，拒绝|
|4,604候选|22,000|630个采样超阈；最小−0.00195775，且有退化面，拒绝|

Blender检查当前实际闭合身体，使用077同精度有符号索引；覆盖全部顶点、三角面心与三边中点。没有放宽接触阈值。34,680候选最高离体0.00060326，不高于原版0.00060735。此为静态诊断；不替代动作、完整鳍根、身体透明覆盖及最终导出门。

Godot新进程冷加载25%候选，使用实际工厂装配原鱼，再单独替换候选唇带。看过整鱼、侧面、正面、斜视A/B；所捕获尺度未见明显轮廓断裂，有少量光栅/明暗差异。另测一个游动时刻的头部图几乎重复，未保留，不作为动态证明。存储权重和原版同有约1.52e-5求和误差；首次1e-5诊断断言因此失败，改为报告实测值，未将其包装为通过原生权重门。

## Planet Zoo 1公开对照与来源限制

|公开上传的模型|页面Triangles|来源说明|
|---|---:|---|
|[Hippopotamus Planet Zoo](https://sketchfab.com/3d-models/hippopotamus-planet-zoo-ca96934a7f804ef091cc22d814786234)|13.1k|上传者说明来自游戏；无可核对LOD级别|
|[African Elephant Planet Zoo](https://sketchfab.com/3d-models/african-elephant-planet-zoo-56bd35c75a5d463889ef2e49b714337d)|17.4k|上传者说明来自游戏；无可核对LOD级别|
|[另一上传者同名大象](https://sketchfab.com/3d-models/elefante-planet-zoo-a3793cd8c33042d4842764386be87290)|17.4k|同一物种旁证，不是第三种动物|

这是第三方发布页对所上传模型的计数，不能确认为官方LOD0或全游戏统一预算。未下载/复用游戏资产。没有查到可信的官方逐物种面数表，不能编出狮虎数字。[原制作人员Carl-Christian Gehl](https://charactercarl.artstation.com/projects/8ekEd6)确认其制作的狐猴、山魈采用自定义毛发shader、多张贴图和顶点色、PBR；未公布面数。这解释外观复杂度和基础网格面数并非一一对应，但也不能据此说毛发无成本。

## 后续优化顺序

先按实际屏幕大小设每部件预算与误差，再改生成器：保留口裂/外轮廓/嘴角转折，平滑区稀疏；局部接触失败局部补拓扑，不整带翻16倍。高精度贴图继续保留，几何密度独立控制；小表面明暗用贴图/法线处理，真实轮廓和活动嘴不能烘成一条平线。眼片降低环扇区并复验贴体，身体做曲率驱动重拓扑，鳍保留鳍根与弯折密度。最后统一近/中/远LOD、固化导出，逐鱼验动作及切换。

面数优化之外，上轮50鱼测试已经发现控制器CPU和surface批次显著成本；这次减面不能被解释成卡顿全部解决。普通鱼近景先以数千至约两万面做试验目标，特殊大型展示鱼单独分配预算，最终由实际画面和群体性能决定，不强制跨鱼套用一个数字。

## 复现与保留

依次运行Foundry `probe_lip_reduction.gd`（Godot headless）、`check_reduced_lip_contact.py`（Blender background）、`render_lip_reduction.gd`（实际Compatibility GPU），均传`--output/目录`；最后`finish_lip_reduction.py --review <目录> --cleanup`。输出必须在本游戏`plans/reviews`下。详见三个脚本的参数入口；通用性能方法见Foundry skill `references/performance-audit.md`。

保留唯一有用候选lips-25.res、四张A/B、原始计数/接触/新进程报告、紧凑日志和本说明。原版资源继续由生产路径和SHA绑定；删除可重建二进制采样、两份失败候选和重复游动头图。精确删项、哈希、字节见validation-report.json；这不是用户验收，也没有提交推送。
'''
(root/'reduction-review.md').write_text(markdown,encoding='utf8')
result['cleanup']['remaining_files']=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(root.rglob('*')) if p.is_file() and p.name!='validation-report.json']
result['cleanup']['remaining_bytes_excluding_this_report']=sum(q['bytes'] for q in result['cleanup']['remaining_files'])
(root/'validation-report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'status':'done','candidate_status':result['candidate_status'],'inputs_checked':len(bindings),'removed_bytes':sum(q['bytes'] for q in deleted),'remaining_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),'report':str(root/'reduction-review.md')},ensure_ascii=False))
