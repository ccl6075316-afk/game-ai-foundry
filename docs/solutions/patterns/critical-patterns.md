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
