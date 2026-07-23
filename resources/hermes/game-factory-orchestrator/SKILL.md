---
name: game-factory-orchestrator
description: "Orchestrate Game AI Foundry: brief → seven agents → gamefactory CLI."
version: 1.0.0
author: Game AI Foundry
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Game-Dev, Assets, Pipeline, Orchestrator, Godot]
    related_skills: [game-factory-prompt-crafter, game-factory-image-generator, game-factory-video-generator, game-factory-godot-assembler, game-factory-godot-developer, game-factory-tester]
---
# Game Factory Orchestrator

# Orchestrator

You are the **orchestrator** agent. You coordinate **five** separate agents.
You are none of them.

| Agent | Role | CLI |
|-------|------|-----|
| **You** | orchestrator | `context`, delegate, validate flow |
| **prompt-crafter** | writes prompts | `prompt craft` |
| **image-generator** | calls image API | `image generate --plan-file` |
| **video-generator** | calls Seedance API | `video generate --plan-file` |
| **godot-assembler** | Godot .NET assembly | `godot assemble --assemble-file` |

Resolve routing: `python gamefactory.py agents show` (see **AGENT-ROUTING** in `docs/`).

## Your job

- Read `brief.json` and shared context.
- Delegate prompt writing to the **prompt-crafter** agent (separate session/skill).
- Delegate image API calls to the **image-generator** agent (separate session/skill).
- Delegate Godot assembly to the **godot-assembler** agent — **`godot assemble --assemble-file`**, not `godot inject` / GDScript.
- Prefer **`pipeline run`** for trim, matte, split-frames, and Godot Pass 3 (default executor=`pipeline` for workers).
- Run post-process CLI (`trim`, `remove-bg`, `slice`, `video`) **only after** image-generator `--validate` passes. See **matting** skill.
- If image validate fails with `next_action: prompt_crafter_regenerate`, delegate prompt revision — never matting on a bad background.
- Retry or escalate on validation failure.

## Not your job

- Do not craft prompts (no `prompt craft` in your session).
- Do not call image APIs directly (no `image generate --prompt` in your session).
- Do not write GDScript or C# game code (godot-assembler uses fixed .NET templates).
- Do not load `prompt-crafter/`, `image-generator/`, or `godot-assembler/` skills in your session.

## Shared context (all agents)

```bash
python gamefactory.py context --brief brief.json --asset knight
```

Same `{ project, asset }` JSON — each agent loads **its own** skills only.

## Multi-asset pipeline

For **multiple assets** after brief sign-off, use **pipeline manifest** (parallel by layer). See **pipeline-schedule** skill.

Pass 3 (when `--godot` default): `{brief}.godot.assemble` runs `godot assemble --assemble-file … --validate`.

Serial single-asset example:

```bash
python gamefactory.py prompt craft \
  --brief brief.json --asset knight \
  -o plans/knight.json

# Step 2 — image-generator agent (different Hermes skill set)
python gamefactory.py image generate \
  --plan-file plans/knight.json \
  --output output/knight.png --validate
# If exit 2 + next_action=prompt_crafter_regenerate → DO NOT trim/remove-bg.

# Step 3 — orchestrator or pipeline: post-process ONLY after image validate passed
python gamefactory.py image trim \
  --input output/knight.png --output output/knight_trimmed.png

python gamefactory.py image remove-bg \
  --input output/knight_trimmed.png --output output/knight_nobg.png
```

## Animation (Seedance — video-generator agent)

1. prompt-crafter: `prompt craft --animation --asset knight_walk -o plans/knight_walk.json`
2. image-generator: reference still must pass `--validate` (pure white bg)
3. **video-generator**: `video generate --plan-file plans/knight_walk.json --reference-image output/knight_raw.png --model mini`
   - Use **raw** still from step 2 — **do not trim** before Seedance
4. pipeline or orchestrator: `video split-frames --frames 8` → `video matte-frames --engine ai` (not `image remove-bg`)
5. **godot-assembler**: `godot assemble --assemble-file plans/godot_knight.json` (or pipeline Pass 3)
6. Never one image with multiple action frames.

