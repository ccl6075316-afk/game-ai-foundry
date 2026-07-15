# Game AI Foundry — Roadmap

| | |
|--|--|
| **读者** | 维护者、贡献者 |
| **侧重** | **进度、里程碑 %、Backlog** |
| **不写** | CLI 复制块、抠图规则、角色表 — 见 [`docs/README.md`](docs/README.md) |

## Vision

**An AI-driven game factory.** Describe a game idea in natural language → AI generates all assets (sprites, animations, music, code) → assembles them into a working Godot project → you play it.

Orchestrated by **Agent + Skill + `gamefactory` CLI** (Hermes / Cursor / Codex via terminal). **Electron GUI** is the primary local interface; Hermes/Codex/Cursor are **not bundled** — user installs via GUI wizard or CLI.

**Contract rule:** after brainstorm export, **`brief.json` is the single source of truth**.

**Iteration rule:** post-demo changes → [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md).

---

## Current Status (2026-07-15)

### ✅ Done

**Seven-agent pipeline**
- orchestrator / prompt-crafter / image-generator / video-generator / godot-assembler / godot-developer / tester
- Handoff JSON + skills in `resources/skills/`
- Agent routing: `agents show` / `agents resolve` — [`docs/AGENT-ROUTING.md`](docs/AGENT-ROUTING.md)

**Brief frozen contract**
- `brief validate` / `brief brainstorm export` with `brief_meta`
- P0 gameplay fields + `animation_graphs[]`
- GUI `/brief` multi-turn brainstorm

**Pipeline program runner**
- `pipeline plan` / `run` / `status` / `reconcile` — manifest DAG, `--jobs` parallel
- GUI `/plan` `/run --run-prompts` + board panel

**GUI (Electron + React)**
- Chat-first UI, media preview, command guide (`/guide`)
- **Provider 设置重构**：生文 / 生图 / 生视频；`provider_accounts` 多账号；DeepSeek / Kimi / GLM 预设
- **环境面板**：本机工具列表 + **执行器分步向导**（Hermes / Codex / Cursor）
- **环境工具栏**：工具链 + 执行器状态芯片
- Codex/Cursor 角色页：登录说明，隐藏 API Key 项
- **Release**：embedded Python + rembg + electron-builder

**Doctor & toolchain**
- `doctor --json` — API keys, executors, capabilities
- **自动安装**：FFmpeg、Godot .NET、.NET SDK（必需，启动时后台安装）
- `setup executor status|step` — 执行器 CLI 安装、Codex 登录、Hermes API 同步
- rembg：**Release 内嵌**，不再出现在 `setup check` 列表
- FFmpeg 多源 fallback；Godot zip 自动 chmod

**Documentation**
- [`docs/TOOLS.md`](docs/TOOLS.md) — 本机工具配置、纠错、外部 Agent 操作手册
- [`docs/GUI-CONFIG.md`](docs/GUI-CONFIG.md) — Provider vs 执行器边界
- GUI 指南推荐配置 Agent

**Tests**: **~105** CLI unit tests — toolchain, executor_setup, env_discover, llm_config, godot_sources, etc.

**E2E smoke**
- [x] e2e-smoke-brief → plan → run
- [x] Godot + .NET real install verified (macOS)

### 🔄 In Progress

- [ ] GUI 主聊天路由到配置的 host executor（当前 Brief 仍直连 LLM API）
- [ ] 首次启动引导流（工具链 → API → 执行器 → `/brief`）
- [ ] Magic Prince full chain re-run under new brief contract

### 🔜 Next (P0)

- [ ] One-shot brief → plan → run from GUI without manual path juggling
- [ ] Frame resize 128×128 post-matte
- [ ] Windows Release E2E on clean VM

### ⬜ Not Started

- [ ] Change Request / Production Delta CLI
- [ ] Validation Report JSON + `project-state.json`
- [ ] Audio generation CLI
- [ ] Hermes Kanban / auto multi-session orchestration
- [ ] CI / matting regression tests with real assets

---

## Architecture

```
User (GUI / Cursor / Hermes / Codex)
        │
        ├─ GUI chat: LLM API (/brief) + slash commands (/plan, /run, …)
        ├─ GUI env: toolchain auto-install + executor wizard
        └─ External agent: docs/TOOLS.md → terminal → gamefactory CLI
        │
        ▼
   brief.json (frozen) ──► pipeline run ──► output/ ──► games/
        │
        ▼
   godot-developer (Codex/Cursor) — Pass 4 C#
```

---

## Milestones

| Milestone | Progress | Notes |
|-----------|----------|-------|
| M1 Video + Godot pipeline | ~100% | CLI complete |
| M2 Hermes + pipeline | ~92% | Executor wizard + Hermes API sync |
| M3 GUI | ~90% | Provider 多账号、工具链自动装、执行器向导、TOOLS.md |
| M4 Brief → playable | ~65% | Magic Prince E2E + Change Request CLI pending |
| M5 Gameplay (Pass 4) | ~70% | dev-context; Codex wizard in GUI |

---

## Quick Start

→ [`README.md`](README.md) · CLI → [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) · 工具与 Agent → [`docs/TOOLS.md`](docs/TOOLS.md)
