# 工程 Spec：策划内制作完备性审查（Makeability Critic）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-07-27
- **Updated**：2026-07-27
- **Confirmed By**：user 选择方案 2（意图归 brief / 细节归 production；PM 可推进 production，不改 brief 意图）
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan`
- **Requirements Source**：用户对话（fish2d 类「玩法散文圆了、数值/规则未定」；子 LLM 审查；策划对话框内完成意图缺口；避免 PM 阶段折返改 brief）
- **Background Inputs**：[`ITERATIVE-PRODUCTION.md`](../../ITERATIVE-PRODUCTION.md) Design vs Production 拆分；[`HOST-CHAT-PRODUCT.md`](../../HOST-CHAT-PRODUCT.md) 三角色契约；现有 `host-chat` / `commit-brief` / `production derive`
- **Compounded Knowledge**：not yet compounded

## 背景输入

用户痛点：单一策划 LLM 会话能把「玩法听起来没问题」的 brief 写出来，但**制作细节**（数值、规则表、状态边界、胜负判定参数）常未拍板。到项目经理开流水线或程序员写 C# 时才暴露，导致要么折返回策划改 brief，要么程序员瞎编。

用户已明确：

- 需要 **子 LLM**（或等价独立调用）做审查，不要圆桌多 Agent 对聊。
- 审查与**意图级补齐**应在 **策划对话框内**完成，避免切到 PM 后再整段回改。
- **权威分工（方案 2）**：
  - **brief** = 设计意图（循环、胜负、系统边界、体验目标）
  - **production** = 施工规格（数值表、规则参数、状态机细节、暂定默认）
  - **项目经理** = 推进、分诊、**可填/改 production 暂定项**；**禁止改 brief 玩法意图**
  - 仅当「改循环 / 加系统 / 改体验目标」时才回策划

## 工程理解

Foundry 已有 Design / Production 概念（ITERATIVE §0），但今日 **`brief.json` 仍是 worker 单一冻结契约**；`production derive` 主要产出 scenes / godot_tasks / layout / acceptance_criteria，**不会系统性地逼问「数值与规则表是否齐」**。

现有策划路径：

- `host-chat` 渐进 `draft_brief` + `gaps` + `ready_to_export`
- `commit-brief` 落实时 LLM 补全
- `_audit_draft_gaps` 偏 **brief 契约字段**，抓不到「咬钩率未定」类施工细节

缺口类型应显式二分：

| 类型 | 例子（fish2d） | 权威落点 | 谁关 |
|------|----------------|----------|------|
| **意图缺口** | 胜负条件模糊、核心循环缺一步、系统边界未定 | `brief.project` | **策划**（对话框内） |
| **施工细节缺口** | 咬钩率、鱼价表、冷却秒数、失败惩罚数值 | `production_doc` 新节 | **策划先标出** → **PM 可代填暂定** → 用户可拍板 |

子 LLM **Makeability Critic** 的职责：读当前 `draft_brief`（+ 可选 genre 启发式），输出结构化审查结果，**不替代用户拍板**。

## 目标

1. 在 **策划对话框内** 提供「制作完备性审查」：独立子 LLM 调用，与写 brief 的主会话上下文隔离（fresh critic prompt + 当前 draft JSON）。
2. 审查结果分 **`intent_gaps`**（阻塞交接）与 **`detail_gaps`**（施工细节，进 production）。
3. **交接门闩**：存在未关闭的 `intent_gaps` 时，不得 `ready_to_export` / 不得提示「可交项目经理」。
4. **`detail_gaps`** 在 brief export 后由 **`production derive` 合并**（或首次 derive 时写入 `production_doc.makeability`），PM 可读、可补暂定值，**不改 brief**。
5. 策划 UI 展示审查清单 + 可点选项 / 用户一句回复 → 同一会话更新 `draft_brief`（意图项）或标记「细节移交 production」（施工项）。
6. 文档与 skill 更新：`commit-brief.md` / `host-chat.md` / `product-host.md` 写清权责；PM skill 增加「读 makeability、填 production 暂定、派程序员任务」。

## 非目标

- 多角色圆桌会议定 brief
- 新雇「审查员」工种与独立聊天窗（v1）
- 项目经理修改 `brief.json` 玩法意图（v1 禁止）
- Critic 静默把数值写进 brief 散文（禁止；细节进 production）
- 全自动闭环验收（仍属后续）
- 用 vision / 背景图分析补细节

## 当前架构约束

- 策划：`host-chat` 薄 Chat（非 Agent 环）；会话 `plans/conversations/brief/<id>.json`
- 落实：`commit-brief` skill → export `brief.json`
- 施工：`production derive` → `production.json`（`production_doc.*`）
- PM：`product-host.md` Agent，读文件，不写 brief
- 已有 `brief chat autofix` 模式可借鉴「结构化缺口 → 再一轮 LLM」

## 方案选择

**采用：策划内子 LLM Critic + 意图/细节二分 + production 承载施工细节（用户确认方案 2）**

流程（目标态）：

```text
策划聊天 → draft_brief 基本成形
    → 用户点「制作审查」或落实前自动触发 critic
    → critic 返回 { intent_gaps[], detail_gaps[], suggested_defaults[] }
    → 策划对话：关 intent_gaps（更新 draft_brief / choices）
    → detail_gaps 标记 pending_production（不落 brief 散文）
    → ready_to_export + export brief
    → production derive 写入 production_doc.makeability + 可选 tuning_tables
    → PM：读 makeability，代填 provisional，派 godot_task，不改 brief
