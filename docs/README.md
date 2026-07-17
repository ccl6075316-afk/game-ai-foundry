# 文档索引

各文档 **只写自己那一层**，避免同一流程在多处复制粘贴。

## 当前版本要点（2026-07-17）

- **v0.0.4 可用边界**：[`RELEASE-NOTES-0.0.4.md`](RELEASE-NOTES-0.0.4.md) — AI 公司前台 + 分诊一键执行 + Delta
- **GUI 主路径**：同事（策划 / 项目经理 / 程序员，可多实例）
- **Brief**：策划岗 `brief chat`（落实才写盘）；CLI `brainstorm` 仅兼容
- **最低开工**：OpenRouter（或 LLM Provider）Key → 策划对话落实 brief → `/run`
- **推荐**：再配 Hermes / Cursor / Codex 执行器（②③ Agent 依赖）
- **工具链**：FFmpeg、Godot、.NET 启动自动安装；rembg 打包自带
- **外部 AI**：读 [`TOOLS.md`](TOOLS.md) 代操 Foundry

---

| 文档 | 读者 | 侧重 | 不写什么 |
|------|------|------|----------|
| [`../README.md`](../README.md) | 新人 / GitHub | 功能一览、Quick Start、前置依赖 | 字段 schema、角色边界 |
| [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md) | Host / 全角色 | **设计 vs 施工**、Change Request | CLI 命令、里程碑 |
| [`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md) | Host / 维护者 | **施工体系**：production、壳、验收、进度 | brief 字段全文 |
| [`AI-HANDOFF.md`](AI-HANDOFF.md) | 接手 Agent（中文） | **CLI 速查**、brief 字段、抠图铁律 | 产品方法论、进度表 |
| [`AGENT-ROUTING.md`](AGENT-ROUTING.md) | 混排编排 | **七角色 + executor** | brief 字段全文 |
| [`HERMES-CODEX.md`](HERMES-CODEX.md) | Hermes / Codex 用户 | skill 安装、terminal、`pty=true` | brief schema |
| [`TOOLS.md`](TOOLS.md) | **外部 AI Agent** / 运维 | **工具配置、功能、纠错**、JSON 探测 | brief 字段、设计方法论 |
| [`HOST-CHAT-PRODUCT.md`](HOST-CHAT-PRODUCT.md) | 产品 / GUI | **AI 公司前台**：策划 / 项目经理 / 程序员（可多实例）；文件总线；用户为决策人 | pipeline 命令细节 |
| [`GUI-CONFIG.md`](GUI-CONFIG.md) | GUI / Release 用户 | **Provider、执行器、最低 vs 推荐** | CLI 大全 |
| [`RELEASE.md`](RELEASE.md) | 发布 / 维护者 | 打包、纯净机首次运行 | brief 字段 |
| [`RELEASE-NOTES-0.0.2.md`](RELEASE-NOTES-0.0.2.md) | 用户 | v0.0.2 新功能与变更 | — |
| [`../AGENTS.md`](../AGENTS.md) | Codex 单文件入口 | 最短 workflow + 铁律 | 细节 |
| [`../ROADMAP.md`](../ROADMAP.md) | 维护者 | **进度、里程碑 %** | 命令复制块 |
| [`../resources/skills/orchestrator/pipeline-schedule.md`](../resources/skills/orchestrator/pipeline-schedule.md) | Runner | **`pipeline run` 阶段** | GUI |
| [`../resources/skills/tester/`](../resources/skills/tester/) | Tester | **截图 + 视觉 QA** | brief 字段 |

## 读法建议

```text
新人 30 秒        → README（功能表 + Quick Start）
要跑通一条线       → AI-HANDOFF §5–§6
要配 GUI          → GUI-CONFIG
要配工具 / 排错    → TOOLS.md
外部 AI 代操       → TOOLS.md §2、§8
要理解分工         → AGENT-ROUTING
要定施工架构       → CONSTRUCTION-SYSTEM
主对话 / AI 公司前台  → HOST-CHAT-PRODUCT（策划 · 项目经理 · 程序员）
要用 Hermes        → HERMES-CODEX
Codex 会话         → AGENTS.md
看进度             → ROADMAP
发 Release         → RELEASE + RELEASE-NOTES-0.0.2
```

## 设计 vs 施工（一句话）

- **设计（Design）**：玩家体验、胜负、验收标准 → **ITERATIVE §1.1**；今天嵌在 `brief.project`
- **施工（Production）**：资产表、尺寸、Godot 任务 → **ITERATIVE §1.2**；今天 = `brief.json`（`brief export`）
- **怎么敲命令**：**AI-HANDOFF** + **TOOLS**，不是 ITERATIVE
