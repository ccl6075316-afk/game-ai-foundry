# Game AI Foundry — AI Agent Handoff

> **读者**：后续接手的 AI Agent / 自动化编排器（中文操作手册）。  
> **侧重**：仓库结构、**brief 字段**、CLI 速查、抠图/动画铁律、配置。  
> **不写**：设计 vs 施工方法论、六角色边界、里程碑进度 — 分别见 [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)、[`AGENT-ROUTING.md`](AGENT-ROUTING.md)、[`ROADMAP.md`](../ROADMAP.md)。  
> **索引**：[`docs/README.md`](README.md)

---

## 0. 执行摘要

```text
brief export（冻结）→ prompt craft → pipeline plan/run → godot assemble → dev-context → C# 玩法
```

- **契约**：export 后只读 `brief.json` + `plans/` + manifest；聊天记忆无效（§1）。
- **批量资产**：用 `pipeline run`，不要逐步 Hermes terminal（[`pipeline-schedule.md`](../resources/skills/orchestrator/pipeline-schedule.md)）。
- **迭代改需求**：流程见 ITERATIVE §3.2；今天 = 改 brief → `plan --merge` → `run`。

---

## 1. 操作流水线（CLI 视角）

| 步 | 执行者 | 命令 / 产物 |
|----|--------|-------------|
| 1 | orchestrator | `brief brainstorm` → `brief export` → `brief_meta` |
| 2 | prompt-crafter | `prompt craft` → `plans/*.json`（runner 默认跳过，加 `--run-prompts`） |
| 3 | **`pipeline run`** | `pipeline plan` → manifest；`run --jobs N` → `output/` + `assets-manifest.json` |
| 4 | godot-assembler | manifest 内 `godot.assemble` 或 `godot assemble` |
| 5 | godot-developer | `godot dev-context` → `plans/dev_*.json` → 写 C# |
| 异常 | orchestrator | `exit 2` → 改 plan/brief → `pipeline reset` → 再 `run` |

角色分工表 → [`AGENT-ROUTING.md`](AGENT-ROUTING.md)。

### 1.1 Brief 门禁

- 多轮对话 **仅** brainstorm；export 后下游只读文件。
- 改素材/玩法 → 改 brief → `pipeline plan`（必要时 `--merge`），不能靠会话记忆。

---

## 2. 项目结构

```
game-ai-foundry/
├── cli/                    # gamefactory 入口（在此目录执行命令）
├── resources/
│   ├── asset-brief.example.json   # git 内唯一示例 brief
│   └── skills/                    # 六角色 skill 源（hermes sync 生成包）
├── pipeline/ plans/ output/ games/   # 本地运行产物（gitignored）
└── docs/                   # 文档索引 → docs/README.md
```

**入口**：`cd cli && python gamefactory.py --help`

---

## 3. Brief 契约（export 门禁）

> 设计意图 vs 施工规格的 **概念拆分**见 ITERATIVE §1；下列为 **当前 `brief.json` 校验规则**。

### `project` 必填（P0 玩法）

| 字段 | 说明 |
|------|------|
| `title`, `description`, `art_direction`, `dimension` | 基础 |
| `genre` | 如 `2d_platformer` |
| `gameplay_loop`, `session_goal` | 英文；godot-developer 完成标准 |
| `player_asset` | 有 player 向 asset 时必填 |
| `controls` | 动作 → 按键 |
| `viewport` | `{ width, height }` |
| `camera` | 平台类 genre 必填 |

### `project` 可选（P1）

`visual_reference`、`project.visual_target{}`、`hud[]`（有 `ui_element` 素材时必填）

#### 尺寸契约（godogen ASSETS.md Size 列）

**权威字段**：`assets[].display_size: { width, height }` = 在 `project.viewport` 里**看起来多大**（游戏内像素）。

| 层级 | 字段 | 含义 |
|------|------|------|
| 北极星 | `visual_reference` | 整屏构图 + 物体屏上比例（不写进 display_size） |
| 游戏内 | `display_size` | 玩家眼里多大 → assemble **缩放到此**，Godot scale=1 |
| 生成 | handoff `image_size` | API 出图分辨率（按 display 推导，勿手填） |

兼容旧 brief：`"128x128 px"` 字符串仍可 parse。

**校验**：同 `reference_asset` 家族 / 同 `animation_graphs` 角色 → `display_size` 必须一致。

