# Host LLM 对话模式（Skill 路由）

面向 GUI / CLI **直连 LLM** 的主对话：做成简化版 Chat App，**不是**带工具的 Agent。

## 模式一览

| Skill | 文件 | 何时加载 |
|-------|------|----------|
| **默认聊天** | [`host-chat.md`](host-chat.md) | 几乎所有轮次；咨询、商量、实现讨论 |
| **落实 Brief** | [`commit-brief.md`](commit-brief.md) | 用户明确要 brief / 定稿开项目 |
| **落实文档** | [`commit-doc.md`](commit-doc.md) | 用户明确要 markdown 等普通文档 |
| **旧问卷式策划** | [`brief-brainstorm.md`](brief-brainstorm.md) | 兼容旧流程；新 GUI 应优先 host-chat → commit-brief |

## 宿主（App）应做的事

```text
1. 默认 system = host-chat.md
2. 维护 messages[]（商量过程只活在这里）
3. 每轮解析 JSON：
   - intent_hint == commit_brief → 下一轮（或本轮切换）加载 commit-brief.md
     并传入完整 conversation，允许写入 artifact.draft_brief
   - intent_hint == commit_doc → 加载 commit-doc.md
   - intent_hint == clarify_commit → 保持 host-chat，问清 brief 还是文档
4. 仅当 ready_to_export && artifact 非空：
   - brief → brief validate / export
   - document → 写入用户指定路径
5. 未落实前：不要因聊天内容改 brief.json
```

## 原则

- **商量 ≠ 契约**：对话可自由；文件只在落实后出现。  
- **LLM 重填充**：落实 brief 时由模型补全大量英文细节；用户负责方向与纠错。  
- **无工具环**：这些 skill 不要求 CLI；跑 pipeline 仍用斜杠命令或外部 Agent。

## 与 brief-brainstorm.md

`brief-brainstorm.md` 是早期「每轮填表 / 每问更新 draft」模型。  
新产品行为以 **host-chat + commit-*** 为准；旧 skill 可保留给 CLI `brief brainstorm` 直到宿主切换完成。
