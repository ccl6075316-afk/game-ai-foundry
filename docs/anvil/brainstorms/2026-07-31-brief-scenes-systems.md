# 工程 Spec：Brief 按「场景 + 逻辑系统」划分

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-31
- **Updated**：2026-07-31
- **Source Of Truth Until**：本 Spec 已确认；实现以 [`docs/anvil/plans/2026-07-31-brief-scenes-systems-plan.md`](../plans/2026-07-31-brief-scenes-systems-plan.md) 为准（plan 待用户确认）
- **Confirmed By**：user 对齐「场景 + 脱离场景的逻辑系统」划分，并要求写 plan（2026-07-31）
- **Requirements Source**：fishing `brief.draft.json` 反例讨论；description 过载另案；ui_panels 已落地
- **Background Inputs**：[`2026-07-31-ui-panels-wireframe.md`](2026-07-31-ui-panels-wireframe.md) 中「description 过载另案」；Godot 场景 vs Autoload 开发习惯
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：用户确认 plan 后 `/anvil:code`

## 背景输入

- fishing 类模拟经营：**不是一切都能用漂亮 `gameplay_loop` 表达**；主循环可以短，水族馆/经济/图鉴等是并行系统。
- 当前常见失败：机制、鱼种表、数值、美术、UI 实现约束全堆进 `project.description`（fishing 上 description ≈ loop 的 3 倍），下游 AI 难分权威。
- 开发视角应对齐 Godot：**有画面的场景** + **跨场景的逻辑系统**；资产可按场景/系统归类；纯逻辑系统可无贴图。
- `ui_panels` 已解决「有哪些 UI 块」；本需求解决「玩法/规则与施工边界」的信息架构，不替代 ui_panels。

## 工程理解

Brief / draft 增加两层可选结构化清单：

1. **`project.scenes[]`**  
   运行时有进出的一屏（主界面、钓场搏鱼、商店、水族馆、日结等）。承载：这屏做什么、关联哪些 UI 面板/资产（弱引用）。

2. **`project.systems[]`**  
   脱离单场景的规则与状态（时间池、经济、图鉴解锁、水族馆运转、纪录片分成等）。可无专属资产。

配套纪律：

- **`description`**：短产品总览（若干句：类型、核心体验、视角），**不是**规则全书。
- **`gameplay_loop`**：玩家在场景间如何串（可短）；**不**要求装下全部系统细节。
- **`session_goal`**：本构建胜负或明确「开放无终局」；模拟类允许短声明。
- **资产**：可选 `scene_ids` / `system_ids` 归类；同一资产可挂多个；不强制与清单交叉校验。

## 目标

1. Draft/Brief 支持可选 `project.scenes[]`、`project.systems[]`。  
2. 策划对话 / 补全细节：聊到屏或跨屏规则时写入对应清单，而不是堆进 `description`。  
3. Skills 明确四类字段分工：`description` / `gameplay_loop` / `scenes` / `systems`。  
4. 导出上下文、程序员提示能带上 scenes/systems（若存在）；缺失不挡导出/pipeline。  
5. 资产可选归类字段，便于生图与施工按屏/系统找料。  
6. 以 fishing 为验收样例口径（文档/测试用合成样例即可；**不强制**自动改写用户现有 draft）。

## 非目标

- 不强制 `scenes` / `systems` 为 validate / 导出必填。  
- 不强制 scenes ↔ ui_panels ↔ assets ↔ hud 一致性校验。  
- 不做自动迁移器把旧 `description` 拆进 scenes/systems（可后续工具）。  
- 不新增真实 UI 生图；不改 pipeline 产线阶段图。  
- 不废除 `gameplay_loop` / `session_goal`（仍保留；loop 允许短）。  
- 不在本期重做 GUI 大型 Brief 编辑器（技能写入即可；GUI 只做最小展示/文档提示若成本低）。

## 约束

- 与 `ui_panels` 正交：面板可挂 `scene_id`（可选），但 panels 仍可独立存在。  
- 英文字段值惯例：brief 内规则/描述英文（现有 commit-brief 纪律），对用户中文。  
- 可选字段缺失 = 合法；行为与今日兼容。  
- 同资产多场景引用：只一条 asset，多 id 引用，禁止复制多条 brief 条目「假装归类」。

## 功能需求

1. **FR1** `ProjectContext` + normalize：`scenes[]` / `systems[]`；非法项丢弃或降级；缺省 `[]`。  
2. **FR2** `shared_context` / 导出 dict：非空则带上。  
3. **FR3** validate：**不**因缺失 scenes/systems 失败；`description` / `gameplay_loop` 仍按现有必填策略（若需为「开放无终局」放宽 session_goal，仅允许显式短句，不删字段）。  
4. **FR4** host-chat / enrich / commit-brief：写入纪律与禁止把系统规则堆进 description。  
5. **FR5** 资产可选 `scene_ids` / `system_ids`（字符串列表）；normalize 去空。  
6. **FR6** 程序员/PM 上下文：若存在 scenes/systems，附加结构化摘要或路径提示（软）。  
7. **FR7** AI-HANDOFF（或等价）文档说明字段分工；可用 fishing 作反例/正例对照（节选）。

## 验收标准

1. 无 scenes/systems 的旧 brief 仍能 validate/export（与现有必填字段规则一致）。  
2. 含 scenes/systems 的 draft 经 normalize 后结构稳定；共享上下文可见。  
3. 单元测试覆盖 normalize / 导出 / 资产归类可选字段。  
4. Skill 文案含：description 短、loop 可短、细节进 scenes/systems。  
5. 不引入「无 scenes 不可导出」类硬门槛。

## 待决（已在对话中拍板）

| 项 | 结论 |
|----|------|
| 划分主轴 | 场景 + 脱离场景的逻辑系统 |
| loop | 可短；不装全部系统 |
| description | 短总览；禁止当规则全书 |
| 必填 | scenes/systems **可选** |
| 资产 | 可选 scene_ids / system_ids；弱耦合 |
| 旧 draft | 不自动迁移 |

## 风险

- 策划模型仍可能把细节写入 description → 靠 skill + enrich 纪律，必要时后续加长度/结构 soft warn。  
- scenes 与 ui_panels 概念重叠 → 文档写清：scene=运行时屏，panel=屏内块。  
| 范围蔓延成完整设计工具 → 本期只做契约 + 技能 + 上下文，不做编辑器。
