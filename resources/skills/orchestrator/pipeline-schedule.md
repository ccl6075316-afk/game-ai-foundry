# Pipeline scheduling (concurrent production)

After the **product brief is finalized**, use a **program runner** for CLI work. Reserve Hermes/AI for brief, prompt craft, and failures.

## Phase A — AI (serial / parallel sessions)

User + prompt-crafter → `brief.json` + `plans/*.json`

```bash
python gamefactory.py prompt craft --brief ../resources/foo.json --asset bar -o ../plans/bar.json
```

## Phase B — Program runner (no Hermes)

```bash
cd cli

# 1. Build DAG once
python gamefactory.py pipeline plan \
  --brief ../resources/test-brief-dino-idle.json \
  -o ../pipeline/dino-idle.json \
  --output-dir ../output/dino-idle

# 2. Run (skips prompt.craft if plan files exist; parallel --jobs)
python gamefactory.py pipeline run \
  --manifest ../pipeline/dino-idle.json \
  --jobs 4

# Dry run first wave
python gamefactory.py pipeline run --manifest ../pipeline/dino-idle.json --dry-run

# Status anytime
python gamefactory.py pipeline status --manifest ../pipeline/dino-idle.json
```

Default: **`pipeline run` skips `prompt-crafter`** (expects `plans/`). Use `--run-prompts` to call LLM from the runner.

## Phase C — AI on failure only

When `pipeline run` exits **2** (validation / pause):

1. Read JSON in manifest task `result.parsed`
2. prompt-crafter fixes plan
3. Reset and retry:

```bash
python gamefactory.py pipeline reset \
  --manifest ../pipeline/dino-idle.json \
  --task-id raptor_scavenger.image.generate \
  --cascade

python gamefactory.py pipeline run --manifest ../pipeline/dino-idle.json
```

## What the runner does

1. `pipeline ready` — tasks with deps done
2. Up to `--jobs` parallel **subprocess** (not Hermes terminal)
3. Parse exit code + stdout JSON → `record` in manifest
4. Next wave until done, blocked, or `--stop-on-fail`

## Phase D — Godot assembly (godot-assembler)

After assets exist (especially `*_nobg` / `walk_frames_nobg`):

**Automatic** — `pipeline plan` with default `--godot` appends `{brief}.godot.assemble`:

```bash
python gamefactory.py pipeline plan \
  --brief ../resources/test-brief-prison-walk.json \
  -o ../pipeline/prison-walk.json \
  --output-dir ../output/prison-test \
  --godot-project ../games/prison-demo

python gamefactory.py pipeline run --manifest ../pipeline/prison-walk.json --jobs 4
```

**Manual** — when not using pipeline Godot task:

```bash
python gamefactory.py godot assemble \
  --assemble-file ../plans/godot_prison_demo.json
python gamefactory.py godot validate --project ../games/prison-demo
```

Delegate to **godot-assembler** skill. Assembler imports assets only — **game logic is godot-developer (Phase E)**.

## Phase E — Game logic (godot-developer, Pass 4)

After **godot.assemble** completes, delegate to **godot-developer** (Codex / Cursor — not `pipeline run` by default):

```bash
# Optional: pipeline writes dev handoff only
python gamefactory.py pipeline run \
  --manifest ../pipeline/prison-walk.json \
  --run-game-dev

# Or manual handoff
python gamefactory.py godot dev-context \
  --brief ../resources/test-brief-prison-walk.json \
  --project ../games/prison-demo \
  --assemble-file ../plans/godot_test-brief-prison-walk.json \
  -o ../plans/dev_test-brief-prison-walk.json
```

Then open a **godot-developer** session (skill `game-factory-godot-developer`), read `plans/dev_*.json`, implement C#, run `godot validate`.

Default `pipeline run` **skips** godot-developer (marks Pass 4 skipped — same as prompt.craft without `--run-prompts`).

## Orchestrator role now

- **Not** required to call every `terminal` step
- Use for: brief, delegating prompt craft, failure triage, optional manual Godot assemble
- Use **`pipeline run`** for: image/video generate, trim, matte, split-frames, **godot assemble (Pass 3)**
- Use **godot-developer** (Codex/Cursor) for: C# gameplay after Pass 3

## Worker agents

Still valid as **documentation boundaries**. The runner enforces the same commands without separate Hermes sessions.
