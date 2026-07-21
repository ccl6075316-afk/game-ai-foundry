# 工程 Spec：设置 Agent 预设 + 雇人/对话配置（去掉角色页）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-21
- **Updated**：2026-07-21
- **Source Of Truth Until**：本 Spec 已确认；实现以 [`docs/anvil/plans/2026-07-21-settings-agent-hire-config-plan.md`](../plans/2026-07-21-settings-agent-hire-config-plan.md) 为准
- **Confirmed By**：user「没问题」（2026-07-21）；此前确认：方案 1、雇人深度 C、设置 Tab 含 Agent、对话改实例不回写 Agent 预设
- **Change Log**：相对 [`2026-07-21-per-role-provider.md`](2026-07-21-per-role-provider.md)：配置入口从「设置→角色」迁到「设置→Agent 工具预设 + 雇人弹窗 + 对话内配置」；去掉角色/工种配置页；增加按执行器（Pi/Hermes/Codex/Cursor）的全局预设并可被雇人/对话沿用；plan 已确认
- **Requirements Source**：用户 Grill（梳理配置 → 去掉设置里角色配置 → 对话内配置 → 雇人先弹窗 → 深度 C → 增设 Agent 页沿用预设 → 对话不回写预设）
- **Background Inputs**：[`2026-07-21-per-role-provider.md`](2026-07-21-per-role-provider.md)（已落地：`agents.instances`、解析链、Codex sync、策划/IT 快选）；[`docs/GUI-CONFIG.md`](../../GUI-CONFIG.md)；当前 `SettingsPanel` 角色页过载
- **Compounded Knowledge**：not yet compounded
- **Supersedes (UX only)**：per-role-provider Spec 中「设置→角色按实例编辑」的 UI 要求；**保留**其 config 权威 `agents.instances`、Key 仅 `provider_accounts`、解析与 Codex/Cursor 边界

## 背景输入

- 设置「角色」页同时混有：同事实例选择器、项目经理/程序员工种默认、执行器、Provider、Codex 第三方；与 Provider 页、聊天快选、环境执行器安装互相打架，用户找不到「Codex 第三方」等入口。
- 已落地：`agents.instances`、实例级鉴权、策划/IT 聊天一行快选、程序员工种默认上的第三方勾选（仍难发现）。
- 用户目标：设置变少、好懂；**钥匙**与**工具预设**分开；**人**的配置放在雇人与对话。

## 工程理解

配置拆成四层，禁止再出现「角色配置页」：

1. **Provider（账号库）**：各厂商 API Key / 生图 / 生视频。  
2. **Agent（工具预设）**：Pi / Hermes / Codex / Cursor 各自的默认连法（用哪家账号、模型、Codex 是否第三方）。  
3. **同事实例**：雇人时写入、对话里可改；落盘 `agents.instances.<id>`；**默认沿用**对应执行器的 Agent 预设。  
4. **环境**：只安装/登录 CLI，不配业务字段。

对话内修改只更新该实例，**不回写** Agent 全局预设。

## 目标

1. 设置 Tab 改为：**Provider | Agent | 本机**；**删除「角色」页**（含同事实例编辑器与「工种默认」卡片）。
2. **Agent 页**按工具配置预设（见下表）；保存写入 config；Codex 勾选第三方时保存触发 `sync_api`（与现行为一致，数据源改为工具预设或当前触发的实例）。
3. **雇人**：创建同事前弹出配置框；必填规则按工种 C（见下）；表单预填 Agent 预设；确认后创建花名册实例并写入 `agents.instances`。
4. **对话**：每个同事可打开配置（策划/IT 沿用/升级现有快选；PM/程序员含执行器+Provider+模型+Codex 第三方）；变更立即持久化到该实例。
5. 旧同事缺必填项：不强制重雇；进对话黄条「去配置」打开同一表单。
6. Key **永不**出现在雇人/对话表单；仅选账号库 id；未填 Key 黄条指向 Provider 页。

## 非目标

- 不把生图/视频岗位配进 Agent 页或雇人弹窗。
- Cursor v1 仍无第三方 Key 同步。
- 对话「另存为 Agent 默认」按钮本轮不做。
- 不解决 Electron Node vs Pi 运行时另轨问题。
- 不删除 CLI 侧 `agents.brief` / `orchestrator` / `godot-developer` 等工种块的 skill/executor 兼容字段（可只读迁移）；**GUI 不再以「角色」编辑它们的业务 Provider**。

## 术语

| 术语 | 含义 |
|------|------|
| Provider / 账号库 | `provider_accounts` + 生图/视频账号 |
| Agent 预设 | 按执行器工具的全局默认连法 |
| 同事实例 | 花名册一人；配置在 `agents.instances` |
| 执行器 | `pi` \| `hermes` \| `codex` \| `cursor` |
| 沿用 | 雇人/新表单打开时预填 Agent 预设；用户可改后再写入实例 |

## 方案选择

**选定：设置 Agent 工具预设 + 雇人弹窗（深度 C）+ 对话内实例配置；去掉设置角色页。**

### Config 契约（增量）

新增（或等价命名）`agents.executors`：

