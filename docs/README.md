# 文档索引

各文档 **只写自己那一层**，避免同一流程在多处复制粘贴。

| 文档 | 读者 | 侧重 | 不写什么 |
|------|------|------|----------|
| [`../README.md`](../README.md) | 新人 / GitHub | 30 秒是什么、Quick Start、前置依赖 | 字段 schema、角色边界、迭代契约 |
| [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md) | Host / 全角色 | **设计 vs 施工**、Change Request、切片、验收哲学 | CLI 命令、Hermes 安装、里程碑百分比 |
| [`AI-HANDOFF.md`](AI-HANDOFF.md) | 接手 Agent（中文） | **CLI 速查**、brief 字段、抠图铁律、配置与本机工具 | 产品方法论、六角色表、进度表 |
| [`AGENT-ROUTING.md`](AGENT-ROUTING.md) | 混排编排 | **七角色 + executor** | brief 字段、Change Request 全文 |
| [`HERMES-CODEX.md`](HERMES-CODEX.md) | Hermes / Codex 用户 | **安装 skill、terminal 约定** | 设计文档、brief schema |
| [`../AGENTS.md`](../AGENTS.md) | Codex 单文件入口 | 最短 workflow + 5 条铁律 | 一切细节（链到上表） |
| [`../ROADMAP.md`](../ROADMAP.md) | 维护者 | **做了什么 / 待做什么 / 里程碑 %** | 命令复制块、抠图规则 |
| [`../resources/skills/orchestrator/pipeline-schedule.md`](../resources/skills/orchestrator/pipeline-schedule.md) | Runner / orchestrator skill | **`pipeline run` 阶段** | 产品迭代、GUI |
| [`../resources/skills/tester/`](../resources/skills/tester/) | Tester skill | **截图 + 视觉 QA、`test run`** | brief 字段 |

## 读法建议

```text
要跑通一条线     → README Quick Start → AI-HANDOFF §5–§6
要配本机工具       → `setup check` / GUI 启动弹窗 → README Prerequisites
要理解分工       → AGENT-ROUTING
要定需求/改需求   → ITERATIVE-PRODUCTION
要用 Hermes      → HERMES-CODEX
Codex 会话       → AGENTS.md（再按需打开上表）
看进度           → ROADMAP
```

## 设计 vs 施工（一句话）

- **设计（Design）**：玩家体验、胜负、验收标准 → 详见 **ITERATIVE §1.1**；今天嵌在 `brief.project`
- **施工（Production）**：资产表、尺寸、Godot 任务 → 详见 **ITERATIVE §1.2**；今天 = 整份 `brief.json`（`brief export`）
- **怎么敲命令**：**AI-HANDOFF**，不是 ITERATIVE
