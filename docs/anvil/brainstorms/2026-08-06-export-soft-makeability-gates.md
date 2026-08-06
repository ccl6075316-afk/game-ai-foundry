# 导出软闸门 + 制作审查验写入降噪

> 状态：已确认并已实现（2026-08-06）
> 背景：策划卡在产品文档过久；验写入 `repair_failed` 过频；「存」被意图缺口/指纹挡住。

## 目标

1. **导出 Brief**：只硬拦会导致 **JSON 解析失败** 或 **生图/生视频/管线解析失败** 的结构问题（`audit_brief_for_export` / `_audit_draft_gaps`）。
2. **产品逻辑 / 意图缺口 / 审查指纹 / decision ledger**：不硬拦导出；制作审查改为建议，用户自决是否继续审。
3. **验写入降噪**：按 **decision 单条** 过关，不再整卡一票否决；验证以 **target_paths（主路径）** 为准，多路径同步降为尽力；后续补丁 **不再** 因路径碰触把已 `verified` 降成 `repair_failed`。

## 非目标

- 不删除制作审查功能，不取消 repair 卡 / 重试写入。
- 不放宽 asset id / display_size / animation_graph 等结构校验。
- 不改 pipeline 对已导出 brief 的 `validate_brief_for_export`。

## 验收

- 无结构 gaps 时可点「存」并 `export_brief` 成功，即使无制作审查、指纹过期、或仍有 intent / repair_failed。
- 一次答 3 条：2 条 Verifier satisfied、1 条 missing → 仅 1 条 `repair_failed`，另 2 条 `verified`。
- 已 verified 决定在后续无关/相关 path 补丁后仍保持 `verified`（不自动打回 repair）。
- 既有结构校验测试仍过；更新 makeability gate 测试口径。
