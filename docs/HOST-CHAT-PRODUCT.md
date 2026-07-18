# GUI：AI 公司对话前台

| | |
|--|--|
| **读者** | 产品 / GUI / 接手 Agent |
| **日期** | 2026-07-17 |
| **状态** | **心智已拍板**；① `brief chat`；②③ `agent turn`→CLI；分诊可写 `plans/handoffs/` + progress；GUI 同事多实例已有 |
| **不写** | pipeline 命令细节 → `AI-HANDOFF`；施工验收细节 → `CONSTRUCTION-SYSTEM` |

---

## 1. 一句话目标

用户打开 GUI，看到的不是一排工具按钮，而是 **一家 AI 游戏公司的对话前台**：

- 用户是 **决策人**（拍板、验收、改主意）
- 公司里有多位 **可对话的同事**（工种固定，**人数可增**）
- 同事之间 **不靠共享聊天上下文协作**，靠 **本地文件**（brief、production、progress、task 包）

**最大使用场景是修改**：试玩后发现问题，找 **项目经理** 说；项目经理分诊派工；**程序员** 按任务改工程——全程像在公司里对齐，而不是用户手搓 CLI。

---

## 2. 产品心智：AI 公司，不是工具面板

```text
                    ┌─────────────────┐
                    │  用户（决策人）   │
                    └────────┬────────┘
                             │ 和「同事」1:1 聊天
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ① 策划 / Brief      ② 项目经理          ③ 程序员
   （主对话，出 brief）  （分诊、派工）        （写码、验收）
         │                   │                   │
         │  薄 Chat + skill  │  Agent 环         │  Agent 环
         │  (host-chat)      │  Hermes/Cursor/   │  Hermes/Cursor/
         │                   │  Codex executor   │  Codex executor
         └───────────────────┴───────────────────┘
                             │
                    协作总线 = 本地文件
              brief · production · progress · task 包 · 工程目录
```

| 维度 | 本产品 | 不要做成 |
|------|--------|----------|
| 用户感受 | 和公司里的人聊天、拍板 | 对着 pipeline 面板点按钮 |
| 角色 | **工种** + **可多个实例** | 全局只有一个 Host、一个程序员 |
| 跨角色协作 | **写文件 / 读文件** | 把 A 的聊天记录塞给 B 当契约 |
| ②③ 后端 | **Agent**（有工具、可多步） | 单次 LLM 补全假装分诊完事 |
| ① 后端 | **薄 Chat**：边聊边维护 `draft_brief`；**落实/导出才冻结写盘** | 带终端的万能 Agent 环；未拍板就写 `resources/` |

---

## 3. 三种工种（跟用户直接对话的角色）

用户只和 **三种工种** 对话；每种可 **雇佣多个实例**（例如「项目经理·小王」「程序员·平台组」「程序员·战斗」）。

| 工种 | 用户怎么叫 | 职责 | 对话后端 |
|------|------------|------|----------|
| **① 策划 / Brief** | 主对话、出 brief | 边聊边扩写工作草稿（侧栏可全盘查看）；用户明确「落实/导出」才写 `brief.json` | **薄 Chat**：`host-chat`（增量 `draft_brief`）→ `commit-brief`；**不是** Agent 环 |
| **② 项目经理** | 产品、Host | **修改主入口**：听反馈 → 分诊 A/B/C/D → 派工、推进 progress、触发验收 / 定点 pipeline | **Agent**（Hermes / Cursor / Codex 等 executor） |
| **③ 程序员** | 程序员 | 接项目经理下发的 task；改 Godot C#；跑 validate / 测试 | **Agent**（同上） |

**命名对齐（避免混淆）：**

- **「项目经理」= 产品 = Host** → 指 **② 这个可对话角色**，不是设置里某个 API 字段的别名。
- 设置里的 **Host LLM / 项目经理 API** → 只是 **① 策划岗** 用的生文接口；与 **② Agent 岗** 是不同层。

**禁止并错：**

- 不要把策划（出 brief）和项目经理（分诊派工）合成一个聊天窗。
- 不要把「项目经理」实现成「拼文件 + 调一次 LLM 出 JSON」——那是宿主辅助，**② 的主路径是 Agent**。

---

## 4. 多实例：可雇多个项目经理、多个程序员

用户可按项目需要 **创建多个同事实例**：

```text
同事列表示意
├── 策划 · 默认
├── 项目经理 · 主线
├── 项目经理 · 素材跟进        ← 第二个项目经理实例
├── 程序员 · 玩法
└── 程序员 · UI                ← 第二个程序员实例
```

每个实例拥有：

