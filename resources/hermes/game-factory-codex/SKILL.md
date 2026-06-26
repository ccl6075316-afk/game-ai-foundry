---
name: game-factory-codex
description: "Run gamefactory CLI from Hermes terminal or delegate to Codex exec."
version: 1.0.0
author: Game AI Foundry
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Game-Dev, Codex, Terminal, Hermes]
    related_skills: [game-factory-orchestrator, codex]
---
# Game Factory Codex

# Game Factory × Hermes × Codex

Use this skill when **Hermes orchestrates** and **Codex** (or terminal) runs `gamefactory` CLI.

## Architecture

```
User → Hermes (orchestrator skill: game-factory-orchestrator)
         ├─ terminal → gamefactory prompt craft     (prompt-crafter skill session)
         ├─ terminal → gamefactory image generate   (image-generator skill session)
         ├─ terminal → gamefactory video generate   (video-generator skill session)
         └─ terminal → trim / matte / godot         (orchestrator post-process)
```

Each agent = **separate Hermes session** with **one skill loaded**. Never merge roles in one session.

## Quick start (character + idle animation)

```bash
# 0. Install skills once
cd <repo>/cli && python gamefactory.py hermes install

# 1. prompt-crafter session — load skill game-factory-prompt-crafter
python gamefactory.py prompt craft \
  --brief ../resources/test-brief-dino-idle.json \
  --asset raptor_scavenger \
  -o ../plans/raptor_scavenger.json

python gamefactory.py prompt craft \
  --brief ../resources/test-brief-dino-idle.json \
  --asset raptor_scavenger_idle \
  --animation \
  -o ../plans/raptor_scavenger_idle.json

# 2. image-generator session — load skill game-factory-image-generator
python gamefactory.py image generate \
  --plan-file ../plans/raptor_scavenger.json \
  --output ../output/dino-idle/raptor_scavenger_raw.png \
  --validate

# 3. video-generator session — raw still, NO trim before Seedance
python gamefactory.py video generate \
  --plan-file ../plans/raptor_scavenger_idle.json \
  --reference-image ../output/dino-idle/raptor_scavenger_raw.png \
  --output ../output/dino-idle/raptor_idle.mp4

# 4. orchestrator session — matting-video skill
python gamefactory.py video split-frames \
  --input ../output/dino-idle/raptor_idle.mp4 \
  --output-dir ../output/dino-idle/idle_frames \
  --frames 8

python gamefactory.py video matte-frames \
  --input-dir ../output/dino-idle/idle_frames \
  --output-dir ../output/dino-idle/idle_nobg \
  --engine ai --no-trim
```

## Hermes terminal rules

1. **`pty=true`** for all `gamefactory` and `codex` calls.
2. **`workdir`** = repository root; commands `cd cli && python gamefactory.py ...`.
3. **Git repo required** for Codex `exec` — this project is a git repo.
4. Long jobs: `background=true` + `process(action="poll")`.
5. Gateway sandbox issues: `codex exec --sandbox danger-full-access "..."`.

## Codex runtime (optional)

If Hermes uses `/codex-runtime codex_app_server`, Codex native tools handle file edits;
still call `gamefactory` via terminal for asset generation (not apply_patch).

Expose via MCP callback: `skill_view` → load `game-factory-orchestrator` when user asks
to generate game assets.

## Config checklist

| Key | Purpose |
|-----|---------|
| `~/.gamefactory/config.json` | OpenRouter + Seedance + matting |
| `image.proxy` | Clash for OpenRouter (`127.0.0.1:7897`) |
| `video.api_key` | Volcengine Ark / Seedance |

## Validation gates (do not skip)

| Step | Gate |
|------|------|
| `image generate --validate` | Pure white bg — fail → prompt-crafter regenerate |
| `remove-bg` (static) | `validate-matting` |
| Animation reference | **Raw** PNG to Seedance — never trim first |
| Video frames | `video matte-frames` — not `image remove-bg` |


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
  command="cd /Users/czl/projects/game-ai-foundry/cli && python gamefactory.py prompt craft --brief ../resources/test-brief-dino.json --asset raptor_scavenger -o ../plans/raptor.json",
  workdir="/Users/czl/projects/game-ai-foundry",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="/Users/czl/projects/game-ai-foundry"`.
