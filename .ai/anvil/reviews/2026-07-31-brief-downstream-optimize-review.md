# 评审报告：`2026-07-31-brief-downstream-optimize`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（下游四项优化） |
| Author | test_analysis / ITERATIVE / implement(+Hermes) / production+visual_target + commit-brief 示例行 |
| Review Date | 2026-07-31 |
| Status | `APPROVED` |
| Spec 背景 | scenes/systems + ui_panels；能力侧消费对齐 |
| 前序 | ui-panels / scenes-systems / capability-sync 均为 APPROVED |

**Loaded standards:** Anvil review；Karpathy；brief vs production 同名分离。

**变更规模：** Small–Medium（共享 `brief_structure_summaries` + 多消费点）

---

## 1. 自动化预检

| 检查项 | 结果 |
|--------|------|
| `test_test_analysis`（含新 scenes/systems 测）+ scenes + production + ui_panels + enrich | PASS（44） |
| GUI typecheck | PASS |
| Lint | N/A |

---

## 2. 安全扫描

CLEAN。visual_target 仅拼 prompt 文本；无路径/密钥变化。

---

## 3. Karpathy

| 原则 | 结论 |
|------|------|
| Think | 共享摘要函数避免三处各写一套 | PASS |
| Simplicity | `brief_structure_summaries` 够用；未建框架 | PASS |
| Surgical | 未碰 production 脚手架生成逻辑 | PASS |
| Goal-Driven | 新测锁「有结构时 description 截断 + scenes 源」 | PASS |

**Score:** 4/4

---

## 4. 对抗式维度

| 项 | 判断 | 级别 |
|----|------|------|
| production 验收是否与 `production.scenes` 混淆 | 前缀 `brief design:` 明确 | PASS |
| visual_target `except Exception` | 吞掉非 Import 异常可能藏 bug | L1 |
| playtest_plan 未复用 helper | 行为已对齐，DRY 未做 | L2 |
| validate 错误文案仍写 description=gameplay/scope | 与新政「短总览」不符 | M1 |
| CONSTRUCTION-SYSTEM L1 `scenes[]` | 指 production 施工层，与 brief 设计清单同名 | M2（文档） |

**维度结论：** PASS（无阻塞）

---

## 5. 发现项

### Critical / High

无。

### Medium（建议，不挡提交）

| # | 描述 | 动作 |
|---|------|------|
| M1 | `audit_brief_for_export` 对 `description` 的错误文案仍是 `gameplay / scope in English` | 改成 short product overview 口径 |
| M2 | `docs/CONSTRUCTION-SYSTEM.md` L1 的 `scenes[]`/`systems[]` 易与 brief 设计清单混淆 | 加一句「此为 production 施工树，非 brief.project.scenes」 |

### Low

| # | 描述 |
|---|------|
| L1 | `visual_target._base_scene_description` 裸 `except Exception` |
| L2 | `playtest_plan` 可改为调用 `brief_structure_summaries` |
| L3 | production 验收新行无专用单测（行为靠 smoke） |
| L4 | `prompt_craft` VT 规则回退仍 `desc[:220]`，未附 scenes（LLM 关时） |

---

## 6. 门禁结论

- [x] **APPROVE**
- [ ] BLOCK

---

## 附录：再审 — 能力侧还剩什么

### 已齐（可停）

写稿 skills、makeability、enrich critique、product-host、HOST-CHAT、zh-doc、shared_context、godot 目标、playtest、test_analysis、production 验收摘要、visual_target、implement/Hermes、ITERATIVE 映射、AI-HANDOFF。

### 仅剩卫生项（非功能缺口）

| 优先级 | 项 |
|--------|-----|
| 中 | M1 validate description 错误文案；M2 CONSTRUCTION-SYSTEM 同名澄清 |
| 低 | playtest DRY、visual_target except 收窄、prompt_craft 规则回退、GUI 预览/types、session_status 计数、Hermes 双份长期同步 |
| 不做 | production 脚手架桥接、强制 scenes、自动迁稿、pipeline 改产线 |

### 再审结论

**能力主路径已闭环。** 再改只剩文案/DRY/GUI 可视；**无必须再开的功能缺口。** 总包可提交；若顺手可修 M1+M2。