```

**策划内补齐方式（推荐，作为 plan 默认）**：

- Critic **不静默改稿**
- `intent_gaps` → 气泡选项 / 用户回复 → host-chat 合并进 `draft_brief`
- `detail_gaps` → 展示「将进 production」摘要；export 后 derive 物化

## 被排除方案

| 方案 | 排除原因 |
|------|----------|
| 仅 PM 阶段审查 | 用户明确要求避免折返回策划；且 PM 不应成第二策划 |
| PM 二次改 brief | 与三角色契约冲突；brief 双写风险 |
| 圆桌多 Agent | 贵、慢、难控 |
| 纯代码 checklist | 抓不到「玩法圆了、数值未定」 |
| 细节全部塞进 brief 必填字段 | brief 膨胀；违背 Design/Production 拆分 |

## 边界与失败模式

| 失败模式 | 处理 |
|----------|------|
| Critic 幻觉编造数值 | 细节只进 `production` 且标 `provisional: true`；程序员 skill 要求读表不读散文 |
| 用户强行 export | GUI 门闩：`intent_gaps` 非空时禁用或二次确认 |
| PM 误改 brief | skill 硬规则 + CLI 无 `brief` 写权限白名单 |
| Critic 与主 LLM 同上下文 | **必须**独立调用（子 LLM），仅传入 draft JSON + genre 模板 |
| fish2d 类无 genre 模板 | v1 通用 critic prompt；genre 模板作增强，非阻塞 |
| derive 未跑 makeability | PM 首跑 checklist 仍见 `makeability.status=pending` |

## 工程代价

| 模块 | 改动量级 |
|------|----------|
| `cli/host_chat.py` | 中：critic 调用、会话字段、门闩 |
| 新 skill `makeability-critic.md` | 小 |
| `cli/production.py` derive | 中：`production_doc.makeability` schema + merge detail_gaps |
| GUI 策划 Tab | 中：审查按钮、缺口面板、choices |
| `product-host.md` | 小：读 makeability、填 provisional |
| 测试 | 中：critic JSON 解析、门闩、derive merge |
| 文档 | AI-HANDOFF、HOST-CHAT-PRODUCT、ITERATIVE 一节 |

## 显式假设

- v1 critic 用与策划相同的 text LLM backend（独立 prompt），不强制第二模型。
- `production_doc.makeability` 为新可选节；旧 production 无此节仍合法。
- 「暂定默认」需用户或 PM 一次确认才标 `provisional: false`（plan 可细化）。
- fish2d 作为验收样例，但不内置私仓；用 generic fishing 模板即可。

## 领域语言

| 术语 | 含义 |
|------|------|
| **Makeability Critic** | 策划侧子 LLM，审查「能否开干」 |
| **intent_gaps** | 设计意图未拍板，阻塞 export / 交接 PM |
| **detail_gaps** | 施工细节未拍板，权威在 production |
| **provisional** | 暂定默认值，可玩但未最终平衡 |
| **makeability** | `production_doc` 内节，承载 detail_gaps 与 tuning 表 |

## 功能需求

### FR-1 Critic 调用

- 输入：`draft_brief` JSON、`project.genre`、可选 bound project slug
- 输出 JSON：
  - `intent_gaps[]`: `{ id, question, why_blocking, choices[]? }`
  - `detail_gaps[]`: `{ id, topic, suggested_table_shape, example_keys[] }`
  - `suggested_defaults[]`: `{ gap_id, value, confidence, note }`（仅 detail，且标 provisional）
- 不修改会话主 draft；结果写入 session `makeability_review`

### FR-2 策划 UI / 对话

- 按钮：「制作审查」（可重复跑）
- 落实 / export 前：若从未审查或 draft 大改，提示先审查（可配置强制）
- 展示 intent_gaps：可点选项写入下一轮 host-chat
- 展示 detail_gaps：说明「导出后进 production，PM 可补」

### FR-3 Export 门闩

- `intent_gaps` 非空 → `ready_to_export=false`；GUI「保存 Brief」禁用或强确认
- `detail_gaps` 允许 export（用户接受「细节进 production」）

### FR-4 Production 物化

- `production derive` 读取 brief + session 最近一次 `makeability_review`（或 brief 附属 meta）
- 写入 `production_doc.makeability`:
  - `status`: `pending` | `partial` | `ready`
  - `intent_resolved_at`（如有）
  - `detail_items[]`: `{ id, topic, status, provisional_values?, owner: "pm"|"programmer" }`
- 可选 `production_doc.tuning`：键值表（如 `bite_rate`, `fish_prices`）

### FR-5 项目经理

- 读 `production_doc.makeability`；对 `provisional` 项可 GUI/Agent 补值
- **禁止** `brief` 写操作；改意图必须引导回策划
- 可生成 handoff：「实现 tuning 表」godot_task

### FR-6 Skills / 文档

- 新增 `resources/skills/orchestrator/makeability-critic.md`
- 更新 `commit-brief.md`：区分 gaps vs makeability
- 更新 `product-host.md`：makeability 消费路径

## 非功能需求

- Critic 单次调用 P95 < 30s（与现有 chat 相当）
- 审查结果可持久化到 session，刷新 GUI 不丢
- JSON 解析失败时降级为「请重试」，不 corrupt draft

## 安全关注点

- Critic 不接收用户密钥回显；仅 brief 内容
- PM 写 production 仍走现有文件权限；不扩 brief 写白名单

## 成功标准

1. **fish2d 类 brief**（循环清晰、无数值）：critic 列出 ≥3 条 `detail_gaps`（如咬钩判定、经济、会话长度），0 条误标为 intent 或反之可接受。
2. **intent 未关**：export 被门闩挡住。
3. **export + derive** 后 `production.json` 含 `makeability.detail_items`。
4. PM turn 注入 makeability 摘要，skill 测试断言不提议改 brief。
5. 单测覆盖 critic 解析、门闩、derive merge。

## PR Review 关注点

- brief / production 边界是否被新字段打破
- PM 路径是否误开 brief 写权限
- GUI 是否只在策划 Tab 触发 critic
- 旧工程无 makeability 时 derive / PM 仍可用

## 开放问题

| 项 | 状态 | 说明 |
|----|------|------|
| 审查强制时机 | deferred → plan | 「仅按钮」vs「export 前强制」；建议 export 前强制一次 |
| `tuning` schema 是否 genre 模板化 | deferred → plan | v1 泛化 JSON 表即可 |
| detail 默认值谁确认 | deferred → plan | 建议 PM 代填仍标 provisional 直至用户试玩确认 |
| GUI 是否展示 production makeability | deferred → plan | PM 看板或 DocsPreview 二选一 |
