# Debug Session: Hermes ACP 无权限卡片

- **Created**: 2026-07-22
- **Updated**: 2026-07-22
- **Mode**: Normal（本机 ACP 探针 + `~/.hermes/logs/errors.log`）
- **Symptom**: Hermes `yolo=false` 对话不出批准卡
- **Status**: root cause found + Foundry runtime patch shipped

## 证据

1. GUI 日志：`hermes acp handshake complete` / `session created` → ACP 路径已走通。
2. 探针：`echo` / 普通命令 **从不**发 `session/request_permission`（Hermes 仅危险命令审批）。
3. 危险命令 `rm -rf …`：终端结果 `BLOCKED: User denied`，但 stdout **无** `session/request_permission`。
4. `~/.hermes/logs/errors.log`：
   - `TypeError: ... unexpected keyword argument 'allow_permanent'`
   - 补丁后：`validation error for RequestPermissionRequest` — `ToolCallStart` vs `ToolCallUpdate`

## 根因（High）

Hermes 0.13.x `acp_adapter.permissions.make_approval_callback` 双缺陷：

1. 回调签名不接受 `allow_permanent=`（`tools.approval` 会传入）→ 捕获后 deny。
2. 使用 `start_tool_call` → `ToolCallStart`，但 ACP 需要 `ToolCallUpdate` → 校验失败 → deny。

因此 GUI 永远收不到 permission RPC，表现为「没有权限卡片」；危险命令被静默拒绝。

## 修复

- `gui/electron/hermes_acp_runtime/sitecustomize.py`：替换 `make_approval_callback`（接受 kwargs + `ToolCallUpdate`）。
- `hermes_acp_session.mjs`：优先 spawn Hermes **venv** 二进制并注入 `PYTHONPATH`（避开 `~/.local/bin/hermes` unset PYTHONPATH）。
- 文档：说明仅危险命令弹卡。

## 验证

- 探针：`got_perm True`，options `allow_once|allow_always|deny`。
- `node --test hermes_acp_*.test.mjs`（修复后应绿）。
- 用户手测：关 YOLO → 要求执行危险命令（如 `rm -rf /tmp/...`）→ 应出卡。
