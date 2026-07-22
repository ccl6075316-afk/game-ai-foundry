# 工程 Spec：Codex app-server mid-turn 审批

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：code（实现完成）
- **Created**：2026-07-22
- **Updated**：2026-07-22（实现已落地，待手测）
- **Confirmed By**：user「ok」（2026-07-22）
- **Source Of Truth Until**：手测签收或 `/anvil:review` 通过后由 compound 取代；plan 见 [`docs/anvil/plans/2026-07-22-codex-app-server-midturn-plan.md`](../plans/2026-07-22-codex-app-server-midturn-plan.md)
- **Requirements Source**：用户选「下一步 → 1 Codex」；Grill Q1–Q7（全 A）；账本默认非目标与 execpolicy 永久修订处理经用户「ok」
- **Background Inputs**：[`docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md`](../../superpowers/specs/2026-07-22-executor-permission-b2-spike.md)；[`docs/anvil/brainstorms/2026-07-22-cursor-acp-midturn.md`](2026-07-22-cursor-acp-midturn.md)；[`docs/anvil/brainstorms/2026-07-22-hermes-acp-midturn.md`](2026-07-22-hermes-acp-midturn.md)；B v2 `sandbox` 旋钮；本机 `codex` 0.145 `app-server` + `generate-json-schema`
- **Compounded Knowledge**：[`docs/solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md`](../../solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md)；[`docs/solutions/failures/2026-07-22-hermes-acp-permission-bridge.md`](../../solutions/failures/2026-07-22-hermes-acp-permission-bridge.md)；[`docs/solutions/patterns/critical-patterns.md`](../../solutions/patterns/critical-patterns.md)

## 背景输入

- Foundry 对 Codex 今日走 one-shot `codex exec` + `--sandbox`（默认 `workspace-write`）；**无** mid-turn GUI 批准。
- Spike：`codex exec` JSONL 为观察流，不是审批总线；机读审批走 **`codex app-server`**（experimental）。
- Cursor/Hermes mid-turn 已落地：GUI 常驻协议 + Pi 同款卡；CLI 在非一键安全模式拒跑；本会话不落盘；失败禁止静默回退。
- 本机：`codex app-server` 支持 `--listen stdio://`；schema 含多种 `requestApproval`（command / fileChange / exec / patch / permissions 等）；决定枚举含 `accept` / `acceptForSession` 等。

## 工程理解

为 **Codex** 增加并行路径：当生效 `sandbox ≠ danger-full-access` 时，由 Electron 按**同事实例**维护常驻 `codex app-server`（stdio）；审批类 ServerRequest 挂起 → GUI 内联卡 → 回写决定 → 继续。  
`danger-full-access` 保持现有 one-shot `codex exec`。  
CLI 无卡片宿主：非 `danger-full-access` **拒跑**，引导 GUI 或改 sandbox。

硬约束：禁止「收紧 sandbox 却仍 `capture_output` 假安全」；禁止 app-server 失败时静默改回 exec。

**默认行为跳变（已确认）**：默认 `workspace-write` → **默认 GUI Codex 走 app-server**（与 Cursor 默认 force、Hermes 默认 yolo 不对称，属有意「默认更安全」）。

## 目标

1. **触发条件**：解析后的 Codex `sandbox`（实例 → 全局 → 默认 `workspace-write`）≠ `danger-full-access`，且请求来自 **GUI** `agent-turn`。  
2. **生命周期**：每同事实例最多一个 stdio `codex app-server` 子进程；首次非 danger 回合拉起；后续复用；切到 `danger-full-access` / 卸同事 / 关窗 / 空闲超时 → 停止。  
3. **审批 UI**：复用 Pi/Cursor/Hermes 四键。  
4. **语义映射**：  
   - 一次 → `accept`（或协议等价单次）  
   - 本回合 → Foundry turn 级缓存  
   - 本会话 → Foundry session 缓存 + 协议 `acceptForSession`（或等价）**仅进程内存活**，不写 config / 不采用永久 execpolicy amendment 作为「本会话」  
   - 拒绝 / 超时 → decline / 等价 deny  
