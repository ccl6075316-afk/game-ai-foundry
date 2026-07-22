---
title: "Critical patterns"
module: "cross-cutting"
date: "2026-07-22"
last_reviewed: "2026-07-22"
category: "patterns"
status: "active"
confidence: "high"
tags: ["json-rpc", "acp", "critical"]
---

# Critical Patterns

## ❌ WRONG — 用 JSON-RPC `id` 先匹配出站 pending，再看 `method`

入站 **请求**（如 `session/request_permission`）也有 `id`。与客户端出站 id 撞车时会被当成响应，权限/回调丢失。

## ✅ CORRECT — 先分流 `method`，出站 id 用独立命名空间

1. `typeof msg.method === "string"` → 入站请求/通知  
2. 仅 `result`/`error` 且无 `method` → 匹配 pending  
3. 客户端 id 使用前缀字符串（如 `gaf-N`），避免与对端数字 id 重叠  

详见：[ACP JSON-RPC id 撞车](../failures/2026-07-22-acp-jsonrpc-id-collision.md)

## ❌ WRONG — 假设第三方 ACP「关自动放权」后所有工具都会 `request_permission`

Hermes 仅对**危险终端命令**走审批；且上游回调签名/`ToolCallUpdate` 缺陷会导致**静默 deny、不出 RPC**。

## ✅ CORRECT — 危险命令探针 + 检查 errors.log；Foundry 对 Hermes 注入 permission bridge 补丁

1. 用 `rm -rf /tmp/...` 类命令验证 `session/request_permission`  
2. 关注 `~/.hermes/logs/errors.log` 的 `Approval callback failed` / `RequestPermissionRequest`  
3. Spawn Hermes **venv** 二进制并带 `hermes_acp_runtime` sitecustomize（勿依赖会 `unset PYTHONPATH` 的 wrapper）

详见：[Hermes ACP 审批桥](../failures/2026-07-22-hermes-acp-permission-bridge.md)
