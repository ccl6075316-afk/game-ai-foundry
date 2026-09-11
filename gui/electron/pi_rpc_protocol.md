# Pi RPC 协议（Foundry 最小子集）

内嵌 `@earendil-works/pi-coding-agent` 的 **官方 NDJSON RPC**，非 ACP / 非 MCP。

## 进程入口

| 方式 | 命令 | 说明 |
|------|------|------|
| **推荐** | `node <embed>/dist/rpc-entry.js` | 薄包装，等价于 `main(["--mode","rpc", ...])` |
| 等价 | `node <embed>/dist/cli.js --mode rpc` | 与官方 `RpcClient` 默认 spawn 一致 |

`<embed>` 通常为 `gui/runtime/pi`（见 `embed-manifest.json`）。`cwd` 建议设为 embed 根或仓库根。

## 传输

- **stdin**：客户端 → Pi，每行一条 JSON 命令（LF 分隔，严格 JSONL）
- **stdout**：Pi → 客户端，每行一条 JSON **response** 或 **event**
- **stderr**：人类可读日志；Foundry 仅截尾调试

## 命令（出站）

每条命令带 `type`；客户端应附加字符串 `id` 做关联（Foundry 建议前缀 `gaf-pi-N`，避免与 Pi 内部 UUID 撞车）。

| type | 字段 | 说明 |
|------|------|------|
| `prompt` | `message`, `images?` | 发用户消息；响应快返，流式内容走 event |
| `new_session` | `parentSession?` | 新建会话 |
| `switch_session` | `sessionPath` | 切换会话文件 |
| `get_messages` | — | 返回 `data.messages` |
| `get_state` | — | 返回 `data`（`RpcSessionState`） |
| `abort` | — | 中止当前运行 |

完整命令表见 embed 包 `dist/modes/rpc/rpc-types.d.ts`。

## 响应（入站，`type: "response"`）

```json
{ "type": "response", "id": "gaf-pi-1", "command": "get_state", "success": true, "data": { ... } }
```

失败：

```json
{ "type": "response", "id": "gaf-pi-1", "command": "prompt", "success": false, "error": "..." }
```

`prompt` / `steer` / `follow_up` / `abort` 等成功响应通常无 `data`。

## 事件（入站，非 response）

Agent 流式输出与会话生命周期事件，**无** `type: "response"`，例如：

- `agent_settled` — 一轮结束；客户端 `waitForIdle` 等此事件
- `agent_message_chunk` / 其它 `AgentSessionEvent`（见 embed 运行时）

扩展 UI（RPC 模式可选）：

```json
{ "type": "extension_ui_request", "id": "<uuid>", "method": "confirm", ... }
```

客户端回复：

```json
{ "type": "extension_ui_response", "id": "<uuid>", "confirmed": true }
```

## 入站分流（Foundry 必守）

参考 `RpcClient.handleLine` 与 `docs/solutions/patterns/critical-patterns.md`：

1. **`type === "response"` 且 `id` 命中 pending** → 完成出站请求
2. **其它** → 当作 event（含 `extension_ui_request`）；**不能**仅凭 `id` 匹配 pending

## 最小交互序列

```
→ {"type":"new_session","id":"gaf-pi-1"}
← {"type":"response","id":"gaf-pi-1","command":"new_session","success":true,"data":{"cancelled":false}}
→ {"type":"get_state","id":"gaf-pi-2"}
← {"type":"response","id":"gaf-pi-2","command":"get_state","success":true,"data":{...}}
→ {"type":"prompt","id":"gaf-pi-3","message":"hello"}
← {"type":"response","id":"gaf-pi-3","command":"prompt","success":true}
← {"type":"agent_message_chunk", ...}   // 若干 event
← {"type":"agent_settled", ...}
→ {"type":"get_messages","id":"gaf-pi-4"}
← {"type":"response","id":"gaf-pi-4","command":"get_messages","success":true,"data":{"messages":[...]}}
```

## 参考实现

- `gui/runtime/pi/node_modules/@earendil-works/pi-coding-agent/dist/modes/rpc/rpc-client.js`
- `gui/runtime/pi/node_modules/@earendil-works/pi-coding-agent/dist/modes/rpc/rpc-types.d.ts`
- `gui/runtime/pi/node_modules/@earendil-works/pi-coding-agent/dist/modes/rpc/rpc-mode.js`