| 属性 | 说明 |
|------|------|
| `role_kind` | `brief` \| `product_manager` \| `programmer` |
| `instance_id` | 唯一 id |
| `display_name` | 用户可见名（「小王」「平台组」） |
| `executor` | ②③ 绑定的 Agent 执行器（Hermes / Cursor / Codex） |
| `sessions[]` | 该实例自己的对话历史（不与其他实例共享） |

**协作不靠聊天串线：**

- 项目经理 A 派给「程序员·玩法」→ 写 `progress.json` task / handoff 文件
- 程序员打开自己的对话 → Agent **读 task 文件 + brief + 工程**，不读项目经理的闲聊记录

---

## 5. 文件总线（权威分层）

| 层 | 内容 | 权威性 |
|----|------|--------|
| 任一同事的聊天过程 | 该实例的 `messages[]` | **不是**契约 |
| 策划会话内 `draft_brief` | `plans/conversations/brief/<id>.json` 工作草稿 | **不是**契约；可纠偏 |
| Brief 落实产物 | `projects/<slug>/brief.json`（validate/export 后） | Design 契约 |
| 工程蓝图 | `projects/<slug>/production.json` | 施工蓝图 |
| 进度与任务 | `projects/<slug>/progress.json`、task / handoff 包 | 派工与续作真相 |
| 工程与资产 | `projects/<slug>/game/`、`output/`、`pipeline/` | 实现真相（同目录隔离） |

原则：**口头聊过但没写入文件的，一律无效。** 跨角色只传 **文件与 task id**。

---

## 6. 修改优先：项目经理分诊（② 的核心）

用户在 **项目经理** 实例里说试玩反馈后，Agent 应分诊为：

| 类型 | 含义 | 项目经理动作（目标） |
|------|------|----------------------|
| **A. 纯 Bug** | 实现错，brief 仍对 | 开/标 `godot_task` → 派给目标 **程序员** 实例 |
| **B. 图/动画不对** | 资产质量或绑定错 | 确认后定点重跑该 asset 的 pipeline / assemble |
| **C. 逻辑不符 brief** | 代码偏离冻结契约 | **不改 brief**；派程序员按 brief 纠偏 |
| **D. 改需求** | 用户想法变了 | 引导用户找 **策划** 实例落实 brief，或 Production Delta |

CLI 零件（scaffold、validate、test、pipeline）与 **GUI Agent 接单** 已接通：项目经理分诊可写 `plans/handoffs/` + progress；程序员 turn 注入未读 handoff。仍缺：按 `target_instance_id` 精确路由、executor 流式日志、Production Delta。

---

## 7. 各工种与 Skill / 后端

路由总览：[`../resources/skills/orchestrator/chat-modes.md`](../resources/skills/orchestrator/chat-modes.md)

### ① 策划 / Brief

| Skill | 文件 | 作用 |
|-------|------|------|
| 默认聊天 | `host-chat.md` + `brief-animation-graphs.md` | 商量；聊游戏时每轮输出完整 `artifact.draft_brief`（工作草稿） |
| 落实 Brief | `commit-brief.md` + `brief-animation-graphs.md` | 在现有草稿上精修 + gaps；`ready_to_export` |
| 项目经理 | `product-host.md` | 首跑引导点 GUI「生成流水线→运行资产生成」；config 仅用户明确要求时可改 |
| 落实文档 | `commit-doc.md` | 普通 markdown |
| 旧问卷式 | `brief-brainstorm.md` | CLI 兼容；GUI 勿默认 |

宿主：`host-chat` 每轮 deep-merge 持久化 `draft_brief` → 落实意图切 `commit-*` → 仅 `ready_to_export` 时 export 写 `resources/*-brief.json`。  
GUI：顶部「文档」侧栏实时预览会话内 `draft_brief` / `draft_document`，以及当前项目落盘文件（exported brief、production、progress、`docs/*.md` 等）；读 `host-chat status` / 仓库文本，不重新跑 LLM。  
**自动修 brief**：侧栏「自动修到可导出」或 `/brief autofix [轮数]` → 宿主把当前校验 gaps + 已有 clip 名注入对话，循环让策划 LLM 改草稿，直到 `audit` 通过、卡住或达上限（默认 5 轮）。  
CLI：`brief chat *`；`brief chat autofix --session-id … --max-rounds 5`；会话 `plans/conversations/brief/<id>.json`。

### ② 项目经理（Agent）

- 规范：[`product-host.md`](../resources/skills/orchestrator/product-host.md)
- **运行时**：GUI 内嵌或外接 **executor Agent 环**（可读 progress、调白名单 CLI、写 task）
- **上下文**：**文件优先**（brief、production、progress、validation report）；本会话仅作与用户沟通
- **输出**：对用户可读说明 + 结构化派工（写 progress / handoff），不是只吐一段 triage JSON 就结束

