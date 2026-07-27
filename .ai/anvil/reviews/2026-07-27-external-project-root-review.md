# 评审报告：`2026-07-27-external-project-root`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | uncommitted working tree（外置工程根） |
| Author | anvil-code + review-fix doer |
| Review Date | 2026-07-27 |
| Status | `APPROVED`（含 nits；**未提交** — commit policy pause / 待用户确认） |
| Spec | `docs/anvil/brainstorms/2026-07-27-external-project-root.md`（confirmed） |
| Plan | `docs/anvil/plans/2026-07-27-external-project-root-plan.md` |
| Loaded standards | Anvil review template；历史 lenses（路径接线 / 白名单 / 移除≠删盘） |

**变更规模：** Large · Code + Docs · 全 8 维  
**复审：** 首轮 BLOCK（H1–H4）→ doer 修 Electron 路径契约 → 本轮复审通过

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | |
| 类型检查 | `cd gui && npm run typecheck` | PASS | |
| CLI 单测 | `python -m unittest test_external_projects test_project_paths test_host_chat test_makeability_gate -q` | PASS | 55 |
| GUI path 单测 | `npx tsx --test src/chat/projectPaths*.test.ts` | PASS | 7 |
| Electron helper | `node --test electron/externalFs.test.mjs` | PASS | 7 |

---

## Harness / Spec 追溯

| 检查 | 结果 |
|------|------|
| FR-1 索引 CRUD / 去重 | PASS |
| FR-2 双形态探测 | PASS |
| FR-3 GUI 打开/切换/徽标/移除不删盘 | PASS |
| FR-4 产物路径落 `root_abs` | PASS（复审：`cliArgForRel` / `absForRel` + list docs/manifests） |
| FR-5 export 外置根 | PASS（复审：`host-chat-export` 绝对 `-o`） |
| FR-6 文档 | PASS |
| 非目标 | PASS — 无强制 `projects/`、无 GUI 文本路径 |
| Resume | 可 commit；当前 pause 待用户确认 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| resolve vs wire | helper 与 IPC 同测 | 复审后 PASS — `externalFs` + main 接线 |
| 仅目录选择器 | dialog in main | PASS |
| 移除≠删盘 | CLI 单测 | PASS |
| Docs 勿错 resolve | listProjectDocs 外置分支 | PASS |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 路径穿越 | `parseExternalVirtual` 拒 `..`；containment | — | OK |
| 任意写开放 | 仅 registry 内 root | — | OK |
| XSS / CVE | 无 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 结论 | 严重级别 |
|------|------|----------|
| Think Before Coding | 复审后 Electron 契约与 Spec 对齐 | PASS |
| Simplicity First | `externalFs.mjs` 提取合理、可测 | PASS |
| Surgical Changes | 改动可追溯到 FR | PASS |
| Goal-Driven Execution | CLI + externalFs + projectPaths 测覆盖关键契约 | PASS |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度（复审摘要）

### 4.1–4.3 设计 / 功能 / 复杂度
首轮 H1–H4 已关闭：

| # | 修复证据 |
|---|----------|
| H1 | `main.mjs` `host-chat-export`：`absForRel` + `cliArgForRel` 绝对 `-o`；`zh_doc_rel` 映射 `external:<id>/…` |
| H2 | pipeline-* / loadManifest / open-godot / briefCliArg 走统一解析 |
| H3 | listProjectDocs 外置分支；listManifests 扫 registry pipeline；findManifestForBrief 认 `external:<id>` |
| H4 | `gui/electron/externalFs.mjs` + `externalFs.test.mjs`（7） |

### 4.8 测试
故意破坏 containment / virtual parse 会使 externalFs 测失败。无完整 Electron E2E（残余风险，不阻塞）。

**各维结论：** PASS（残余见 Low/Medium）

---

## 5. 发现项摘要

### Critical / High
无未解决项。

### Medium（不阻塞；建议后续）

| # | 描述 | 建议 |
|---|------|------|
| M1 | `add_external_project` 在 godot_missing 时仍写 `godot_rel="."` | 保留 missing 信号；open Godot 明确报错 |
| M-res | `visual-target-status` / `patchBriefProject` 仍偏 `projects/` | 外置北极星 / patch 若需要再接线 |
| M-res2 | 无真实 dialog+registry Electron E2E | 手工验收或后续集成测 |

### Low / Nit

| # | 描述 |
|---|------|
| N1 | export 文案已修外置（doer） |
| N2 | `ExternalProjectEntry` 双定义可收敛 |
| N3 | DocsPreview `externalEntryById` 进 disk-list effect deps |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical | [x] |
| 无未解决 High | [x] |
| 评审文档完整 | [x] |
| Spec 追溯完整 | [x] |
| 已提交独立 commit | [ ] **用户确认前 pause** |

### 结论

- [ ] **BLOCK**
- [x] **APPROVE** — 门禁通过；**请用户确认后再 commit**（plan commit policy = pause；用户规则：未明确要求不提交）

### 评审备注

首轮正确拦住「CLI 契约完整、Electron 半接线」风险。复审后路径模型闭环，满足外置根一等公民 Spec。  
建议下一步：用户确认 → 单 commit（含 review 文档 + `git add -f` plan 若需入库）→ 可选 `/anvil:compound`。

手工冒烟建议：打开外置根 → 导出 Brief 确认落在外置目录 → 生成流水线确认 `root_abs/pipeline` → 列表移除后磁盘仍在。
