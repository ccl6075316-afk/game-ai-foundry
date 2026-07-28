# 工程 Spec：设置全页壳 + ChatWise 式 Provider/Agent

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：executed
- **Created**：2026-07-28
- **Updated**：2026-07-28
- **Source Of Truth Until**：已落地；导航与布局以代码与 [`GUI-CONFIG.md`](../../GUI-CONFIG.md) 为准
- **Confirmed By**：user「确认」Spec/Plan；user「实现」
- **Requirements Source**：用户 Grill（全页设置；环境/指南并入；侧栏仅文档/看板/资产；Provider/Agent 主从）
- **Background Inputs**：[`2026-07-28-open-provider-accounts-model-catalog.md`](2026-07-28-open-provider-accounts-model-catalog.md)；ChatWise/Alma
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：已合入主线实现；见 RELEASE-NOTES-UNRELEASED
- **Supersedes (UX)**：设置/环境/指南作为侧栏的入口布局（配置契约仍见 [`2026-07-21-settings-agent-hire-config.md`](2026-07-21-settings-agent-hire-config.md)）

## 背景输入

- 开放账号 + 模型目录落地后，Provider 仍塞在约 440px 侧栏：Chips + 下拉 + 添加表单 + 生文/生图/批量三套，认知负担高。
- ChatWise / Alma：设置 = 服务商列表 → 单页详情（Key / Base / Fetch Models）；模型切换多在对话处。
- 用户要求：设置单独完整页面；环境、指南并入设置；现侧栏位置只留给开发期文档 / 看板 / 资产。

## 工程理解

配置壳与业务字段分离：

1. **设置全页**：独立于聊天主区的完整视图（非 `side-panel`），含 Tab：**Provider | Agent | 本机 | 环境 | 指南**。
2. **开发侧栏**：仅 **文档 | 看板 | 资产**（现有 `sidePanel` 能力保留）。
3. **Provider Tab**：ChatWise 主从——左账号列表、右详情；页内短选「生文用谁 / 生图用谁」；批量进高级。
4. **Agent Tab**：同风格主从——左 Pi / Hermes / Codex / Cursor，右该工具预设详情。
5. **本机 / 环境 / 指南**：迁入全页 Tab，内容以现有面板为准，放宽宽度，不做列表→详情（除非实现时几乎零成本复用壳）。

账号/模型 **config 契约**沿用已落地的开放 `provider_accounts` + `setup provider models`；本 Spec 以 **GUI 信息架构与导航** 为主，不改 CLI 协议除非全页需要新入口参数（一般不需要）。

## 目标

1. 顶栏「设置」打开**全页设置**（遮住或替换聊天工作区）；提供明确「返回」回到聊天。
2. 顶栏不再用侧栏打开环境、指南、设置；环境/指南仅作为设置内 Tab。
3. 侧栏开关仅保留文档、看板、资产（及与之相关的现有行为）。
4. Provider：左列表（内置 + 自建，`+` 添加）/ 右详情（label、base、key、拉模型、默认文模型、默认图模型、删除用户账号）；顶区或详情旁：**生文活跃账号**、**生图活跃账号**（可勾沿用生文）；**批量**折叠在「高级」。
5. Agent：左四工具 / 右现有预设字段（Provider 仅内置、模型 CatalogPicker、Codex 第三方与沙箱、Hermes YOLO、Cursor 权限等），去掉四块卡片纵向堆叠的重复感。
6. `/settings` 指令与环境页「打开设置」链到全页设置（可带初始 Tab）。

## 非目标

- 不重做雇人弹窗 / 对话顶栏的整体视觉（可继续用 CatalogPicker）。
- 不把模型选择「只」放到聊天顶栏而取消设置内默认模型（Foundry 仍需 host/image 默认）。
- 不改视频账号为开放多条目（仍视频小节；可在 Provider 高级区保留现视频小节）。
- 不改 `provider_accounts` / `agents.executors` 磁盘 schema（除非为 UI 状态增加无关紧要的 last-selected id，可选且非必须）。
- 不做移动端专项布局。

## 当前架构约束

- `App.tsx`：`sidePanel` 含 `settings | env | guide | docs | board | assets`；设置宽 `min(440px, 44vw)`。
- `SettingsPanel`：三 Tab providers/agents/local；Provider 仍复杂。
- `EnvPanel` / `GuidePanel`：独立侧栏组件。
- 账号开放与 `ModelCatalogPicker` / `providerModels` IPC 已可用。

## 方案选择

**选定：设置全页五 Tab；Provider 与 Agent 均为左列表右详情；开发侧栏仅文档/看板/资产；本机/环境/指南内容迁入全页。**

