"""Publish the six accepted, source-owned fish registry and handoff.

Run after species agents have completed their own release and cleanup.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/six-fish-release-20261104'
NAMES=dict(red_seabream='真鲷',black_seabream='黑鲷',crucian='鲫鱼',grass_carp='草鱼',carp='鲤鱼',bluegill='蓝鳃太阳鱼')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def ref(p):return {'path':str(p.resolve()),'sha256':sha(p)}
def main():
 records=[];index=[]
 for s,name in NAMES.items():
  folder=R/s;row=read(folder/'manifest.json')
  assert row['status']=='done' and row['installed'] and row['user_acceptance'] and row['formal_acceptance'],s
  for key in ['model','metadata','production_review','final_spec']:
   assert sha(row[key]['path'])==row[key]['sha256'],(s,key)
  spec=read(folder/'spec.json');sop=read(folder/'sop.validation.json');assert sop['ok'] and sop['evidence_count']>=54
  assert sop['review_sha256']==sha(folder/'production-review.json')
  canonical=read(folder/'canonical-load.validation.json');pixels=read(folder/'canonical-pixels.validation.json');assert canonical['ok'] and pixels['ok']
  source=G/f'assets/source/fish/{s}/fish.blend';freeze=G/f'assets/source/fish/{s}/frozen-static.json'
  records.append({**row,'name':name,'appearance_and_rig_frozen':True,'source':ref(source),'static_freeze':ref(freeze),'triangles':spec['expected']['triangles'],'sop_report':ref(folder/'sop.validation.json')})
  index.append({'species':s,'name':name,'metadata':row['metadata'],'model':row['model'],'source':ref(source),'static_freeze':ref(freeze)})
 cleanup=read(R/'cleanup-summary.validation.json')
 write(R/'manifest.json',{'kind':'six_fish_final_release','status':'done','next_action':'none','user_acceptance_date':'2026-11-04','user_acceptance_scope':'User explicitly extended finished-fish release/cleanup/commit to all six; requested seabream fin-border repair completed before freezing.','installed':True,'formal_acceptance':True,'appearance_and_rig_frozen':True,'future_scope':'Motion only by default; static reopening requires explicit user request.','completed_count':6,'records':records,'cleanup_summary':ref(R/'cleanup-summary.validation.json'),'protected_previous_finished_fish':ref(R/'protected-finished-fish.validation.json')})
 write(ROOT/'resources/volume-fish/final-six-fish-20261104.json',{'status':'finished','user_acceptance_date':'2026-11-04','appearance_and_rig_frozen':True,'future_scope':'Motion only by default, same finished-static category as accepted Nile tilapia R5. Explicit user reopening required for static changes.','release_handoff':str(R/'HANDOFF.md'),'fish':index})
 table='\n'.join(f"| {r['name']} | {r['triangles']} | `{r['model']['sha256']}` |"for r in records)
 handoff=f'''# 六鱼成品发布 — 2026-11-04

用户明确本轮真鲷、黑鲷、鲫鱼、草鱼、鲤鱼和蓝鳃太阳鱼全部归入成品，与罗非鱼R5同类；在指出真鲷鳍边线后要求修好、清理实验并提交。修复已完成，六鱼均已安装、整鱼接受、正式固化。默认后续只改动作，外形、全部鳍、UV/材质、蒙皮及骨架静态数据冻结；重新开启静态修改须有明确用户要求。

## 当前入口

- 总索引：Foundry `resources/volume-fish/final-six-fish-20261104.json`；本目录 `manifest.json` 是本轮状态入口。
- 每鱼：本目录 `<species>/spec.json`、`production-review.json`、`sop.validation.json` 和 `HANDOFF.md`。
- 可编辑源：游戏 `assets/source/fish/<species>/fish.blend`；成品：`game/assets/models/fish/<species>.glb`。
- 只读预览：Foundry `.venv/Scripts/python.exe resources/scripts/volume-fish/open_six_final.py --godot <Godot路径>`。

| 鱼 | 完整三角面 | 正式GLB SHA256 |
|---|---:|---|
{table}

## 本轮方法与参数

先对照本地鱼资料库与当前逐鱼SOP，逐条补缺；库模型作为美术/比例参考，不冒充生物实测。鲫、草、鲤、蓝鳃的体宽、口唇、头底供体、有限鳍根调整及未知均见各鱼handoff。厚度、取样、唇线及用户接受均没有跨鱼继承。

真鲷浮线来自鳍厚度侧壁使用不透明内缩UV，而对应原画鳍面透明。按同鱼原生source_u/v恢复侧壁与双侧鳍面一致的采样，真鲷修1284个wall loops，黑鲷独立确认同问题后修1158个。几何、法线、蒙皮、动作、原atlas RGBA及非wall UV保持逐项一致。实际看过新七鳍贴图/灰模、多视及正式四动作，独立浮线已消失，保留原画鳍条和像素轮廓。其余四鱼逐鳍复看，未把正常像素/鳍条边缘当成同一缺陷盲改；蓝鳃少量wall/cap边界差异及鲤鱼FLOAT32边界差异在专项报告如实保留。

## 当前验证

六鱼各自当前SOP的9阶段全部通过（每鱼54项基础证据，真鲷56项、黑鲷60项含本次修复追加项）；已完成原生口唇/上下颌体积、完整七鳍、同姿态490鳍根与鳍面、072、077 GPU覆盖、头型正负例、法线射线实厚/尾截面、原生循环与四动作/切换专项，以及可编辑源新进程冷导出。报告绑定实际当前输入；迁移历史报告时保留原字节、原SHA与明确路径映射，不把旧报告换模型SHA充当新验证。

游戏新进程实际正式入口、cache与独立GLB的静态数组/材质RGBA一致，480组动作控制、360组切换骨骼差为0，四动作GPU像素对为0差异。鲤鱼保留其实际审过的控制器，字节相同地部署为 `ReleasedCarpMotion20261104.gd`，没有替换成别鱼控制器。真鲷显示体长仍30cm：实际scale乘源bbox长度为0.3m；旧表名义scale .3不等于源bbox为1，此次未改变游戏尺寸。

旧四个运行时静态装配分支、相应导入钩子和final165/167/168/175重复载荷已在无live引用核验后移除。静态数据来自正式导出，正常实时动作保留。既有罗非鱼和上一批五鱼的静态指纹、实际加载及四动作像素再次核验一致，证据见 `protected-finished-fish.validation.json`；旧SOP仍是当时历史报告，该补充不冒充它们重走新版整套SOP。

## 清理与保留

本轮实际删除 **{cleanup['deleted_bytes']:,} bytes**，精确文件清单、SHA、逐事件收据和范围见 `cleanup-summary.validation.json` 引用。包含本轮六鱼被替代的候选、密集采样/截图、旧模型重复导出、已退役逐鱼实验与旧静态载荷，以及罗非鱼两个过时实验。保留当前规范源、游戏成品、必要原始供体/来源、可复现方法、完整数值结论、必要负例及少量代表图；未另建大压缩包。混合物种历史归档仍含未完成鱼的唯一输入，保留原处。

本轮以各项实际删除收据计数，不重复累计其内部引用的更早cleanup历史。Git删除减少当前检出体积；既有Git/LFS历史对象没有重写。当前保留范围和实际大小见 `retained-size.json`。提交前检查两仓库差异及新增LFS对象，只推送有保留价值的源、成品、方法与紧凑证据。
'''
 (R/'HANDOFF.md').write_text(handoff,encoding='utf8')
 old=G/'plans/reviews/six-fish-database-20261104';write(old/'manifest.json',{'kind':'retired_six_fish_database_review','status':'done','next_action':'none','retired':True,'reason':'All six accepted, installed and frozen; authoritative final records relocated.','current_manifest':str(R/'manifest.json'),'original_manifest':str(R/'history/initial-six-review-manifest.json')})
 (old/'HANDOFF.md').write_text('# 本轮实验已转成品\n\n六条鱼均已安装、用户接受并冻结。当前状态与证据见 [六鱼成品发布](../six-fish-release-20261104/HANDOFF.md)。原实验记录作为历史保留，已删除的密集采样或候选路径不再是当前入口。\n',encoding='utf8')
 print(json.dumps({'ok':True,'finished':list(NAMES),'deleted_bytes':cleanup['deleted_bytes']}))
if __name__=='__main__':main()
