# 评审报告：`2026-07-27-brief-enrich-and-topic-brainstorm`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | uncommitted working tree |
| Author | anvil-code session |
| Review Date | 2026-07-27 |
| Status | `APPROVED`（含 nits；**未提交** — commit policy pause） |
| Spec | `docs/anvil/brainstorms/2026-07-27-brief-enrich-and-topic-brainstorm.md` |
| Plan | `docs/anvil/plans/2026-07-27-brief-enrich-and-topic-brainstorm-plan.md` |
| Loaded standards | Anvil review template；历史 lenses（makeability 门闩 / resolve≠wire / 不定死 schema） |

**变更规模：** Large（~780+ 行 + 新模块）· Code + Skills + Docs

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | |
| 类型检查 | `cd gui && npm run typecheck` | PASS | |
| 单元测试 | `python -m unittest test_brief_enrich test_topic_brainstorm test_host_chat -q` | PASS | 49 tests（含复审新增 preserve-assets） |

---

## Harness / Spec 追溯

| 检查 | 结果 |
|------|------|
| 可选按钮、不绑 export | PASS |
| 先吵后拣 | PASS（topic-brainstorm → apply） |
| 不定死 screens schema | PASS |
| 资产候选写回 | PASS |
| 数值可进 production / 参数名在 brief | PASS（skill + critic 观感段） |
| CLI 命名 | 实现用 `topic-brainstorm`（避与旧 `brief_brainstorm.py` 冲突）— 与 plan 字面略异，可接受 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| makeability 门闩 | enrich 后 ready_to_export=false / fingerprint stale | PASS |
| resolve≠wire | GUI IPC → CLI 同命令 | PASS（无 Electron 单测，有 CLI mock） |
| 不定死 schema | validate 仅 project dict | PASS |
| 假成功/部分写回 | 校验失败不改 session | PASS |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 路径写盘 | 仅 session draft | — | OK |
| XSS | prompt/聊天文本 | Low | OK |
| 注入 | 用户 hint/topic 进 LLM | 预期 | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 结论 | 严重级别 |
|------|------|----------|
| Think Before Coding | 整稿替换曾会丢 assets — 复审已改为 overlay+merge | PASS（已修） |
| Simplicity First | topic_brainstorm 独立模块合理 | PASS |
| Surgical Changes | 可追溯 Spec | PASS |
| Goal-Driven Execution | merge/enrich/brainstorm 有 mock 测 | PASS |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度（摘要）

### 4.2 功能 — 复审修复

| # | 问题 | 处理 |
|---|------|------|
| H1 | `apply_draft_replacement` 整稿替换：LLM 省略 `assets[]` 会丢掉旧资产 | **已修**：以旧 draft 为底 overlay project/其它键，再 merge candidate assets + proposals；新增 `test_apply_preserves_assets_when_candidate_omits_assets` |

### 其余维
设计/复杂度/命名/风格：PASS（见 nits）。  
测试：CLI 覆盖充分；GUI 无 E2E（残余）。

---

## 5. 发现项摘要

### Critical / High（未解决）
无。

### Medium（不阻塞）

| # | 描述 | 建议 |
|---|------|------|
| M1 | `topic_brainstorm` 导入 `host_chat._parse_llm_json` / `_utc_now` 私有符号 | 导出公开 alias 或移到 `llm_json` 工具 |
| M2 | 「融合前两个方案」写死 `p1,p2`（排序后 id），未必是用户看到的前两项语义 | UI 记住展示顺序 id 列表 |
| M3 | Electron enrich/brainstorm 无加长超时，多角色并行可能被默认 CLI 超时打断 | 与 makeability 对齐或显式加长 |

### Low / Nit

| # | 描述 |
|---|------|
| N1 | GUI 用 `window.prompt` 收 hint/topic — v1 可接受 |
| N2 | plan 写 `brainstorm`，实现为 `topic-brainstorm` — 文档已对齐实现 |
| N3 | 无 GUI 集成测 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical/High | [x] |
| 评审文档完整 | [x] |
| Spec 追溯完整 | [x] |
| 已提交 | [ ] pause / 待用户确认 |

### 结论

- [ ] **BLOCK**
- [x] **APPROVE** — 可 commit；建议后续处理 M1–M3

### 评审备注

首轮抓住「整稿替换丢资产」为真 High，已在复审修复合并策略并补测。功能面与 Spec 一致：按钮可控、先吵后拣、不定死 schema、资产候选、makeability 过期。

回复 **commit**（或 commit + push）即可入库。