Video frame matting details: see **matting-video** skill.


---

# Pipeline scheduling (concurrent production)

| | |
|--|--|
| **读者** | orchestrator skill、`pipeline run` 实现与调试 |
| **侧重** | Phase A–E、reset/cascade、`--run-prompts` / `--run-game-dev` |
| **不写** | 设计/施工方法论、六角色总表 |
| **姊妹文档** | 产品契约 → `docs/ITERATIVE-PRODUCTION.md` · CLI 大全 → `docs/AI-HANDOFF.md` |

After the **product brief is finalized**, use a **program runner** for CLI work. Reserve Hermes/AI for brief, prompt craft, and failures.

**Canonical example brief in git:** `resources/asset-brief.example.json`. Local demos (`resources/test-brief-*.json`, `tests/fixtures/`) are gitignored.

## Phase A — AI (serial / parallel sessions)

User + orchestrator + prompt-crafter → frozen `brief.json` + `plans/*.json`

```bash
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py prompt craft \
  --brief ../resources/asset-brief.example.json --asset knight -o ../plans/knight.json
```

## Phase B — Program runner (no Hermes)

```bash
cd cli

# 1. Build DAG once
python gamefactory.py pipeline plan \
  --brief ../resources/asset-brief.example.json \
  --output-dir ../output/asset-brief.example

# 2. Run (skips prompt.craft if plan files exist; parallel --jobs)
python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json \
  --jobs 4

# Dry run first wave
python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json --dry-run

# Status anytime
python gamefactory.py pipeline status \
  --manifest ../pipeline/asset-brief.example.json
```

Default: **`pipeline run` skips `prompt-crafter`** (expects `plans/`). Use `--run-prompts` to call LLM from the runner.

## Phase C — AI on failure only

When `pipeline run` exits **2** (validation / pause):

1. Read JSON in manifest task `result.parsed`
2. prompt-crafter fixes plan (or orchestrator updates brief if scope changed)
3. Reset and retry:

```bash
python gamefactory.py pipeline reset \
  --manifest ../pipeline/asset-brief.example.json \
  --task-id knight.image.generate \
  --cascade

python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json
```

Record validation failures per `docs/ITERATIVE-PRODUCTION.md` §6 when playtest criteria fail (future: `validation/*.json`).

## What the runner does

1. `pipeline ready` — tasks with deps done
2. Up to `--jobs` parallel **subprocess** (not Hermes terminal)
3. Parse exit code + stdout JSON → `record` in manifest
4. Next wave until done, blocked, or `--stop-on-fail`

## Phase D — Godot assembly (godot-assembler)

After assets exist (especially `*_nobg` / `walk_frames_nobg`):

**Automatic** — `pipeline plan` with default `--godot` appends `{slug}.godot.assemble`:

```bash
python gamefactory.py pipeline plan \
  --brief ../resources/asset-brief.example.json \
  --output-dir ../output/asset-brief.example \
  --godot-project ../games/asset-brief.example

python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json --jobs 4
```

**Manual** — when not using pipeline Godot task:

```bash
python gamefactory.py godot assemble \
  --assemble-file ../plans/godot_asset-brief.example.json
python gamefactory.py godot validate --project ../games/asset-brief.example
```

Delegate to **godot-assembler** skill. Assembler imports assets only — **game logic is godot-developer (Phase E)**.

## Phase E — Game logic (godot-developer, Pass 4)

After **godot.assemble** completes, delegate to **godot-developer** (Codex / Cursor — not `pipeline run` by default):

```bash
# Optional: pipeline writes dev handoff only
python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json \
  --run-game-dev

# Or manual handoff
python gamefactory.py godot dev-context \
  --brief ../resources/asset-brief.example.json \
  --project ../games/asset-brief.example \
  --assemble-file ../plans/godot_asset-brief.example.json \
  -o ../plans/dev_asset-brief.example.json
```

Then open a **godot-developer** session (skill `game-factory-godot-developer`), read `plans/dev_*.json`, implement C#, run `godot validate`.

Default `pipeline run` **skips** godot-developer (marks Pass 4 skipped — same as prompt.craft without `--run-prompts`).

