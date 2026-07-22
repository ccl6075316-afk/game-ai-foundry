---
title: "cli/pipeline + cli/brief 风格相关沉淀"
module: "cli"
date: "2026-07-22"
last_reviewed: "2026-07-22"
category: "architecture"
status: "active"
confidence: "high"
problem_type: "knowledge_note"
severity: "low"
symptoms:
  - "模块索引：cli pipeline / brief 风格栈条目"
root_cause: "模块累计多条 solutions 时需要索引页"
solution: "本页列出 cli 风格相关 entries"
prevention: "新条目双向链到本页"
sources:
  - "docs/solutions/reviews/identity-anchor-resolve-vs-manifest-wire-pipeline-20260722.md"
  - "docs/solutions/architecture/style-group-img2img-and-art-tokens-20260722.md"
applies_to:
  - "cli/pipeline_manifest.py"
  - "cli/brief.py"
verified_by:
  - "compound 2026-07-22"
related:
  - "reviews/identity-anchor-resolve-vs-manifest-wire-pipeline-20260722.md"
  - "architecture/style-group-img2img-and-art-tokens-20260722.md"
supersedes: []
superseded_by: []
tags:
  - "cli"
  - "pipeline"
  - "brief"
  - "module-index"
---

# Module: cli（风格 / pipeline）

| 条目 | 类别 | 摘要 |
|------|------|------|
| [identity resolve vs manifest wire](../reviews/identity-anchor-resolve-vs-manifest-wire-pipeline-20260722.md) | reviews | resolve 优先 identity 但接线仍用 style_anchor |
| [style_group + art_tokens 栈](../architecture/style-group-img2img-and-art-tokens-20260722.md) | architecture | 正交字段、单槽、tokens、strength |
