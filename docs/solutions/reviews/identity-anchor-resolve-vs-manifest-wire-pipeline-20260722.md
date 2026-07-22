---
title: "style img2img：resolve 优先 identity 但 manifest 仍接线 style_anchor"
module: "cli/pipeline"
component: "pipeline_manifest._static_asset_tasks"
date: "2026-07-22"
last_reviewed: "2026-07-22"
category: "reviews"
status: "active"
confidence: "high"
problem_type: "review_finding"
severity: "high"
symptoms:
  - "resolve_style_img2img_path 对 follower 返回 hero_id_raw.png（identity），但 pipeline image.generate 命令仍带 hero_a_raw.png"
  - "manifest depends_on 挂在 style_anchor 的 image.generate，而非 identity 资产 → 竞态/错误参考图"
  - "单测只覆盖 resolve 路径、未覆盖 manifest 接线时漏检"
root_cause: "路径解析与任务接线拆成两处：resolve_* 已实现 identity 优先，_static_asset_tasks 仍按 style_anchor_kind==asset 固定找 style_anchor 产物，忽略已算出的 style_path 与 identity_anchor"
solution: "接线时先找 identity_anchor 对应资产作为 source；否则再 style_anchor / visual_reference。depends_on 与 --reference-image 必须来自同一 source；补回归测试断言 identity raw + task id"
prevention: "凡有 resolve_X_path 又有独立 wiring：测试必须覆盖 wiring（命令字符串/depends_on），不能只测 resolve；单槽优先级变更时同步改所有消费者"
sources:
  - ".ai/anvil/reviews/2026-07-22-style-img2img-stack-review.md"
  - "docs/anvil/brainstorms/2026-07-22-style-ref-enhance.md"
  - "cli/pipeline_manifest.py"
  - "cli/test_style_group.py::test_follower_identity_anchor_wires_reference_and_dep"
  - "commit dfcbf5e"
applies_to:
  - "cli/pipeline_manifest.py style img2img 分支"
  - "任何 resolve_* 与 depends_on/--flag 分离的 pipeline 接线"
verified_by:
  - "python -m unittest test_style_group test_pipeline_manifest … 54 OK"
  - "review APPROVED after fix"
related:
  - "architecture/style-group-img2img-and-art-tokens-20260722.md"
supersedes: []
superseded_by: []
tags:
  - "pipeline_manifest"
  - "identity_anchor"
  - "style_group"
  - "img2img"
  - "review_finding"
  - "depends_on"
---

## 症状

Phase 1 单测证明 `resolve_style_img2img_path(..., identity_anchor=hero_id)` → `hero_id_raw.png`，但 `pipeline plan` 生成的 follower `image.generate` 仍 `--reference-image …/hero_a_raw.png`，且 `depends_on` 只挂 style anchor 任务。

## 证据来源

- Review H1：`.ai/anvil/reviews/2026-07-22-style-img2img-stack-review.md`
- Spec：`docs/anvil/brainstorms/2026-07-22-style-ref-enhance.md`（单槽 identity 优先）
- 修复 commit：`dfcbf5e`

## 排查尝试

- 对抗式读 `resolve_*` → 逻辑正确，误以为接线已共用
- 对照 `_static_asset_tasks` asset 分支 → 发现覆盖了 `style_path`

## 根因分析

**解析与接线双源**：helper 已按 Spec 优先 identity；manifest 仍用「kind=asset → style_anchor」旧路径写 `ref_flag` / deps。`style_path` 只做了空值校验后被丢弃。

## 解决方案

### 修复前
```text
style_path = resolve_style_img2img_path(...)  # may be identity
if kind == "asset":
    target = find_asset(assets, spec.style_anchor)  # ignores identity
    depends_on(style_anchor); --reference-image style_anchor raw
```

### 修复后
```text
style_path = resolve_style_img2img_path(...)
if identity_anchor → source = that asset
elif kind == asset → source = style_anchor
elif visual_reference → ref_flag = style_path (no asset dep)
if source: depends_on(source.image.generate); --reference-image source raw
```

## 验证

- `test_follower_identity_anchor_wires_reference_and_dep`
- 相关 suite 54 OK；review 复审 APPROVED

## 适用范围

- **适用**：Foundry CLI pipeline 风格 img2img；同类「resolve 与 wire 分离」
- **不适用**：仅 `character_pose.reference_asset` 旧路径（本就同源接线）

## 预防措施

1. 优先级规则变更 → 列出全部消费者（manifest / meta / docs）  
2. 回归测 **命令与 depends_on**，不只测 path helper  
3. Review 对「算出 path 却未使用」做红旗检查

## 交叉引用

- 栈约定：[style-group + art_tokens](../architecture/style-group-img2img-and-art-tokens-20260722.md)
