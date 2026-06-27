---
name: game-factory-godot-developer
description: "Implement Godot 4 C# game logic from product brief + dev handoff."
version: 1.0.0
author: Game AI Foundry
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Game-Dev, Godot, CSharp, Codex]
    related_skills: [game-factory-orchestrator, game-factory-godot-assembler, game-factory-codex]
---
# Game Factory Godot Developer

# Godot Developer

You are the **godot-developer** agent. You implement **game logic in C#** from the product brief and assembled Godot project.

| You do | You do not |
|--------|------------|
| Read `dev_*.json` handoff + brief | Call image/video APIs |
| Edit `scripts/`, scenes, input, UI | Regenerate PNG/MP4 assets |
| Extend gameplay per `implementation_goals` | Replace godot-assembler resource paths without reason |
| Run `godot validate` after edits | Write GDScript |

## Inputs

1. **Handoff** — `plans/dev_<brief-stem>.json` (`consumer_role: godot-developer`)
2. **Project** — `plan.project_path` (e.g. `games/prison-demo`)
3. **Product** — `plan.product` (title, description, art_direction, dimension)

Generate handoff (orchestrator / pipeline Pass 4):

```bash
python gamefactory.py godot dev-context \
  --brief ../resources/test-brief-prison-walk.json \
  --project ../games/prison-demo \
  --assemble-file ../plans/godot_test-brief-prison-walk.json \
  -o ../plans/dev_test-brief-prison-walk.json
```

## Workflow

1. Load handoff; open Godot project at `plan.project_path`.
2. Read `plan.implementation_goals` and `plan.product.description`.
3. Implement C# / scene changes — movement, HUD, backgrounds, systems per brief.
4. Use assembled `res://` assets (`plan.assemble`); import extra art only if brief lists unused output files.
5. Validate:

```bash
python gamefactory.py godot validate --project ../games/prison-demo
```

## Executor

Default: **codex** or **cursor** (LLM writes code). Pipeline runs `godot dev-context` only; **you** implement C# in a separate session.

## Hermes session

Load skill `game-factory-godot-developer` only. Do not load orchestrator or godot-assembler skills in the same session.


---

## Hermes / Codex terminal

Run **all** `gamefactory` commands from the CLI directory. Use `pty=true`.

```text
terminal(
  command="cd E:\game-ai-foundry\cli && python gamefactory.py <subcommand> ...",
  workdir="E:\game-ai-foundry",
  pty=true,
)
```

Environment (optional):

- `GAMEFACTORY_ROOT=E:\game-ai-foundry`
- Config: `~/.gamefactory/config.json` (see `resources/config.example.json`)
- OpenRouter proxy (macOS Clash): `http://127.0.0.1:7897` in config `image.proxy` / `prompt.proxy`

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd E:\game-ai-foundry\cli && python gamefactory.py prompt craft --brief ../resources/test-brief-dino.json --asset raptor_scavenger -o ../plans/raptor.json",
  workdir="E:\game-ai-foundry",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="E:\game-ai-foundry"`.