5. **danger-full-access 路径**：仍 `run_codex_turn` one-shot exec，不启 app-server。  
6. **CLI**：`agent turn` 且 Codex 且 sandbox≠danger-full-access → `AgentTurnError`。  
7. **多种审批请求**：command / file / patch / permissions 等统一进同一套卡（文案可区分类型）；具体方法名以 schema/探针为准。  
8. Cursor ACP、Hermes ACP、Pi 桥 **行为不变**（除文档交叉引用与共用 stop IPC 已有能力）。

## 非目标

- 本机共享 `app-server daemon` / remote-control  
- 永久落盘「一律允许」或 v1 采用 `acceptWithExecpolicyAmendment` 永久修订（若协议强制出现：映射为 once 或明确拒绝该选项，plan 锁定）  
- 抽 Cursor/Hermes/Codex 共用 mid-turn 基类  
- CLI TTY 审批  
- 新 config 键（v1 用现有 `sandbox`）  
- 改变 Codex 模型列表 / 第三方 Provider 解析（除非 app-server 最小接线需要）  
- 假安全：静默回退 exec  

## 当前架构约束

| 证据 | 含义 |
|------|------|
| `cli/agent_turn.py` `run_codex_turn` + `resolve_codex_sandbox` | 今日仅 exec；需 GUI 并行 app-server；CLI 非 danger 拒跑 |
| `gui/electron/*_acp_*` + 批准卡 + `agent-acp-stop-instance` | UX/生命周期可对照；Codex 平行模块，勿硬塞 acp 命名 |
| `agents.executors.codex.sandbox` / 实例覆盖 | 作为开关，无需新键 |
| 本机 `codex app-server` + schema | 入口与审批类型可锁定 |
| Compounded：JSON-RPC / 上游桥 | stdio 双向请求须 method-first；上游缺陷要用探针验证 |

## 方案选择

| 决策 | 选择 |
|------|------|
| 触发 | `sandbox ≠ danger-full-access` |
| 默认 sandbox | 保持 `workspace-write`（→ 默认 GUI app-server） |
| 进程 | 每同事实例 stdio，不用 daemon |
| 入口 | 仅 GUI；CLI 拒跑 |
| 卡片 | 对齐四键；本会话非永久 |
| 失败 | 硬失败，不静默 exec |
| 代码 | `codex_app_server_*` 平行模块 |

## 被排除方案

- 新键独立开 app-server  
- GUI 一律 app-server 且忽略 sandbox  
- 改默认 sandbox 为 danger-full-access 以回避跳变  
- 仅 `read-only` 走 app-server（回改 Q1）  
- 共享 daemon  
- CLI 继续 exec 造成同配置语义分叉  

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| `danger-full-access` | one-shot exec，与今日一致 |
| GUI + workspace-write / read-only | app-server + 卡 |
| CLI + 非 danger | 报错，不挂起 |
| app-server 崩溃 / 握手失败 | 本回合失败；不改用户 sandbox；不回退 exec |
| 审批超时 | deny；不崩 Electron |
| 用户切到 danger-full-access | 停该实例 app-server；下轮 exec |
| 删除同事 / 关窗 | 停该实例 app-server（复用 stop IPC） |
| `codex` / app-server 不可用 | 明确错误 |
| 永久 execpolicy amendment 选项 | v1 不作为「本会话」；不落盘 |

## 工程代价

- Electron：`codex_app_server_adapter` / `codex_app_server_session`（spawn stdio app-server、JSON-RPC/协议帧、按 instance 路由多种 approval）  
- `main.mjs`：Codex 分流 + record-turn；切 danger 时 stop  
- CLI：非 danger 拒跑文案  
- 文档：`GUI-CONFIG.md` — 默认 sandbox = GUI 审批路径  
- 单测：分流、CLI 拒跑、协议 mock、撞车/入站顺序（若适用）  
- **预估**：中大型（experimental 协议；多种 approval）；plan 以「一条 command approval 卡跑通」为第一竖切  

## 显式假设

