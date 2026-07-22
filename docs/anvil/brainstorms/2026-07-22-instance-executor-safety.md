# 工程 Spec：同事实例覆盖执行器安全旋钮

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-22
- **Updated**：2026-07-22（用户「确认」）
- **Confirmed By**：user「确认」（2026-07-22）
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan` artifact [`docs/anvil/plans/2026-07-22-instance-executor-safety-plan.md`](../plans/2026-07-22-instance-executor-safety-plan.md) once that plan is user-confirmed for `/anvil:code`
- **Requirements Source**：用户选产品选项「3」实例级覆盖；Grill：入口方案 2、换执行器方案 1、继承 UX 方案 1、松紧无钳制方案 1；用户确认 Spec
- **Background Inputs**：[`2026-07-22-executor-safety-config.md`](2026-07-22-executor-safety-config.md)（B v2 已落地全局旋钮；Deferred 含 instance 覆盖）；[`2026-07-21-settings-agent-hire-config.md`](2026-07-21-settings-agent-hire-config.md)（雇人 + 对话配置入口）；聊天确认「3 = 开跑前按同事定规矩」
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：Spec 已确认；plan 已写出 → 用户确认 plan 或「开始实现」→ `/anvil:code`

## 背景输入

- B v2 已在 `agents.executors.{codex,cursor,hermes}` 提供 `sandbox` / `permission_mode` / `yolo`，由 `agent_turn` 组装 argv；GUI 在「设置 → Agent」。
- 同事实例配置在 `agents.instances.<id>`（执行器 / Provider / 模型等），经雇人弹窗与 `ColleagueConfigBar` 编辑；**当前安全旋钮不读实例**。
- 用户要：某个同事可以和全局 Agent 预设不同的安全档，仍不做 ACP mid-turn。

## 工程理解

在既有「实例覆盖工具预设」模型上，把 B v2 三个安全字段做成**可选实例覆盖**：

1. **全局**：`agents.executors.*`（设置 → Agent）不变。  
2. **实例**：`agents.instances.<id>` 可额外带同名字段；**缺省键 = 继承全局**。  
3. **生效**：`agent_turn` 按 **当前实例 executor** 只取对应键（Codex→sandbox，Cursor→permission_mode，Hermes→yolo）；非法值回退全局，再回退硬默认。  
4. **展示/编辑**：雇人弹窗 + 对话顶栏；Pi 同事不出现这些控件。

硬约束继承 B v2：Hermes `yolo=false`（全局或实例生效值）→ **拒绝开跑**，禁止假安全。

## 目标

1. CLI：`resolve_codex_sandbox` / `resolve_cursor_permission_mode` / `resolve_hermes_yolo`（或等价）支持 `instance_id`：  
   **实例显式合法值 → `agents.executors` → 硬默认**。  
2. `run_executor_turn` / 各 `run_*_turn` 在已有 `instance_id` 路径上使用上述解析结果。  
3. GUI 类型：`AgentInstanceRecord` 增加可选 `sandbox?` / `permission_mode?` / `yolo?`；load/save/serialize 保留「缺键 = 继承」。  
4. **雇人弹窗**（`HireColleagueModal`）：当所选执行器为 codex/cursor/hermes 时，显示对应旋钮；首项 **「继承全局」**；确认时仅写入非继承项。  
5. **对话顶栏**（`ColleagueConfigBar`）：同上；改旋钮立即持久化到该实例；选「继承全局」→ **删除**实例上对应键。  
6. 换执行器：盘上可残留其它执行器的安全键；**UI 与 resolve 只认当前 executor 相关键**（不自动清除历史键）。  
7. 实例可任意合法枚举（可比全局更松或更紧）；**不做**「不得松于全局」钳制。  
8. 文档：`docs/GUI-CONFIG.md` 短更一层「实例可覆盖安全旋钮」。

## 非目标

- ACP / app-server / mid-turn 审批卡（选项 4）  
- Pi `FOUNDRY_TOOL` 审批协议变更  
- 设置 → Agent 页按实例编辑（全局预设页保持工具级）  
- IT 工具箱强制写入实例安全字段（可不做；若 upsert 实例则遵循同一 omit 语义）  
- 对话「另存为 Agent 默认」把实例安全回写全局  
- 切换执行器时自动清理历史安全键  

## 当前架构约束

| 证据 | 含义 |
|------|------|
| `cli/agent_turn.py` `resolve_*` 只读 `_executor_preset` | 需扩展 instance 层 |
| `gui/src/settings/agentInstances.ts` `AgentInstanceRecord` | 现无安全字段 |
| `HireColleagueModal` + `ColleagueConfigBar` | 已有实例编辑入口，应复用 |
| B v2 Hermes yolo=false | 实例生效 false 时同样拒绝开跑 |

## 方案选择

- **入口**：雇人 + 对话顶栏（Grill 方案 2）  
- **换执行器**：只按当前 executor 应用/展示对应键（Grill 方案 1）  
- **继承**：下拉「继承全局」= 删键（Grill 方案 1）  
- **松紧**：允许实例任意合法值（Grill 方案 1）  
- **落盘形状**：实例根上扁平可选字段（与 `agents.executors.*` 同名），不另套 `safety` 对象  

## 被排除方案

- 仅对话或仅雇人可改  
- 切换执行器清键 / 全部重置为继承  
- 雇佣时快照拷贝全局（改全局不影响未覆盖实例的反面：本 Spec 要「缺键跟随全局」）  
- 实例不得松于全局的钳制  
- ACP  

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| 实例无安全键 | 用 `agents.executors` 对应值 |
| 实例键非法 / 空串 | 忽略，回退全局 → 硬默认 |
| 实例有 `sandbox` 但当前 executor=cursor | 忽略 sandbox；用 permission_mode 或继承 |
| 生效 yolo=false | `AgentTurnError`，不启 hermes |
| brief/it（pi） | 不展示、不写入安全键 |
| 旧配置无字段 | 行为与今日全局-only 一致 |

## 工程代价

- `cli/agent_turn.py` + `cli/test_agent_turn.py`（带 `instance_id` 的 resolve / argv / yolo 拒绝）  
- `gui/src/settings/agentInstances.ts`（类型与 load/save）  
- `HireColleagueModal` / `hireColleague` 表单  
- `ColleagueConfigBar` 控件  
- `docs/GUI-CONFIG.md`  
- 可选：example config 注释一行  

## 显式假设

1. `agent turn --instance-id` 已能加载该实例的 executor；安全解析挂同一路径。  
2. 「继承全局」在 UI 用哨兵值（如空串 / `__inherit__`）仅存于表单态，**落盘不写该哨兵**。  
3. 单用户本机信任模型：更松的实例覆盖可接受。  

## 领域语言

| 术语 | 含义 |
|------|------|
| Agent 预设 / 全局安全旋钮 | `agents.executors.<executor>` |
| 实例覆盖 | `agents.instances.<id>` 上显式存在的安全键 |
| 继承全局 | 实例缺省对应键；UI「继承全局」删除该键 |
| 当前执行器相关键 | codex→`sandbox`；cursor→`permission_mode`；hermes→`yolo` |

## 功能需求

1. 解析优先级：实例显式合法相关键 → 全局 executors → 硬默认。  
2. 雇人确认：仅把非继承安全字段写入新实例。  
3. 对话变更：立即 patch 实例；继承 = delete key。  
4. 仅 non-Pi 执行器显示对应一个控件（一次只显示与当前 executor 匹配的旋钮）。  
5. 文案：Hermes 关 YOLO 时说明未接 ACP 前会拒绝开跑（与设置页一致）。  

## 非功能需求

- 默认路径零行为变化（无实例键时 argv 与 B v2 相同）。  
- 单测覆盖：实例覆盖、继承、非法值、换 executor 不串键、yolo=false。  
- `npx tsc --noEmit` 绿。  

## 安全关注点

- 旋钮只影响本机 CLI argv，不引入新网络鉴权。  
- 允许实例比全局更危险（用户显式选择）；不在本版做策略引擎。  
- 禁止「去掉 --yolo/--force 却仍 capture_output 挂起」的假收紧。  

## 成功标准

1. 单测：实例 `sandbox=read-only` + 全局 `danger-full-access` → argv 含 `read-only`。  
2. 单测：实例无键 → 与仅全局配置一致。  
3. 单测：实例 `yolo=false` → 拒绝且不调 hermes。  
4. 单测：实例存 `sandbox` 但 executor=cursor → 使用 cursor 的 permission_mode/全局，不影响 sandbox 解析路径。  
5. GUI：雇人 + 顶栏可选继承；选继承后 config 中该键消失。  
6. Pi 同事界面无安全旋钮。  

## PR Review 关注点

- resolve 是否误用非当前 executor 的键  
- 继承是否误把哨兵写入 JSON  
- Hermes 假安全回归  
- 是否回写 `agents.executors`  

## 开放问题

（无阻塞项。非阻塞：IT `setup` 是否暴露实例安全 upsert — 本版不做，owner=后续产品。）

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | 做实例覆盖（产品选项 3） |
| 已确认 | 入口：雇人 + 对话顶栏 |
| 已确认 | 换执行器：只应用当前相关键，保留历史键 |
| 已确认 | UI「继承全局」= 删键 |
| 已确认 | 允许实例比全局更松 |
| 已排除 | ACP；钳制；快照拷贝；切换清键 |

## Resume

- **下一步**：用户确认本 Spec（回「确认」）→ `/anvil:plan` 拆任务 DAG → `/anvil:code`。  
