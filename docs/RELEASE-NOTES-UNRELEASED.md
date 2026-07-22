# Unreleased — 下一版 Release Notes 草稿

相对当前已打标签的 [`v0.0.6`](RELEASE-NOTES-0.0.6.md)。打版时把本节并入正式 `RELEASE-NOTES-x.y.z.md`。

## Breaking：`icon_kit` 产物布局

- **不再**生成一张网格 sheet 再 `image slice` 成 `*_0.png` / `*_1.png`。
- Pipeline 对 `items[]` **逐项** `image.generate` → trim → remove-bg；产物名为  
  `{kit_id}__{item_slug}_raw.png` / `_nobg.png`（slug 来自 item **`id`**）。
- 旧工程若依赖格子序号切图路径，需改 brief / Godot 引用到上述路径。
- 配置：`image.bulk_model`（GUI：**批量单图 model（bulk）**）；未配则回退 `image.model`。

## 增强：`items` 对象 + 玩法绑定

- `items` 仍可为字符串；亦可为  
  `{ "id": "health_potion", "label": "red potion", "usage": "pickup", "usage_description": "…" }`。
- `production derive` 写出 `production_doc.collectible_items[]`（`item_id` / `nobg_path_hint` / `usage`），供程序员按 id 接线 pickup / UI。
- 显式对象 `id` 重复 → brief 校验失败；纯字符串重复仍用 slug `_2` 后缀。

## 已合入但未进 0.0.6 笔记的相关能力（摘要）

- 执行器安全旋钮 + Cursor/Hermes ACP + Codex app-server 审批卡  
- `style_group` / `art_tokens` / DocsPreview 风格只读标注  
- GUI `image.bulk_model` 字段  
