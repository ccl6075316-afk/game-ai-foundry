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
