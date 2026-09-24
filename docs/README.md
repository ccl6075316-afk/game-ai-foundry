# 文档索引

## 当前入口

项目最终形态是：外部 Agent → 通用 Skill → `workflow` CLI → 确定性模块 → JSON 文件状态。

| 需要 | 文档 |
|---|---|
| 外部 Agent 协议 | [`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md) |
| CLI、Brief 字段、资产审查、matting | [`AI-HANDOFF.md`](AI-HANDOFF.md) |
| 本机工具、配置、故障排查 | [`TOOLS.md`](TOOLS.md) |
| 施工体系与验收 | [`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md) |
| Change Request 与 Production Delta | [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md) |
| 架构归属 | [`ARCHITECTURE-LAYER-INVENTORY.md`](ARCHITECTURE-LAYER-INVENTORY.md) |
| 架构交接 | [`ARCHITECTURE-REFACTOR-HANDOFF.md`](ARCHITECTURE-REFACTOR-HANDOFF.md) |
| Active Pipeline Skill | [`../resources/skills/orchestrator/pipeline.md`](../resources/skills/orchestrator/pipeline.md) |
| Pipeline 阶段顺序 | [`../resources/skills/orchestrator/pipeline-schedule.md`](../resources/skills/orchestrator/pipeline-schedule.md) |
| Roadmap | [`../ROADMAP.md`](../ROADMAP.md) |
| External Agent one-pager | [`../AGENTS.md`](../AGENTS.md) |

## 读取顺序

1. 先读 [`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md)。
2. 需要字段和命令细节时读 [`AI-HANDOFF.md`](AI-HANDOFF.md)。
3. 需要环境或排错时读 [`TOOLS.md`](TOOLS.md)。
4. 需要改需求时读 [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)。

## 状态原则

`brief.json` 是冻结后的设计契约；`production.json` 是工程蓝图；`manifest`、`progress`、`handoff`、`assets-manifest`、`validation report` 是唯一权威状态。不要另建状态副本。

## 已移除文档

以下文件已移除或归档，仅保留历史记录，不是当前入口：

- `GUI-CONFIG.md`：已移除。
- `HOST-CHAT-PRODUCT.md`：已移除。
- `HERMES-CODEX.md`：已移除。
- `AGENT-ROUTING.md`：已移除。
- `RELEASE.md`：已移除。

历史计划、旧发布说明和归档内容位于 [`archive/README.md`](archive/README.md)、[`anvil/`](anvil/)、[`superpowers/`](superpowers/) 与 `RELEASE-NOTES-*.md`；其中出现的旧入口均只作历史记录。