### `assets[]` 每项

`name`, `type`, `usage`, `usage_description`, `display_size`, `generate_method`；音频见 `type: audio`；视差见 `parallax_order` / `scroll_factor`。

### `animation_graphs[]`

多 clip 角色必填；`from`/`to`/`then`/`bidirectional`。

**校验**：`python gamefactory.py brief validate --brief ../resources/asset-brief.example.json`

完整示例 → [`resources/asset-brief.example.json`](../resources/asset-brief.example.json)

---

## 4. 抠图 + 动画帧（必读）

| 来源 | 工具 | 说明 |
|------|------|------|
| 静图 | `image remove-bg --mode color` | 纯白底；~0.1s |
| 视频帧 | `video matte-frames --engine ai` | rembg；**禁止**静图色键 |

- 禁止用拆帧前几帧当 idle；禁止用 `*_raw.png` 当游戏站立图
- `video split-frames` 默认 trim 片头过渡；idle 用独立 `*_nobg.png`

---

## 5. 命令速查

```bash
cd cli

# Brief
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py brief export --brief ../resources/my-game-brief.json

# Visual Target（brief 定稿后：prompt craft → image generate → pick）
python gamefactory.py prompt craft-visual-target --brief ../resources/my-game-brief.json --variant a -o ../plans/visual_target_a.json
python gamefactory.py image generate --plan-file ../plans/visual_target_a.json -o ../output/my-game/visual-target/candidate_a.png --no-validate
python gamefactory.py brief visual-target generate --brief ../resources/my-game-brief.json --candidates 3
python gamefactory.py brief visual-target list --brief ../resources/my-game-brief.json
python gamefactory.py brief visual-target pick --brief ../resources/my-game-brief.json --id b

# Pipeline（推荐路径）
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4
python gamefactory.py pipeline status --manifest ../pipeline/asset-brief.example.json

# 单资产调试
python gamefactory.py prompt craft --brief ../resources/asset-brief.example.json --asset knight -o ../plans/knight.json
python gamefactory.py image generate --plan-file ../plans/knight.json -o ../output/asset-brief.example/knight_raw.png --validate

# Godot
python gamefactory.py godot assemble --assemble-file ../plans/godot_asset-brief.example.json
python gamefactory.py godot dev-context \
  --brief ../resources/asset-brief.example.json \
  --project ../games/asset-brief.example \
  -o ../plans/dev_asset-brief.example.json
python gamefactory.py godot validate --project ../games/asset-brief.example

# Tester（Pass 5 验收）
python gamefactory.py test plan --brief ../resources/asset-brief.example.json
python gamefactory.py test play \
  --project ../games/asset-brief.example \
  --plan ../plans/playtest_asset-brief.example.json \
  --brief ../resources/asset-brief.example.json

# 环境
python gamefactory.py agents show
python gamefactory.py doctor --json
```

本地 demo brief（`test-brief-*`、`magic-prince-brief.json`、`tests/fixtures/`）均为 **gitignored**；clone 后用 `asset-brief.example.json`。

---

## 6. 配置

模板：`resources/config.example.json` → `~/.gamefactory/config.json`

- OpenRouter：常需代理 `127.0.0.1:7897`
- 视频 AI 抠图：`pip install "rembg[cpu]"`

---

## 7. 操作原则

1. 只读 brief — 不补猜未写入 JSON 的内容  
2. 生图 `exit 2` → prompt-crafter，不要 trim/remove-bg  
3. 视频帧只用 `video matte-frames`  
4. Pass 3 = assemble；Pass 4 = dev-context 再写 C#  
5. 省钱默认：mini + 480p + 4s + 8 帧 + no audio  
6. godot-developer 不扩 scope（ITERATIVE §8）

---

## 8. 代码索引

| 用途 | 路径 |
|------|------|
| Brief 校验 | `cli/brief.py` |
| Pipeline DAG / runner | `cli/pipeline_manifest.py`, `cli/pipeline_runner.py` |
| Godot handoff | `cli/godot_dev.py`, `cli/godot_assemble.py` |
| Tester / screenshot | `cli/test_analysis.py`, `cli/godot_screenshot.py` |
| Runner 阶段说明 | `resources/skills/orchestrator/pipeline-schedule.md` |

---

*文档版本：2026-06-25*
