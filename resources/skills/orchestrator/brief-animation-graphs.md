# Brief `animation_graphs` — clip 名契约（Foundry）

写 / 改 `draft_brief.animation_graphs` 时必须遵守本 skill。  
校验实现：`cli/brief.py` → `resolve_animation_name` / `audit_animation_graphs`。  
宿主会先做代码级 remap；你仍须输出**已对齐**的图，不要发明第二套 schema。

---

## 禁止（常见幻觉）

| 禁止 | 原因 |
|------|------|
| `states[]` / `states[].id` / `states[].clip` | Foundry brief **没有** states；只有 `transitions` |
| `from`/`to`/`then` 写资产全名（如 `球员_普通_跑动`） | 图里必须用 **Godot clip 名**（通常是后缀 `跑动`） |
| 自创 clip（资产里没有对应条目） | 校验会报 `unknown … clip` |
| 把中文「状态 id」当 clip | 除非某资产的 `animation_name` 或推导名正好是该字符串 |

---

## Clip 名怎么来（唯一真相）

对每个角色 `character_asset = C`，合法 clip 集合由 `assets[]` 推导：

1. 静图角色 `name == C`（无 `action`）→ clip **`idle`**（除非显式 `animation_name`）
2. 视频动画：`reference_asset == C` 且 `animation_method: "video"`（或等价 generate video）
3. 单条资产的 clip 名 = `resolve_animation_name`：
   - 有 `animation_name` → 用它
   - 否则若 `name` 形如 `{C}_{suffix}` → clip = **`suffix`**
   - 否则静图 → `idle`；其它 → `name`

**例**

| assets.name | reference_asset | → clip |
|-------------|-----------------|--------|
| `球员_普通` | （静图） | `idle` |
| `球员_普通_跑动` | `球员_普通` | `跑动` |
| `球员_普通_倒地` | `球员_普通` | `倒地` |
| `hero_walk` | `hero` | `walk` |

图里必须写：`"from":"idle","to":"跑动"`，**不要**写 `"to":"球员_普通_跑动"`。

---

## `animation_graphs[]` 形状

```json
{
  "character_asset": "球员_普通",
  "default_clip": "idle",
  "summary": "可选说明",
  "transitions": [
    { "from": "idle", "to": "跑动", "bidirectional": true },
    { "from": "跑动", "to": "倒地", "then": "idle" }
  ]
}
```

规则：

- 同一角色有 **2+ clip** 时必须有一条 `character_asset` 对应该角色的图。
- `default_clip` / `from` / `to` / `then` ∈ 该角色合法 clip 集合。
- `animation_loop: false`（one-shot）作为 `to` 时 **必须** 有 `then`（播完回到哪个 clip，常用 `idle`）。
-  idle ↔ 移动 可用 `"bidirectional": true`。
- **不要**输出 `states`。

缺动画时：先补 `assets[]`（video + `reference_asset` + `action`），再写 transition；不要只改图里的字符串幻想出 clip。

---

## 自动修 / 对齐 gaps 时

若宿主注入了「资产 → clip」表或 `unknown … clip` 错误：

1. 只改 `transitions` / `default_clip` / 必要的 `assets[]`。
2. 把错误 token **改成表里的 clip 列**，或删掉无法映射的边。
3. 删除任何 `states`。
4. 输出**完整** `draft_brief`，不要只给 graph 碎片。

## `project.hud`（ui_element）

每个 `usage: "ui_element"` 的资产必须在 `project.hud` 有一条：

```json
{ "asset": "判罚事件UI", "anchor": "top_right", "description": "…" }
```

`asset` 必须与 `assets[].name` **完全一致**。宿主会代码补齐缺失条目；你仍应在草案里写上，不要只口头声称已改。
