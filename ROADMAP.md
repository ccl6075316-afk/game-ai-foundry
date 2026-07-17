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

## Current Status (2026-07-16)

### ✅ Done

**Seven-agent pipeline**
- orchestrator / prompt-crafter / image-generator / video-generator / godot-assembler / godot-developer / tester
- Handoff JSON + skills in `resources/skills/`
- Agent routing: `agents show` / `agents resolve` — [`docs/AGENT-ROUTING.md`](docs/AGENT-ROUTING.md)

**Brief frozen contract**
- `brief validate` / `brief brainstorm export` with `brief_meta`
- P0 gameplay fields + `animation_graphs[]`
- GUI `/brief` multi-turn brainstorm

**Construction system（施工体系）** — 多轮迭代，非「一句话一次完美」
- `production derive|validate|show` — brief → 工程蓝图 `production.json`
- `godot scaffold` — 可编译 Godot C# 壳（场景 / InputMap / 占位脚本 / 单测工程）
- `project progress` — `progress.json` 任务与验收续作账本
- 验收金字塔：`godot validate` · `test unit` · `test play`（`assert_*` + `--task`）· `test regression`
- Godot 子进程注入 toolchain `PATH` / `DOTNET_ROOT`（修复「检测成功但 import 找不到 dotnet」）
- Vendored Godot skills：`resources/skills/godot-developer/vendor/fetasty-godot-skills/`
- 文档：[`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md)

**Pipeline program runner**
- `pipeline plan` / `run` / `status` / `reconcile` — manifest DAG, `--jobs` parallel
- GUI `/plan` `/run --run-prompts` + board panel

**GUI (Electron + React)**
- Chat-first UI, media preview, command guide (`/guide`)
- **Provider 设置重构**：生文 / 生图 / 生视频；`provider_accounts` 多账号；DeepSeek / Kimi / GLM 预设
- **环境面板**：本机工具列表 + **执行器分步向导**（Hermes / Cursor / Codex）
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
- [`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md) — 施工体系
- GUI 指南推荐配置 Agent

**Tests**: CLI unit tests cover production / progress / scaffold / unit / regression / task playtest + toolchain

**E2E smoke**
- [x] e2e-smoke-brief → plan → run
- [x] Godot + .NET real install verified (macOS)
- [x] construction smoke：`scaffold` → `validate` → `test unit` → `test play --skip-analyze` → `test regression`（macOS）

### 🔄 In Progress

- [ ] GUI **三对话 Tab**：Brief 创建 / 产品 Host / 程序员（见 [`docs/HOST-CHAT-PRODUCT.md`](docs/HOST-CHAT-PRODUCT.md)）
- [ ] GUI 会话管理 + 上下文（抄开源壳；按 role 持久化）
- [ ] Brief Tab：`host-chat` → `commit-brief` 接线（替换默认 brainstorm merge）
- [ ] 产品 Host：分诊（bug / 图 / 不符 brief / 改需求）+ 派工
- [ ] 程序员 Tab：接 executor 或内嵌工具环
- [ ] 首次启动引导流（工具链 → API → 执行器 → Brief Tab）
- [ ] Magic Prince full chain re-run under new brief contract
- [ ] Orchestrator / Host 默认串：progress → 本轮 task → 验收 → 写回

### 🔜 Next (P0)

- [ ] **修改闭环**（最大场景）：Host 反馈入口 → 分诊 → pipeline 定点重跑 / 程序员施工 → 验收 → progress
- [ ] **Production Delta / Change Request CLI**（想法变更 → 增量改蓝图）
- [ ] 视觉 QA 硬门禁（`test analyze` 失败可卡本轮）
- [ ] One-shot brief → plan → run from GUI without manual path juggling
- [ ] Windows Release E2E on clean VM

### ⬜ Not Started / Backlog

- [ ] 子场景 / 模块隔离 harness（L3）
- [ ] GdUnit4 场景树单测（可选；现有 L1 为 `dotnet test` + PlayerStats）
- [ ] playtest `change_scene` / `--craft` 长剧本
- [ ] Validation Report 与 `project-state.json` 统一
- [ ] Audio generation CLI
- [ ] Hermes Kanban / auto multi-session orchestration
- [ ] CI / matting regression tests with real assets
- [ ] Frame resize 128×128 post-matte

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
   brief.json (Design) ──► production.json (工程蓝图) ──► scaffold 壳
        │                         │
        │                         ▼
        │                  progress.json（续作）
        ▼
   pipeline run ──► assemble / inject ──► games/
        │
        ▼
   godot-developer（Pass 4）──► validate / unit / play / regression
```

---

## Milestones

| Milestone | Progress | Notes |
|-----------|----------|-------|
| M1 Video + Godot pipeline | ~100% | CLI complete |
| M2 Hermes + pipeline | ~92% | Executor wizard + Hermes API sync |
| M3 GUI | ~90% | Provider 多账号、工具链自动装、执行器向导、TOOLS.md |
| M4 Brief → playable（迭代施工） | ~78% | production / scaffold / progress / 验收金字塔已通；Delta + 编排待补 |
| M5 Gameplay (Pass 4) | ~75% | scaffold 壳 + unit/play 门禁；玩法填满靠多轮 Agent |

---

## Quick Start

→ [`README.md`](README.md) · CLI → [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) · 工具与 Agent → [`docs/TOOLS.md`](docs/TOOLS.md) · 施工 → [`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md)
