# 工程 Spec：icon_kit items 对象化（id + usage）

## 执行元数据

- **Status**：confirmed（用户「135」含本项）
- **Workflow Stage**：implement
- **Created**：2026-07-23
- **Requirements Source**：[`2026-07-22-icon-kit-single-object-design.md`](2026-07-22-icon-kit-single-object-design.md) Deferred「items 对象级 usage」；用户优先级 1
- **Deferred（仍不做）**：kit 内 style 锚 + bulk img2img；视觉认格

## 目标

1. `items[]` 支持 **string** 或 **`{id, label?, usage?, usage_description?}`**；string ≡ `{id: s, label: s}`。
2. 文件/任务键 slug 来自 **`id`**（非展示 label）；`--item` 可匹配 id 或 label。
3. Production 导出 **per-item 绑定表**（kit + item_id + slug + usage + nobg 提示路径），供 Godot/程序员按 id 接线。
4. assets-manifest 的 kit brief 带 `items`；stage 记录带 `kit_item_id` / slug（有则）。

## 非目标

- 强制所有 brief 改成对象（旧 string[] 仍合法）。
- 改 assembler 自动摆 pickup 场景（蓝图绑定即可）。
- kit 级 style img2img。

## Brief 契约

| 形态 | 示例 |
|------|------|
| string | `"potion"` |
| object | `{"id":"health_potion","label":"red potion","usage":"pickup","usage_description":"…"}` |

- `id` 必填（object 可用 `label`/`name` 回退生成 id）。
- 显式 `id` 重复 → 校验错误；纯 string 重复仍靠 slug `_2` 后缀（兼容一期）。
- kit 级 `usage` 仍为整套默认；item 级 `usage` 覆盖绑定表中的该项。

## 成功标准

1. 单测：parse 混合 items；slug 跟 id；production 含 collectible_items。
2. 示例 brief 至少一项为对象。
3. skill / AI-HANDOFF / GUI-CONFIG 一句说明。