### 导航（Plan 默认可落地）

- 状态机：`appView: "chat" | "settings"`（名称可调整）。
- `appView === "settings"` 时主区渲染全页设置；同事侧栏可隐藏或保留极简，**以不抢宽度为准**（建议隐藏同事栏，设置自带顶栏：返回 + Tab）。
- 全页可用 `?tab=` 或 props 指定初始 Tab：`providers | agents | local | env | guide`。
- 侧栏 `sidePanel` 从联合类型中**移除** `settings | env | guide`。

### Provider 主从

| 区域 | 内容 |
|------|------|
| 左列表 | 账号 id/label、已配置标记；`+` 添加（弹层或列表内联最少字段：id/label/base/key） |
| 右详情 | 当前账号：显示名、api_base（用户账号可编）、api_key、刷新模型、默认 text_model、默认 image_model；用户账号可删（引用守卫保留） |
| 全局短控 | 生文用账号；生图用账号 +「沿用生文」；高级：批量账号/模型、视频（现逻辑） |

去掉：Chips 与 Select 双重选择、常显大块「添加账号」区与三套完整重复账号选择器。

### Agent 主从

| 区域 | 内容 |
|------|------|
| 左列表 | Pi / Hermes / Codex / Cursor |
| 右详情 | 该工具现有字段（内置 Provider + CatalogPicker 等） |

## 被排除方案

- 仅加宽侧栏：用户明确不要侧栏承载设置。
- 设置极简到「只账号、无默认模型」：与 Foundry host/image 需求不符。
- Agent 本轮不重排：用户选了列表→详情。

## 边界与失败模式

- 全页打开时若有侧栏文档打开：关闭侧栏或保持互斥（**默认互斥**：进设置清掉 sidePanel）。
- 删除仍被引用的账号：阻止并提示先改「生文/生图用谁」。
- 环境安装长日志：全页 Tab 内可滚动，行为与现 EnvPanel 一致。

## 工程代价

- **模块**：`App.tsx` 导航、`SettingsPanel`（或拆 `SettingsPage` + Provider/Agent 子视图）、迁入 Env/Guide、CSS、短文档。
- **测试**：`tsc`；手动：设置进出、Tab、Provider/Agent 主从、侧栏仅三件。
- **回滚**：恢复 sidePanel 枚举即可回退壳；账号逻辑不回滚。

## 显式假设

1. 「完整页面」= 替换主工作区的设置视图，不是系统原生多窗口。
2. 本机 Tab 内容保持现 Settings「本机工具」块。
3. 视频保留在 Provider「高级」，不新开 Tab。

## 领域语言

| 术语 | 含义 |
|------|------|
| 设置全页 | `appView=settings` 下的完整设置 UI |
| 开发侧栏 | 文档 / 看板 / 资产 |
| 账号主从 | Provider 左列表右详情 |
| 工具主从 | Agent 左执行器右预设 |

## 功能需求

1. 顶栏「设置」→ 全页；「返回」→ 聊天。
2. 顶栏无环境/指南侧栏按钮；设置内有对应 Tab。
3. 侧栏仅文档/看板/资产。
4. Provider / Agent 主从交互与上文表一致；模型目录能力不回退。
5. 环境、指南功能与现面板等价迁入。
6. 文档：`GUI-CONFIG.md` 更新入口说明。

## 非功能需求

- 设置全页在常见桌面宽度（≥1100px）下左列表约 240–280px，右侧可读。
- 不引入新依赖。

## 安全关注点

- Key 仍只在 Provider 详情编辑；不进 Agent 详情。
- 无新增 Key 落盘位置。

## 成功标准

1. 点设置进入全页；返回后聊天可用。
2. 顶栏无法再打开环境/指南侧栏；二者在设置 Tab 内可用。
3. 侧栏只能打开文档/看板/资产。
4. Provider：选中一账号只在右侧编辑；生文/生图短选可用；批量在高级。
5. Agent：选中一工具只在右侧编辑预设。
6. `tsc` 通过；开放账号与 models 刷新仍可用。

## PR Review 关注点

- `sidePanel` 是否残留 settings/env/guide。
- Provider 是否仍保留双重 Chips+Select。
- Agent 是否误允许自建账号。
- 进设置是否错误卸载聊天状态（应保持 store，仅切换视图）。

## 开放问题

- （非阻塞 / plan）同事侧栏在设置全页时隐藏 vs 缩成窄条。
- （非阻塞 / plan）添加账号用 modal 还是列表底部内联。
- （延期）Agent 工具预设的更深向导化。