```json
{
  "agents": {
    "executors": {
      "pi": { "provider": "openrouter", "model": "" },
      "hermes": { "provider": "deepseek" },
      "codex": {
        "use_third_party": false,
        "provider": "openrouter",
        "model": ""
      },
      "cursor": {}
    },
    "instances": {
      "<instanceId>": {
        "role_kind": "programmer",
        "executor": "codex",
        "provider": "openrouter",
        "model": "",
        "use_third_party": true
      }
    }
  }
}
```

- **权威运行时**：仍以 `agents.instances[id]` 为准（有则覆盖）。  
- **解析链（修订）**：实例字段 → `agents.executors[<executor>]` → 生文/host 账号回退。  
  - 兼容：若无 `executors`，可读旧工种块（`brief`/`it`→pi，`orchestrator`→hermes 的 provider，`godot-developer`→codex）再回退 host。  
- Key 只在 `provider_accounts`（及既有 host 兼容）。

### 设置 · Agent 页字段

| 工具 | 字段 |
|------|------|
| Pi | 默认 Provider、模型 |
| Hermes | 默认 Provider（保存后可提示去环境同步） |
| Codex | 用第三方开关；为 true 时 Provider + 模型；为 false 时提示订阅登录 |
| Cursor | 只读说明：本机登录/订阅 |

### 雇人弹窗必填（深度 C）

| 工种 `role_kind` | 必填 | 可选 |
|------------------|------|------|
| `brief` / `it` | Provider（执行器固定 Pi） | 模型 |
| `product_host` / `programmer` | 执行器 | Provider、模型、Codex 第三方 |

预填：按将选/默认执行器读取 `agents.executors.*`。

### 对话配置

- 全工种可编辑本实例配置（字段与雇人一致，执行器受工种允许集约束：brief/it 锁 Pi）。  
- 保存：只 upsert `agents.instances[id]`；**不**修改 `agents.executors`。  
- Codex 且 `use_third_party=true`：保存时 `sync_api`（带 `instanceId`）。

## 被排除方案

- 设置保留「角色」页仅改文案（用户明确去掉）。  
- 雇人最少项 B（用户选 C）。  
- 对话改配置回写 Agent 预设（用户明确不要）。  
- 设置三栏留空角色引导 B（已收敛为 Provider \| Agent \| 本机）。

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| Agent 预设未配、雇人未改 | 用 executors 缺省 → host/生文回退；不崩溃 |
| Provider 无 Key | 可选中但警告；回合失败文案指向 Provider |
| Codex 第三方同步失败 | 实例配置可保存；明确报同步失败 |
| 删除同事 | 清理 `agents.instances[id]`（保持既有要求） |
| 旧 config 无 `executors` | 兼容读取工种块；首次打开 Agent 页可展示推断值，保存后写出 `executors` |
| 设置里找「角色」 | 无此 Tab；文档/空态不提供第三套入口 |

## 工程代价

- **GUI**：Settings 去角色、加 Agent；雇人 modal；对话配置（扩展快选至 PM/程序员）；roster 雇佣流改异步确认。  
- **CLI**：解析链增加 `executors` 层；迁移读旧字段；example config / TOOLS / GUI-CONFIG 更新。  
- **测试**：解析兼容；GUI 关键测或最小单测（serialize executors）；雇人必填逻辑单测（可抽纯函数）。  
- **文档**：GUI-CONFIG、HOST-CHAT、ROADMAP 短更。

预估：跨 gui 为主 + cli 解析/文档；属 Full Spec → `/anvil:plan`。

## 显式假设

1. `agents.executors` 为工具预设权威；工种块 skill/默认 executor 类型仍可用于「该岗位允许哪些执行器」。  
2. 花名册显示名/雇佣仍在 GUI；LLM 相关只进 config instances + executors。  
3. 环境面板职责不变。  
4. 本机 Tab 仍为 Godot 等，不与 Agent 合并。

## 验收标准

1. 设置无「角色」Tab；有 Provider / Agent / 本机。  
2. Agent 页可保存 Pi/Hermes/Codex(/Cursor 说明) 预设到 `agents.executors`。  
3. 雇策划未选 Provider → 不能确认；雇程序员未选执行器 → 不能确认。  
4. 雇人预填来自 Agent 预设；确认后 `instances` 有对应 id。  
5. 对话改模型只变该实例；再开 Agent 页预设不变。  
6. 旧无 `executors` 的 config：对话/回合仍可用（兼容链）；不因缺字段崩溃。  
7. Codex 第三方：勾选并保存后仍触发同步（实例或预设路径之一，行为可测）。  
8. Key 不出现在雇人/对话表单。

## 安全

- Key 不进 `executors` / `instances`。  
- Codex `.env` 写入仍须用户显式保存/同步触发。  
- 日志继续用 `has_api_key`，禁止 Key 原文。

## Resume

- **下一步**：`/anvil:plan` 拆 GUI/CLI 任务 DAG。  
- **Deferred**：对话「存为 Agent 默认」；Cursor 第三方；Node/Pi 运行时。

## 决策账本（摘要）

| 状态 | 决策 |
|------|------|
| 已确认 | 去掉设置角色配置；增设 Agent 工具预设；雇人弹窗深度 C；对话可配；沿用预设；对话不回写预设；Tab = Provider \| Agent \| 本机 |
| 已排除 | 角色页留空引导；雇人最少 B；对话回写全局 |
| 默认写入 Spec | config 键名 `agents.executors`；解析链 instance → executors → host |