## Phase F — Validation (tester)

After Pass 4 (or smoke after Pass 3):

```bash
python gamefactory.py test run \
  --project ../games/asset-brief.example \
  --brief ../resources/asset-brief.example.json
```

Loads skill `game-factory-tester`. Produces `output/<slug>/validation/report-*.json` + screenshot PNG.

On **exit 2** → orchestrator triage (Change Request / brief delta) — tester does not fix code.

## Orchestrator role now

- **Not** required to call every `terminal` step
- Use for: brief, Change Request → brief delta, delegating prompt craft, failure triage
- Use **`pipeline run`** for: image/video generate, trim, matte, split-frames, **godot assemble (Pass 3)**
- Use **godot-developer** (Codex/Cursor) for: C# gameplay after Pass 3

## Worker agents

Still valid as **documentation boundaries**. The runner enforces the same commands without separate Hermes sessions.


---

# Matting & Trim（切图 / 抠透明）

Orchestrator post-process skill. **切图** here means **trim white borders** (tight crop), **not** grid-splitting icon kits.

## Terminology

| 用户说法 | CLI | 作用 |
|----------|-----|------|
| 切图、裁边、去白边（画布） | `image trim` | 按内容外接矩形裁掉四周白边 |
| 抠图、透明底、去背景 | `image remove-bg` | 白底 → 透明 PNG |
| 边缘校验、检查白边 | `image validate-matting` | 1–2px 轮廓带检测白晕 |
| 拆 kit、网格切 | `image slice --mode grid` | icon_kit 2×2 等分（与切图不同） |

## Standard pipeline（必须按顺序）

```bash
python gamefactory.py image trim \
  --input output/asset.png \
  --output output/asset_trimmed.png

python gamefactory.py image remove-bg \
  --input output/asset_trimmed.png \
  --output output/asset_nobg.png
# remove-bg 默认附带 validate-edges；失败 exit 2

# 或单独复检
python gamefactory.py image validate-matting \
  --input output/asset_nobg.png
```

`remove-bg` 成功后 **必须** 通过 `validate-matting`。未通过 → 按下方 escalation 调参重跑 `remove-bg`，不要直接交付。

Optional: `image resize` after matting passes.

## Color-key 算法（`remove-bg --mode color`，默认）

白底黑边精灵专用，无 ML。通过 **`key_scope`** 控制抠白范围：

| `key_scope` | CLI | 行为 |
|-------------|-----|------|
| `exterior`（默认） | `--key-scope exterior` | 只抠与画布边缘连通的外侧白底（魔术棒），角色内部浅色高光/金属反光 **保留** |
| `global` | `--key-scope global` | 所有符合亮度/色差的白色像素都变透明（含角色内部浅色） |

1. 四角采样背景色 → 候选背景像素（亮度 / 色差）
2. **exterior**：从画布四边 flood-fill → 仅外侧背景透明；**global**：候选白 + 内部近白 spill 全透明
3. （仅 exterior）轮廓贴外缘的 1px 白晕再清一次
4. Morph：`erode` / `dilate` / `despeckle`
5. 硬 alpha + 透明区 RGB 清零

**trim** 与 remove-bg 共用 `key_scope` 前景 mask，避免裁切时把内部浅色算进背景。

## Config (`~/.gamefactory/config.json`)

```json
"matting": {
  "trim": { "threshold": 240, "padding": 2 },
  "color_key": {
    "threshold": 235,
    "fuzz": 24,
    "key_scope": "exterior",
    "morph_erode": 2,
    "morph_dilate": 1,
    "despeckle": 1
  },
  "validate_edges": {
    "edge_width": 2,
    "brightness_threshold": 220,
    "max_white_ratio": 0.01,
    "max_semi_transparent": 0
  }
}
```

See `resources/config.example.json`.

### Parameter cheat sheet

