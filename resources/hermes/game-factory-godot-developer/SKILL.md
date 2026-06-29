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

You are the **godot-developer** agent. You implement **game logic in C#** from the **frozen brief contract** and assembled Godot project.

| You do | You do not |
|--------|------------|
| Read `dev_*.json` handoff **authoritative_sources only** | Read brainstorm session or host chat memory |
| Use `runtime_bindings` + `animation_graphs` from handoff | Guess paths under `output/` or invent clip names |
| Edit `scripts/`, scenes, input, UI | Call image/video APIs |
| Extend gameplay per `implementation_goals` | Regenerate PNG/MP4 assets |
| Run `godot validate` after edits | Write GDScript |

## Authoritative sources (only these)

1. **`plan.authoritative_sources.brief`** — product + assets + animation_graphs (frozen at export)
2. **`plan.authoritative_sources.assets_manifest`** — pipeline stages + `runtime.res://` bindings (if present)
3. **`plan.authoritative_sources.godot_project`** — assembled Godot tree

`plan.contract_rules` repeats: **brief is the only product spec.** If something is not in brief or assets-manifest, it does not exist.

## Inputs

Handoff — `plans/dev_<brief-stem>.json` (`consumer_role: godot-developer`):

- `plan.runtime_bindings[]` — per asset: `usage`, `clip_name`, `loop`, `runtime.sprite_frames`, `runtime.res_path`
- `plan.animation_graphs[]` — state transitions (`from` → `to` → `then`)
- `plan.implementation_goals` — derived from brief only

Generate handoff:

```bash
python gamefactory.py godot dev-context \
  --brief ../resources/magic-prince-brief.json \
  --project ../games/magic-prince \
  --assemble-file ../plans/godot_magic-prince-brief.json \
  -o ../plans/dev_magic-prince-brief.json
```

## Workflow

1. Load handoff; read **only** `authoritative_sources` files (not session history).
2. Open Godot project at `plan.project_path`.
3. Implement C# using `runtime_bindings` for SpriteFrames paths and `animation_graphs` for AnimationPlayer / state logic.
4. Backgrounds: use `runtime.res_path` from bindings where `usage` is `world_background`.
5. Validate:

```bash
python gamefactory.py godot validate --project ../games/magic-prince
```

## Executor

Default: **codex** or **cursor**. Pipeline runs `godot dev-context` only; **you** implement C# in a separate session.

## Hermes session

Load skill `game-factory-godot-developer` only. Do not load orchestrator or godot-assembler skills in the same session.


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
