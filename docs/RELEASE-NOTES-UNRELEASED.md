# Unreleased — 下一版 Release Notes 草稿

相对当前已打标签的 [`v0.2.2`](RELEASE-NOTES-0.2.2.md)。打版时把本节并入正式 `RELEASE-NOTES-x.y.z.md`。

- Brief 叙事中文优先；移除 `brief.zh.md`；prompt-crafter 二次生成英文 prompt；`brief localize` 一次迁移
- **Host 桥接层**：`host retry-asset` 单资产 reset + 可选 recraft；`host run-assets --auto-fix` 失败自愈循环（最多 2 轮）
- **CJK craft 失败**：归类为 `validation`，auto-fix 自动带 `--run-prompts`
- **GUI 接线**：「运行资产生成」「项目经理处理失败」→ Host；看板失败资产「重跑」+ 资产表整资产重生成 → `hostRetryAsset`
- code heal 清零失败后自动续跑（审查 H1）
- 历史 Release Notes（v0.0–v0.1）合并为 [`archive/RELEASE-NOTES-LEGACY.md`](archive/RELEASE-NOTES-LEGACY.md)
- **VT 闸门单源**：Electron 改调 CLI `brief visual-target status`，删除独立 hydrate 副本
- **角色文档**：prompt-crafter 降为 pipeline 内部步骤，非 GUI 聊天同事（见 [`AGENT-ROUTING.md`](AGENT-ROUTING.md)）
- **目标模式**：运行资产生成失败 → 自动 diagnose/heal/串跑 fix_commands → 必要时 PM Agent → 续跑（GUI）
- **ACP 收口**：全角色 `agent prompt`；`record-turn` 应用 dispatch（等同 `agent turn` 落盘）
- 架构与重构交接：[`ARCHITECTURE-REFACTOR-HANDOFF.md`](ARCHITECTURE-REFACTOR-HANDOFF.md)
- 三层功能归属清单：[`ARCHITECTURE-LAYER-INVENTORY.md`](ARCHITECTURE-LAYER-INVENTORY.md)
- Host 桥接层收口 Plan（已执行）：[`anvil/plans/2026-08-20-host-layer-refactor-plan.md`](anvil/plans/2026-08-20-host-layer-refactor-plan.md)
