# 工程 Spec：Cursor ACP mid-turn 审批试点

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-22
- **Updated**：2026-07-22（用户「确认」）
- **Confirmed By**：user「确认」（2026-07-22）
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan` artifact [`docs/anvil/plans/2026-07-22-cursor-acp-midturn-plan.md`](../plans/2026-07-22-cursor-acp-midturn-plan.md) once that plan is user-confirmed for `/anvil:code`
- **Requirements Source**：用户「做 acp」；Grill：先 Cursor、非 force→ACP、按实例常驻、仅 GUI、Pi 四键 always→本会话；用户确认 Spec
- **Background Inputs**：[`docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md`](../../superpowers/specs/2026-07-22-executor-permission-b2-spike.md)；B v1 Pi 审批卡 Spec；B v2 安全旋钮 + 实例覆盖（已落地）；聊天确认选项 4
- **Compounded Knowledge**：[`docs/solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md`](../../solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md)

## 背景输入

- Foundry 对 Cursor 今日走 one-shot `agent turn` + `--force`（或静态 `permission_mode`），**无法** mid-turn GUI 批准。
- Spike：Cursor 有 `agent acp`（stdio JSON-RPC + permission）；与 one-shot **不兼容**。
- Pi 已有 Electron loopback 桥 + 内联卡（once / 本回合 / 本会话 / 拒绝）。
- Hermes/Codex ACP·app-server、永久一律允许，仍后置。

## 工程理解

为 **Cursor** 增加并行路径：当生效 `permission_mode ≠ force` 时，由 Electron 按**同事实例**维护常驻 `agent acp` 会话；`session/request_permission`（及等价 permission 请求）挂起 → GUI 内联卡 → 回写 ACP 决定 → 继续。  
`force` 保持现有 one-shot，行为与今日一致。  
CLI 无卡片宿主：非 force Cursor **拒跑**并提示改 GUI 或改回 force。

硬约束：禁止「去掉 `--force` 却仍 `capture_output` 阻塞等待」的假安全。

## 目标

1. **触发条件**：解析后的 Cursor `permission_mode`（实例 → 全局 → 默认）≠ `force`，且请求来自 **GUI** `agent-turn`（或等价聊天 IPC）。  
2. **生命周期**：每同事实例最多一个 ACP 子进程；首次非 force 回合拉起；后续消息复用；切回 force / 卸载同事 / 关窗 / 空闲超时 → 停止。  
3. **审批 UI**：复用 Pi 卡片交互：`允许一次` | `本回合允许` | `本会话允许` | `拒绝`。  
4. **语义映射**：  
   - 一次 → ACP `once`（或等价单次）  
   - 本回合 → Foundry turn 级缓存（对齐 Pi turnAllow）  
   - 本会话 → Foundry session 级缓存，并对 ACP `always` **仅映射为进程存活期内允许**，**不**写入 config 永久放权  
   - 拒绝 / 超时 → deny；回合不崩，错误回传模型侧（若协议支持）或用户可见失败气泡  
5. **force 路径**：仍 `run_cursor_turn` one-shot + `--force`（或现有 force 组装），不启 ACP。  
6. **CLI**：`agent turn` 且 Cursor 且 mode≠force → `AgentTurnError`，文案引导 GUI 或改 force。  
7. Pi `FOUNDRY_TOOL` 桥与 Hermes/Codex one-shot **不变**。

## 非目标

- Hermes ACP、Codex app-server  
- 一次上三家 mid-turn  
- CLI TTY 问答式审批  
- 永久落盘「一律允许」/ 设置页全局永远放权  
- 用假安全方式在非 force 下继续 one-shot capture  
- 重写全部聊天为通用流式多执行器协议（仅 Cursor 非 force 分支）  
- 改变模型列表 / Provider 解析  

## 当前架构约束

| 证据 | 含义 |
|------|------|
| `cli/agent_turn.py` `run_cursor_turn` + `capture_output` | 不能挂 mid-turn；需并行路径 |
| `gui/electron/tool_permission_bridge.mjs` + Pi 卡 | 可复用 UX/超时模式；ACP 传输改为 stdio JSON-RPC |
| `permission_mode` 已在 executors/instances | 作为 ACP vs one-shot 开关，无需新配置键（v1） |
| Spike 硬约束 | ACP ≠ exec JSONL 观察流 |

## 方案选择

| 决策 | 选择 |
|------|------|
| 试点执行器 | Cursor only |
| 触发 | `permission_mode ≠ force` |
| 进程粒度 | 每同事实例常驻 |
| 入口 | 仅 GUI；CLI 非 force 拒跑 |
| 卡片 | 复用 Pi 四键；always→本会话（非永久） |

## 被排除方案

- 凡 Cursor 一律 ACP  
- 每消息冷启动 ACP  
- 全局单例 ACP  
- CLI 静默当 force  
- 永久 always 落盘  

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| force | one-shot，与今日一致 |
| GUI + auto_review/plan/ask | ACP + 卡 |
| CLI + 非 force | 报错，不挂起 |
| ACP 进程崩溃 | 本回合失败提示；下次可重启；不清用户 config |
| 审批超时 | deny；不崩 Electron |
| 用户切 force | 停 ACP；下轮 one-shot |
| 删除同事 | 停该实例 ACP |
| `agent acp` 不可用 | 明确错误（安装/登录），不回退假 force |

## 工程代价

- Electron：ACP 会话管理器（spawn `agent acp`、JSON-RPC、按 instance 路由 permission）  
- 渲染：扩展/复用 Pi 权限卡（标执行器来源 Cursor）  
- CLI：Cursor 分支分流；CLI 非 force 拒跑；可能薄封装供 Electron 调或 Electron 直连 agent  
- 单测：模式分流、CLI 拒跑；ACP 协议可用 mock stdio  
- 文档：`GUI-CONFIG.md` — 非 force = ACP 审批  

**预估**：中大型（会话模型变更）；建议 plan 拆多层、可单会话先做「可跑通一条 permission 卡」竖切。

## 显式假设

1. 本机 `agent`/`cursor-agent` 支持 `acp` 子命令且 permission 方法稳定到可试点程度（实现期以本机 `--help`/探测为准；若方法名差异，plan 锁定适配层）。  
2. v1 不要求新 config 键；用现有 `permission_mode`。  
3. 「本会话」= 该同事实例 ACP 进程生命周期 + Foundry sessionAllow 缓存，进程死后需重新批准。  

## 领域语言

| 术语 | 含义 |
|------|------|
| ACP 路径 | Cursor 非 force 的常驻协议回合 |
| one-shot 路径 | 现 `run_cursor_turn` |
| 本会话允许 | 进程内 + Foundry 缓存，非永久落盘 |
| 生效 permission_mode | 实例 → executors.cursor → `force` |

## 功能需求

1. GUI 发 Cursor 消息时按生效 mode 分流。  
2. ACP permission 请求弹出与 Pi 同结构的卡（文案可含工具/路径摘要）。  
3. 用户决定后 ACP 继续或拒绝。  
4. 流式/最终助手文本仍写入该同事聊天会话（具体 IPC 形状由 plan 定，验收：用户能看到回复与卡）。  
5. force / CLI 行为符合边界表。  

## 非功能需求

- 空闲超时可配置或沿用 Pi 级默认（约 5min 审批超时；进程空闲可更长，plan 定）。  
- 不泄漏 Bearer/桥 token 到日志。  
- Pi 回归：既有 tool permission 测绿。  

## 安全关注点

- 禁止非 force one-shot 假安全。  
- 禁止永久 always 落盘。  
- ACP stdio 仅本机；鉴权/配对若官方有要求则遵循。  
- session/turn allow 集合按 instance 隔离，禁止跨同事串放权。  

## 成功标准

1. GUI：Cursor + `auto_review`（或 plan/ask）发消息 → 需要权限时出卡 → 允许一次后继续出回复。  
2. GUI：选本会话允许后，同实例后续同类请求不再弹（进程存活期内）。  
3. GUI：`force` 无卡，行为同今日。  
4. CLI：非 force Cursor `agent turn` 退出非 0 且文案含 GUI/force。  
5. 关窗/删同事后无残留 `agent acp` 孤儿（或有清理钩子可测）。  
6. Pi 权限单测仍绿。  

## PR Review 关注点

- 是否在非 force 下误走 capture_output  
- always 是否写了 config  
- 跨 instance 放权串台  
- Hermes/Codex 是否被误改  

## 开放问题

（无阻塞。非阻塞：ACP 具体 JSON-RPC 方法名以本机探测为准，属 plan/code 适配；Hermes ACP 二期 owner=后续。）

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | 做 Cursor ACP 试点 |
| 已确认 | 仅 `permission_mode ≠ force` 走 ACP |
| 已确认 | 每同事实例常驻进程 |
| 已确认 | 仅 GUI；CLI 非 force 拒跑 |
| 已确认 | 复用 Pi 四键；always→本会话非永久 |
| 已排除 | Hermes/Codex mid-turn；永久放权；假 force |

## Resume

- **下一步**：用户确认本 Spec（回「确认」）→ `/anvil:plan` 拆任务 DAG → `/anvil:code`。  
