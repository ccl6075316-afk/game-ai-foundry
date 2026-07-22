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
| 「这几个角色要同一画风」 | 保守写 `style_group` + `style_anchor`（见下）；无明确关系则不建组 |
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
- 可选：`hud`；`visual_reference` **导出时留空**（仅图片路径，由 visual-target pick 写入；禁止风格文案）；`art_tokens`（结构化风格硬锁，与 `art_direction` 并存，见下）

**`art_tokens`（可选）** — 仅在用户给出**具体、可执行**的风格锁（配色 hex、线宽、禁止项、剪影比例等）时**保守填写**；模糊或仅散文描述 → 只写 `art_direction`，省略本字段。键均为**英文**字符串：

| 键 | 类型 | 说明 |
|----|------|------|
| `line` | string | 线宽 / 描边风格，如 `clean 2px outline` |
| `palette` | string \| string[] | 主色或 hex 列表 |
| `forbid` | string[] | 生成器必须避开的风格/效果 |
| `silhouette` | string | 剪影 / 头身比等硬约束 |

`art_direction` 仍必填，负责 mood / 氛围散文；有 `art_tokens` 时 prompt-crafter 优先把 tokens 落实为 `style_lock` 硬锁。

### `assets[]`

- `name`, `id`（英文 slug，必填）, `type`, `usage`, `usage_description` 或 `description`
- `display_size`（character / pose / background / icon_kit / ui_element）
- `generate_method`：`image` | `video` | `procedural` | `file`
- 类型：`character`, `character_pose`, `icon_kit`, `texture`, `background`, `audio`
- 视频动画：`reference_asset` + `action`；one-shot → `animation_loop: false`
- `parallax_layer` → `parallax_order`, `scroll_factor`
- `audio` → `usage` music|sfx；music 要 `audio_loop`
- **产物路径只用 `id`**（如 `plans/referee.json`、`referee_raw.png`）；`name` 可中文
- **风格组（可选）**：`style_group`、`style_anchor_kind`（`asset`|`visual_reference`）、`style_anchor`、`use_style_img2img`（缺省 true，`false` 退回纯文生图）

### 风格组 — 保守标定

**仅在对话有明确同族 / 从属 / 套图关系时**写入 `style_group`；**禁止**把所有 still 默认塞进一个「项目总组」。

| 字段 | 说明 |
|------|------|
| `style_group` | 共享组名；无关系 → 省略 |
| `style_anchor_kind` | `asset`（默认）或 `visual_reference` |
| `style_anchor` | kind=`asset` → 锚点 `name`/`id`；kind=`visual_reference` → 省略，用 `project.visual_reference` |
| `use_style_img2img` | 缺省 **true**；设 `false` 对该资产 opt-out |

- **正交于 `reference_asset`**：pose / 视频动作族仍用 `reference_asset`；风格组只管 still 的 img2img，二者不互替。
- **视频优先**：video 任务 / 动画 clip 参考图规则不变（跟 `reference_asset`）；其依赖的初始 still 可先走风格 img2img。
- **北极星作锚**：仅 `style_anchor_kind: visual_reference` 时把 `project.visual_reference` 当风格参考；否则默认 kind=`asset`，锚 = 组内主资产 raw。

### `animation_graphs[]`

完整契约见 [`brief-animation-graphs.md`](brief-animation-graphs.md)（宿主会注入 system）。

- 多 clip 角色必填；`from`/`to`/`then`/`default_clip` = **Godot clip 名**（资产名后缀，不是全名）
- **禁止** `states[]`
- one-shot 作 `to` 时必须有 `then`

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
