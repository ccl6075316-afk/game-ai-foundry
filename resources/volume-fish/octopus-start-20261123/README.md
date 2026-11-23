# 章鱼动作基础 · 2026-11-23

当前可继续制作的版本为 **R7**。用户已认可右前腕更紧的卷曲，并明确允许卷层内部少量穿插；本次提交保存工作基础，后续动作由用户继续制作。

## 直接继续做动作

- **Blender源**：[motion-r7/octopus-actions.blend](motion-r7/octopus-actions.blend)。这是当前完整可编辑模型。
- **导出模型**：[motion-r7/octopus-actions.glb](motion-r7/octopus-actions.glb)。
- **动作预览**：[10秒收放录像](motion-r7/tighter-roll.mp4)。
- **状态入口**：[release.json](release.json)，完整过程与参考见[handoff.md](handoff.md)。

Blender打开源文件后选章鱼骨架，在Dope Sheet的Action Editor中选 `TightRoll`、`ProbeTouch` 或 `AlternatingTouch` 编辑。源为30 fps：TightRoll帧1–301（10秒），其余两段帧1–481（16秒）。NLA轨道默认静音供选择，切换Action时不要同时混入同名NLA轨道；`TightRoll_Baseline`是旧曲线留档，不是当前导出动作。

八条腕足各64骨，命名如 `R_IV_00` 到 `R_IV_63`；加Root共513骨。完整资产50,000三角面，512个代表性吸盘。当前只有右IV的TightRoll比R5增加9%局部弯曲；其他七腕及两段触底动作未继承本次外观认可。

## 预览

macOS可双击 `open-motion-review.command`（当前机器Godot路径）。其他电脑使用Godot 4 Mono，打开 `motion-r7/review/project.godot`，或在此目录运行：

```sh
godot --path motion-r7/review --script motion-r7/review/Actions.gd --rendering-method gl_compatibility
```

Blender与GLB/PDF通过仓库百度LFS存储。另一台电脑拉取前按[存储说明](../../../docs/storage/baidu-lfs-20261109/AUTO-TRANSFER.md)配置已有百度传输工具，再 `git lfs pull`。

## 本次接受范围与后续

优先卷拢的外观；卷层内部少量重叠可以接受。只修明显穿出外皮、露馅交叉及动作突变，不再为了零穿插刻意留缝。R6局部压平导致方形内圈的路线已停用。

这是已认可的右前腕动作基础，尚未完成整章鱼的游动、取食、吸附物理、全身动作与材质，也未安装到游戏。不要将单腕认可或源冷导通过写成完整物种/生产SOP通过。物种比例以Enteroctopus dofleini为基础，宽厚等造型插值的限制沿用原记录。

R5源/GLB保留为R7作者脚本与差异检查的输入；若直接编辑R7源，不要随后误运行build_tighter_roll.py覆盖你的手工修改。旧候选重型文件已退休，历史报告保留其当时SHA和结论；逐文件清单见checkpoint-cleanup.validation.json。
