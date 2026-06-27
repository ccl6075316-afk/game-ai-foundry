# Game AI Foundry

**AI-driven game factory** — describe a game in natural language → freeze a **brief JSON** → generate sprites, animations, and Godot projects → hand off gameplay code to a developer agent.

Orchestrated by **Agent + Skill + `gamefactory` CLI** (Cursor / Hermes). **Electron GUI** (`start-gui.bat`) is the primary local interface for brainstorm → plan → run.

## How it works

```
Brainstorm → brief.json (frozen contract)
                │
                ▼
         pipeline plan / run  →  output/{slug}/
                │              assets-manifest.json
                ▼
         godot assemble       →  games/{slug}/
                │
                ▼
         godot dev-context     →  godot-developer writes C# gameplay
```

After export, **`brief.json` is the only source of truth** — pipeline, prompt-crafter, assembler, and godot-developer read the file, not chat history.

See [`ROADMAP.md`](ROADMAP.md) for milestones and [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) for agent handoff details.

## Quick start

### GUI (recommended)

```bat
start-gui.bat
```

Configure **设置 → 项目经理** API key → `/brief` → export → `/plan` → `/run --run-prompts`

### CLI

```bash
cd cli
pip install -r requirements.txt

# Validate a brief (export gate)
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json

# Plan + run asset pipeline
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4

# Godot assemble + dev handoff
python gamefactory.py godot assemble --assemble-file ../plans/godot_asset-brief.example.json
python gamefactory.py godot dev-context --brief ../resources/asset-brief.example.json --project ../games/asset-brief.example -o ../plans/dev_asset-brief.example.json

python gamefactory.py doctor --json
```

Config template: `resources/config.example.json` → `~/.gamefactory/config.json`

## Brief contract (summary)

| Section | Purpose |
|---------|---------|
| `project` | Title, art direction, **genre**, **gameplay_loop**, **session_goal**, **controls**, **viewport**, **camera** |
| `assets[]` | Every asset: `name`, `type`, `usage`, `usage_description`, `display_size`, `generate_method` |
| `animation_graphs[]` | Clip transitions (`from` / `to` / `then`) for multi-clip characters |
| `brief_meta` | Stamped on export: `contract_version`, `frozen_at` |

Asset types: `character`, `character_pose`, `icon_kit`, `texture`, `background`, **`audio`**

Optional P1 fields: `project.visual_reference`, `project.hud[]`, parallax (`parallax_order`, `scroll_factor`), audio (`audio_loop`, `generate_method: procedural|file`).

Example in git: [`resources/asset-brief.example.json`](resources/asset-brief.example.json)  
Local project briefs (`resources/*-brief.json`) are gitignored.

## Architecture

```
game-ai-foundry/
├── cli/                         # gamefactory CLI
│   ├── brief.py                 # Brief types + export validation
│   ├── assets_manifest.py       # Asset ledger + runtime bindings
│   ├── pipeline_manifest.py     # brief → task DAG
│   ├── pipeline_runner.py       # Subprocess runner (--jobs N)
│   ├── godot_assemble.py        # Pass 3: PNG → Godot .NET project
│   └── godot_dev.py             # Pass 4: dev-context handoff
├── resources/
│   ├── asset-brief.example.json # Canonical brief example (in git)
│   ├── skills/                  # Per-agent skill docs
│   └── godot-templates/dotnet/  # Godot 4 .NET template
├── tests/fixtures/              # E2E smoke briefs + prison reference assets
├── gui/                         # Electron + React chat UI
├── pipeline/                    # Manifest JSON (local runs, gitignored)
├── output/                      # Generated assets (gitignored)
└── games/                       # Godot projects (gitignored)
```

## Six agents

| Agent | CLI / role |
|-------|------------|
| orchestrator | Brief brainstorm, pipeline triage |
| prompt-crafter | `prompt craft` → plan JSON |
| image-generator | `image generate` |
| video-generator | `video generate`, split/matte frames |
| godot-assembler | `godot assemble`, `import-sprites` |
| godot-developer | Reads `dev-context` JSON, writes C# gameplay |

Routing: `python gamefactory.py agents show` — see [`docs/AGENT-ROUTING.md`](docs/AGENT-ROUTING.md)

## Tests

```bash
cd cli && python -m unittest discover -q
```

**73 tests** (1 skipped) — brief contract, pipeline manifest, assets manifest, Godot assemble, E2E smoke.

## Supported AI providers

| Provider | Model | Type |
|----------|-------|------|
| OpenRouter | `google/gemini-3.1-flash-image` | Image |
| Volcengine ARK | `doubao-seedance-*` | Video (i2v) |

Audio: brief schema supports `type: audio` with `procedural` / `file` placeholders; **BGM/SFX generation CLI not implemented yet**.

## Prerequisites

- Python 3.11+
- ffmpeg (video frame split)
- Godot 4.x **.NET** build (assemble + validate)
- API keys: OpenRouter (image/prompt), Volcengine ARK (video)

## License

MIT
