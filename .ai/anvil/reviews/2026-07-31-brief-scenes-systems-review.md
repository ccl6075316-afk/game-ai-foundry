# 评审报告：`2026-07-31-brief-scenes-systems`（含审查同步）

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（uncommitted） |
| Author | `/anvil:code`（scenes/systems）+ 审查/zh-doc/playtest/godot 同步 |
| Review Date | 2026-07-31 |
| Status | `APPROVED` |
| Spec | `docs/anvil/brainstorms/2026-07-31-brief-scenes-systems.md`（confirmed） |
| Plan | `docs/anvil/plans/2026-07-31-brief-scenes-systems-plan.md`（executed；`plans/` 仍被 gitignore） |
| 同工作区 | UI panels 已有独立评审 `2026-07-31-ui-panels-wireframe-review.md`（APPROVED）；本报告覆盖 **scenes/systems + 下游同步**，并复核叠加 diff |

**Loaded standards:** Anvil `/anvil:review`；Karpathy；`docs/solutions` style_group「正交字段写清」lens；禁止与 `production.scenes` 混同。

**变更规模：** Medium（契约 + skills + 若干消费方；~契约/测为主）

**Spec 追溯：** FR1–FR7 均有对应；非目标（强制必填、自动迁移 fishing、production 桥接、新 GUI 编辑器）未越界。审查同步属于用户明确「改」的延伸，落在「下游读字段对齐」而非范围蔓延到 production。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 无统一 lint |
| 类型检查 | `cd gui && npm run typecheck` | PASS | GUI 含 ui-wireframe IPC（同工作区） |
| 单元测试 | `test_brief_scenes_systems` + `test_ui_panels` + `test_ui_wireframe` + `test_brief_zh_doc` + `test_agent_turn` | PASS（70） | |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| style_group / art_tokens | 新 brief 字段正交、勿进 pipeline 平行模型 | PASS：scenes/systems 仅 brief/上下文/技能 |
| ui_panels 评审 H1 | external 路径 | PASS：wireframe 已用 `paths_for_brief_key` |
| ui_panels M1 | 缺 skill 文件 | **已补** `resources/skills/orchestrator/ui-wireframe.md` |

---

## 1.5 Harness / Spec 门禁

| 项 | 状态 |
|----|------|
| Spec → Plan → Diff | PASS |
| 可选不挡导出 | PASS（单测） |
| 未自动迁移 fishing | PASS |
| 未桥接 production.scenes | PASS（刻意） |
| Resume / 无平行任务状态 | PASS |
| Plan 可入库 | WARN：`plans/` gitignore（既有 L） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 路径穿越 | soft hint 只读 brief；wireframe 仍有 `_assert_safe_output_path` | — | OK |
| 注入 | playtest/zh-doc 字符串拼接进 md/JSON，非 shell | — | OK |
| 日志敏感 | 无 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 结论 | 严重级别 |
|------|------------|------|----------|
| Think Before Coding | 模拟类 loop 短是否写进审查纪律？ | PASS：makeability 已改 | — |
| Simplicity First | 是否过度建编辑器/迁移器？ | PASS：仅契约+技能+软消费 | — |
| Surgical Changes | production derive 是否被误改？ | PASS：未碰 | — |
| Goal-Driven Execution | normalize/validate/导出/soft hint/zh-doc 有测？ | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计
`scenes` / `systems` 与 `ui_panels` 正交；description/loop 纪律靠 skill + critic，符合「开发向划分」。与 `production.scenes|systems` **同名不同物**已在 critic / Spec / plan 标明，暂不桥接正确。

**维度结论：** PASS

### 4.2 功能

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `normalize_scenes/systems` | 缺 id/title 是否丢弃？ | 是；单测覆盖 | PASS |
| validate | 是否强制？ | 否 | PASS |
| `makeability-critic.md` | 短 loop 是否误判 intent？ | 纪律明确禁止 | PASS（技能层，无单测） |
| `godot_dev` | 有结构时是否仍灌整段 description？ | 截断为 overview | PASS |
| `playtest_plan` | acceptance 是否随 scenes 膨胀？ | 可能；见 M1 | Medium |
| soft hint | 是否读 draft 而非 brief.json？ | 读 `brief_path` 文件；未同步时可能空 | Low |

**维度结论：** PASS（无阻塞）

### 4.3–4.7
复杂度与 ui_panels normalize 同构；命名清晰；文档 AI-HANDOFF / skills 对齐；无无关重构。

**维度结论：** PASS

### 4.8 测试
契约 / 导出 / soft hint / zh-doc 面板节有覆盖。缺 makeability LLM 集成测——可接受（技能变更）。

**维度结论：** PASS

---

## 5. 发现项摘要

### Critical（阻塞提交）

| # | 描述 | 必须动作 |
|---|------|----------|
| — | 无 | — |

### High（阻塞提交）

| # | 描述 | 必须动作 | 状态 |
|---|------|----------|------|
| — | 无 | — | — |

### Medium（强烈建议）

| # | 描述 | 必须动作 |
|---|------|----------|
| M1 | `playtest_plan._acceptance_from_brief` 对每个 scene/system 各加一条 criterion，大型模拟 brief 可能极长 | 后续可截断（如前 N 条）或只取 summary；**不阻塞**本期 |
| M2 | `brief.project.scenes` 与 `production.scenes` 同名，未来桥接易混 | 文档已警示；桥接须另开 Spec，禁止静默合并 |

### Low / Nit

| # | 描述 | 必须动作 |
|---|------|----------|
| L1 | `plans/` gitignore 吞 plan | 另案 |
| L2 | 程序员 soft hint 依赖磁盘 brief；仅草稿未同步时看不到 scenes | 可接受（先同步草稿） |
| L3 | 同工作区 ui-panels 的 zh-doc external 拼法另案（见 panels 评审 M2） | 另案 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical | [x] |
| 无未解决 High | [x] |
| Spec 可追溯 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 允许提交
- [ ] **BLOCK**

### 评审备注

- 按用户 git 规则：**未自动 commit**。回复「提交」后建议一次提交或拆两笔：
  1. ui_panels + wireframe（含 skill）
  2. scenes/systems + makeability/zh-doc/playtest/godot 同步  
  亦可合并为一笔 feat（写清两层产物）。
- 建议写集：`cli/*`、`gui/*`（panels）、`resources/skills/**`、`docs/AI-HANDOFF.md`、`docs/HOST-CHAT-PRODUCT.md`、brainstorms、`.ai/anvil/reviews/*`、新测与 `ui_wireframe.py`。
- 手动：fishing 用「补全细节」按 scenes/systems 重构 → 制作审查不应再因 loop 短误杀 → 同步草稿 → zh-doc 应出现场景/系统节。
