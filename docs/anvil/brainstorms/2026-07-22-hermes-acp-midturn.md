# 工程 Spec：Hermes ACP mid-turn 审批

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：code
- **Created**：2026-07-22
- **Updated**：2026-07-22（code 已落地；待手测）
- **Confirmed By**：user「确认」（2026-07-22）
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan` artifact [`docs/anvil/plans/2026-07-22-hermes-acp-midturn-plan.md`](../plans/2026-07-22-hermes-acp-midturn-plan.md) once that plan is user-confirmed for `/anvil:code`
- **Requirements Source**：用户「按顺序来」→ Hermes ACP 二期；Grill Q1–Q7（A/A/A/A/A/A/B）；账本默认非目标与生命周期经用户「确认」
- **Background Inputs**：[`docs/anvil/brainstorms/2026-07-22-cursor-acp-midturn.md`](2026-07-22-cursor-acp-midturn.md)；[`docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md`](../../superpowers/specs/2026-07-22-executor-permission-b2-spike.md)；B v2 `yolo` 旋钮；`GUI-CONFIG.md`「未接 Hermes ACP」文案
- **Compounded Knowledge**：[`docs/solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md`](../../solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md)（JSON-RPC 先 `method` 后响应；客户端 id 命名空间）

## 背景输入

- Foundry 对 Hermes：`yolo=true` 仍 one-shot `hermes chat … --yolo`；`yolo=false` 时 **GUI** 走常驻 `hermes acp --accept-hooks` + 批准卡；**CLI** `yolo=false` 仍拒跑并引导 GUI 或开 YOLO。
- Spike / 本机：`hermes acp` 存在（stdio ACP；可选 `--accept-hooks`）。
- Cursor 试点已落地：非 force → 常驻 ACP + Pi 同款批准卡；CLI 非 force 拒跑；「本会话」不落盘。
- Codex app-server、永久 always 仍后置。

## 工程理解

为 **Hermes** 增加并行路径：当生效 `yolo=false` 时，由 Electron 按**同事实例**维护常驻 `hermes acp`（带 `--accept-hooks`）；工具侧 `session/request_permission`（及等价）挂起 → GUI 内联卡 → 回写决定 → 继续。  
`yolo=true` 保持现有 one-shot `--yolo`。  
CLI 无卡片宿主：`yolo=false` **继续拒跑**，文案改为引导 GUI 或开回 YOLO。

硬约束：禁止「去掉 `--yolo` 却仍 `capture_output` 阻塞等待」的假安全；禁止 ACP 失败时静默改回 YOLO。

## 目标

1. **触发条件**：解析后的 Hermes `yolo`（实例 → 全局 → 默认 `true`）为 `false`，且请求来自 **GUI** `agent-turn`（或等价聊天 IPC）。  
2. **生命周期**：每同事实例最多一个 `hermes acp` 子进程；首次非 YOLO 回合拉起；后续消息复用；切回 `yolo=true` / 卸载同事 / 关窗 / 空闲超时 → 停止。  
3. **审批 UI**：复用 Pi/Cursor 卡片：`允许一次` | `本回合允许` | `本会话允许` | `拒绝`。  
4. **语义映射**：与 Cursor 试点同构（一次 / 本回合 / 本会话仅进程内存活 + Foundry 缓存 / 拒绝·超时 deny）；**不**永久落盘。  
5. **YOLO 路径**：仍 `run_hermes_turn` one-shot + `--yolo`，不启 ACP。  
6. **CLI**：`agent turn` 且 Hermes 且 `yolo=false` → `AgentTurnError`（引导 GUI 或改 YOLO）。  
7. **启动参数**：`hermes acp --accept-hooks`（hooks 静默；**工具** permission 仍走 GUI 卡）。  
8. Cursor ACP、Pi 桥、Codex one-shot **行为不变**（除文档交叉引用）。

## 非目标

- Codex app-server mid-turn  
- 一次上三家 mid-turn  
- CLI TTY 问答式审批  
- 永久落盘「一律允许」  
- 新 config 键（v1 用现有 `yolo`；不新增 hooks 旋钮）  
- 本期抽 Cursor/Hermes 共用 ACP 基类（平行模块即可）  
- 改变 Hermes Provider/模型列表解析（除非 ACP 路径为跑通所必需的最小接线，由 plan 限定）  
- 用假安全方式在 `yolo=false` 下继续 one-shot capture 或静默 YOLO  

## 当前架构约束

| 证据 | 含义 |
|------|------|
| `cli/agent_turn.py` `run_hermes_turn` + `resolve_hermes_yolo` | `yolo=false` 已拒跑；需 GUI 并行 ACP 路径后改文案并放行 GUI |
| `gui/electron/cursor_acp_*.mjs` + 批准卡 IPC | UX/路由可复用模式；Hermes 平行实现，勿硬塞进 cursor_* |
| `agents.executors.hermes.yolo` / 实例覆盖 | 作为 ACP vs one-shot 开关，无需新键 |
| 本机 `hermes acp --help` | 入口确认；`--accept-hooks` 可用 |
| Compounded：JSON-RPC id 撞车 | Hermes 宿主必须先 `method` 再匹配 pending；出站 id 用独立命名空间 |

## 方案选择

| 决策 | 选择 |
|------|------|
| 试点执行器 | Hermes（接 Cursor 之后） |
| 触发 | 生效 `yolo=false` |
| 进程粒度 | 每同事实例常驻 |
| 入口 | 仅 GUI；CLI `yolo=false` 拒跑 |
| 卡片 | 对齐 Cursor；本会话非永久 |
| ACP 失败 | 硬失败，不静默 YOLO |
| 代码组织 | `hermes_acp_*` 平行模块 |
| hooks | 始终 `--accept-hooks` |

## 被排除方案

- 新键独立开 ACP、与 YOLO 解耦（本期）  
- 全局单例 / 每消息冷启动 ACP  
- CLI 静默当 YOLO 或 TTY 审批  
- 永久 always 落盘  
- 抽大基类后再实现 Hermes  
- ACP 不可用自动回退 `--yolo`  

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| `yolo=true` | one-shot `--yolo`，与今日一致 |
| GUI + `yolo=false` | ACP + 卡（工具调用时） |
| CLI + `yolo=false` | 报错，不挂起 |
| ACP 进程崩溃 / 握手失败 | 本回合失败提示；不改用户 `yolo`；下次可重启 |
| 审批超时 | deny；不崩 Electron |
| 用户切回 `yolo=true` | 停该实例 ACP；下轮 one-shot |
| 删除同事 / 关窗 | 停该实例 ACP |
| `hermes` / `hermes acp` 不可用 | 明确错误；不回退 YOLO |
| 纯闲聊无工具 | 可不弹卡（与 Cursor 一致） |
| shell hooks | 因 `--accept-hooks` 不弹卡；**不**视为工具 permission 替代 |

## 工程代价

- Electron：`hermes_acp_adapter` / `hermes_acp_session`（spawn `hermes acp --accept-hooks`、JSON-RPC、按 instance 路由 permission）  
- `main.mjs`：Hermes 分流（对齐 Cursor agent-turn 路由）  
- 渲染：复用批准卡（标执行器来源 Hermes）  
- CLI：更新 `yolo=false` 拒跑文案（去掉「未接 ACP」过时表述；区分 GUI 已接 / CLI 仍拒）  
- 文档：`GUI-CONFIG.md` — `yolo=false` = GUI ACP 审批  
- 单测：分流、CLI 拒跑、JSON-RPC id 撞车回归（照搬 Cursor 模式）、mock stdio permission  
- **预估**：中型（可对照 Cursor 竖切）；plan 以「一条 permission 卡跑通」为第一竖切  

## 显式假设

1. 本机 `hermes acp` 的 permission / session 方法稳定到可试点；具体方法名以 plan/code 探测为准。  
2. v1 不新增 config 键；用现有 `yolo`。  
3. 「本会话」= 该同事实例 ACP 进程生命周期 + Foundry sessionAllow，进程死后需重新批准。  
4. `--accept-hooks` 仅覆盖 Hermes hooks 面，不替代工具 `request_permission`。  
5. Provider/模型经 ACP 的接线若与 `chat` 不同，plan 做最小必要适配，不借机重做设置页。  

## 领域语言

| 术语 | 含义 |
|------|------|
| ACP 路径 | Hermes `yolo=false` 的常驻协议回合 |
| one-shot 路径 | 现 `run_hermes_turn` + `--yolo` |
| 本会话允许 | 进程内 + Foundry 缓存，非永久落盘 |
| 生效 yolo | 实例 → `executors.hermes` → 默认 `true` |
| accept-hooks | 启动 ACP 时静默批准 shell hooks |

## 功能需求

1. GUI 发 Hermes 消息时按生效 `yolo` 分流。  
2. ACP 工具 permission 弹出与 Pi/Cursor 同结构的卡。  
3. 用户决定后 ACP 继续或拒绝。  
4. 助手文本写入该同事聊天会话（IPC 形状由 plan 定）。  
5. `yolo=true` / CLI 行为符合边界表。  
6. 文档与拒跑文案反映「GUI 已接 ACP」。  

## 非功能需求

- 审批超时沿用 Pi/Cursor 级默认（约 5min；plan 可对齐）。  
- 不泄漏 token 到日志。  
- Cursor ACP 与 Pi 权限相关测绿；新增 Hermes mock 测。  
- JSON-RPC 入站处理遵守 compounded 防撞车模式。  

## 安全关注点

- 禁止 `yolo=false` one-shot 假安全与静默 YOLO 回退。  
- 禁止永久 always 落盘。  
- `--accept-hooks` 扩大 hooks 放权面：文档必须写明；工具面仍须 GUI。  
- session/turn allow 按 instance 隔离。  
- ACP stdio 仅本机。  

## 成功标准

1. GUI：Hermes + `yolo=false` → 需工具权限时出卡 → 允许一次后继续出回复。  
2. GUI：本会话允许后，同实例后续同类请求进程内存活期内不再弹。  
3. GUI：`yolo=true` 无卡，行为同今日。  
4. CLI：`yolo=false` 的 Hermes `agent turn` 非 0，文案含 GUI/YOLO。  
5. ACP 不可用时失败且不改 `yolo`、不跑 `--yolo`。  
6. 关窗/删同事无残留 `hermes acp` 孤儿（或有可测清理）。  
7. Cursor/Pi 相关回归绿。  

## PR Review 关注点

- 是否在 `yolo=false` 下误走 capture one-shot  
- 失败路径是否静默 YOLO  
- always 是否写 config  
- 跨 instance 放权串台  
- 是否误改 Cursor ACP / 是否用 cursor_* 硬塞 Hermes  
- `--accept-hooks` 是否被误当成「全部工具自动过」  

## 开放问题

（无阻塞。）

非阻塞（plan/code）：

| 项 | owner | 触发 |
|----|--------|------|
| Hermes ACP 具体 JSON-RPC 方法名 / session 模型与 Cursor 差异 | implementer | 本机探针 |
| 助手消息持久化是否复用 `agent record-turn` 或 Hermes session id | implementer | 对照 Cursor 路径 |
| 空闲超时具体数值 | implementer | 对齐 Cursor 即可 |

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | `yolo=false` → Hermes ACP |
| 已确认 | 每同事实例常驻 |
| 已确认 | 仅 GUI；CLI 拒跑 |
| 已确认 | 卡与本会话语义对齐 Cursor |
| 已确认 | ACP 失败硬失败 |
| 已确认 | 平行 `hermes_acp_*` |
| 已确认 | 始终 `--accept-hooks` |
| 已确认 | 非目标：Codex、永久 always、三家一次、CLI TTY、本期大抽基类 |
| 已确认 | 切 YOLO/卸同事/关窗 → 停该实例 ACP |

## Resume

- **Code Status**：T1–T6 已落地（`hermes_acp_adapter` / `hermes_acp_session`、`main.mjs` GUI 分流、CLI 拒跑文案、`GUI-CONFIG.md`）。  
- **下一步**：GUI 手测（Hermes + `yolo=false` → 工具调用出卡 → 允许后继续回复）；可选 `/anvil:review`。  
- **Compound 文档**：`docs/solutions/` 已有 ACP id 撞车条目；手测通过后若有 Hermes 特有差异可再补。  
