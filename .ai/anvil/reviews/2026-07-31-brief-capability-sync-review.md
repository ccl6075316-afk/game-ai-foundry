# 评审报告：`2026-07-31-brief-capability-sync`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区增量（能力侧同步 4 处） |
| Author | 能力残留改造（enrich critique / product-host / HOST-CHAT / Hermes tester） |
| Review Date | 2026-07-31 |
| Status | `APPROVED` |
| Spec 背景 | `2026-07-31-brief-scenes-systems` + ui_panels；本期仅为消费方/文档对齐 |
| 前序评审 | `ui-panels-wireframe-review` APPROVED；`brief-scenes-systems-review` APPROVED |

**Loaded standards:** Anvil review；Karpathy；正交字段 lens；生产脚手架 vs brief 设计清单分离。

**变更规模：** Trivial–Small（~4 文件，文案/skill/一句 critique）

**Spec 追溯：** 属于 scenes/systems 验收后的能力对齐，未扩大到 production 桥接或强制字段。

---

## 1. 自动化预检

| 检查项 | 结果 |
|--------|------|
| `test_brief_enrich` + scenes/ui_panels 相关 | PASS |
| 断言 critique / product-host / HOST-CHAT / Hermes tester 含新口径 | PASS |
| Lint / typecheck | N/A（无 TS 改动） |

---

## 2. 安全扫描

无密钥、无路径、无注入面变化。CLEAN。

---

## 3. Karpathy

| 原则 | 结论 |
|------|------|
| Think | 只补消费纪律，不迁 projects 稿 | PASS |
| Simplicity | 无新抽象 | PASS |
| Surgical | 四文件对症 | PASS |
| Goal-Driven | enrich 测仍绿；skill 文本可检索 | PASS |

**Score:** 4/4

---

## 4. 对抗式维度（本增量）

| 项 | 判断 |
|----|------|
| enrich critique 是否强制 scenes？ | 否：optional gaps，与 Spec 一致 | PASS |
| product-host 是否误禁 production.scenes？ | 已区分同名不同物 | PASS |
| Hermes tester 是否与主 playtest 漂移？ | visual source 已改 loop；正文已提 scenes/systems | PASS |
| 是否漏测 critique 字符串？ | 无专用单测；Low | L1 |

**维度结论：** PASS

---

## 5. 发现项

### Critical / High

无。

### Medium

无（本增量）。

### Low

| # | 描述 |
|---|------|
| L1 | `_brief_enrich_critique_system` 无单测锁关键字；回归靠人工 |
| L2 | Hermes 包与 `resources/skills` 双份维护，仍可能再漂移 |

---

## 6. 门禁结论

- [x] **APPROVE** — 本增量可随总包提交  
- [ ] BLOCK

---

## 附录：能力侧剩余优化清单（审查续扫）

> 不含 `projects/` 工程稿；不含 GUI 预览（你自理工程侧）。下列为 Foundry **能力**上仍可优化、但非本增量阻塞项。

### A. 值得做（行为/一致性，中优）

| 能力 | 问题 | 建议 |
|------|------|------|
| **`test_analysis.py`（截图视觉 QA 准则）** | 仍把整段 `project.description` 塞进 criteria；重构后 description 变短、规则在 systems，准则会偏 | 有 scenes/systems 时优先用其 summary；description 仅作 overview |
| **`production.py` acceptance** | derive 验收仍几乎只拼 loop/session_goal | 可选附加 brief.scenes/systems **摘要**进 validation（勿与 production.scenes 节点表混淆） |
| **`visual_target.py` / VT craft 上下文** | `_base_scene_description` 仍灌满 description+loop | 有结构时截断 description，可附 1–2 个 scene summary 作「北星一帧」提示 |
| **`godot-developer/implement.md`**（及 Hermes 同源副本若存在） | 只强调 `production.scenes`，未提示 brief `project.scenes/systems` 为玩法意图 | 加一句：设计意图读 brief 清单；脚手架路径读 production |
| **`docs/ITERATIVE-PRODUCTION.md` §0.1** | Design Doc 映射仍写 description 为玩法载体 | 更新为 description 短总览 + loop + 可选 scenes/systems/ui_panels |
| **`commit-brief.md` 映射表** | 有 ui_panels 行，缺「聊到屏/系统」→ scenes/systems 示例行 | 补两行示例，减少落实时漏写 |

### B. 可后补（体验/卫生，低优）

| 能力 | 问题 |
|------|------|
| GUI `briefPreviewFormat` / `types.ts` | 预览与类型未声明新字段（你若主要看 JSON/Docs 可缓） |
| `session_status` API | 未暴露 scene/system 计数（侧栏摘要用） |
| playtest acceptance 条数 | 每 scene/system 一条，大 brief 膨胀（前序 M1） |
| Hermes 双份 skill | 长期应用同步脚本或单一真源 |

### C. 明确不做（另案 / 非漏改）

| 项 | 原因 |
|----|------|
| brief ↔ `production.scenes` 自动桥接 | 同名不同物；需独立 Spec |
| validate 强制 scenes/systems | Spec 可选 |
| 自动迁移旧 draft | Spec 非目标 |
| pipeline 产线参数 | 正交；不进生图后端 |

### 能力完备度结论

- **写稿 / 审查 / 导出 / zh-doc / 程序员提示 / playtest 主路径 / 本次 4 处消费对齐：已齐。**
- **下一刀若优化：** 优先 `test_analysis` → `ITERATIVE` 映射表 → `implement.md` →（可选）production acceptance 摘要 / visual_target 截断。
- **无阻塞提交项。**
