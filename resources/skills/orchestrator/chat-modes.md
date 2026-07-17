# GUI 对话模式（三角色 Skill 路由）

面向 Foundry **GUI 三 Tab**：Brief 创建 / 产品 Host / 程序员。  
产品目标总述：[`docs/HOST-CHAT-PRODUCT.md`](../../../docs/HOST-CHAT-PRODUCT.md)。

## 角色 → Skill

| Tab | 角色 | Skill / 规范 | 何时用 |
|-----|------|--------------|--------|
| **① Brief 创建** | 设计对话 | [`host-chat.md`](host-chat.md) 默认；落实用 [`commit-brief.md`](commit-brief.md) / [`commit-doc.md`](commit-doc.md) | 商量需求；明确「落实」才写文件 |
| **② 产品 Host** | 编排分发 | [`product-host.md`](product-host.md)（分诊 → 派工） | **修改主入口**；读 progress / production |
| **③ 程序员** | 写码 | `resources/skills/godot-developer/`（implement + vendor） | 接 Host 的 task；改 C#、validate |

兼容旧路径：[`brief-brainstorm.md`](brief-brainstorm.md) 仅 CLI / 旧 GUI；新 GUI ① 用 host-chat → commit-*。

## ① Brief 创建 — 宿主应做的事

```text
1. 默认 system = host-chat.md
2. 维护本 Tab 的 messages[]（商量只活在这里）
3. intent_hint == commit_brief|commit_doc → 切换落实 skill，传入完整 conversation
4. 仅 ready_to_export && artifact → brief validate/export 或写 md
5. 未落实前：不要因聊天改 brief.json
```

原则：商量 ≠ 契约；LLM 重填充 brief；**本 Tab 无终端工具环**。

## ② 产品 Host — 宿主应做的事（目标）

```text
1. 上下文优先加载：brief、production、progress、最近 validation report
2. 用户反馈 → 分诊 A/B/C/D（见 HOST-CHAT-PRODUCT §4）
3. 派工：
   - A/C → 写入/更新 progress task，通知程序员 Tab（或打开任务包）
   - B → 确认后触发定点 pipeline / assemble
   - D → 引导 Brief Tab 落实变更，或 Production Delta
4. 可触发 test unit/play/regression；结果写回 progress
5. 不在此 Tab 直接大改玩法 C#
```

## ③ 程序员 — 宿主应做的事（目标）

```text
1. 只读 authoritative 文件 + Host 下发的 task 包（不读 Brief Tab 闲聊）
2. 工具：改工程、godot validate、必要时 CLI
3. 完成后回报 Host / 写 progress（task done 或 last_error）
```

## 会话隔离

- 三 Tab **各自 session**（或同库用 `role`: `brief` | `product_host` | `programmer`）。
- 跨 Tab 传递的是 **文件与任务 id**，不是把对方整段聊天当契约。
