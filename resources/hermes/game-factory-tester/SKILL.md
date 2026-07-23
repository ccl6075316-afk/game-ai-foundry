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

**Ops:** `wait_frames` · `press` · `screenshot` · `assert_action` · `assert_node` · `assert_property`

Per-task harness (production-driven):

```bash
python gamefactory.py test plan --brief ../resources/asset-brief.example.json --task player_controller
python gamefactory.py test play \
  --project ../games/forest-platformer \
  --plan ../plans/playtest_asset-brief.example_player_controller.json \
  --progress ../plans/progress_forest-platformer.json \
  --skip-analyze
```

Passing `test play --progress` snapshots the plan for L4 regression:

```bash
python gamefactory.py test regression --progress ../plans/progress_forest-platformer.json
```

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
| `assert_action` | `action` | InputMap must contain action (exit 2/3) |
| `assert_node` | `path` | SceneTree node must exist (e.g. `/root/Main/Player`) |
| `assert_property` | `path`, `property`, one of `equals` / `neq` / `gte` / `lte` | Hard assert on node property |

`visual_checks[]` tie each screenshot name to a criterion string for vision QA.

Generate with:

```bash
python gamefactory.py test plan --brief <brief.json>
python gamefactory.py test plan --brief <brief.json> --task player_controller
```

Runner exit codes: `0` ok · `1` error · `2` InputMap missing · `3` assertion failed.


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
