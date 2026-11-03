"""Record an already reviewed candidate and exact cleanup in the original batch."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True);p.add_argument('--next-species',required=True);a=p.parse_args();s=a.species;root=ROOT/f'projects/fishing-2d/experiments/five-fish-database-20261103/{s}';review=read(root/'production-review.json');assert read(root/'sop-postcleanup.validation.json')['ok'];inv=read(root/'revision-invariants.validation.json');clean=read(root/'cleanup-execution.json');m=Path(review['candidate_files']['model']['path']);assert sha(m)==inv['model_sha256'];f=read(root/'current-evidence.validation.json');obs=f['operator_observations']
if not(root/'HANDOFF.md').exists():
 text=f'''# {s} · 资料库调整 2026-11-03

操作者审核已完成，独立导出候选待用户审阅；未替换游戏旧成品，未声称用户验收。

当前源：`{m.parent.name}/fish.blend`；当前成品：`{m.parent.name}/fish.glb`，SHA256 `{sha(m)}`。

当前完整状态：`production-review.json`、`sop.validation.json`、`sop-postcleanup.validation.json`。9阶段54证据通过；专项delivery manifest为填写整鱼操作者清单前的快照，最终状态以当前SOP报告为准。正式编辑源是packed blend，`source_projection`仅用于保留原source_t的独立验证，逐部件双向对应最终GLB。

本鱼{inv['triangles']}三角面、{inv['bones']}骨骼。身体轴{inv['body_axis_cm']:.6f}cm，最大宽{inv['before_maximum']['before_width_cm']:.6f}→{inv['after_maximum']['after_width_cm']:.6f}cm；库内同口径参考{inv['reference_maximum_width_cm']:.6f}cm。XY/UV/索引/蒙皮/骨架/动作不变，原alpha及受限腹面遮罩外RGBA逐像素不变。参考为第三方游戏美术模型，名称身份/年龄/生物精度未知，不称实测或跨鱼验收。

## 本鱼执行与实际观察
'''
 if inv.get('explicit_root_skin_exception'):text=text.replace('XY/UV/索引/蒙皮/骨架/动作不变','XY/UV/索引/骨架/动作不变；蒙皮只包含当前不变量报告逐点列明的完整鳍根权重修正，其余蒙皮原字节保留')
 if inv.get('explicit_fin_XY_exception'):text=text.replace('XY/UV/索引/骨架/动作不变','UV/索引/骨架/动作不变；XY只包含当前不变量报告逐点列明的亚像素鳍根修正，其余XY原字节保留')
 for stage,v in obs.items():text+=f'\n- **{stage}**：{v}\n'
 text+='''
## 来源、参数、方法与恢复

来源网格SHA、分组/排除部位、归一化及199截面：Foundry `output/five-fish-database-20261103/body-preflight/`内本鱼报告和transform报告。旧安装精确源、原生唇作者模型和独立source_t模板：`output/five-fish-database-20261103/restored/`内本鱼及恢复映射。

具体宽度场见`width-r1/deformation.plan.json`；后续微调各轮plan记录实测失败SHA和独立毫米位移。腹部来源/ROI/SHA/密度/原唇保护在`ventral-quilt-r2.config.json`、`ventral-protection.parameters.json`、`ventral-patch-r2.config.json`。原完整根域和实际当前嘴/厚度/尾截面/冷导出证明由`current-evidence.validation.json`索引；历史原唇作者报告绑定历史模型，不伪造为本轮运行。原生动作和Godot四动作/切换均为当前候选实际验证；离散490不证明全连续时间。

通用方法引用`resources/skills/fish-volume-production/references/five-fish-width-release-lessons-20261101.md`中2026-11-03补充；本鱼风险、适用证据和失败原因已写入上述实际观察。旧成品与新候选的接受状态分开，不照搬任何上一鱼参数。全490重验需用当前plan/模型重新导出，不能复用已精简的旧采样缓存。

## 交互与代表证据

`current-visual-review.jpg`、`source-final-side-comparison.jpg`、`motion-review.jpg`、本鱼`*-database-review.mp4`、`fin-volume-*`两张端/俯/斜视厚度图及`unlit-review`。影片为24秒真实Godot，非原画动画。批次交互入口在同级`review/`的catalog与启动器，完成整批后建立。

## 精确清理
'''
 text+=f"\n已删除{clean['removed_files']}文件、{clean['removed_bytes']}字节；清理后本鱼保留{clean['retained_files']}文件、{clean['retained_bytes_before_receipt']}字节（收据及本记录另计）。清单和SHA详见`cleanup.plan.json`、`cleanup-execution.json`。保留唯一当前源/成品、必要原始输入、完整数值、实际失败GLB及代表图视频；无新大压缩包。清理后SOP已再通过。\n"
 (root/'HANDOFF.md').write_text(text,encoding='utf8')
batch=ROOT/'projects/fishing-2d/plans/reviews/five-fish-width-detail-20261031';manifest=read(batch/'manifest.json');v=manifest['database_revision_20261103'];v['current_species']=a.next_species;v['next_action']=a.next_species+'_reference_review';row=dict(species=s,model=m.relative_to(ROOT).as_posix(),sha256=sha(m),status='done',next_action='human_review',installed=False,user_acceptance=False,handoff=(root/'HANDOFF.md').relative_to(ROOT).as_posix());v['candidates_completed']=[r for r in v['candidates_completed']if r['species']!=s]+[row];(batch/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
with (batch/'handoff.md').open('a',encoding='utf8') as fp:fp.write(f"\n2026-11-03 {s}资料库候选完成：{row['handoff']}；SOP/冷读/完整门及实际审图通过，安装和用户接受均false。删除{clean['removed_bytes']}字节，保留{clean['retained_bytes_before_receipt']}字节（后续记录另计）。\n")
print(json.dumps({'ok':True,'species':s,'next':a.next_species}))