| Key | 效果 |
|-----|------|
| `trim.threshold` | 裁边：亮度 ≥ 此值视为白底 |
| `trim.padding` | 裁切后保留外边距像素 |
| `color_key.threshold` | 抠图亮度阈值 |
| `color_key.fuzz` | 与四角背景色的色差容差 |
| `color_key.key_scope` | `exterior` 仅外侧白底；`global` 全部白色透明 |
| `color_key.morph_erode` | 腐蚀 alpha，吃边缘白晕 |
| `color_key.morph_dilate` | 膨胀 alpha，补回主体 |
| `color_key.despeckle` | 开运算，去零散白点 |
| `validate_edges.edge_width` | 边缘检测带宽（默认 2px） |
| `validate_edges.brightness_threshold` | 边缘上亮度 ≥ 此值计为白点 |
| `validate_edges.max_white_ratio` | 边缘带内白点最大占比（默认 1%） |

## 边缘校验（validate-matting）

在 opaque 轮廓 **最外 1–2px** 采样，检查：

- 高亮像素占比是否超过 `max_white_ratio`
- 是否存在半透明 + 高亮的 halo 像素
- 轮廓外一圈是否有残留 alpha

**未通过时自动处理**（不要重生成图）：

1. `remove-bg --erode N+1 --dilate 1 --despeckle 1 --fuzz +2`
2. 或写 config：`morph_erode++`, `threshold: 235`, `fuzz: 24`
3. 重跑 remove-bg → 再 validate-matting
4. 仍失败才考虑 `prompt craft` / `image generate`

## 用户消息 → 自动处理

| 用户说（含同义） | 判断 | 自动动作 |
|------------------|------|----------|
| 白边、白晕、边缘没抠干净 | 色键 halo | `--erode 2`；config `morph_erode: 2`；跑 validate-matting |
| 白点、碎屑、脏点 | 零散高亮 | `--despeckle 1` |
| 抠完太瘦、线变细 | erode 过猛 | `morph_erode: 1`, `morph_dilate: 2` |
| 还有白底 | 阈值太严 | `--fuzz 24`, `threshold: 235`；先 trim |
| 校验不过 / 边缘有问题 | validate 失败 | 按 escalation 调参重跑 remove-bg |
| 四周空白太多 | 画布白边 | `image trim` 后再 remove-bg |

### Escalation recipe（白边）

1. `trim` 已跑？
2. `remove-bg --erode 2 --dilate 1 --despeckle 1 --fuzz 24 --threshold 235`
3. `validate-matting` 必须通过
4. 仍失败 → `morph_erode: 3` 或 `--mode ai`（最后手段）

## CLI reference

```bash
python gamefactory.py image trim --input raw.png --output trimmed.png
python gamefactory.py image remove-bg --input trimmed.png --output nobg.png
python gamefactory.py image validate-matting --input nobg.png
python gamefactory.py image remove-bg --input trimmed.png --output nobg.png \
  --erode 2 --dilate 1 --despeckle 1 --fuzz 24 --no-validate-edges
```

## Not your job

- Do not use `image slice` for single-character trim.
- Do not skip `validate-matting` after `remove-bg` on deliverable assets.
- Do not re-generate art for pure matting / white-edge issues.
- Do not use this pipeline on **video animation frames** — use **matting-video** skill (`video matte-frames`).


---

# Video Frame Matting（视频帧抠图）

Orchestrator post-process skill for **animation frames** extracted from Seedance video.
**Do not** use `image remove-bg --mode color` on video frames — backgrounds drift to gray/off-white.

## Static vs video

| Source | Background | Tool |
|--------|------------|------|
| Studio still (character / icon) | Pure `#FFFFFF` | `image trim` → `image remove-bg --mode color` |
| Seedance video frames | Gray / off-white drift | `video matte-frames --engine ai` |

## Standard animation pipeline

```bash
# After video-generator produces MP4
python gamefactory.py video split-frames \
  --input output/walk.mp4 \
  --output-dir output/walk_frames \
  --frames 8

python gamefactory.py video matte-frames \
  --input-dir output/walk_frames \
  --output-dir output/walk_frames_nobg \
  --engine ai
# default --no-trim: keep full frame after video (do not crop before matting)
```

## Before video (reference still)

