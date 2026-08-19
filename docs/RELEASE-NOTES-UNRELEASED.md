# Unreleased — 下一版 Release Notes 草稿

相对当前已打标签的 [`v0.2.2`](RELEASE-NOTES-0.2.2.md)。打版时把本节并入正式 `RELEASE-NOTES-x.y.z.md`。

- Brief 叙事中文优先；移除 `brief.zh.md`；prompt-crafter 二次生成英文 prompt；`brief localize` 一次迁移
- **目标模式**：运行资产生成失败 → 自动 diagnose/heal/串跑 fix_commands → 必要时 PM Agent → 续跑（GUI）
- **ACP 收口**：全角色 `agent prompt`；`record-turn` 应用 dispatch（等同 `agent turn` 落盘）
- 架构与重构交接：[`ARCHITECTURE-REFACTOR-HANDOFF.md`](ARCHITECTURE-REFACTOR-HANDOFF.md)
