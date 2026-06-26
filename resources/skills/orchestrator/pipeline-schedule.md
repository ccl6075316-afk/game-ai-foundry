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

## Orchestrator role now

- **Not** required to call every `terminal` step
- Use for: brief, delegating prompt craft, failure triage, Godot assembly (future)
- Use **`pipeline run`** for: image/video generate, trim, matte, split-frames

## Worker agents

Still valid as **documentation boundaries**. The runner enforces the same commands without separate Hermes sessions.
