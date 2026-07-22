# 工程 Spec：Phase 3 — GUI 风格关系只读标注

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：code（executed）
- **Created**：2026-07-22
- **Updated**：2026-07-22（T1+T2 落地；未 commit）
- **Confirmed By**：user「确认」（Spec + plan）
- **Source Of Truth Until**：代码 + DocsPreview；后续以 review/commit 为准
- **Requirements Source**：终局 C Phase 3（[`2026-07-22-style-ref-enhance.md`](2026-07-22-style-ref-enhance.md)）；用户选择 A/D/A/A/B
- **Background Inputs**：Phase1/2 已落地（`dfcbf5e`）；DocsPreviewPanel；solutions style-group 栈
- **Compounded Knowledge**：接线真相在 CLI；GUI 不复刻 resolve

## 工程理解

在 GUI **Docs 预览**中，对 Brief（会话草稿与可解析的磁盘 brief JSON）**只读**展示：

1. 项目级：`art_direction` 下的 **`art_tokens`**（有则展示）  
2. 资产级：`style_group` / `style_anchor_kind` / `style_anchor` / `identity_anchor` / `use_style_img2img`（有则标）

不写回；不派生 resolve；看板延后。

## 目标

1. 共享 `formatBriefDocument` — **Code Status**：done（`briefPreviewFormat.ts`）  
2. 会话草稿 — **Code Status**：done  
3. 磁盘 brief JSON — **Code Status**：done（`tryFormatBriefJsonText`）  
4. 中英标签 — **Code Status**：done  
5. 旧 brief 无噪音 — **Code Status**：done  

## 非目标

- 可编辑 / 写回 — **Code Status**：not applicable  
- 看板标注 — **Code Status**：not applicable（延后）  
- 前端 resolve — **Code Status**：not applicable  

## 方案选择

| 决策 | 选择 |
|------|------|
| 深度 | 只读 |
| 表面 | DocsPreview；看板延后 |
| art_tokens | 项目级只读本期做 |
| 字段 vs 派生 | 仅声明 |
| 覆盖 | 会话 + 磁盘可解析 brief |

## 成功标准

1. style 资产行可见 — **Code Status**：done（5 单测）  
2. art_tokens 块 — **Code Status**：done  
3. 磁盘示例可结构化 — **Code Status**：done  
4. 无风格字段无噪音 — **Code Status**：done  
5. 无写回/无看板 — **Code Status**：done  

## 决策账本

| 已确认 | 只读；DocsPreview；tokens；声明字段；草稿+磁盘 |

## Resume

实现完成（pause）。下一步：`/anvil:review` + commit（可连同未提交 compound wiki）。