1. 本机 Codex app-server 审批方法在试点期足够稳定；细节以 `generate-json-schema` + 探针为准。  
2. v1 不新增 config 键；用现有 `sandbox`。  
3. 「本会话」= 该实例 app-server 进程生命周期 + Foundry 缓存。  
4. 默认 sandbox 跳变已获用户确认。  
5. Provider/模型经 app-server 的接线若与 exec 不同，plan 做最小必要适配。  

## 领域语言

| 术语 | 含义 |
|------|------|
| app-server 路径 | Codex `sandbox ≠ danger-full-access` 的常驻协议回合 |
| exec 路径 | 现 `run_codex_turn` one-shot |
| 本会话允许 | 进程内 + Foundry 缓存，非永久落盘 |
| 生效 sandbox | 实例 → `executors.codex` → 默认 `workspace-write` |

## 功能需求

1. GUI 发 Codex 消息时按生效 sandbox 分流。  
2. app-server 审批请求弹出与 Pi 同结构的卡（可标类型）。  
3. 用户决定后协议继续或拒绝。  
4. 助手文本写入该同事会话（IPC/持久化由 plan 定，优先对齐 `record-turn`）。  
5. danger / CLI 行为符合边界表。  
6. 文档反映默认 sandbox → GUI 审批。  

## 非功能需求

- 审批超时对齐 Pi/Cursor/Hermes（约 5min；plan 可对齐）。  
- 不泄漏 token 到日志。  
- Cursor/Hermes/Pi 相关测绿；新增 Codex mock 测。  
- stdio 入站处理遵守 compounded 防撞车/先 method 模式（若协议为 JSON-RPC）。  

## 安全关注点

- 禁止非 danger 下假安全 exec / 静默回退。  
- 禁止永久 always / execpolicy 落盘作为本会话。  
- session/turn allow 按 instance 隔离。  
- app-server stdio 仅本机；不用 daemon remote-control。  

## 成功标准

1. GUI：Codex + `workspace-write` → 需审批时出卡 → 允许一次后继续出回复。  
2. GUI：本会话允许后，同实例进程内存活期内同类请求不再弹（按协议缓存语义）。  
3. GUI：`danger-full-access` 无卡，行为同今日 exec。  
4. CLI：非 danger 的 Codex `agent turn` 非 0，文案含 GUI / danger-full-access。  
5. app-server 不可用时失败且不跑 exec。  
6. 关窗/删同事无残留 app-server 孤儿（或有可测清理）。  
7. Cursor/Hermes/Pi 回归绿。  

## PR Review 关注点

- 是否在非 danger 下误走 capture exec  
- 失败路径是否静默 exec  
- always / execpolicy 是否落盘  
- 是否误用共享 daemon  
- 是否硬塞进 `*_acp_*` 或破坏 Cursor/Hermes  

## 开放问题

（无阻塞。）

非阻塞（plan/code）：

| 项 | owner | 触发 |
|----|--------|------|
| 各 `requestApproval` 方法名与决策枚举完整表 | implementer | `generate-json-schema` + 探针 |
| `acceptWithExecpolicyAmendment` 出现时的精确映射（once vs 忽略） | implementer | 对照 Spec 非目标 |
| turn/start 会话模型与 record-turn | implementer | 对照 Cursor/Hermes |
| 传输帧格式（JSON-RPC NDJSON vs 其他） | implementer | 本机探针 |

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | `sandbox ≠ danger-full-access` → app-server |
| 已确认 | 每同事实例 stdio 常驻 |
| 已确认 | 仅 GUI；CLI 拒跑 |
| 已确认 | 卡与本会话对齐另两家 |
| 已确认 | 失败硬失败 |
| 已确认 | 平行 `codex_app_server_*` |
| 已确认 | 默认 workspace-write → 默认 GUI app-server |
| 已确认 | 非目标：daemon、永久放权、抽基类、假安全 |

## Resume

- **实现状态**：已落地（`codex_app_server_*`、GUI 分流、CLI 非 danger 拒跑、[`GUI-CONFIG.md`](../../GUI-CONFIG.md) T6）。
- **下一步**：手测 GUI Codex + 默认 `workspace-write` 审批路径；可选 `/anvil:review`。  
