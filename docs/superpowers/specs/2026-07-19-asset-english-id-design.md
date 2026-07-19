# 资产英文 id（路径）设计

**日期：** 2026-07-19  
**状态：** 已实现  
**已定决策：** 方案 1 + 策略 A

## 目标

避免中文文件名导致的终端乱码、路径编码与工具兼容问题。Brief 里仍可用中文 `name`（对话 / HUD / `reference_asset`），**磁盘产物与 pipeline task 前缀一律英文 `id`**。

## 非目标

- 不自动拼音转写
- 不强制把 HUD / 对话改成英文
- 不自动搬迁已有中文文件名产物（缺文件则按现有逻辑重生成）

## Brief 字段

每个 `assets[]` 项：

| 字段 | 必填 | 规则 |
|------|------|------|
| `name` | 是 | 可中文；工程内唯一；引用（HUD、`reference_asset`、`player_asset`）仍用 `name` |
| `id` | **是** | `^[a-z][a-z0-9_]*$`；工程内唯一；仅 ASCII |

`pipeline plan` / `brief validate` / `brief export`：缺 `id`、非法字符、或重复 → **报错**（策略 A，不静默生成）。

## 产物路径

相对 `output/`、`plans/`，一律用 `id`：

- `plans/{id}.json`
- `{id}_raw.png` / `_trimmed.png` / `_nobg.png` / `_tiles/`
- `{id}.mp4` / `{id}_frames/` / `{id}_nobg/`

## Pipeline

- task id：`{id}.image.generate`（不再用中文 name）
- `task.asset`：保留 brief `name`（看板可读）
- `task.asset_id`：英文 id（路径解析）
- `reference_asset`：仍写中文 `name`；解析时查表 → 对应资产的 `id` 再拼路径

## 文档与示例

- 更新 `docs/AI-HANDOFF.md`：`assets[]` 说明补 `id`
- 示例 brief（`resources/asset-brief.example.json` 等）补英文 `id`（如 `knight`）

## 迁移：black-whistle

为现有资产补 `id`，然后 `pipeline plan` 重建 manifest。建议映射：

| name | id |
|------|-----|
| 比赛场地 | pitch |
| 裁判 | referee |
| 裁判_跑动 | referee_run |
| 裁判_吹哨 | referee_whistle |
| 裁判_举手 | referee_raise_hand |
| 球员_普通 | player |
| 球员_跑动 | player_run |
| 球员_射门 | player_shoot |
| 球员_摔倒 | player_fall |
| 球员_庆祝 | player_celebrate |
| 球员_争顶 | player_header |
| 球员_铲球 | player_tackle |
| 球员特写_拉扯 | player_closeup_pull |
| 球员特写_冲撞 | player_closeup_clash |
| 球员特写_假摔表演 | player_closeup_dive |
| 越位线_裁判视角 | offside_line |
| 判罚事件UI | foul_event_ui |
| 判罚事件反馈图标 | foul_feedback_icons |
| 裁判表情图标 | referee_emotion_icons |
| UI面板 | ui_panel |
| 犯规程度进度条UI | foul_severity_bar |
| 球出界_角球_球门球指示箭头 | ball_out_arrows |

（实际 name 以 brief 为准；实现时按 brief 逐条写入。）

## 验收

1. 无 `id` 的 brief → `brief validate` / `pipeline plan` 失败并提示缺哪些 name  
2. 有 `id` → 产物路径无非 ASCII  
3. `reference_asset` 中文引用仍能解析到英文路径  
4. black-whistle replan 后 task id 为英文；删产物后可重生成到英文路径  
