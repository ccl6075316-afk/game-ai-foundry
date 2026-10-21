---
{
  "module": "cli/volume-fish",
  "date": "2026-10-15",
  "problem_type": "logic_bug",
  "severity": "high",
  "symptoms": [
    "八项技术检查和包络全绿，但巨骨眼位头高17.29cm仍明显偏离暂定资料范围。",
    "双髻鲨胸/腹鳍根边界悬空约1.8–3.8cm，原生和实际Godot动作均可复现。",
    "原尾叶polygon只保留同ROI源轮廓43.21%/48.40%，UV不透明检查不能发现削窄。"
  ],
  "root_cause": "验证只覆盖文件、网格闭合、权重、循环和边界包络，未把研究资料、解剖测位、实际蒙皮接触和源图轮廓转成独立条件。",
  "solution": "补充带来源和限制的截面/围度对照、完整成对鳍根表面投影与身体权重、同ROI尾叶恢复以及四动作实际蒙皮检查；保留整体视觉pending。",
  "prevention": "准备阶段冻结可比测位、比例分母、未知项与失败基线；交付分别验证六层条件并绑定模型和检查器哈希，禁止用局部通过替整鱼接受。",
  "tags": [
    "fish",
    "3d",
    "anatomy",
    "validation",
    "preparation"
  ]
}
---

## Symptoms

可复现的052基线检查：`FAILED (failures=4)`。眼位头高9.556%暂定SL，超出原样本4–8.2%；成对鳍根整段在体外；18原生相位和32个实际Godot动作采样均悬空；尾叶轮廓面积不足一半。全鱼最大宽与鳃盖局部宽不可直接比较。

## Investigation Attempts

只压鳃盖Y宽保留了过高头部和粗躯干；保留原生拓扑/动画也保留原悬空鱼鳍。扩大正面投影或修UV不能更改隐藏截面和尾叶polygon。技术检查和包络通过无法解释这些用户可见错误。

## Root Cause Analysis

研究数据没有进入逐测位比较；侧图腹缘v加独立root_depth不是身体表面；尾叶UV可全部不透明，几何轮廓仍可被削窄。圈定的根带要与真实解剖对应，斜向尾骨t参数不能泛化到所有鱼鳍。

## Solution

### Before

```python
# 不充分的验收含义：单个封闭部件和包络无法证明接住身体。
checks = {"closed_mesh": closed, "animation_loop": loop_ok}
inside_envelope = contained
```

### After

```text
准备：物种/体型 → 原表/测法图 → TL/SL与测位 → 证据类别/未知 → 冻结输入
验证：技术 + 资料对照 + 根部接触 + 源图轮廓 + 实机蒙皮动作 + 灰模/整体视频
结论：限定指标通过；缺失截面失败；未知项和整体视觉继续pending
```

053实测眼位头高11.0168cm；中段周长95.361/95.367/95.315cm，符合明确标记的95.3561cm派生场景。成对鳍在四动作各8时点保持接触；同ROI尾叶覆盖上/下99.29%/98.61%。嘴宽属于制作推断，未解决头肩接缝等观感问题，正式游戏模型未替换。

## Prevention

准备前写出同测位比较和能抓住旧问题的失败基线。均值、SD、观测范围、工程容差、跨研究外推分别记录。缺测位/空采样/重复采样/陈旧哈希必须失败。保存实际皮肤蒙皮证据，不能拿包络检查替代。长报告无损归档，模型和代表性视频可复现。

## Cross References

- [完整排障](../../anvil/debug-sessions/2026-10-15-fish-anatomy-validation-session.md)
- [限定范围复审](../../anvil/reviews/2026-10-15-fish-anatomy-phase4-review.md)
- [常用工作流](../../FISH-VOLUME-WORKFLOW.md)
- fish本地准备/验证指南：`projects/fishing-2d/docs/3d-fish/PREPARATION.md`、`VALIDATION.md`。


相关材质案例：[源描边污染新增鱼皮肤](source-outline-contaminates-fish-skin-20261020.md)，独立解释像素供体、透明扩展与局部保留门，不替代解剖/鳍身门。
