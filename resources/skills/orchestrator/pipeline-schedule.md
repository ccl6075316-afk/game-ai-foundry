# Pipeline scheduling (concurrent production)

| | |
|--|--|
| **读者** | orchestrator skill、`pipeline run` 实现与调试 |
| **侧重** | Phase A–E、reset/cascade、`--run-prompts` / `--run-game-dev` |
| **不写** | 设计/施工方法论、六角色总表 |
| **姊妹文档** | 产品契约 → `docs/ITERATIVE-PRODUCTION.md` · CLI 大全 → `docs/AI-HANDOFF.md` |

After the **product brief is finalized**, use a **program runner** for CLI work. Reserve Hermes/AI for brief, prompt craft, and failures.

**Canonical example brief in git:** `resources/asset-brief.example.json`. Local demos (`resources/test-brief-*.json`, `tests/fixtures/`) are gitignored.

## Phase A — AI (serial / parallel sessions)

User + orchestrator + prompt-crafter → frozen `brief.json` + `plans/*.json`

```bash
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py prompt craft \
  --brief ../resources/asset-brief.example.json --asset knight -o ../plans/knight.json
```

## Phase B — Program runner (no Hermes)

```bash
cd cli

# 1. Build DAG once
python gamefactory.py pipeline plan \
  --brief ../resources/asset-brief.example.json \
  --output-dir ../output/asset-brief.example

# 2. Run (skips prompt.craft if plan files exist; parallel --jobs)
python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json \
  --jobs 4

# Dry run first wave
python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json --dry-run

# Status anytime
python gamefactory.py pipeline status \
  --manifest ../pipeline/asset-brief.example.json
```

Default: **`pipeline run` skips `prompt-crafter`** (expects `plans/`). Use `--run-prompts` to call LLM from the runner.

## Phase C — AI on failure only

When `pipeline run` exits **2** (validation / pause):

1. Read JSON in manifest task `result.parsed`
2. prompt-crafter fixes plan (or orchestrator updates brief if scope changed)
3. Reset and retry:

```bash
python gamefactory.py pipeline reset \
  --manifest ../pipeline/asset-brief.example.json \
  --task-id knight.image.generate \
  --cascade

python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json
```

Record validation failures per `docs/ITERATIVE-PRODUCTION.md` §6 when playtest criteria fail (future: `validation/*.json`).

## What the runner does

1. `pipeline ready` — tasks with deps done
2. Up to `--jobs` parallel **subprocess** (not Hermes terminal)
3. Parse exit code + stdout JSON → `record` in manifest
4. Next wave until done, blocked, or `--stop-on-fail`

## Phase D — Godot assembly (godot-assembler)

After assets exist (especially `*_nobg` / `walk_frames_nobg`):

**Automatic** — `pipeline plan` with default `--godot` appends `{slug}.godot.assemble`:

```bash
python gamefactory.py pipeline plan \
  --brief ../resources/asset-brief.example.json \
  --output-dir ../output/asset-brief.example \
  --godot-project ../games/asset-brief.example

python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json --jobs 4
```

**Manual** — when not using pipeline Godot task:

```bash
python gamefactory.py godot assemble \
  --assemble-file ../plans/godot_asset-brief.example.json
python gamefactory.py godot validate --project ../games/asset-brief.example
```

Delegate to **godot-assembler** skill. Assembler imports assets only — **game logic is godot-developer (Phase E)**.

## Phase E — Game logic (godot-developer, Pass 4)

After **godot.assemble** completes, delegate to **godot-developer** (Codex / Cursor — not `pipeline run` by default):

```bash
# Optional: pipeline writes dev handoff only
python gamefactory.py pipeline run \
  --manifest ../pipeline/asset-brief.example.json \
  --run-game-dev

# Or manual handoff
python gamefactory.py godot dev-context \
  --brief ../resources/asset-brief.example.json \
  --project ../games/asset-brief.example \
  --assemble-file ../plans/godot_asset-brief.example.json \
  -o ../plans/dev_asset-brief.example.json
```

Then open a **godot-developer** session (skill `game-factory-godot-developer`), read `plans/dev_*.json`, implement C#, run `godot validate`.

Default `pipeline run` **skips** godot-developer (marks Pass 4 skipped — same as prompt.craft without `--run-prompts`).

## Phase F — Validation (tester)

After Pass 4 (or smoke after Pass 3):

```bash
python gamefactory.py test run \
  --project ../games/asset-brief.example \
  --brief ../resources/asset-brief.example.json
```

Loads skill `game-factory-tester`. Produces `output/<slug>/validation/report-*.json` + screenshot PNG.

On **exit 2** → orchestrator triage (Change Request / brief delta) — tester does not fix code.

## Orchestrator role now

- **Not** required to call every `terminal` step
- Use for: brief, Change Request → brief delta, delegating prompt craft, failure triage
- Use **`pipeline run`** for: image/video generate, trim, matte, split-frames, **godot assemble (Pass 3)**
- Use **godot-developer** (Codex/Cursor) for: C# gameplay after Pass 3

## Worker agents

Still valid as **documentation boundaries**. The runner enforces the same commands without separate Hermes sessions.
