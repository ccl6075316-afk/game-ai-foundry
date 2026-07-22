---
title: "Brief 风格栈：style_group img2img、identity 单槽、art_tokens"
module: "cli/brief"
component: "style_group / art_tokens"
date: "2026-07-22"
last_reviewed: "2026-07-22"
category: "architecture"
status: "active"
confidence: "high"
problem_type: "architecture_issue"
severity: "medium"
symptoms:
  - "需要同屏角色/贴图风格一致，但仅靠 art_direction 文生图漂移大"
  - "pose/视频参考与风格锚点易混用同一字段"
  - "Gemini 路径几乎不尊重 API strength，只改 config 无效"
root_cause: "风格从属、身份锁定、动作参考是正交关注点；散文 art_direction 不足以作硬锁；默认图像后端对 strength 支持弱"
solution: "style_group + style_anchor(_kind) 驱动 still img2img；identity_anchor 占用唯一 --reference-image 槽且优先于 style；pose/视频仍用 reference_asset；可选 project.art_tokens 注入 craft；strength 默认 0.25 best-effort + prompt soft 文案为主；icon_kit 禁止 style img2img"
prevention: "brief/skills 写清正交字段；pipeline 与 resolve 共用优先级；新后端再谈 LoRA；Phase3 GUI 只暴露已有字段勿另造平行模型"
sources:
  - "docs/anvil/brainstorms/2026-07-22-style-group-img2img.md"
  - "docs/anvil/brainstorms/2026-07-22-style-ref-enhance.md"
  - "docs/anvil/brainstorms/2026-07-22-art-tokens.md"
  - "docs/AI-HANDOFF.md"
  - "commit dfcbf5e"
applies_to:
  - "cli/brief.py"
  - "cli/pipeline_manifest.py"
  - "cli/shared_context.py"
  - "resources/skills/prompt-crafter/*"
  - "resources/skills/orchestrator/commit-brief.md"
verified_by:
  - "cli/test_style_group.py"
  - "cli/test_art_tokens.py"
  - "cli/test_image_strength.py"
  - "review 2026-07-22-style-img2img-stack APPROVED"
related:
  - "reviews/identity-anchor-resolve-vs-manifest-wire-pipeline-20260722.md"
supersedes: []
superseded_by: []
tags:
  - "style_group"
  - "art_tokens"
  - "img2img"
  - "identity_anchor"
  - "brief"
  - "prompt-crafter"
---

## 症状 / 产品动机

同组角色/贴图需要视觉一致；仅 `art_direction` 散文不稳定。需要可审计的 brief 字段与 pipeline 自动 `--reference-image`，且不破坏 pose / i2v 的 `reference_asset`。

## 证据来源

- Specs：`style-group-img2img`、`style-ref-enhance`（终局 C / 本期 A→已做 Phase1+2）、`art-tokens`
- 落地 commit：`dfcbf5e`
- 文档：`docs/AI-HANDOFF.md` 风格组与 art_tokens 节

## 架构要点

| 关注点 | 字段 / 机制 |
|--------|-------------|
| 风格从属 | `style_group`, `style_anchor`, `style_anchor_kind`, `use_style_img2img` |
| 身份优先（单槽） | `identity_anchor` > style anchor / visual_reference |
| 动作 / 视频 | `reference_asset`（不替换） |
| 硬锁文案 | 可选 `project.art_tokens`（`line`/`palette`/`forbid`/`silhouette`）+ 必填 `art_direction` |
| 强度 | config `image.style_img2img_strength` best-effort；**Gemini 以 prompt soft 为主** |
| Recipe | character/texture/background 可；**icon_kit 否** |

## 解决方案（已落地）

- `should_use_style_img2img` / `resolve_style_img2img_path` + manifest 接线（含 identity）
- `normalize_art_tokens` / context 注入；skills 优先 tokens → `style_lock`
- 示例：`resources/style-group-img2img.example.json`

## 验证

单元测试 + stack review APPROVED + push `main@dfcbf5e`

## 适用范围

- **适用**：Foundry brief → pipeline still 生成
- **不适用**：LoRA / 本地 SD 后端（未接）；Phase 3 GUI（未做）

## 预防措施

- 勿把风格散文写入 `visual_reference`
- 改优先级必同步 manifest（见 related review 页）
- Phase 3 只绑现有字段

## 交叉引用

- [identity resolve vs wire](../reviews/identity-anchor-resolve-vs-manifest-wire-pipeline-20260722.md)
