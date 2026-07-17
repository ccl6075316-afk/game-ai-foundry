# GUI 三对话对象（Brief / 产品 Host / 程序员）

| | |
|--|--|
| **读者** | 产品 / GUI / 接手 Agent |
| **日期** | 2026-07-17 |
| **状态** | **目标已拍板**；Skill 部分已起草；**GUI 三 Tab + 会话系统未接线** |
| **不写** | pipeline 命令细节 → `AI-HANDOFF`；施工验收细节 → `CONSTRUCTION-SYSTEM` |

---

## 1. 一句话目标

在 **Foundry GUI** 里用三个独立对话入口完成「定设计 → 派工/改版 → 写码」，而不是一次成型 demo。

**最大使用场景是修改**：试玩后发现 bug、图不对、逻辑不符 brief、或想法变了——都应能在 GUI 里对某个对话对象说清楚，由系统分诊并推进，而不是用户手搓 pipeline / 手改代码才算「会用工具」。

---

## 2. 三个可对话对象（三 Tab）

| Tab | 角色 | 职责 | 工具强度 |
|-----|------|------|----------|
| **① Brief 创建** | 设计对话 | 长时间商量需求；仅在用户明确「落实」时生成 `brief.json` | **弱**：直连 LLM + skill；**不要**做成带终端的万能 Agent 环 |
| **② 产品 Host** | 编排 / 分发 | 读 brief、production、progress；**分诊反馈**并派工（素材 / 写码 / 验收）；推进本轮任务 | **中**：可调 CLI（progress、pipeline 定点重跑、开 task、触发验收），不直接大改 C# |
| **③ 程序员** | 写码 Agent | 按 Host 派发的 task / delta 改 Godot C#；跑 `godot validate` 等 | **强**：工具型 Agent（内嵌或接 Cursor/Codex/Hermes executor） |

```text
① Brief 创建  ──落实/export──►  brief.json
                                    │
② 产品 Host  ◄──试玩/反馈/改版──  用户（主入口）
       │ 派工
       ▼
③ 程序员     ──改代码/validate──►  games/ + progress 写回
```

**禁止并错：** 不要把「创建 brief」和「产品 Host」合成一个聊天窗。前者管设计定稿，后者管施工与修改派发。

---

## 3. 权威性分层（全仓一致）

| 层 | 内容 | 权威性 |
|----|------|--------|
| 任一 Tab 的商量过程 | 会话 `messages[]` | **不是**契约 |
| Brief 落实产物 | `brief.json`（validate/export 后） | Design 契约 |
| 工程蓝图 / 进度 | `production.json`、`progress.json` | 施工与续作真相 |
| 下游 | pipeline / Godot 工程 | **只读文件**，不读聊天记忆 |

原则：口头聊过但没写入文件的，一律无效。

---

## 4. 修改优先：Host 分诊（② 的核心）

用户在 **产品 Host** Tab 描述问题后，Host 应分诊为：

| 类型 | 含义 | Host 动作（目标行为） |
|------|------|------------------------|
| **A. 纯 Bug** | 实现错，brief 仍对 | 开/标 `godot_task` → 派给 **③ 程序员** |
| **B. 图/动画不对** | 资产质量或绑定错 | 定点重跑该 asset 的 pipeline / assemble（可先确认） |
| **C. 逻辑不符 brief** | 代码偏离冻结契约 | **不改 brief**；派 **③** 按 brief 纠偏 |
| **D. 改需求** | 用户想法变了 | 引导回 **①** 落实 brief 变更，或走 Change Request / Production Delta（CLI 待补） |

今天 CLI 零件已有（scaffold、validate、unit、play、regression、pipeline）；**缺的是 GUI 入口 + Host 分诊编排**。若修改麻烦，本工具等于没用。

---

## 5. 各 Tab 与 Skill / 后端

路由总览：[`../resources/skills/orchestrator/chat-modes.md`](../resources/skills/orchestrator/chat-modes.md)

### ① Brief 创建

| Skill | 文件 | 作用 |
|-------|------|------|
| 默认聊天 | `host-chat.md` | 商量；`artifact=null` |
| 落实 Brief | `commit-brief.md` | 按全文对话合成 `draft_brief` |
| 落实文档 | `commit-doc.md` | 普通 markdown |
| 旧问卷式 | `brief-brainstorm.md` | CLI 兼容；GUI 新路径勿默认 |

