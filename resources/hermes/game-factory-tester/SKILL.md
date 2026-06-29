---
name: game-factory-tester
description: "Autonomous playtest: godot validate, headless screenshot, vision QA report."
version: 1.0.0
author: Game AI Foundry
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Game-Dev, QA, Testing, Vision]
    related_skills: [game-factory-orchestrator, game-factory-godot-developer]
---
# Game Factory Tester

# Tester — playtest plan + command playback

You are the **tester** agent. Read the **Design Doc** (today: `brief.project` — `gameplay_loop`, `session_goal`, `controls`) and produce **playtest JSON**, then execute it. You do **not** fix code.

Contract: `docs/ITERATIVE-PRODUCTION.md` §6.  
Godogen equivalent: per-task **test harness** + screenshots + **visual-qa** (we use `test analyze` / vision model).

## Workflow (autonomous)

```bash
cd cli

# 1. Generate playtest commands from brief (design → test JSON)
python gamefactory.py test plan \
  --brief ../resources/asset-brief.example.json \
  -o ../plans/playtest_asset-brief.example.json

# 2. Execute: validate → simulate inputs → multi-screenshot → vision QA
python gamefactory.py test play \
  --project ../games/asset-brief.example \
  --plan ../plans/playtest_asset-brief.example.json \
  --brief ../resources/asset-brief.example.json

# Or one-shot (uses plans/playtest_<brief>.json if present)
python gamefactory.py test run \
  --project ../games/asset-brief.example \
  --brief ../resources/asset-brief.example.json
```

## Playtest JSON shape

```json
{
  "schema_version": 1,
  "playtest_id": "forest-platformer-smoke",
  "acceptance_criteria": [{"source": "brief.project.session_goal", "criterion": "..."}],
  "input_actions": ["move_right", "attack"],
  "steps": [
    {"op": "wait_frames", "frames": 30},
    {"op": "screenshot", "name": "boot"},
    {"op": "press", "action": "move_right", "duration_ms": 1200},
    {"op": "screenshot", "name": "after_move_right"}
  ],
  "visual_checks": [
    {"screenshot": "boot", "criterion": "...", "source": "brief.project.description"}
  ]
}
```

**Ops:** `wait_frames` · `press` (uses Godot `InputMap` action names from `brief.controls`) · `screenshot`

Edit plans manually for longer scenarios (collect item → reach exit). Do not invent actions not in `brief.controls`.

## Godogen comparison

| Godogen | Game AI Foundry tester |
|---------|------------------------|
| Decomposer writes verification criteria in `PLAN.md` | `test plan` writes `plans/playtest_*.json` from brief |
| Task executor writes test harness + runs headless | `playtest_runner.gd` + `test play` |
| `visual-qa` skill on screenshots | `visual_checks[]` → vision LLM per frame |
| Reference image `reference.png` | Optional `project.visual_reference` (future compare) |

## Rules

1. Criteria come from **brief / playtest plan** — not chat.
2. **exit 2** on `InputMap` missing → report to orchestrator → godot-developer wires `brief.controls`.
3. Do not edit C# or brief; file Validation Report only.
4. Config: `test.vision_model` in `~/.gamefactory/config.json`.

## Output

- `output/<slug>/validation/play-<timestamp>/` — screenshots + `manifest.json`
- `output/<slug>/validation/report-<timestamp>.json` — full Validation Report


---

# Vision analysis

Use when `test run` is too heavy or you already have a screenshot.

## Analyze vs brief

```bash
python gamefactory.py test analyze \
  --image ../output/my-game/validation/screenshots/latest.png \
  --brief ../resources/my-game-brief.json \
  -o ../output/my-game/validation/analysis.json
```

## Custom criteria file

```json
[
  {
    "source": "design_doc.acceptance_criteria[0]",
    "criterion": "Player can see the forest gate and a slime enemy at start."
  }
]
```

```bash
python gamefactory.py test analyze \
  --image path/to.png \
  --criteria-file criteria.json
```

## What to check visually

| Layer | Look for |
|-------|----------|
| Build | N/A — use `godot validate` first |
| Scene | Main scene loaded; no grey void / missing textures |
| Functional hints | HUD, player sprite, enemies visible if brief says so |
| Art | Matches `art_direction` in brief |

Model returns JSON: `status`, `summary`, `failed_criteria`, `visual_notes`.

**Exit 2** when `status` is `failed` — hand off to orchestrator, not godot-developer directly unless dispatched.


---

# Playtest JSON schema (v1)

Steps use Godot **InputMap** action names from `brief.project.controls`.

| `op` | Fields | Notes |
|------|--------|-------|
| `wait_frames` | `frames` (int) | Let physics/animations settle |
| `press` | `action`, `duration_ms` | `Input.action_press` for duration |
| `screenshot` | `name` | Saves `<name>.png` under run directory |

`visual_checks[]` tie each screenshot name to a criterion string for vision QA.

Generate with `python gamefactory.py test plan --brief <brief.json>`.


---

## Hermes / Codex terminal

Run **all** `gamefactory` commands from the CLI directory. Use `pty=true`.

```text
terminal(
  command="cd /Users/czl/projects/game-ai-foundry/cli && python gamefactory.py <subcommand> ...",
  workdir="/Users/czl/projects/game-ai-foundry",
  pty=true,
)
```

Environment (optional):

- `GAMEFACTORY_ROOT=/Users/czl/projects/game-ai-foundry`
- Config: `~/.gamefactory/config.json` (see `resources/config.example.json`)
- OpenRouter proxy (macOS Clash): `http://127.0.0.1:7897` in config `image.proxy` / `prompt.proxy`

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd /Users/czl/projects/game-ai-foundry/cli && python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4",
  workdir="/Users/czl/projects/game-ai-foundry",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="/Users/czl/projects/game-ai-foundry"`.
