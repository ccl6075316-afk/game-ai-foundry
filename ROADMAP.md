# Game AI Foundry — Roadmap

## Vision

**An AI-driven game factory.** Describe a game idea in natural language → AI generates all assets (sprites, animations, music, code) → assembles them into a working Godot project → you play it.

The pipeline is orchestrated by **Hermes Agent** (Nous Research), which calls standalone CLI tools. GUI (Electron + React) is a skin on top — the CLI is the engine.

## Current Status (2025-06-25)

### ✅ Done

**CLI Toolchain** (`cli/`)
- `gamefactory image generate` — text-to-image via OpenRouter (Nano Banana / GPT-5-Image)
- `gamefactory image slice` — auto-detect sprites from sprite sheet (OpenCV contour detection)
- `gamefactory image remove-bg` — background removal (rembg)
- `gamefactory image resize` — batch resize
- `gamefactory video generate` — stub for Seedance (Volcengine ARK) — **API endpoint found, auth works, models need activation**
- `gamefactory video split-frames` — ffmpeg frame extraction
- `gamefactory godot init` — create empty Godot project from template
- `gamefactory godot inject` — inject GDScript into project
- `gamefactory godot validate` — validate project structure

**Config**
- `~/.gamefactory/config.json` — API keys, proxy, model defaults
- Proxy support for OpenRouter (works through Clash Verge `127.0.0.1:7897`)

**AI Providers Integrated**
| Provider | Auth | Status |
|----------|------|--------|
| OpenRouter (Nano Banana) | API Key | ✅ Working |
| OpenRouter (GPT-5-Image) | API Key | ✅ Working |
| Volcengine ARK (Seedance) | API Key | 🔶 Auth OK, models pending |

### 🔶 In Progress

- **Seedance video generation** — Volcengine ARK API key works (`/api/v3/responses` returns 200 for VLM models), but Seedance models return 500 (likely post-activation propagation delay, or need endpoint creation in ARK console at `https://console.volcengine.com/ark/region:ark+cn-beijing/endpoint`)

### ⬜ Not Started

- **Hermes ↔ gamefactory integration** — Hermes calling `gamefactory` via `terminal()` tool
- **Electron + React GUI** — desktop app shell
- **GUI ↔ Hermes IPC** — stdio pipe, MCP protocol (JSON-RPC)
- **Godot full pipeline** — auto-generate complete game scenes, not just init
- **Audio generation** — music/SFX via Suno API or similar
- **Automated end-to-end** — "make me a platformer" → playable game

## Architecture (Planned)

```
User (Telegram / GUI)
        │
        ▼
   Hermes Agent (DeepSeek V4 Pro)
        │ terminal()
        ▼
   gamefactory CLI ──┬── image generate  → OpenRouter API
                     ├── image slice     → OpenCV
                     ├── image remove-bg → rembg
                     ├── video generate  → Volcengine ARK
                     ├── video split     → ffmpeg
                     └── godot *         → Godot headless CLI
        │
        ▼
   output/  (generated assets)
        │
        ▼
   Godot project  (assembled game)
```

**Future GUI path:**
```
React (Renderer) ↔ contextBridge IPC ↔ Electron Main Process ↔ stdio ↔ Hermes ↔ terminal ↔ gamefactory
```

## Next Milestones

### M1: Seedance video generation working
- [ ] Resolve 500 error — create ARK inference endpoint or wait for activation
- [ ] Implement `gamefactory video generate` → actual MP4 output
- [ ] End-to-end test: prompt → video → split-frames → sprites

### M2: Hermes integration
- [ ] Hermes calls `gamefactory image generate` via terminal
- [ ] Hermes calls `gamefactory video generate`
- [ ] Hermes calls `gamefactory godot init` + `inject`
- [ ] Document prompt patterns for Hermes

### M3: GUI skeleton
- [ ] Electron app with React frontend
- [ ] IPC bridge to Hermes
- [ ] Asset preview panel
- [ ] Godot project browser

### M4: Full pipeline demo
- [ ] "Make me a space shooter" → complete playable Godot project
- [ ] All assets AI-generated
- [ ] One-click export

## Quick Start for AI Agents

Reading this project? Here's what you need to know:

1. **CLI lives in `cli/`** — `gamefactory.py` is the entry point. Run `python gamefactory.py --help`.
2. **Config** at `~/.gamefactory/config.json` — contains API keys and defaults.
3. **Output** goes to `output/` (gitignored).
4. **Godot engine** at `E:\Godot_v4.6.1-stable_mono_win64\`.
5. **Proxy** — OpenRouter needs VPN proxy. Clash Verge at `127.0.0.1:7897`.
6. **Hermes** orchestrates. Current session runs on Telegram.
7. **Windows** host. Use bash (git-bash) for terminal commands. Python 3.11 via `uv`.
