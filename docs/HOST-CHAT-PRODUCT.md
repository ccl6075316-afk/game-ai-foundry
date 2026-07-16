# Host 对话产品目标（Chat App 式策划）

| | |
|--|--|
| **读者** | 另一台机器上继续开发的你 / Agent |
| **日期** | 2026-07-17 |
| **状态** | 目标已对齐；Skill 已起草；**GUI/CLI 尚未接线** |
| **不写** | pipeline / 施工验收细节 → 见 `CONSTRUCTION-SYSTEM.md` |

---

## 1. 一句话目标

主对话要像 **DeepSeek / ChatGPT App**：可以长时间商量、咨询、谈实现；**不必做游戏**。  
只有用户明确说 **「落实成 brief / 文档」** 时，才生成结构化产物。  
Brief 里的大量细节由 **LLM 填充**；用户负责方向与拍板，不是逐字段填表。

**不要**把这条路径做成「带终端工具的 Agent 环」。工具型 Agent（Cursor / Hermes）另作施工、排错、写码。

---

## 2. 分层（必须分清）

| 层 | 内容 | 权威性 |
|----|------|--------|
| **商量 / 咨询** | 纠结、对比、举例、改主意、技术问答 | 只活在会话 `messages`；**不是**契约 |
| **落实产物** | `brief.json` 或普通 markdown 文档 | 用户明确落实 +（brief 则）`validate`/`export` 后才权威 |
| **下游** | pipeline / production / Godot | **只读文件**，不读聊天记忆 |

原则（与全仓一致）：口头聊过但没写入文件的，一律无效。

---

## 3. 要 vs 不要

### 要

- 类消费级聊天体验（多轮自然对话）
- LLM **重填充** brief（英文 description、资产表、controls、合理默认等）
- 「落实」前不改 `brief.json`
- 无工具环也能聊完并定稿 Design

### 不要

- 默认每轮 merge 进 `draft_brief`（旧问卷式 brainstorm）
- 主路径依赖 Hermes/Cursor 才能策划
- 把商量过程整段塞进 brief 字段
- 为聊天再造一套带 CLI 的 Agent Runtime（除非产品上 GUI 必须自建）

---

## 4. 已起草的 Skill（仓库内）

路由总览：[`../resources/skills/orchestrator/chat-modes.md`](../resources/skills/orchestrator/chat-modes.md)

| Skill | 文件 | 作用 |
|-------|------|------|
| 默认聊天 | `resources/skills/orchestrator/host-chat.md` | `artifact=null`；可闲聊/咨询；`intent_hint` 表达落实意图 |
| 落实 Brief | `…/commit-brief.md` | 根据**全文对话**合成 `draft_brief`；LLM 补细节；过冻结清单 |
| 落实文档 | `…/commit-doc.md` | 普通 markdown，非 brief 契约 |
| 旧问卷式 | `…/brief-brainstorm.md` | CLI `brief brainstorm` 仍在用；顶部已指向新路径 |

**宿主职责（未实现）：**

1. 默认加载 `host-chat.md`
2. 维护会话 `messages[]`
3. 见 `intent_hint: commit_brief|commit_doc` → 切换对应 skill，传入完整 conversation
4. 仅 `ready_to_export && artifact` 时写盘（brief → validate/export）

---

## 5. 会话系统（若自建 GUI 聊天则需要）

做成 Chat App 就必须产品化：

- **上下文** = 当前 conversation 的 `messages`（+ 可选标题）
- **新对话** = 新 session id；旧会话归档或丢弃
- **落实** = 只针对当前会话合成 artifact
- 可选：长对话摘要压缩（保留摘要 + 近 N 轮）

未落实前：**不要**因聊天改 `brief.json`。

存储示意（未落地）：

```text
conversations/{id}.json   → messages, title, created_at, mode
export 后才有 resources/*-brief.json 或用户指定的 .md
```

---

## 6. 与「直接用 Agent」的关系（决策备忘）

| 问题 | 结论 |
|------|------|
| 自建会话 + skill 路由是否一定更好？ | **不一定**。对话体验上 Cursor/GPT 往往够用且少维护。 |
| 市面有无成品？ | **有**：Open WebUI / LibreChat / Dify / Cursor 等已含会话与提示路由。 |
| Foundry 真正要自建的？ | 常常只是 **落实 → brief validate/export** 这一薄层，不是整套 ChatGPT。 |
| Skill 还有没有用？ | **有**——可挂 GUI，也可当 Cursor/Hermes 的说明书。 |

**务实分流（建议）：**

- **个人 / 重度（Cursor）**：用 Agent 聊 + 落实时跑 CLI；skill 当规范。
- **Release GUI 用户**：若需要聊天窗，优先套开源壳或轻量 session，再接到 `commit-brief`；不要先造完整中台。

明天续写时先定：**GUI 是否必须成为主聊天入口**。不定这个，会话系统可缓做。

---

## 7. 与现状代码的差距

| 现状 | 目标 |
|------|------|
| GUI 非 `/` 文本 → 进 brainstorm 或直接 `start` | 默认 `host-chat`，不写 brief |
| 每轮 merge `draft_brief` | 仅落实 skill 才写 artifact |
| 基本单文件 `plans/brainstorm-session.json` | 多会话 + 新对话（若做 GUI Chat App） |
| Skill 已存在 | **接线未做** |

相关代码入口：

- `cli/brief_brainstorm.py` — 仍加载 `brief-brainstorm.md`
- `gui/src/App.tsx` — `handleSend` 末尾非命令 → brainstorm
- `gui/electron/main.mjs` — `brief-brainstorm-*` IPC

---

## 8. 建议落地顺序（另一台电脑）

1. **定产品入口**：GUI 主聊天 vs Agent 为主（见 §6）。
2. 若 GUI：会话 CRUD（新对话 / 历史）→ 默认 `host-chat` → 「落实 brief」切 `commit-brief` → `brief validate/export`。
3. 若 Agent 为主：完善 skill 文档 + `TOOLS.md` 一段「如何落实 brief」即可；会话交给 Cursor。
4. 旧 `brief brainstorm` CLI：保留兼容，或逐步改为调用同一套 commit 逻辑。
5. 不要与施工体系（production / progress / harness）绑死——那是 brief **之后**的事。

---

## 9. 相关文档

- Skill 路由：`resources/skills/orchestrator/chat-modes.md`
- Brief 契约 / CLI：`docs/AI-HANDOFF.md`
- 设计 vs 施工：`docs/ITERATIVE-PRODUCTION.md`
- GUI Provider vs 执行器：`docs/GUI-CONFIG.md`
- 进度：`ROADMAP.md`（可后续加一条「Host Chat App / 落实式 brief」）

---

*写给明天的你：先读 §1–§3 与 §6；Skill 已在仓库；先拍板 GUI 是否主入口，再写会话或只接 Agent。*
