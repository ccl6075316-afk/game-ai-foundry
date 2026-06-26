# Pipeline scheduling (concurrent production)

After the **product brief is finalized**, do not run assets one-by-one from memory.
Build a **manifest DAG**, fan out **ready** tasks in parallel, and **record** results.

## Phase A — communication (serial)

User + product agent agree on `brief.json`: every static asset, every animation, `reference_asset` links.

## Phase B — production (parallel by layer)

```bash
cd cli

# 1. Expand brief → task DAG
python gamefactory.py pipeline plan \
  --brief ../resources/test-brief-dino-idle.json \
  -o ../pipeline/dino-idle.json

# 2. See what can run now (often many prompt.craft at layer 0)
python gamefactory.py pipeline ready --manifest ../pipeline/dino-idle.json --json

# 3. Fan out: one Hermes session per ready task (same role can run in parallel)
#    prompt-crafter sessions → all layer-0 prompt.craft tasks
#    image-generator sessions → all ready image.generate with no mutual deps
#    video-generator sessions → video.generate when reference still exists

# 4. After each terminal returns, record status (orchestrator only)
python gamefactory.py pipeline record \
  --manifest ../pipeline/dino-idle.json \
  --task-id raptor_scavenger.image.generate \
  --status done --exit-code 0

# 5. Repeat ready → dispatch → record until pipeline status shows complete

# Resume after crash: merge old status or reconcile disk artifacts
python gamefactory.py pipeline plan ... -o ../pipeline/dino-idle.json \
  --merge ../pipeline/dino-idle.json
python gamefactory.py pipeline reconcile --manifest ../pipeline/dino-idle.json
```

## Dependency rules (automatic from brief)

| Asset kind | Tasks |
|------------|-------|
| Static (character, bg, icon_kit, texture) | `prompt.craft` → `image.generate` → orchestrator post (trim/remove-bg/slice per type) |
| Video animation (`action` + `reference_asset`) | `prompt.craft` ∥ ref still; then `video.generate` → `split-frames` → `matte-frames` |
| `character_pose` | waits for `reference_asset` still, then img2img `image.generate` + post |

**Animation uses reference raw still** — `video.generate` depends on `{reference}.image.generate`, not trim/nobg.

## Orchestrator rules

1. **Never generate** — only `pipeline ready`, delegate, `pipeline record`.
2. **Parallelize** all tasks in `pipeline ready` with the **same role** across separate sessions.
3. On `image.generate` **exit 2** → `record --status failed`, re-delegate `prompt.craft` for that asset only.
4. Do not start `video.generate` until manifest shows `{ref}.image.generate` **done**.
5. Prefer `pipeline record --exit-code N` over guessing from log text.

## Worker agents

Workers run **only** the `command` field from their task (from `pipeline show` or `ready --json`).
They do **not** update the manifest — orchestrator records.

## JSON supervision

After each command, capture stdout. Pass validation JSON to `pipeline record --result-json '...'` when present.
