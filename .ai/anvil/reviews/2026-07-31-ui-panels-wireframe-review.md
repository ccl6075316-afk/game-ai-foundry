# 评审报告：`2026-07-31-ui-panels-wireframe`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（uncommitted） |
| Author | `/anvil:code` doers + review 修复（external brief-rel） |
| Review Date | 2026-07-31 |
| Status | `APPROVED`（H1 评审中已修） |
| Spec | `docs/anvil/brainstorms/2026-07-31-ui-panels-wireframe.md`（confirmed） |
| Plan | `docs/anvil/plans/2026-07-31-ui-panels-wireframe-plan.md`（executed；`plans/` 仍被 gitignore） |

**Loaded standards:** Anvil `/anvil:review`；Karpathy；`docs/solutions` 无直接 UI panels 先例；遵守 2026-07-27「禁止强制 screens」lens。

**变更规模：** Medium–Large（~360+ 行业务 + 新模块/测；跨 CLI + GUI + skills + docs）

**Spec 追溯：** FR1–FR7 均有对应实现；非目标（description 过载、强制 hud 绑定、自动示意、生图）未越界。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 无统一 lint |
| 类型检查 | `cd gui && npm run typecheck` | PASS | |
| 单元测试 | `test_ui_panels` + `test_ui_wireframe` + soft hint | PASS | 评审修复后 wireframe **7** 测 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| 2026-07-27 enrich Spec | 禁止强制 screens 死表 | PASS：ui_panels 可选、validate 不要求 |
| docs/solutions | 无 panels 先例 | 无额外 finding |

---

## 1.5 Harness / Spec 门禁

| 项 | 状态 |
|----|------|
| Spec → Plan → Diff | PASS |
| 可缺省不挡导出 | PASS（单测） |
| 示意仅点击路径 | PASS（独立 IPC/CLI；enrich 未调用） |
| Resume / 无平行任务状态 | PASS |
| Plan 可入库 | WARN：`plans/` gitignore（既有） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 路径穿越 | `_assert_safe_output_path` + 文件名固定；external 经 `paths_for_brief_key` | — | OK（修后） |
| XSS | md 写入工程文档，非 HTML 注入渲染路径 | — | OK |
| 日志敏感 | 无 key 入 argv | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 结论 | 严重级别 |
|------|------------|------|----------|
| Think Before Coding | 可选 vs 强制是否写清？ | PASS | — |
| Simplicity First | 是否过度建 screens 系统？ | PASS：最小 panels + 按需 md | — |
| Surgical Changes | description 是否误改？ | PASS：未碰过载整改 | — |
| Goal-Driven Execution | 测是否覆盖空 panels / 路径 / validate？ | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计
可选清单 + 按需示意符合「用户预览、非施工硬依赖」。与 2026-07-27 不冲突。

**维度结论：** PASS

### 4.2 功能

| 行号 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `brief_cmds.py` chat ui-wireframe（修前） | `external:` 是否写错盘？ | **已修**为 `paths_for_brief_key` | High→已解决 |
| `ui_wireframe.py` 166–171 | 空 panels 是否写文件？ | 不写并返回 error | PASS |
| enrich / IPC | 是否自动示意？ | 分离 | PASS |
| `agent_turn` soft hint | 缺文件是否炸 turn？ | 吞异常返回 [] | PASS |

**维度结论：** PASS（修复后）

### 4.3–4.7
复杂度可控；命名清晰；skill 提示到位；风格对齐 zh-doc IPC；系统健康中性偏好。

**维度结论：** PASS

### 4.8 测试
normalize / validate / 写盘 / 空 panels / 路径 escape / external CLI / soft hint 均有覆盖。缺 dedicated skill 文件时用 fallback——可接受（Low）。

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
| H1 | `brief chat ui-wireframe` 对 `external:<id>/…` 用 `repo/rel` 拼路径，示意可能写到错误目录 | 改用 `paths_for_brief_key` + 测 | **已修** |

### Medium（强烈建议）

| # | 描述 | 必须动作 |
|---|------|----------|
| M1 | `resources/skills/orchestrator/ui-wireframe.md` 未落地，靠 fallback | 可选补 skill 文件；不阻塞 |
| M2 | `brief chat zh-doc` 仍可能有同类 external 拼法（既有模式） | 另案对齐 `paths_for_brief_key` |

### Low / Nit

| # | 描述 | 必须动作 |
|---|------|----------|
| L1 | `plans/` gitignore 吞掉 plan 文件 | 另案修 ignore |
| L2 | GUI 先查 `briefDraft` 再调 CLI；panels 空时仍依赖 CLI 报错文案 | 可接受 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical | [x] |
| 无未解决 High | [x]（H1 已修） |
| Spec 可追溯 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 允许提交
- [ ] **BLOCK**

### 评审备注

- 按用户 git 规则：**未自动 commit**。回复「提交」后按写集提交。
- 建议提交写集含：CLI/GUI/skills/docs/brainstorm/review；新测与 `ui_wireframe.py`；plan 若需入库须先修 gitignore。
- 手动：策划聊装备面板 → draft 有 `ui_panels` → 点「生成 UI 示意」→ Docs 打开 md；无 panels 点按钮应看到 CLI 错误提示。
