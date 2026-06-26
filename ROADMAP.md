# Game AI Foundry — Roadmap

## Vision

**An AI-driven game factory.** Describe a game idea in natural language → AI generates all assets (sprites, animations, music, code) → assembles them into a working Godot project → you play it.

Orchestrated by **Agent + Skill + `gamefactory` CLI** (Hermes / Cursor via terminal). GUI (Electron) is future skin on top.

---

## Current Status (2026-06-25)

> **Git**：`main` 超前 origin 1 commit（`53d45d1` godot-assembler）；`games/` 已 gitignore，不纳入版本库。

### ✅ Done

**Four-agent pipeline** → **Five-agent pipeline**
- orchestrator / prompt-crafter / image-generator / video-generator / **godot-assembler**
- Handoff JSON (`plan_io.py`) + skills in `resources/skills/`
- Agent routing: `agents show` / `agents resolve` — see `docs/AGENT-ROUTING.md`

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
- `video split-frames --frames N` — **先裁 i2v 头尾（可关）→ 再均匀采样**
- `cli/frame_sequence.py` — 共享 trim-then-sample；`trim_lead` / `trim_trail` 配置项
- `video matte-frames --engine ai` — rembg BiRefNet for video frames (separate from static color-key)

**Godot (.NET assembly)**
- `godot init --template dotnet` — Godot 4 .NET C# 模板
- `godot import-sprites` — trim/sample → PNG → `res://` + SpriteFrames `.tres`
- `godot assemble --assemble-file` — handoff → 工程 + `idle_still` + validate
- `games/` — assemble 产出目录（**gitignored**，默认 `games/<brief-stem>/`）
- Pipeline Pass 3: `{brief}.godot.assemble`（role=`godot-assembler`）

**Hermes / Codex**
- `hermes sync` / `install` / `paths` / `list` / `show` — SKILL.md packages → `~/.hermes/skills`
- 6 skills: orchestrator, prompt-crafter, image-generator, video-generator, **godot-assembler**, codex-delegate
- Docs: `docs/HERMES-CODEX.md`, `docs/AGENT-ROUTING.md`, `AGENTS.md`

**Pipeline 程序 runner**
- `pipeline plan` / `run` / `reset` / `status` — subprocess 自动执行 manifest DAG，`--jobs` 并行
- 默认跳过 `prompt.craft`（需先有 `plans/`）；`--run-prompts` 可含 LLM
- `resources/skills/orchestrator/pipeline-schedule.md`

**Verified demo**: prison walk + **Godot assemble** (`games/prison-demo`)；dino idle；wasteland mutant_boar idle

### 🔄 进行中（本地）

- Pipeline 全链 E2E：`pipeline plan` → `pipeline run` 含 Pass 3 godot.assemble（待跑）

### 🔜 Next (P0)

- [ ] **Pipeline 全链 E2E** — brief → `pipeline run`（含 Pass 3 godot.assemble）→ 可玩工程
- [ ] Frame resize 128×128 post-matte
- [ ] One-shot brief → playable export（编排层，非新 CLI）

### ⬜ Not Started

- [ ] Hermes Kanban / auto multi-session orchestration
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
                     └── godot assemble/import → Godot 4 .NET (C#)
        │
        ▼
   output/  →  games/  (Godot 组装产物，gitignored)
```

---

## Milestones

| Milestone | Progress | Notes |
|-----------|----------|-------|
| M1 Video + Godot pipeline | ~100% | 拆帧 trim/sample + assemble + prison E2E |
| M2 Hermes + pipeline | ~90% | 五 Agent + routing；Kanban 可选 |
| M3 GUI skeleton | 0% | |
| M4 Full playable demo | ~50% | Godot walk 可玩；缺 pipeline 一键 Godot + 一句话编排 |

---

## Quick Start for AI Agents

1. **Read first**: `docs/AI-HANDOFF.md` (detailed status, commands, config)
2. **Agent routing**: `docs/AGENT-ROUTING.md` — executor mix (pipeline / hermes / cursor / codex)
3. **Hermes/Codex**: `docs/HERMES-CODEX.md` — `python gamefactory.py hermes install`
3. **CLI**: `cd cli && python gamefactory.py --help`
3. **Config**: `~/.gamefactory/config.json` (see `resources/config.example.json`)
4. **Output**: `output/` (gitignored)
5. **Godot**: `E:\Godot_v4.6.1-stable_mono_win64\` — set `godot.engine_path` in config
6. **Proxy**: OpenRouter needs Clash `127.0.0.1:7897`; Seedance usually direct
7. **Windows** host; Python 3.11+
