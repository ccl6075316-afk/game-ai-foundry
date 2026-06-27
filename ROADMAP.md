# Game AI Foundry — Roadmap

## Vision

**An AI-driven game factory.** Describe a game idea in natural language → AI generates all assets (sprites, animations, music, code) → assembles them into a working Godot project → you play it.

Orchestrated by **Agent + Skill + `gamefactory` CLI** (Hermes / Cursor via terminal). **Electron GUI** is the primary local interface; Hermes/Codex are dev-time executors, not shipped with the repo.

---

## Current Status (2026-06-25)

### ✅ Done

**Six-agent pipeline**
- orchestrator / prompt-crafter / image-generator / video-generator / godot-assembler / **godot-developer**
- Handoff JSON (`plan_io.py`) + skills in `resources/skills/`
- Agent routing: `agents show` / `agents resolve` — see `docs/AGENT-ROUTING.md`

**Brief & orchestration**
- **Brief brainstorm** — multi-turn requirement refinement (`brief brainstorm start|turn|export`)
- Skill: `resources/skills/orchestrator/brief-brainstorm.md`
- GUI: natural language → brainstorm → export `resources/{slug}-brief.json` → `/plan` → `/run`
- LLM config: `config.host` (项目经理), fallbacks for `prompt` / `code` (`cli/llm_config.py`)

**Image / Video / Godot CLI** — unchanged from prior milestones (OpenRouter, Seedance, assemble, Pass 4 dev-context)

**Pipeline program runner**
- `pipeline plan` / `run` / `status` — manifest DAG, `--jobs` parallel
- Default skips `prompt.craft` unless `--run-prompts`
- Paths derived from brief slug: `pipeline/{slug}.json`, `output/{slug}`, `games/{slug}`

**GUI (Electron + React)** — `start-gui.bat`
- Chat-first UI, settings (岗位语言 + API keys), pipeline board
- Media preview in chat (`gamefactory-media://`)
- Commands: `/brief` `/doctor` `/plan` `/run` `/board` `/settings` `/godot`
- **No hardcoded game template** — workflow is brief-driven, not prison-demo preset

**Doctor & env**
- `gamefactory doctor --json` — Python, Godot, API keys, executor availability

**Tests**: 38+ CLI unit tests (incl. brief brainstorm, llm_config, env_discover)

### 🔄 In Progress

- [x] Full E2E smoke (`e2e-smoke-brief` → plan → run --run-prompts) — 4/4 tasks
- [ ] Full E2E with Godot assemble on smoke brief
- [ ] Frame resize 128×128 post-matte

### 🔜 Next (P0)

- [ ] One-shot brief → plan → run from GUI without manual path juggling
- [x] GUI `/run --run-prompts`
- [x] Prison test assets relocated to `tests/fixtures/` (not release defaults)

### ⬜ Not Started

- [ ] Hermes Kanban / auto multi-session orchestration
- [ ] Audio generation (BGM/SFX)
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
   gamefactory CLI ──┬── brief brainstorm → brief JSON
                     ├── pipeline plan/run → output/
                     ├── image / video generation
                     └── godot assemble → games/  (gitignored)
        │
        ▼
   godot-developer (Codex/Cursor) — gameplay code
```

---

## Milestones

| Milestone | Progress | Notes |
|-----------|----------|-------|
| M1 Video + Godot pipeline | ~100% | CLI complete |
| M2 Hermes + pipeline | ~90% | Kanban optional |
| M3 GUI | ~75% | Chat + brief + board; needs polish & E2E |
| M4 Brief → playable | ~45% | Brainstorm + plan wired; stable E2E pending |
| M5 Gameplay (Pass 4) | ~60% | dev-context handoff; executor on host |

---

## Quick Start

1. **GUI**: `start-gui.bat` → configure **设置 → 项目经理** API key → `/brief`
2. **CLI**: `cd cli && python gamefactory.py --help`
3. **Config**: `~/.gamefactory/config.json` (see `resources/config.example.json`)
4. **Output**: `output/`, `games/`, `pipeline/`, `plans/` (gitignored — local test runs)
5. **Example brief only in git**: `resources/asset-brief.example.json`