宿主：默认 `host-chat` → 落实意图切 `commit-*` → 仅 `ready_to_export` 写盘。

### ② 产品 Host

- Skill：[`product-host.md`](../resources/skills/orchestrator/product-host.md)（分诊、派工、读 progress）
- 上下文：**文件优先**（brief、production、progress、最近 validation report），会话只作本轮沟通。
- 可对 **③** 发「任务包」（task id、路径、验收命令）；不替程序员写大段玩法代码。

### ③ 程序员

- 规范：`resources/skills/godot-developer/`（含 vendored Godot skills）。
- 交接：`godot dev-context` / progress 当前 task；**不读 ① 的闲聊记录**。
- 后端：GUI 内 Agent 环，或环境里配置的 Cursor/Codex/Hermes executor。

---

## 6. 会话系统（三 Tab 都需要）

GUI 聊天产品化最低集：

- **Session 管理**：多会话、新对话、历史列表；**按角色分库或 `role` 字段**（`brief` | `product_host` | `programmer`）
- **上下文处理**：当前 `messages[]`；可选摘要（summary + 近 N 轮）；切换项目时绑定 slug / brief 路径
- **落实 / 派工**：只针对当前会话 + 当前项目文件

存储示意（未落地）：

```text
conversations/{role}/{id}.json  → messages, title, project_slug, created_at
```

实现策略：**抄开源壳，不造整套 ChatGPT 中台**。

| 参考 | 用法 |
|------|------|
| Lobe Chat / 各类 Chatbot UI | 抄会话列表 + 消息持久化，嵌进 Electron |
| Open WebUI | 抄交互；不宜整仓塞入 |
| LibreChat | 太重；勿整包依赖 |

Foundry 自建重点：三角色后端接线 + 分诊/派工/落实，不是再造通用聊天平台。

---

## 7. 与「外置 Cursor 聊」的关系

| 场景 | 建议 |
|------|------|
| Release / 主力 GUI 用户 | **三 Tab 在 GUI 内完成**（本产品目标） |
| 个人重度开发 | 仍可用外置 Cursor；skill 当规范；但产品叙事以 GUI 三对象为准 |

已拍板：**GUI 必须成为主对话入口**（含 Brief / Host / 程序员）。外置 Agent 是可选增强与程序员后端实现之一，不是唯一入口。

---

## 8. 与现状差距

| 现状 | 目标 |
|------|------|
| 单一聊天框；非 `/` → brainstorm | **三 Tab**：Brief / 产品 Host / 程序员 |
| 每轮 merge `draft_brief` | ① 仅落实时写 brief |
| 无产品 Host 分诊 | ② 修改主入口 + 派工 |
| 写码靠外置或手改 | ③ Tab 可对话推进施工 |
| 内存 messages / 单文件 brainstorm session | 多会话 + 按 role 持久化 |
| 修改靠手敲 CLI | Host 触发定点 pipeline / 开 task |

代码入口（待改）：

- `gui/src/App.tsx` — `handleSend` → brainstorm
- `cli/brief_brainstorm.py` — 旧路径
- `gui/electron/main.mjs` — `brief-brainstorm-*` IPC

---

## 9. 建议落地顺序

1. 文档与 ROADMAP 以本文件为准（✅ 本修订）
2. GUI：三 Tab 壳 + **抄开源** 做 session CRUD / 上下文
3. 接线 ①：`host-chat` → `commit-brief` → validate/export
4. 接线 ②：product-host 分诊 + 调 CLI（progress / pipeline task / test）
5. 接线 ③：程序员 Agent 或 executor；上下文 = 文件 + 本轮 task
6. 修改闭环 E2E：反馈 → 分诊 → 派工 → 验收 → progress
7. Production Delta CLI（改需求时的增量蓝图）并行补齐

---

## 10. 相关文档

- Skill 路由：`resources/skills/orchestrator/chat-modes.md`
- Brief / CLI：`docs/AI-HANDOFF.md`
- 设计 vs 施工：`docs/ITERATIVE-PRODUCTION.md`
- 施工体系：`docs/CONSTRUCTION-SYSTEM.md`
- GUI Provider / 执行器：`docs/GUI-CONFIG.md`
- 进度：`ROADMAP.md`

---

*修订说明：由「单主对话 / 双对象」更正为 **Brief 创建 · 产品 Host · 程序员** 三对话对象；并明确修改优先与 GUI 为主入口。*
