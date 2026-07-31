# 工程 Spec：可选 UI 面板清单 + 按需字符示意

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-31
- **Updated**：2026-07-31
- **Source Of Truth Until**：本 Spec 已确认；实现以 [`docs/anvil/plans/2026-07-31-ui-panels-wireframe-plan.md`](../plans/2026-07-31-ui-panels-wireframe-plan.md) 为准（plan 仍待用户确认）
- **Confirmed By**：user「确认」（2026-07-31）
- **Requirements Source**：engineering spec derived from user Grill（聊到 UI → ui_panels；示意点击才生成；可选非硬依赖）
- **Background Inputs**：UI 布局缺口讨论；2026-07-27 禁止强制 screens；既有 hud/ui_element
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：确认 plan 后 `/anvil:code`

## 背景输入

- 菜单、装备等面板如今只在 Brief 里薄记（`ui_element` + `hud.anchor` + 长 `description`），**没有**「有哪些面板」的清晰清单，也没有给人看的布局示意。
- 用户不需要此时出真实 UI 贴图；需要的是「有什么、大致在哪」的字符级示意（表格 / ASCII，地图也可用字符拼）。
- 示意主要给**用户预览**；程序员可看，但**不是**施工强制依赖——用户可不建面板，由程序员直接做 UI。
- `description` 字段过载是**另案**，本期不处理。

## 工程理解

拆成两层产物，触发不同：

1. **`project.ui_panels[]`（Brief / draft 结构化清单）**  
   - 用户在策划对话或补全细节中**聊到 / 明确了 UI 面板**时，把它写成独立面板条目，而不是塞进一大段 `description`。  
   - **可选**：无此字段不挡导出、不挡 pipeline、不挡 Godot 任务。  
   - **不强制**与 `assets(ui_element)` / `project.hud` 一一对应或交叉校验（本期）。

2. **`ui-wireframe.md`（或等价项目内文档，字符示意）**  
   - **仅用户点击**「生成 UI 示意」类入口才生成/覆盖。  
   - 内容：用字符/表格画出各面板大致区位与内部主要块（有什么、大致在哪）。  
   - Docs 侧栏可打开；派工上下文**可附路径**（软提示），缺失不失败。

## 目标

1. Draft/Brief 支持可选 `project.ui_panels[]`，把「有哪些 UI 面板」从散文里拆出来。  
2. 策划聊天 / 补全细节：一旦识别到面板意图，写入或更新 `ui_panels`（分开写）。  
3. 提供按需生成字符线稿文档的入口；默认不自动生成示意图。  
4. 程序员/项目经理侧能发现并打开该文档（若存在）；不存在则行为与今日相同。  
5. 明确非目标：`description` 整改、强制 HUD/资产绑定、真实 UI 生图。

## 非目标

- 不改正现有 `assets[].description` / 全局 description 过载问题（另开需求）。  
- 不把 `ui_panels` 设为 `brief validate` / 导出必填。  
- 不强制 `ui_panels` ↔ `ui_element` ↔ `hud` 一致性校验。  
- 不自动跑生图；示意图仅为字符文档。  
- 不做完整交互原型（点击态、动画、精确像素）。  
- 不修改 Seedance / 资产流水线。

## 当前架构约束

- Draft：`host_chat` session `draft_brief` → `brief.draft.json`；补全：`run_brief_enrich`；GUI「补全细节」。  
- HUD：`project.hud[{asset, anchor, description}]`；有 `ui_element` 时 validate 要求 hud 条目。  
- Docs：`DocsPreviewPanel` 可读项目内 md（如 `brief.zh.md`）。  
- Production / godot 任务：有 hud 则「Wire HUD」；无 ui_panels 概念。  
- 2026-07-27 Spec 禁止的是「全品类强制 screens 死表」；本期是**可选** panels + **按需**示意，不违背该边界（须在验收中保持「可缺省」）。

## 方案选择

**选定：可选 `project.ui_panels[]` + 点击才生成字符 `ui-wireframe.md`。**

| 项 | 选定 |
|----|------|
| 面板权威（对人） | `project.ui_panels[]`（可选） |
| 示意载体 | 项目内独立 md（建议名 `ui-wireframe.md`，与 brief 同工程目录） |
| 写入 panels | 对话/补全识别到 UI 面板意图时写入 |
| 写入示意 | 仅用户点击生成 |
| 与资产/hud | 本期不强绑 |
| 施工 | 软可见；缺省不堵 |

### `ui_panels[]` 最小字段（工程结论）

每项建议：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 稳定短 id（如 `equip_panel`） |
| `title` | 是 | 显示名（装备面板） |
| `kind` | 否 | 自由短标签：`hud` / `menu` / `inventory` / `map` / `other` 等，非死枚举强制 |
| `anchor` | 否 | 大致位置：`top_left` 等或短文案 |
| `slots` | 否 | 字符串列表：面板内主要块（「金币」「格子 5×4」），代替长 description |
| `notes` | 否 | 一句备注 |

