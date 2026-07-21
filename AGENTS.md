# Game AI Foundry — Codex / Agent Instructions

> **One-pager for Codex.** Details live elsewhere — see [`docs/README.md`](docs/README.md).

**Flow:** AI for brief + prompts → **`pipeline run`** for assets (no per-step Hermes).

## Setup

```bash
cd cli
pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json
python gamefactory.py setup check --json   # FFmpeg / Godot / .NET
python gamefactory.py doctor --json        # API keys、executors、capabilities
```

**本机工具**：FFmpeg / Godot / .NET 可 `setup install` 或 GUI 启动自动装；**rembg** 在 Release 内嵌 Python 中自带。详见 [`docs/TOOLS.md`](docs/TOOLS.md)。

**执行器**（推荐）：`setup executor status --json`；GUI **环境 → 执行器** 或 `setup executor step …`。

## Workflow

```bash
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4
# exit 2 → fix plan → pipeline reset --task-id <id> → run again
```

## Read next

| Need | Doc |
|------|-----|
| **Tools, config, troubleshooting** | [`docs/TOOLS.md`](docs/TOOLS.md) |
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

## Anvil（可选工作流）

全流程改动走 Anvil：`req` → `plan` → `code` → `review` → `compound`。  
已确认需求与可执行计划见 `docs/anvil/brainstorms/`、`docs/anvil/plans/`。简单单点修复可不走完整流程。

## Hermes (optional)

Brief + prompt craft via Hermes; batch assets via **`pipeline run`**:

```text
terminal(command="cd cli && python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4", workdir="<repo>", pty=true)
```

Install: [`docs/HERMES-CODEX.md`](docs/HERMES-CODEX.md)
