# Game AI Foundry — Codex / Agent Instructions

Production flow: **AI for brief + prompts**, **`pipeline run` for execution** (no Hermes per step).

## Setup

```bash
cd cli
pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json
# Edit API keys (OpenRouter, Volcengine Ark)
python gamefactory.py hermes install   # optional, for Hermes sessions
```

## Recommended workflow

```bash
cd cli
# 1. AI: brief + plans
python gamefactory.py prompt craft --brief ../resources/<brief>.json --asset <name> -o ../plans/<name>.json

# 2. Program runner (parallel, no LLM)
python gamefactory.py pipeline plan --brief ../resources/<brief>.json -o ../pipeline/<run>.json --output-dir ../output/<run>
python gamefactory.py pipeline run --manifest ../pipeline/<run>.json --jobs 4

# 3. On validation failure (exit 2): fix plan, reset, rerun
python gamefactory.py pipeline reset --manifest ../pipeline/<run>.json --task-id <asset>.image.generate
python gamefactory.py pipeline run --manifest ../pipeline/<run>.json
```

## Four agents (role boundaries)

| Role | When |
|------|------|
| prompt-crafter | `prompt craft` only |
| image-generator | `image generate --plan-file` |
| video-generator | `video generate --plan-file` + raw reference |
| godot-assembler | `godot assemble --assemble-file` / `import-sprites` — **C# .NET only, no GDScript** |
| orchestrator | brief, delegate, failure triage — **prefer `pipeline run` over manual terminal** |

Read `docs/AI-HANDOFF.md`, `docs/AGENT-ROUTING.md`, and `resources/skills/orchestrator/pipeline-schedule.md`.

## Critical rules

1. **Validate before matting** — `exit 2` → regenerate prompt, not matting.
2. **Animation** — raw still to Seedance only; split-frames skips lead-in (~15%); idle = separate `*_nobg.png`, not reference still or anim frame 0.
3. **Video frames** — `video matte-frames --engine ai`, not `image remove-bg`.
4. **Image post** — `image trim/remove-bg` use `--input` / `--output` (not `-i`/`-o`).

## Hermes / Codex (optional)

Use for brief discussion and prompt craft. Asset batch execution: **`pipeline run`**, not chained `terminal()` calls.

```text
terminal(command="cd cli && python gamefactory.py pipeline run --manifest ../pipeline/foo.json --jobs 4", workdir="<repo>", pty=true)
```
