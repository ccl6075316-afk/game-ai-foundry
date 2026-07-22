---
title: "Hermes ACP：审批回调签名/ToolCall 类型错误导致无 permission 卡"
module: "gui/electron"
component: "hermes_acp_runtime"
date: "2026-07-22"
last_reviewed: "2026-07-22"
category: "failures"
status: "active"
confidence: "high"
problem_type: "upstream-bridge-bug"
severity: "hermes-acp"
symptoms:
  - "Hermes yolo=false 已走 ACP，危险命令结果为 BLOCKED: User denied，但 GUI 从不出批准卡"
  - "stdout 无 session/request_permission"
root_cause: "Hermes 0.13.x acp_adapter.permissions.make_approval_callback：(1) 不接受 allow_permanent= 被 TypeError 吞掉；(2) start_tool_call 得到 ToolCallStart，RequestPermissionRequest 需要 ToolCallUpdate → 校验失败后 deny"
solution: "Foundry 用 PYTHONPATH sitecustomize 替换 make_approval_callback；spawn Hermes venv 二进制（避开 ~/.local/bin/hermes unset PYTHONPATH）"
prevention: "接第三方 ACP 前用危险命令探针确认 request_permission 出站；记录 stderr/errors.log；勿假设「关 yolo=全工具弹卡」（Hermes 仅危险命令）"
sources:
  - "docs/anvil/debug-sessions/2026-07-22-hermes-acp-no-permission-card-session.md"
  - "docs/anvil/brainstorms/2026-07-22-hermes-acp-midturn.md"
  - ".ai/anvil/reviews/2026-07-22-hermes-acp-midturn-review.md"
  - "commit 6e9ef5d"
  - "用户确认：修后有卡"
applies_to:
  - "gui/electron/hermes_acp_runtime/sitecustomize.py"
  - "gui/electron/hermes_acp_session.mjs"
  - "Hermes Agent ≤0.13.x ACP"
verified_by:
  - "本机探针 got_perm True"
  - "node --test hermes_acp_*.test.mjs"
  - "用户手测确认"
related:
  - "failures/2026-07-22-acp-jsonrpc-id-collision.md"
supersedes: []
superseded_by: []
tags:
  - "hermes"
  - "acp"
  - "permission"
  - "upstream"
  - "electron"
---

## 症状

GUI Hermes `yolo=false` 已 handshake/session created；危险终端命令被 `BLOCKED: User denied`，但**从不**弹出批准卡。

## 证据来源

- Debug session、errors.log（`allow_permanent` TypeError；随后 `ToolCallStart` vs `ToolCallUpdate`）
- 探针：补丁前 `got_perm False`；补丁后 `got_perm True`
- 用户确认「没问题了」

## 排查尝试

- 怀疑 Foundry JSON-RPC id 撞车（Cursor 旧伤）→ Hermes 入站已 method-first，且链路无 permission 帧
- 怀疑 `--accept-hooks` 吞权限 → 去掉后仍无 permission 帧
- 普通 `echo` 不弹卡 → **产品语义**：Hermes 仅危险命令走审批

## 根因分析

`tools.approval.prompt_dangerous_approval` 调用 `approval_callback(..., allow_permanent=)`；上游 ACP 回调签名不匹配 → deny。  
修签名后仍 fail：`start_tool_call` → `ToolCallStart`，协议要 `ToolCallUpdate`。

## 解决方案

### Foundry 侧
1. `hermes_acp_runtime/sitecustomize.py` 替换 `make_approval_callback`
2. `resolveHermesAcpLaunch` 优先 venv `hermes` + `PYTHONPATH`（wrapper 会 `unset PYTHONPATH`）

### 上游
等待 Hermes 正式修复后可考虑去掉补丁。

## 验证

危险命令探针出现 `session/request_permission`；GUI 出卡。

## 适用 / 不适用

- **适用**：Hermes ACP mid-turn 宿主
- **不适用**：Cursor ACP；Hermes one-shot `--yolo`
