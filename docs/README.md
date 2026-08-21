# 文档索引

各文档 **只写自己那一层**，避免同一流程在多处复制粘贴。

## 当前版本（2026-08）

- **已发布最新**：[`RELEASE-NOTES-0.2.2.md`](RELEASE-NOTES-0.2.2.md)（相关分册 / soft-focus / related 完整性）
- **同系列**：[`0.2.1`](RELEASE-NOTES-0.2.1.md) · [`0.2.0`](RELEASE-NOTES-0.2.0.md)
- **下一版草稿**：[`RELEASE-NOTES-UNRELEASED.md`](RELEASE-NOTES-UNRELEASED.md)（含 Host 桥接收口）
- **更早版本摘要**：[`archive/RELEASE-NOTES-LEGACY.md`](archive/RELEASE-NOTES-LEGACY.md)（v0.0–v0.1，独立文件已删）
- **打包 / 更新**：[`RELEASE.md`](RELEASE.md)

### 产品主路径（一句话）

同事（策划 / 项目经理 / 程序员 / IT）→ Brief + 北极星 → `host run-assets --auto-fix` / GUI「运行资产生成」→ 资产审查 → Godot。工具与排错见 [`TOOLS.md`](TOOLS.md)。

---

| 文档 | 读者 | 侧重 |
|------|------|------|
| [`../README.md`](../README.md) | 新人 / GitHub | 功能一览、Quick Start |
| [`AI-HANDOFF.md`](AI-HANDOFF.md) | 接手 Agent | CLI 速查、brief、抠图、资产审查 |
| [`TOOLS.md`](TOOLS.md) | 外部 AI / 运维 | 配置、探测、纠错 |
| [`ARCHITECTURE-REFACTOR-HANDOFF.md`](ARCHITECTURE-REFACTOR-HANDOFF.md) | 维护者 / 下一任 AI | 三层架构、目标模式、P0–P4 |
| [`ARCHITECTURE-LAYER-INVENTORY.md`](ARCHITECTURE-LAYER-INVENTORY.md) | 维护者 | CLI / Host / GUI 归属 |
| [`anvil/plans/2026-08-20-host-layer-refactor-plan.md`](anvil/plans/2026-08-20-host-layer-refactor-plan.md) | 实现 Agent | Host 收口 Plan（已执行） |
| [`AGENT-ROUTING.md`](AGENT-ROUTING.md) | 混排 | 用户可见同事 vs pipeline 内部角色 |
| [`HOST-CHAT-PRODUCT.md`](HOST-CHAT-PRODUCT.md) | 产品 / GUI | AI 公司前台心智 |
| [`GUI-CONFIG.md`](GUI-CONFIG.md) | GUI 用户 | 设置全页、Provider、生图双档 |
| [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md) | Host | 设计 vs 施工 |
| [`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md) | 维护者 | production / 验收 / 进度 |
| [`HERMES-CODEX.md`](HERMES-CODEX.md) | Hermes / Codex | skill / terminal |
| [`solutions/reviews/2026-08-04-whole-project-review-ledger.md`](solutions/reviews/2026-08-04-whole-project-review-ledger.md) | 再 review | Fixed / Accepted / Deferred 账本 |
| [`archive/`](archive/) | 考古 | 旧 Release 摘要 |
| [`../ROADMAP.md`](../ROADMAP.md) | 维护者 | 里程碑进度 |
| [`../resources/skills/orchestrator/pipeline-schedule.md`](../resources/skills/orchestrator/pipeline-schedule.md) | Runner | `pipeline run` 阶段 |

过程史料（默认不读）：`docs/anvil/brainstorms|plans`（已执行的可参考 Resume）、`docs/superpowers/`、`docs/solutions/failures`。

## 读法建议

```text
新人 30 秒        → 仓库 README
要跑通一条线       → AI-HANDOFF §5–§6
要架构 / Host      → ARCHITECTURE-REFACTOR-HANDOFF + LAYER-INVENTORY
要配 GUI / 工具    → GUI-CONFIG · TOOLS
要理解同事分工     → AGENT-ROUTING · HOST-CHAT-PRODUCT
发 Release         → RELEASE + 0.2.2 · 草稿 UNRELEASED · 更早见 archive
```

## 设计 vs 施工

- **设计**：玩家体验、胜负 → ITERATIVE §1.1（`brief.project`）
- **施工**：资产表、Godot 任务 → ITERATIVE §1.2
- **命令**：AI-HANDOFF + TOOLS，不是 ITERATIVE
