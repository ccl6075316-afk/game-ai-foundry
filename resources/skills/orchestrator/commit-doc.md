# Commit Doc — 对话落实为普通文档

仅在用户**明确要求**把讨论整理成**文档**（非 Foundry brief 契约）时使用。  
用于：设计说明、技术调研、方案对比、会议纪要、实现笔记等。

游戏管线用的 **brief.json** 请用 [`commit-brief.md`](commit-brief.md)。  
默认闲聊用 [`host-chat.md`](host-chat.md)。

---

## 何时启用

- 「整理成文档 / markdown / 设计说明 / 方案书」
- 「写个纪要」「输出一份可保存的说明」

未明确时回到 `host-chat`。

---

## 规则

1. 根据对话提炼结构清晰的文档；可主动补章节（背景、目标、方案、风险、下一步）。  
2. 标注哪些是**已拍板**，哪些是**待定 / 假设**。  
3. 不要输出 Foundry `draft_brief`，除非用户改口要 brief（那时 `intent_hint: commit_brief`）。  
4. 对用户说明用中文；文档正文默认中文（用户要英文则英文）。

---

## 输出格式（仅 JSON）

```json
{
  "assistant_message": "中文短说明：文档已生成，可保存或继续改",
  "choices": ["保存", "加一节风险", "改成英文"],
  "mode": "commit_doc",
  "intent_hint": "none",
  "artifact": {
    "kind": "document",
    "title": "文档标题",
    "format": "markdown",
    "body": "# 标题\n\n……完整 markdown ……"
  },
  "gaps": [],
  "ready_to_export": true
}
```

| 字段 | 说明 |
|------|------|
| `artifact.kind` | 固定 `document` |
| `artifact.body` | 完整文档，不要只给大纲（除非用户只要大纲） |
| `ready_to_export` | 内容可保存即为 `true`；若缺关键信息则为 `false` 并列出 `gaps` |
