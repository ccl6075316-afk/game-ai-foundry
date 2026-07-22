# 工程 Spec：风格看板只读 chips + icon_kit 套内风格 img2img

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：implement
- **Updated**：2026-07-23（用户 Spec「确认」后开工）
- **Created**：2026-07-23
- **Confirmed By**：用户 A1 + B3 + 「确认」
- **Requirements Source**：用户「都要」；看板深度 A1；kit 默认 B3
- **Background Inputs**：[`2026-07-22-style-gui-readonly.md`](../../anvil/brainstorms/2026-07-22-style-gui-readonly.md)（Docs 只读已做、看板延后）；[`2026-07-23-icon-kit-item-objects-design.md`](2026-07-23-icon-kit-item-objects-design.md) Deferred kit style；explore 结论：禁令在类型白名单非 audit
- **Deferred**：看板写回 / toggle；跨资产 `style_group` 挂 icon_kit；可配置非首项为锚

## 选型账本

| 决策 | 选择 |
|------|------|
| 看板 | **A1** 只读 chips，不写回 brief |
| Kit 风格 | **B3** N≥2 默认开；`use_style_img2img: false` 整套关 |
| Kit 接线 | **kit-internal**（改 `_icon_kit_item_tasks`），不改 `STYLE_IMG2IMG_ALLOWED_TYPES` |
| 锚 | **items[0]**（按 brief 顺序） |

## 目标

### A — 风格看板只读

1. Pipeline 看板按 `task.asset` 关联 brief 资产行，有则展示：`style_group`、`style_anchor_kind` / `style_anchor`、`identity_anchor`、`use_style_img2img`（声明字段，不 resolve）。
2. 无风格字段 → 无噪音。
3. DocsPreview 行为不变；不写回 brief；不改 pipeline。

### B — icon_kit 套内风格

1. `type: icon_kit` 且 `len(items) ≥ 2` 且 `use_style_img2img` 不是 `false`：  
   - item0：纯文生图（无 `--reference-image`）  
   - item1..：`--reference-image` → item0 的 `*_raw.png`；`depends_on` 含 item0 的 `image.generate`
2. 单 item，或 `use_style_img2img: false`：全部纯文生图（与今日一致）。
3. **不**把 `ICON_KIT` 加入跨资产 style img2img 白名单；kit 挂 `style_group` 仍不因此走跨资产 follower 路径。
4. 模型档仍为 bulk（`image.bulk_model`）；风格只加 reference，不改 tier。

## 非目标

- 看板可编辑 / 写回 `use_style_img2img`
- 资产画廊式看板（仍是 task DAG + 组头 chips）
- kit 用 `style_group` / `style_anchor` 指向另一资产
- 视觉认格、sheet 逃生舱
- Godot 自动摆 pickup

## 架构

```text
A: briefDraft.assets[] ──join──► TaskList 按 task.asset 组头 chips
B: items[0] generate ──raw──► items[1..] generate --reference-image
```

## Brief / 行为契约

| 字段 | Kit 套内语义 |
|------|----------------|
| `use_style_img2img` | 缺省 / `true` / 省略 → N≥2 时套内跟锚；显式 `false` → 全关 |
| `style_group` 等 | 跨资产配方仍忽略 icon_kit；看板若 brief 写了可只读展示，**不**驱动 kit 套内 ref |
| `items[0]` | 套内风格锚（身份仍用各 item 的 id/label） |

## GUI（A）

- 改 `BoardPanel` / `TaskList`（或小组头组件）：传入 brief assets（会话草稿优先）。
- Chip 文案可复用 / 抽离 `briefPreviewFormat` 的字段集合；中英标签与 Docs 对齐即可。
- 无 brief → 不显示风格 chips（仅任务表）。

## CLI（B）

- 主改：`cli/pipeline_manifest.py` → `_icon_kit_item_tasks`
- 可选小 helper：`should_use_kit_style_img2img(spec) -> bool`
- 单测：N=2 默认有 ref + dep；`use_style_img2img: false` 无 ref；N=1 不变；角色 style_group 回归绿
- 文档：`AI-HANDOFF.md`、`asset-gen.md`、icon-kit Spec Deferred 划掉本项

## 成功标准

1. 看板上带 `style_group` 的资产组头可见 chip；无字段无噪音。
2. Kit N≥2 默认：非首项 command 含 `--reference-image` 且依赖首项 generate。
3. Kit `use_style_img2img: false` 或 N=1：无上述 ref。
4. `STYLE_IMG2IMG_ALLOWED_TYPES` 仍不含 `icon_kit`；角色 follower 测例仍过。
5. 无 brief 写回。

## Resume

用户确认设计后：写本 Spec → 用户过目 Spec → plan/实现 A 与 B（可同 PR 或先 B 后 A）。
