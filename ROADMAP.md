# Game AI Foundry — Roadmap

| | |
|--|--|
| **读者** | 维护者、贡献者 |
| **侧重** | **进度、里程碑 %、Backlog** |
| **不写** | CLI 复制块、抠图规则、角色表 — 见 [`docs/README.md`](docs/README.md) |

## Vision

**An AI-driven game factory.** Describe a game idea in natural language → AI generates all assets (sprites, animations, music, code) → assembles them into a working Godot project → you play it.

Orchestrated by **Agent + Skill + `gamefactory` CLI** (Hermes / Cursor / Codex via terminal). **Electron GUI** is the primary local interface — **AI 公司对话前台**（策划 / 项目经理 / 程序员，可多实例）；Hermes/Codex/Cursor 是 **②③ 的 executor CLI**，不打包进 Release。

**Contract rule:** after brief export（`brief chat export` 或兼容 `brief brainstorm export`），**`brief.json` is the single source of truth**.

**Iteration rule:** post-demo changes → [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md).

---

## Current Status (2026-07-17)

> **v0.0.5 可用边界** → [`docs/RELEASE-NOTES-0.0.5.md`](docs/RELEASE-NOTES-0.0.5.md)  
> 收：AI 公司前台 + 分诊一键执行 + 流式日志 + Delta。不收：首次引导完整版、视觉硬门禁、Windows E2E 签字。

### ✅ Done

**Seven-agent pipeline**
- orchestrator / prompt-crafter / image-generator / video-generator / godot-assembler / godot-developer / tester
- Handoff JSON + skills in `resources/skills/`
- Agent routing: `agents show` / `agents resolve` — [`docs/AGENT-ROUTING.md`](docs/AGENT-ROUTING.md)

**Brief frozen contract**
- `brief validate` / export with `brief_meta`
- P0 gameplay fields + `animation_graphs[]`
- **GUI 主路径**：策划岗 `brief chat`（host-chat → 落实才写 brief）
- CLI 兼容：`brief brainstorm`（问卷式 merge；GUI 已不走）

**Construction system（施工体系）** — 多轮迭代，非「一句话一次完美」
- `production derive|validate|show` — brief → 工程蓝图 `production.json`
- `godot scaffold` — 可编译 Godot C# 壳（场景 / InputMap / 占位脚本 / 单测工程）
- `project progress` — `progress.json` 任务与验收续作账本
- 验收金字塔：`godot validate` · `test unit` · `test play`（`assert_*` + `--task`）· `test regression`
- Godot 子进程注入 toolchain `PATH` / `DOTNET_ROOT`
- Vendored Godot skills：`resources/skills/godot-developer/vendor/fetasty-godot-skills/`
- 文档：[`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md)

**Pipeline program runner**
- `pipeline plan` / `run` / `status` / `reconcile` — manifest DAG, `--jobs` parallel
- GUI `/plan` `/run --run-prompts` + board panel

**GUI — AI 公司前台（主体）**
- 同事列表（roster）：多实例雇佣 / 改名 / 解雇；会话按 instance 隔离
- ① 策划：`host-chat` → `commit-brief`（`brief chat`）
- ②③：`agent turn` → executor CLI（Hermes / Codex / Cursor agent）
- 分诊 → progress note + `plans/handoffs/`；程序员 turn 注入未读 handoff
- GUI 闭环可见性：未读角标 / 横幅、「切换到程序员」、关单提示
- Chat-first UI、media preview、command guide（`/guide`）
- Provider 设置：生文 / 生图 / 生视频；`provider_accounts`；环境面板 + 执行器向导
- **Release**：embedded Python + rembg + electron-builder

**Doctor & toolchain**
- `doctor --json` — API keys, executors, capabilities
- 自动安装：FFmpeg、Godot .NET、.NET SDK
- `setup executor status|step` — 执行器 CLI、Codex 登录、Hermes API 同步
- rembg：Release 内嵌；FFmpeg 多源 fallback

**Documentation**
- [`docs/HOST-CHAT-PRODUCT.md`](docs/HOST-CHAT-PRODUCT.md) — AI 公司前台产品
- [`docs/TOOLS.md`](docs/TOOLS.md) · [`docs/GUI-CONFIG.md`](docs/GUI-CONFIG.md) · [`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md)

**Tests**: CLI unit tests cover production / progress / scaffold / host-chat / agent-turn / handoff + toolchain

**E2E smoke**
- [x] e2e-smoke-brief → plan → run
- [x] Godot + .NET real install verified (macOS)
- [x] construction smoke：`scaffold` → `validate` → `test unit` → `test play --skip-analyze` → `test regression`（macOS）

### 🔄 In Progress

- [x] 程序员：多实例 `target_instance_id` 路由；未读按实例过滤
- [x] Production Delta CLI（`production delta` / `apply-delta`）最小切片
- [x] 分诊后 GUI 一键执行白名单 `next_actions`（`project action`）
- [x] Delta → progress 同步（`apply-delta --progress` / `project progress sync`）
- [x] GUI `/delta` 创建并合并 Delta
- [x] 定点 pipeline：`suggest-retry` / 分诊自动带 `reset --task-id` + `run`
- [x] executor / 一键命令流式日志进聊天（复用 pipeline-log）
- [ ] 首次启动引导流（工具链 → API → 执行器 → 策划）— **非 0.0.4 阻塞**
- [ ] Magic Prince full chain re-run under new brief contract
- [ ] 项目经理默认串：全自动跑完验收写回（0.0.4 以一键执行为准）

### 🔜 Next (P0) — 0.0.5+

- [ ] 首次启动引导
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
User（决策人）
        │
        ├─ GUI 同事对话
        │     ① 策划     → brief chat（薄 Chat / Host LLM）
        │     ② 项目经理 → agent turn → executor CLI → handoffs / progress
        │     ③ 程序员   → agent turn → executor CLI → games/
        ├─ GUI 斜杠 / 环境：toolchain + executor wizard
        └─ 外置 Agent：docs/TOOLS.md → terminal → gamefactory CLI
        │
        ▼
   brief.json (Design) ──► production.json ──► scaffold 壳
        │                         │
        │                         ▼
        │                  progress.json + plans/handoffs/
        ▼
   pipeline run ──► assemble ──► games/
        │
        ▼
   godot-developer（Pass 4）──► validate / unit / play / regression
```

产品心智 → [`docs/HOST-CHAT-PRODUCT.md`](docs/HOST-CHAT-PRODUCT.md)

---

## Milestones

| Milestone | Progress | Notes |
|-----------|----------|-------|
| M1 Video + Godot pipeline | ~100% | CLI complete |
| M2 Hermes + pipeline | ~92% | Executor wizard + Hermes API sync |
| M3 GUI | ~96% | 0.0.4 目标：AI 公司前台 + 一键分诊命令 + 流式日志 |
| M4 Brief → playable（迭代施工） | ~82% | Delta + progress sync；全自动验收串待 0.0.5 |
| M5 Gameplay (Pass 4) | ~75% | scaffold 壳 + unit/play 门禁；玩法填满靠多轮 Agent |

---

## Quick Start

→ [`README.md`](README.md) · CLI → [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) · 工具与 Agent → [`docs/TOOLS.md`](docs/TOOLS.md) · 施工 → [`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md) · GUI 前台 → [`docs/HOST-CHAT-PRODUCT.md`](docs/HOST-CHAT-PRODUCT.md)
