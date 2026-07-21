# Spike：Feature B v2 — 三方执行器审批通道（2026-07-22）

**状态**：spike 完成  
**本机**：Hermes `v0.16.0` · Codex `0.144.5` · Cursor Agent `2026.07.16`  
**前提**：B v1（Pi `FOUNDRY_TOOL` GUI 卡片）已上线。  
**探查**：本机 `--help` + [B v2 审批通道 Spike](479f49ea-1b76-443f-b3a4-53b2a8f17c94) 深挖（含 ACP / app-server 文档）

## 结论一句话

当前 Foundry 的 **one-shot + `capture_output`** 路径**不能**做 mid-turn GUI 批准。  
上游**并非没有**协议：Hermes / Cursor 有 **ACP**（stdio JSON-RPC + permission）；Codex 有 **app-server**（experimental）。  
v2 最小有用增量仍是 **配置层安全旋钮**；若要「像 Pi 一样点卡片」，应 **单执行器 ACP 试点**，不要在 `--yolo` / `--force` / `codex exec` 上假变严。

## 总表

| 执行器 | Foundry 今日 | 静态旋钮 | 机读双向审批 | GUI 桥 |
|--------|--------------|----------|--------------|--------|
| Hermes | `chat --yolo` | 关 yolo（无 ACP 会挂） | **`hermes acp`** | ACP **高** / 现状 **低** |
| Codex | `exec` + sandbox | `--sandbox` 三档 | **`codex app-server`**（非 exec JSONL） | app-server **中** / 现状 **低** |
| Cursor | `-p --force` | force / mode plan\|ask / sandbox / `--auto-review` | **`agent acp`** | ACP **高** / 现状 **低** |
| Pi | FOUNDRY_TOOL 桥 | — | loopback HTTP | **已有** |

要点：`codex exec --json`、Cursor `stream-json` 主要是**观察性**事件，**不是**审批握手。

## 产品选项（请选）

### 1 — 配置层安全（推荐作 B v2 本体）★

- Codex：`sandbox` 可配（默认 `workspace-write`）  
- Cursor：强制 / Smart Auto / 只读 plan\|ask  
- Hermes：yolo 开关；**关 yolo 时若未接 ACP → GUI 禁用或明确报错**（禁止挂死）  
- **不做** mid-turn 卡片  

### 2 — Cursor 或 Hermes **ACP 试点** + 复用 Pi 审批卡

- 常驻 ACP 进程；`session/request_permission` → 内联卡 → once/session/always/deny  
- 单执行器先上，Codex 后置  
- 工期中；要改 `agent turn` 会话模型  

### 3 — Codex **app-server** 深度集成（大 Spec / 延后）

- 完整 command/file/permissions 审批；experimental + 会话模型重  

可组合：**先 1 后 2**。

## 硬约束（写进正式 Spec）

1. 禁止「去掉 `--yolo`/`--force` + 仍 `capture_output`」。  
2. exec JSONL / stream-json ≠ 审批总线。  
3. ACP/app-server 与现有 one-shot `agent-turn` **不兼容**——并行新路径或限定角色迁移。  
4. 决策语义对齐：Pi once/turn/session ↔ ACP once/session/always ↔ Codex accept/acceptForSession/decline。

## 明确不做（本阶段）

- 假安全（关 YOLO 却阻塞子进程）  
- 一次上三家完整 mid-turn  
- 永久全局「一律允许」三方工具  
