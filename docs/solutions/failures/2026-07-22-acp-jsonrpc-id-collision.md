---
title: "ACP / JSON-RPC：入站 request 与出站 id 撞车会吞掉 permission"
module: "gui/electron"
component: "cursor_acp_session"
date: "2026-07-22"
last_reviewed: "2026-07-22"
category: "failures"
status: "active"
confidence: "high"
problem_type: "protocol-race"
severity: "cursor-agent-acp"
symptoms:
  - "Cursor ACP 回合能出回复，但从不弹出工具批准卡"
  - "session/request_permission 在链路中丢失"
root_cause: "handleRpcLine 先用 msg.id 匹配 pendingRpc；Agent 入站 permission 请求也带数字 id，与客户端 session/prompt 的 id 撞车时被当成 RPC 响应，权限回调永不触发"
solution: "先处理带 method 的入站消息；客户端出站 id 使用字符串前缀（如 gaf-N）；仅无 result/error 且无 method 的消息匹配 pendingRpc"
prevention: "凡双端共用 stdio JSON-RPC：响应匹配必须排除 method；客户端 id 命名空间与对端隔离；为 permission 路径加撞车回归测"
sources:
  - "docs/anvil/brainstorms/2026-07-22-cursor-acp-midturn.md"
  - ".ai/anvil/reviews/2026-07-22-cursor-acp-midturn-review.md"
  - "commit 882969f"
  - "用户确认：修后批准卡出现"
applies_to:
  - "gui/electron/cursor_acp_session.mjs"
  - "任何自研 ACP/JSON-RPC stdio 宿主"
verified_by:
  - "node --test cursor_acp_*.test.mjs（含 numeric id collision）"
  - "本机 agent acp shell 探针 + GUI 手测"
related: []
supersedes: []
superseded_by: []
tags:
  - "cursor"
  - "acp"
  - "json-rpc"
  - "permission"
  - "electron"
---

## 症状

GUI 已走 Cursor ACP（`permission_mode ≠ force`），助手能回复，但**从不**出现「Cursor 需要批准」卡。

## 证据来源

- Spec / Review：Cursor ACP mid-turn
- 本机探针：`session/request_permission` 在 shell 工具调用时会出现
- 用户确认修复后卡可见

## 排查尝试

- 怀疑未 `set_mode` / 未声明 `clientCapabilities`（相关，但不足以解释「有工具也不弹」）
- 怀疑纯闲聊无工具（真，但是否弹卡的产品边界，不是吞事件的根因）

## 根因分析

Agent→Client 的 `session/request_permission` 是 **带 `id` + `method` 的请求**。  
错误顺序：先 `pendingRpc.has(id)` → 撞车时当作 `session/prompt` 的响应 → `resolve(undefined)` → 回合结束，permission 从未交给 UI。

## 解决方案

### 修复前
```text
if (id in pendingRpc) treat as response
else if (method) feed adapter
```

### 修复后
```text
if (method) feed adapter  // permission / update first
else if (result|error) resolve pendingRpc
client ids: "gaf-1", "gaf-2", ...
```

另：`initialize` 带 `clientCapabilities`；`plan`/`ask` 调 `session/set_mode`。

## 验证

- 单测：numeric permission id 不偷 prompt 响应
- 手测：auto_review + 需 shell 的提示 → 出卡

## 适用 / 不适用

- **适用**：双向 JSON-RPC over stdio（ACP 等）
- **不适用**：单向通知流、或严格分端口的请求/响应通道