禁止把整篇布局散文塞进单一 `notes`；示意细节进 md。

## 被排除方案

- Brief 内强制 `screens[]` 且 validate 必填（与 2026-07-27 及「可不建面板」冲突）。  
- 补全自动生成示意图（用户改为点击才生成）。  
- 仅 md、Brief 无清单（用户要求 Brief 结构化列出面板）。  
- 本期整改 description 过载。

## 边界与失败模式

- 无 `ui_panels`、无 md：全流程与改前一致。  
- 有 panels 无 md：合法；侧栏无示意文件。  
- 有 md 无 panels：合法（用户可先点示意再补清单——实现上可提示「建议先有 panels」，不强制）。  
- 生成示意时 draft 无面板：可基于对话摘要/空模板生成弱示意，或提示「先聊出面板」——plan 定一种，推荐：**无 panels 时按钮可用但文案提示先补全/先聊 UI**。  
- 程序员上下文：handoff/提示可含「若存在则阅读 `ui-wireframe.md`」；文件缺失不报错。

## 工程代价

- CLI：draft/brief 解析与（可选）normalize `ui_panels`；示意生成命令；enrich/chat 提示词要求「聊到面板则写入 ui_panels」。  
- GUI：补全/聊天已能写 draft；新增「生成 UI 示意」按钮；Docs 列出 md。  
- 文档：AI-HANDOFF / HOST-CHAT 短述。  
- 测试：字段 round-trip；缺省不挡 validate；示意命令写文件。  
- 预估：中等跨模块；契约增量小且可选。

## 显式假设

1. 「聊到 UI」由 LLM 在 enrich/chat 回合判断；不要求用户说固定咒语。  
2. 示意文件名/路径在 plan 钉死一种（建议与 `brief.draft.json` 同目录的 `ui-wireframe.md`）。  
3. 中文说明 `brief.zh.md` 可不强制镜像 panels（可二期）；本期至少 draft JSON + md。  
4. description 过载另案，不在本期验收。

## 领域语言

| 术语 | 含义 |
|------|------|
| UI 面板清单 | `project.ui_panels[]` |
| UI 字符示意 | `ui-wireframe.md` 类 ASCII/表格布局 |
| 软可见 | 程序员可看；缺失不失败 |
| 硬依赖 | validate/导出/任务门禁 —— 本期不对 panels/示意启用 |

## 功能需求

1. **FR1** Draft/Brief 可含可选 `project.ui_panels[]`，字段满足上表最小集。  
2. **FR2** 策划对话或补全细节在识别到 UI 面板时，将面板写入 `ui_panels`（分条，不堆进单一 description）。  
3. **FR3** GUI（或等价 CLI）提供「生成 UI 示意」；点击后根据当前 `ui_panels`（及必要 draft 上下文）写出/覆盖字符 md。  
4. **FR4** Docs 侧栏可打开该 md。  
5. **FR5** `brief validate` / 导出：**不因**缺少 `ui_panels` 或 md 而失败。  
6. **FR6** 不新增 `ui_panels` 与 `ui_element`/`hud` 的强制一致性错误。  
7. **FR7** 程序员相关提示或 handoff：**若文件存在**则指向示意路径（软）。

## 非功能需求

- 示意生成仅 LLM 文本，无生图费用。  
- 按钮与补全解耦：补全可写 panels，不自动写 md。  
- 中文 UI 文案；存储 id 用英文蛇形为宜。

## 安全关注点

- 示意 md 写入用户工程目录，路径需限制在当前项目根内（防路径穿越）。  
- 无新密钥面。

## 成功标准

1. 聊到装备/菜单等后，draft 出现分条 `ui_panels`，且非仅埋在 description。  
2. 未点示意按钮则无强制新 md；点了则生成可读字符布局。  
3. 全程无 panels、无 md 仍可导出并跑 pipeline。  
4. Docs 能打开示意；程序员提示在文件存在时能找到路径。  
5. 单测覆盖：可选字段不破坏 validate；示意写入路径安全。

## PR Review 关注点

- 是否误把 `ui_panels` 做成 validate 必填（回归 2026-07-27 禁令）。  
- 补全是否又自动生成 md（违反「点击才生成」）。  
- 是否偷偷整改 description（范围蔓延）。  
- 示意写路径是否逃出项目目录。

## 开放问题

（无阻塞项）

| 项 | 归属 | 触发 | 延期原因 |
|----|------|------|----------|
| description / usage_description 过载拆分 | 另案 | 用户另开 | 明确本期不做 |
| ui_panels ↔ ui_element/hud 硬绑定 | 二期 | 需要施工强制对齐 | 用户选软耦合 |
| brief.zh.md 镜像 panels | 增强 | 中文审阅要对齐 | 非必须 |
| 无 panels 时示意按钮行为细节 | plan | 实现选型 | 不挡 Spec 确认 |
