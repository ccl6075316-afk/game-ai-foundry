# GUI 对话模式（工种 · Skill · 运行时）

面向 Foundry **GUI AI 公司前台**：用户与 **策划 / 项目经理 / 程序员** 对话；工种可多实例。  
产品目标总述：[`docs/HOST-CHAT-PRODUCT.md`](../../../docs/HOST-CHAT-PRODUCT.md)。

## 工种 → Skill / 运行时

| 工种 | 用户称呼 | Skill / 规范 | 运行时 | 何时用 |
|------|----------|--------------|--------|--------|
| **① 策划** | Brief、主对话 | [`host-chat.md`](host-chat.md) 默认；落实 [`commit-brief.md`](commit-brief.md) / [`commit-doc.md`](commit-doc.md) | **薄 Chat**（直连 LLM，无 Agent 环） | 商量需求；明确「落实」才写 `brief.json` |
| **② 项目经理** | 产品、Host | [`product-host.md`](product-host.md) | **Agent**（Hermes / Cursor / Codex executor） | **修改主入口**；分诊、派工、推进 progress |
| **③ 程序员** | 程序员 | `resources/skills/godot-developer/` | **Agent**（同上） | 接 task / handoff；改 C#、validate |

兼容旧路径：[`brief-brainstorm.md`](brief-brainstorm.md) 仅 CLI；GUI ① 用 `brief chat`（host-chat → commit-*）。

## 协作总线（跨工种）

```text
策划落实  ──► brief.json
项目经理  ──► progress.json、handoffs/*.json、定点 pipeline
程序员    ──► games/、validation 结果写回 progress

禁止：把策划或项目经理的 messages[] 当下游契约。
```

## ① 策划 — 宿主应做的事

```text
1. 默认 system = host-chat.md
2. 维护本实例的 messages[]（仅本策划会话）
3. intent_hint == commit_brief|commit_doc → 切换落实 skill
4. 仅 ready_to_export && artifact → brief validate/export
5. 超长 → summary + 近 N 轮（见 cli/host_chat.py）
```

原则：商量 ≠ 契约；**无终端工具环**。

## ② 项目经理 — 宿主应做的事

```text
1. GUI 调 agent turn（executor = Hermes / Codex / Cursor CLI）
2. system 含 product-host.md；注入 brief / production / progress
3. 用户反馈 → 分诊 A/B/C/D（见 HOST-CHAT-PRODUCT §6）
4. 解析回复末尾 JSON → progress note + plans/handoffs/
5. 可触发 test / 定点 pipeline（目标）；结果写回 progress
6. 不在本角色直接大改玩法 C#（交给程序员）
```

当前实现：单轮 `agent turn` + 落盘 handoff；完整多步 tool 环与定点 pipeline E2E 仍在演进。

## ③ 程序员 — 宿主应做的事

```text
1. GUI 调 agent turn；prompt 注入未读 handoffs
2. 读 authoritative 文件 + handoff / progress
3. 不读策划或其他实例的闲聊记录
4. 工具：改工程、godot validate、必要 CLI（经 executor）
5. handoff_done → 关单；写 progress
```

仍缺：`target_instance_id` 精确路由、流式日志。
## 多实例

- 每个 **instance_id** 独立 sessions；`roster.json` 登记 display_name、executor、role_kind。
- 项目经理实例 A 派工给「程序员·玩法」→ handoff 标明 `target_instance_id`。
- 用户可创建多个项目经理、多个程序员实例。

## 会话隔离

- 按 **实例** 分 session，不按「全局唯一 Host」。
- 跨实例传递：**文件与 task id**，不是聊天记忆。
