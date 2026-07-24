# Unreleased — 下一版 Release Notes 草稿

相对当前已打标签的 [`v0.0.6`](RELEASE-NOTES-0.0.6.md)。打版时把本节并入正式 `RELEASE-NOTES-x.y.z.md`。

## Breaking：`icon_kit` 产物布局

- **不再**生成一张网格 sheet 再 `image slice` 成 `*_0.png` / `*_1.png`。
- Pipeline 对 `items[]` **逐项** `image.generate` → trim → remove-bg；产物名为  
  `{kit_id}__{item_slug}_raw.png` / `_nobg.png`（slug 来自 item **`id`**）。
- 旧工程若依赖格子序号切图路径，需改 brief / Godot 引用到上述路径。
- 配置：`image.bulk_model`（GUI：**批量 model**）；未配则回退 `image.model`。
- 配置：`image.bulk_provider`（GUI：**批量 Provider**）；未配则回退 `image.provider`；与主图可各用不同 `provider_accounts` Key/Base。
- 配置：顶层 `proxy`（GUI Provider 页 **网络**）；保存时迁出并清除旧 `host.proxy` / `image.proxy`。

## 增强：风格看板 chips + kit 套内 img2img

- Pipeline 看板按资产组头只读展示 `style_group` / 锚 / `use_style_img2img`（会话 brief 草稿；不写回）。
- `icon_kit` 在 N≥2 且未 `use_style_img2img: false` 时：首项文生图，其余 `--reference-image` 跟首项 raw（仍 bulk 模型；不走跨资产 `style_group`）。

- `items` 仍可为字符串；亦可为  
  `{ "id": "health_potion", "label": "red potion", "usage": "pickup", "usage_description": "…" }`。
- `production derive` 写出 `production_doc.collectible_items[]`（`item_id` / `nobg_path_hint` / `usage`），供程序员按 id 接线 pickup / UI。
- 显式对象 `id` 重复 → brief 校验失败；纯字符串重复仍用 slug `_2` 后缀。

## 增强：资产审查表

- GUI 右侧 **资产** 面板：读 `assets-manifest.json` 展示缩略图与 usage 映射；行内 **采纳 / 重生成 / 本地替换**。
- 软 `review` 标注（`pending` / `accepted` / `replaced`）写入 manifest，**不阻塞** assemble 或程序员派工。
- `icon_kit` 按 item 分行、各行独立 review；CLI `assets review list|accept|replace|regenerate-plan`（GUI 经 Electron IPC 调用）。

## 已合入但未进 0.0.6 笔记的相关能力（摘要）

- 执行器安全旋钮 + Cursor/Hermes ACP + Codex app-server 审批卡  
- `style_group` / `art_tokens` / DocsPreview 风格只读标注  
- GUI `image.bulk_model` / `bulk_provider`；顶层 `proxy`
- `content_class` / `project.view` / 结构化 prompt craft / 分 skill；`prop_stateful` 多状态 img2img
- `production_doc.layout`：regions + placements（规则启发式，非 vision）

发版待办与是否够格打 0.0.7：见 [`HANDOFF-TODO-0.0.7.md`](HANDOFF-TODO-0.0.7.md)。
