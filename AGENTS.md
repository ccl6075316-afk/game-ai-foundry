# Game AI Foundry — Codex / Agent Instructions

> **One-pager for Codex.** Details live elsewhere — see [`docs/README.md`](docs/README.md).

**Flow:** AI for brief + prompts → **`pipeline run`** for assets (no per-step Hermes).

## Setup

```bash
cd cli
pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json
python gamefactory.py setup check --json   # FFmpeg / Godot / rembg 缺失项
```

**Godot**：便携 zip → [godotengine.org/download](https://godotengine.org/download)（.NET / Mono），写入 `godot.engine_path`。GUI 启动会弹窗检测；FFmpeg 可 `setup install ffmpeg`。

## Workflow

```bash
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4
# exit 2 → fix plan → pipeline reset --task-id <id> → run again
```

## Read next

| Need | Doc |
|------|-----|
| CLI + brief fields + matting | [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) |
| Six roles + tester | [`docs/AGENT-ROUTING.md`](docs/AGENT-ROUTING.md) |
| Design vs production, iteration | [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md) |
| `pipeline run` phases | [`resources/skills/orchestrator/pipeline-schedule.md`](resources/skills/orchestrator/pipeline-schedule.md) |
| Autonomous QA | `python gamefactory.py test run --project ... --brief ...` |

## Critical rules

1. **Validate before matting** — `exit 2` → regenerate prompt.
2. **Animation** — raw still to Seedance; idle = separate `*_nobg.png`, not frame 0.
3. **Video frames** — `video matte-frames --engine ai`, not `image remove-bg`.
4. **Image post** — `--input` / `--output` (not `-i`/`-o`).
5. **No scope creep** — godot-developer implements brief / Production Delta only.

## Hermes (optional)

Brief + prompt craft via Hermes; batch assets via **`pipeline run`**:

```text
terminal(command="cd cli && python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4", workdir="<repo>", pty=true)
```

Install: [`docs/HERMES-CODEX.md`](docs/HERMES-CODEX.md)