### ③ 程序员（Agent）

- 规范：`resources/skills/godot-developer/`（含 vendored Godot skills）
- **运行时**：同上，独立 executor 实例
- **输入**：authoritative 文件 + 项目经理写的 task 包；**不读**策划实例的闲聊
- **输出**：改工程、validate、写回 progress（done / last_error）

---

## 8. 会话系统（当前实现）

### 8.1 UI

- 左侧：**同事列表**（头像 + 姓名为主、工种为辅；「+ 雇佣」）
- 右侧：与选中同事的聊天窗 — 多会话、新对话
- 用户感受：像 IM 里找人，不像顶栏切换「工具模式」

### 8.2 存储

| 层 | 位置 |
|----|------|
| 同事实例 roster | GUI `localStorage`（`gamefactory.activeChatSessions.v2`，含 roster） |
| ① 策划后端会话 | `plans/conversations/brief/<id>.json`（summary + 近部） |
| 派工包 | `plans/handoffs/<id>.json` |
| 进度 | `plans/progress_*.json` |

会话 **按 instance 隔离**；跨同事只传文件与 task id。① 已压缩长对话；②③ 依赖 executor 侧上下文 + 注入的 handoff 文本。

---

## 9. 已完成 vs 仍缺

| 已完成 | 仍缺（Next） |
|--------|----------------|
| 同事列表 + 多实例雇佣 / 可收起侧栏 | executor 流式日志进 GUI |
| ① `brief chat` / 边聊边草稿 + 侧栏全盘查看 → 落实才写盘 | 首次启动引导流 |
| ②③ `agent turn` → Hermes / Codex / Cursor CLI | 项目经理 **自动执行** 定点 pipeline（现已写 next_actions） |
| 分诊 → handoff + `target_instance_id` 路由；程序员按实例过滤未读 | 修改闭环全自动验收写回 |
| 关单 → progress task `done` | |
| `production delta` / `apply-delta` CLI | Delta ↔ progress.init 自动展开 |

历史阶段 A–D（三 Tab → roster → Agent → 闭环）中 **A–C 主体已落地**；**D（修改闭环 E2E）** 仍是 P0。

---

## 10. 与「外置 Cursor」的关系

| 场景 | 建议 |
|------|------|
| Release / 主力用户 | **在 GUI 里和项目经理、程序员对话**（本产品目标） |
| 个人重度开发 | 外置 Cursor 仍可用；skill 当规范；executor 可指向同一 Codex/Cursor |

已拍板：**GUI 是主对话入口**；executor 是 **②③ 的运行时**（CLI，不拉桌面 App），不是绕过 GUI 的唯一路径。

---

## 11. 代码入口

| 区域 | 路径 |
|------|------|
| GUI 壳 + 发送 | `gui/src/App.tsx`、`ColleagueRoster.tsx` |
| roster / sessions | `gui/src/chat/roster.ts`、`sessions.ts` |
| ① 策划 | `cli/host_chat.py`；IPC `host-chat-*` |
| ②③ Agent | `cli/agent_turn.py`、`agent_cmds.py`；IPC `agent-turn` / `agent-status` |
| 派工 | `cli/handoff.py`；`project handoff *`；IPC `handoff-list` |
| Skill 路由 | `resources/skills/orchestrator/chat-modes.md` |

**刻意保留（兼容）**：CLI `brief brainstorm` / `brief_brainstorm.py`；GUI **不再**走 brainstorm merge。

**已清理**：GUI `brief-brainstorm-*` IPC、Doctor/Pipeline 面板组件、废弃 `image plan`、未挂载的 `godot inject`。

---

## 12. 建议下一步

1. 程序员多实例：`target_instance_id` 路由 + 未读按实例过滤
2. 修改闭环 E2E：反馈 → 分诊 → 定点 pipeline / 施工 → 验收 → progress
3. Production Delta CLI
4. 首次启动引导（工具链 → API → 执行器 → 策划对话）
5. executor 流式日志 / 更长 Agent 环（多步 tool）体验

---

## 13. 相关文档

- Skill 路由：`resources/skills/orchestrator/chat-modes.md`
- Brief / CLI：`docs/AI-HANDOFF.md`
- 设计 vs 施工：`docs/ITERATIVE-PRODUCTION.md`
- 施工体系：`docs/CONSTRUCTION-SYSTEM.md`
- GUI Provider / 执行器：`docs/GUI-CONFIG.md`
- 进度：`ROADMAP.md`

---

*修订说明：心智为 **AI 公司对话前台**；①②③ 与 roster / handoff 主路径已落地。本文 §8–12 反映 2026-07-17 实现，不再写「三 Tab / ②③ 占位」。*
