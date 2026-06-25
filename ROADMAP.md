# Game AI Foundry — Roadmap

## Vision

**An AI-driven game factory.** Describe a game idea in natural language → AI generates all assets (sprites, animations, music, code) → assembles them into a working Godot project → you play it.

Orchestrated by **Agent + Skill + `gamefactory` CLI** (Hermes / Cursor via terminal). GUI (Electron) is future skin on top.

---

## Current Status (2026-06-25)

### ✅ Done

**Four-agent pipeline**
- orchestrator / prompt-crafter / image-generator / **video-generator**
- Handoff JSON (`plan_io.py`) + skills in `resources/skills/`

**Image**
- `image generate --plan-file` via OpenRouter
- Pure white background validation (fail → prompt-crafter regenerate)
- character / background / icon_kit separate pipelines
- `trim` → `remove-bg` (color key) → `validate-matting`
- `slice` (grid), `resize`

**Video (Seedance)**
- `seedance_api.py` — correct async task API
- `video generate` — image-to-video / text-to-video (pro/fast/mini)
- Cost controls: model, duration, resolution, ratio, audio (brief + config + CLI)
- `video split-frames --frames N` — default 8 sprite frames, evenly spaced
- `video matte-frames --engine ai` — rembg BiRefNet for video frames (separate from static color-key)

**Godot (scaffold only)**
- `godot init` / `inject` / `validate` / `open` / `export`

**Verified demo**: prison character, scene, icons, walk animation (img2video → split → matte)

### 🔜 Next (P0)

- [ ] `godot import-sprites` — PNG frames → `res://` + SpriteFrames
- [ ] Godot scene templates (AnimatedSprite2D, player)
- [ ] orchestrator `godot-assemble` skill
- [ ] E2E: brief → assets → Godot playable walk animation

### ⬜ Not Started

- [ ] Hermes ↔ gamefactory terminal integration
- [ ] Electron + React GUI
- [ ] GUI ↔ Hermes IPC (MCP/JSON-RPC) — **not required for Godot CLI work**
- [ ] Audio generation (BGM/SFX)
- [ ] One-shot demo: "make me a platformer" → playable export
- [ ] CI / matting regression tests

---

## Architecture

```
User (Cursor / Hermes / future GUI)
        │
        ▼
   Agent + Skills
        │ terminal()
        ▼
   gamefactory CLI ──┬── image generate   → OpenRouter
                     ├── video generate   → Volcengine Seedance
                     ├── video split/matte → ffmpeg + rembg
                     ├── image trim/remove-bg → OpenCV color key
                     └── godot *          → Godot headless CLI
        │
        ▼
   output/  →  Godot project (assembly TBD)
```

---

## Milestones

| Milestone | Progress | Notes |
|-----------|----------|-------|
| M1 Video pipeline | ~95% | Missing Godot import + playable loop |
| M2 Hermes integration | 0% | |
| M3 GUI skeleton | 0% | |
| M4 Full playable demo | ~20% | Assets work; no auto Godot assembly |

---

## Quick Start for AI Agents

1. **Read first**: `docs/AI-HANDOFF.md` (detailed status, commands, config)
2. **CLI**: `cd cli && python gamefactory.py --help`
3. **Config**: `~/.gamefactory/config.json` (see `resources/config.example.json`)
4. **Output**: `output/` (gitignored)
5. **Godot**: `E:\Godot_v4.6.1-stable_mono_win64\` — set `godot.engine_path` in config
6. **Proxy**: OpenRouter needs Clash `127.0.0.1:7897`; Seedance usually direct
7. **Windows** host; Python 3.11+
