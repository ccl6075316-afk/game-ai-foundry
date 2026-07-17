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
         ├─ terminal → prompt craft / brief export   (prompt-crafter session)
         ├─ terminal → pipeline run --jobs N         (image / video / matte / assemble)
         └─ terminal → godot dev-context + C#        (godot-developer via Codex)
```

Each agent = **separate Hermes session** with **one skill loaded** for AI work. **Batch assets use `pipeline run`**, not one terminal per image step.

Canonical brief in git: `resources/asset-brief.example.json`.

## Quick start (recommended: pipeline run)

```bash
# 0. Install skills once
cd <repo>/cli && python gamefactory.py hermes install

# 1. prompt-crafter session — load skill game-factory-prompt-crafter
python gamefactory.py prompt craft \
  --brief ../resources/asset-brief.example.json \
  --asset knight \
  -o ../plans/knight.json

python gamefactory.py prompt craft \
  --brief ../resources/asset-brief.example.json \
  --asset knight_walk \
  --animation \
  -o ../plans/knight_walk.json

# 2. Program runner (no per-step Hermes sessions)
python gamefactory.py pipeline plan \
  --brief ../resources/asset-brief.example.json \
  --output-dir ../output/asset-brief.example

python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json \
  --jobs 4
```

See `docs/AI-HANDOFF.md` §5 for manual single-step commands (debug only).

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

Iteration / Change Request: `docs/ITERATIVE-PRODUCTION.md`.


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
- OpenRouter proxy (if needed): set `image.proxy` / `prompt.proxy` (e.g. local Clash `http://127.0.0.1:7897`)

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd <GAMEFACTORY_ROOT>/cli && python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4",
  workdir="<GAMEFACTORY_ROOT>",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="<GAMEFACTORY_ROOT>"`.
