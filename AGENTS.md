# Game AI Foundry — Codex / Agent Instructions

This repo is orchestrated by **Hermes Agent** (sessions + skills) calling **`gamefactory` CLI** via terminal.

## Setup

```bash
cd cli
pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json
# Edit API keys (OpenRouter, Volcengine Ark)
python gamefactory.py hermes install
```

## Four agents (never merge in one session)

| Skill (Hermes) | CLI |
|----------------|-----|
| `game-factory-orchestrator` | Delegate + post-process |
| `game-factory-prompt-crafter` | `prompt craft` |
| `game-factory-image-generator` | `image generate --plan-file` |
| `game-factory-video-generator` | `video generate --plan-file` |

Read `docs/HERMES-CODEX.md` and `docs/AI-HANDOFF.md` before pipeline work.

## Commands always from `cli/`

```bash
cd cli
python gamefactory.py context --brief ../resources/<brief>.json --asset <name>
python gamefactory.py prompt craft --brief ... --asset ... -o ../plans/<name>.json
python gamefactory.py image generate --plan-file ../plans/<name>.json --output ../output/<name>.png --validate
```

## Critical rules

1. **Validate before matting** — failed pure-white → prompt-crafter regenerate, not trim/remove-bg.
2. **Animation** — raw still to Seedance (`adaptive` ratio); no trim before `video generate`.
3. **Video frames** — `video matte-frames --engine ai`, not `image remove-bg`.
4. **Proxy** — OpenRouter needs Clash `127.0.0.1:7897` on macOS rule-mode setups.

## Codex in Hermes

Use `pty=true`. Example:

```text
terminal(command="cd cli && python gamefactory.py hermes paths", workdir="<repo>", pty=true)
```

Long tasks: `codex exec --full-auto "..."` with `workdir` set to this repository.