| Step | Trim? |
|------|-------|
| `image generate` → raw PNG | No |
| `video generate --reference-image <raw>` | **Never trim** — pass original canvas to Seedance |
| `image trim` / `remove-bg` | Only for **static** sprite delivery, not i2v input |

## After video (frames)

| Step | Trim? |
|------|-------|
| `video split-frames` | No |
| `video matte-frames` | Default **no trim** (`--trim` only if you want tight bbox) |

Optional resize per frame after matting: `image resize` (batch script or loop).

## Engines

### `ai` (default, recommended)

Uses [rembg](https://github.com/danielgatis/rembg) (MIT, 23k+ stars) with **BiRefNet** or ISNet.

```bash
pip install "rembg[cpu]"
```

| Model | Notes |
|-------|-------|
| `birefnet-general` | Default — best general quality |
| `isnet-general-use` | Lighter, good fallback |
| `u2net` | Legacy, fastest |

### `soft-key` (fallback, no ML)

Softer color-key for gray backgrounds when rembg unavailable:

```bash
python gamefactory.py video matte-frames \
  --input-dir output/walk_frames \
  --output-dir output/walk_frames_nobg \
  --engine soft-key \
  --threshold 200 --fuzz 36
```

Uses `key_scope: global` by default (video bg is not studio white).

## Config (`~/.gamefactory/config.json`)

```json
"video": {
  "split_frames": { "frames": 8 }
},
"matting": {
  "video_frames": {
    "engine": "ai",
    "model": "birefnet-general",
    "trim": { "threshold": 200, "padding": 2 },
    "soft_key": {
      "threshold": 200,
      "fuzz": 36,
      "key_scope": "global",
      "morph_erode": 1,
      "morph_dilate": 1,
      "despeckle": 1
    }
  }
}
```

| `--frames` | Game use |
|------------|----------|
| 4 | Minimal idle / simple move |
| 8 | Default walk cycle |
| 12 | Smooth run / detailed motion |

Fewer frames = less AI matting time (8 frames ≈ 1 min vs 61 frames ≈ 7 min on CPU).

## Validation

Video frames use **relaxed QA** (opaque ratio sanity check), not strict white-edge validate.
Do **not** run `require_pure_white_background` on video frames.

## Troubleshooting

| Symptom | Action |
|---------|--------|
| rembg not installed | `pip install "rembg[cpu]"` or `--engine soft-key` |
| Gray halo on edges | Retry `birefnet-general`; or soft-key `--threshold 195 --fuzz 40` |
| Subject eaten / holes | `--engine ai` (avoid soft-key on complex bg) |
| Frame mostly transparent | Check source frame; may be empty/corrupt |
| Still has background | AI model swap to `isnet-general-use`; increase trim threshold |

## Not your job

- Do not use `image remove-bg --mode color` on video frames.
- Do not require pure white background on animation frames before matting.
- Reference still for img2video **must** still pass white-bg validate (separate pipeline).


---

## Hermes / Codex terminal

Run **all** `gamefactory` commands from the CLI directory. Use `pty=true`.

Resolve `<GAMEFACTORY_ROOT>` on this machine with:

```bash
cd cli && python gamefactory.py hermes paths
```

(`repo_root` / `cli_dir` in that JSON). Or set env `GAMEFACTORY_ROOT` to the Foundry repo/app root.
`hermes install` stamps the real paths into `~/.hermes/skills` for local use; **Release / git sources stay portable.**

```text
terminal(
  command="cd <GAMEFACTORY_ROOT>/cli && python gamefactory.py <subcommand> ...",
  workdir="<GAMEFACTORY_ROOT>",
  pty=true,
)
```

Environment (optional):

- `GAMEFACTORY_ROOT=<GAMEFACTORY_ROOT>`
- Config: `~/.gamefactory/config.json` (see `resources/config.example.json`)
- OpenRouter proxy (if needed): set top-level `proxy` (e.g. local Clash `http://127.0.0.1:7897`); legacy `image.proxy` / `prompt.proxy` still read

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd <GAMEFACTORY_ROOT>/cli && python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4",
  workdir="<GAMEFACTORY_ROOT>",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="<GAMEFACTORY_ROOT>"`.
