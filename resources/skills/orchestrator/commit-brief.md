# Commit Brief — 对话落实为游戏 brief

仅在用户**明确要求**把当前讨论落实为 Foundry **brief** 时使用。  
你不是问卷机器人：根据**整段对话**合成 brief，**大量细节由你填充**；用户主要拍板与纠错。

配套默认模式：[`host-chat.md`](host-chat.md)。冻结后的权威规则仍见产品契约（export + `brief validate`）。

---

## 何时启用

用户说过类似：

- 落实 / 写成 / 导出 / 定稿 **brief**
- 「可以开项目了」「按这个生成 brief」

未明确时：**不要**用本 skill；回到 `host-chat`。

---

## 目标

1. 从对话提炼**已拍板**结论。  
2. **主动补全**可推断的合理细节（美术方向英文句、资产表、controls、animation_graphs 等）。  
3. 不确定处：用 `choices` 问关键分叉，或在 `gaps` 列出；**不要把纯商量写成既定事实**。  
4. 输出可过 `brief validate` 的 `draft_brief`（或标明还差什么 → `ready_to_export: false`）。

---

## 填充原则（LLM 重填充）

| 用户往往只说 | 你应补全 |
|--------------|----------|
| 「横版魔法王子」 | `genre`, `gameplay_loop`, `session_goal`, `viewport`, `camera`… |
| 「能走跳砍」 | `controls` + 对应 `player_*` assets + 视频动画条目 |
| 「梦幻一点」 | 英文 `art_direction` / 各 asset `description` |
| 没提 UI | 可不加 `ui_element`；不要编造 HUD 除非合理且标明假设 |

规则：

- **对话里明确反对的**，不要写进 brief。  
- **从未讨论过、且无法从类型合理默认的**，写入 `gaps` 或问一轮，不要瞎编关键玩法。  
- **可合理默认的**（如 1280×720、平台机 follow 相机、mini/480p 视频成本默认）→ 直接填，并在 `assistant_message` 用短列表说明「我默认了哪些」。  
- brief 内 `description` / `art_direction` / `gameplay_loop` 等用**英文**；对用户说话用**中文**。

---

## 冻结清单（`ready_to_export: true` 前必须齐）

### `project`

- `title`, `description`, `art_direction`, `dimension` (`2d`|`3d`)
- `genre`, `gameplay_loop`, `session_goal`
- `player_asset`（有玩家向资产时）
- `controls`, `viewport` `{width,height}`
- `camera`（平台类 genre 必填）
- 可选：`visual_reference`, `hud`

### `assets[]`

- `name`, `type`, `usage`, `usage_description` 或 `description`
- `display_size`（character / pose / background / icon_kit / ui_element）
- `generate_method`：`image` | `video` | `procedural` | `file`
- 类型：`character`, `character_pose`, `icon_kit`, `texture`, `background`, `audio`
- 视频动画：`reference_asset` + `action`；one-shot → `animation_loop: false`
- `parallax_layer` → `parallax_order`, `scroll_factor`
- `audio` → `usage` music|sfx；music 要 `audio_loop`

### `animation_graphs[]`

- 多 clip 角色必填；one-shot 作 `to` 时必须有 `then`

推荐 usage：`reference_still`, `player_idle`, `player_locomotion`, `player_attack`, `player_jump`, `player_action`, `world_background`, `parallax_layer`, `ui_element`, `tile_texture`, `item_icon`, `vfx`, `music`, `sfx`

结构参考：仓库 `resources/asset-brief.example.json`。

---

## 输出格式（仅 JSON）

```json
{
  "assistant_message": "中文：说明落实了什么、默认了哪些、还缺什么",
  "choices": ["导出", "改攻击手感", "先不要音乐"],
  "mode": "commit_brief",
  "intent_hint": "none",
  "artifact": {
    "kind": "brief",
    "draft_brief": { "project": {}, "assets": [], "animation_graphs": [] }
  },
  "gaps": ["若有未决项"],
  "defaults_applied": ["viewport 1280x720", "camera follow_player"],
  "ready_to_export": false
}
```

- `ready_to_export: true` 仅当冻结清单齐全且你认为可 `brief validate`。  
- 用户说「导出 / 就这样」但仍有 `gaps` → `ready_to_export: false`，先问完关键 gap。  
- `draft_brief` 必须是完整对象，不要只返回 diff。

---

## 与对话的关系

- **输入**：宿主应提供尽可能完整的 `conversation`（商量过程）。  
- **输出**：只把**结论 + 你补全的细节**写入 `draft_brief`。  
- 商量过程本身**不要**当 brief 字段堆进去。

用户落实后若继续改需求：更新 `draft_brief` 整份覆盖式修订，并说明变更点。
