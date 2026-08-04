---
title: "整仓审查账本（完成优先 · 2026-08）"
date: "2026-08-04"
last_reviewed: "2026-08-04"
category: "reviews"
status: "active"
confidence: "high"
problem_type: "review_ledger"
severity: "high"
tags:
  - "whole_project_review"
  - "completion_first"
  - "permissions"
  - "visual_target"
  - "external_projects"
---

# 整仓审查账本（2026-08）

> **给下一只 AI / 下次 review**：先读本文件，再报「新」问题。  
> **已 Fixed / Accepted / Deferred 的项不要当未处理 Critical 再报一遍**，除非代码回退或有新证据。

## 产品立场（用户已确认 · 勿再争论）

| 原则 | 含义 |
|------|------|
| **完成需求 > 权限剧场** | 非开发会一路点过；细碎 Approve 不作为主防线 |
| **重视「做错 / 做不完」** | 串工程、外置走不通、静默错 type、文档教错命令 |
| **次要：纯信息危险** | redact 可保留；不为密钥面加严挡干活的权限 |
| **本机作者工具** | 不是公网多租户威胁模型 |

相关：[`docs/anvil/brainstorms/2026-08-03-visual-target-product-reframe.md`](../../anvil/brainstorms/2026-08-03-visual-target-product-reframe.md)（全局北极星伪概念 · draft）  
计划：[`docs/anvil/plans/2026-08-04-security-correctness-remediation-plan.md`](../../anvil/plans/2026-08-04-security-correctness-remediation-plan.md)（`git add -f` 入库）

---

## Fixed（已修 · 勿再报）

| ID | 问题 | 落点（约） | 备注 |
|----|------|------------|------|
| F1 | 路径 `..` 逃逸 | `gui/electron/externalFs.mjs` | P0 |
| F2 | `openExternal` 无白名单 | `gui/electron/main.mjs` | https + localhost |
| F3 | FOUNDRY_TOOL I/O 未 redact | `cli/pi_foundry_tools.py` | sk- 形；非完整密钥面 |
| F4 | validate 未知 type → CHARACTER | `cli/gamefactory.py` | exit 1 |
| F5 | 无桥仍可 mutate/`shell` + `--i-confirm` | `cli/pi_foundry_tools.py` | **完成优先**；非 fail-closed |
| F6 | VT status 用 `brief.json` 基名串工程 | `visual-target-status` + `manifestBelongsToBrief` | 只扫本工程树 |
| F7 | 外置 patch/media/ref 不通 | `patchBriefProject`、`resolveMediaAbs`、`refFileOk` | |
| F8 | `sameProjectRoot` 不认 external | `gui/src/chat/projectPaths.ts` | |
| F9 | 桥 URL 在但 HTTP 挂 → 全 deny | `tool_permission` → `unavailable` | 回退 `--i-confirm` |
| F10 | Brief 缺省 `type`→character | `cli/brief.py` AssetSpec / audit | 缺 type 显式错 |
| F11 | AI-HANDOFF 幽灵 `brief export`；VT 无 `--scene` | `docs/AI-HANDOFF.md`、VT skill | 多场景字段已点到 |

多场景北极星核心 CLI（scene pick 不污染 global 等）更早一批已合入；见 `cli/visual_target.py` + `test_visual_target.py`。

---

## Accepted（接受不修 · 下次 review 禁止当 Critical）

| ID | 项 | 用户/产品理由 |
|----|-----|----------------|
| A1 | 无桥 + `--i-confirm` 可跑 shell / pipeline run | 完成优先；白名单 + cwd 够用 |
| A2 | Hermes YOLO 默认开 | 与完成优先一致；勿默认 off 挡 headless |
| A3 | 细碎 GUI 权限弹窗不强制 | 非开发会一路点过 |
| A4 | redact 只覆盖 sk-/sk-or- 形 | 信息危险次要；可后续加强但不挡需求 |
| A5 | 全局 `project.visual_reference` 字段仍存在 | 产品重定位另案；兼容旧 brief |

---

## Deferred（未做 · 可报但须标 Deferred）

| ID | 项 | 优先级 | 说明 |
|----|-----|--------|------|
| D1 | Agent `workspaceCwd` 仍常为工厂 repo | High | 外置顶栏已绑，执行器改错树 |
| D2 | startup / plan 回退 `briefs[0]` | High | 无绑定时错工程 |
| D3 | Pipeline `shell=True` 拼串 | Med | 空格路径易碎 |
| D4 | safe_cli vs Pi 双白名单 | Med | 漂移风险 |
| D5 | `load_config` 迁移失败静默写盘 | Med | |
| D6 | `App.tsx` / `main.mjs` 拆分 | Low | 结构债，单独立 Spec |
| D7 | 北极星产品重定位（取消全局伪概念） | Product | brainstorm draft，未升 Spec |
| D8 | AI-HANDOFF Pipeline 示例仍有扁平路径 | Low | §5 已改 VT/export，pipeline 示例可再清 |
| D9 | `resolveMediaAbs` 截断 `output/` 仍扫多工程 | Low | 弱于旧 VT status |

---

## 给审查者的规则

1. **先对照本账本 Fixed / Accepted**；重复项只写「仍符合 Accepted A#」或「疑似回退 F#」。  
2. **新 Critical** 必须是：做错工程、做不完需求、或 Fixed 项回退。  
3. **不要**把「无桥可跑 shell」「YOLO 默认开」「redact 不完整」再标成必须立刻修的安全 Critical。  
4. 用户口头拍板后：**当场更新本文件**（或同目录新 ledger）并 **commit**，勿只留在对话里。

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-08-04 | 初版：整仓审查 + 完成优先重钉 + Critical 二轮修复入账 |
