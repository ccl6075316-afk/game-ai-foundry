# Game AI Foundry — Roadmap

## Vision

**An AI-driven game factory.** Describe a game idea in natural language → AI generates all assets (sprites, animations, music, code) → assembles them into a working Godot project → you play it.

Orchestrated by **Agent + Skill + `gamefactory` CLI** (Hermes / Cursor via terminal). **Electron GUI** is the primary local interface; Hermes/Codex are dev-time executors, not shipped with the repo.

**Contract rule:** after brainstorm export, **`brief.json` is the single source of truth** — pipeline, skills, and godot-developer must not rely on session memory.

---

## Current Status (2026-06-25)

### ✅ Done

**Six-agent pipeline**
- orchestrator / prompt-crafter / image-generator / video-generator / godot-assembler / **godot-developer**
- Handoff JSON (`plan_io.py`) + skills in `resources/skills/`
- Agent routing: `agents show` / `agents resolve` — see `docs/AGENT-ROUTING.md`

**Brief frozen contract**
- `brief validate` / `brief brainstorm export` with `brief_meta` (`contract_version`, `frozen_at`)
- Asset table: `usage`, `usage_description`, `display_size`, `generate_method`
- **P0 gameplay:** `genre`, `gameplay_loop`, `session_goal`, `player_asset`, `controls`, `viewport`, `camera`
- **P1 extensions:** `visual_reference`, `type: audio` (`music`/`sfx`), parallax fields, `project.hud[]` + `ui_element`
- **`animation_graphs[]`:** clip transitions (`from`/`to`/`then`/`bidirectional`) — godogen-style state machine in JSON
- Skill: `resources/skills/orchestrator/brief-brainstorm.md`

**Assets manifest**
- `output/{slug}/assets-manifest.json` — pipeline stage + Godot runtime bindings
- Wired through `pipeline plan/run/record/reconcile` and post-`godot assemble`

**Brief & orchestration**
- **Brief brainstorm** — multi-turn refinement (`brief brainstorm start|turn|export`)
- GUI: natural language → brainstorm → export `resources/{slug}-brief.json` → `/plan` → `/run`
- LLM config: `config.host` (项目经理), fallbacks for `prompt` / `code` (`cli/llm_config.py`)

**Image / Video / Godot CLI**
- OpenRouter image gen, Seedance i2v, trim/split/matte, Godot .NET assemble
- `godot dev-context` — Pass 4 handoff for godot-developer (brief + assets-manifest + runtime bindings)

**Pipeline program runner**
- `pipeline plan` / `run` / `status` / `reconcile` — manifest DAG, `--jobs` parallel
- Default skips `prompt.craft` unless `--run-prompts`
- Runtime-only assets (`audio` + `procedural`/`file`) skip image pipeline tasks
- Paths from brief slug: `pipeline/{slug}.json`, `output/{slug}`, `games/{slug}`

**GUI (Electron + React)** — `start-gui.bat`
- Chat-first UI, settings (岗位语言 + API keys), pipeline board
- Media preview in chat (`gamefactory-media://`)
- Commands: `/brief` `/doctor` `/plan` `/run` `/board` `/settings` `/godot`
- Brief-driven workflow (no hardcoded prison-demo preset)

**Doctor & env**
- `gamefactory doctor --json` — Python, Godot, API keys, executor availability

**Tests**: **73** CLI unit tests (1 skipped) — brief contract, transitions, assets manifest, E2E smoke + Godot assemble

**E2E smoke**
- [x] `e2e-smoke-brief` → plan → run --run-prompts — asset tasks
- [x] Full smoke with Godot assemble — 5/5 tasks + `godot validate`

### 🔄 In Progress

- [ ] Frame resize 128×128 post-matte
- [ ] Magic Prince full chain re-run under new brief contract (`pipeline plan --merge` → run → dev-context)

### 🔜 Next (P0)

- [ ] One-shot brief → plan → run from GUI without manual path juggling
- [x] GUI `/run --run-prompts`
- [x] Prison test assets relocated to `tests/fixtures/` (not release defaults)
- [ ] Update `ROADMAP` / `AI-HANDOFF` on each milestone (this file)

### ⬜ Not Started

- [ ] Audio **generation** CLI (brief schema ready; `procedural`/`file` placeholders only)
- [ ] Parallax layer assets in example brief + Godot ParallaxBackground wiring
- [ ] `video_start_from` chained i2v (godogen Start From)
- [ ] Hermes Kanban / auto multi-session orchestration
- [ ] CI / matting regression tests with real assets

---

## Architecture

```
User (GUI / Cursor / Hermes)
        │
        ▼
   orchestrator (+ brief brainstorm)
        │
        ▼
   brief.json (frozen) ──► assets-manifest.json
        │
        ▼
   gamefactory CLI ──┬── pipeline plan/run → output/
                     ├── image / video generation
                     ├── godot assemble → games/  (gitignored)
                     └── godot dev-context → plans/dev_*.json
        │
        ▼
   godot-developer (Codex/Cursor) — gameplay C# from dev-context
```

---

## Milestones

| Milestone | Progress | Notes |
|-----------|----------|-------|
| M1 Video + Godot pipeline | ~100% | CLI complete |
| M2 Hermes + pipeline | ~90% | Kanban optional |
| M3 GUI | ~75% | Chat + brief + board; polish & one-click E2E pending |
| M4 Brief → playable | ~65% | Frozen contract + manifest; Magic Prince E2E pending |
| M5 Gameplay (Pass 4) | ~70% | dev-context handoff; executor on host |

---

## Quick Start

1. **GUI**: `start-gui.bat` → configure **设置 → 项目经理** API key → `/brief`
2. **CLI**: `cd cli && python gamefactory.py --help`
3. **Validate brief**: `python gamefactory.py brief validate --brief ../resources/asset-brief.example.json`
4. **Config**: `~/.gamefactory/config.json` (see `resources/config.example.json`)
5. **Output**: `output/`, `games/`, `pipeline/`, `plans/` (gitignored — local test runs)
6. **Example brief in git**: `resources/asset-brief.example.json`
7. **Local project briefs**: `resources/*-brief.json` (gitignored, e.g. `magic-prince-brief.json`)
