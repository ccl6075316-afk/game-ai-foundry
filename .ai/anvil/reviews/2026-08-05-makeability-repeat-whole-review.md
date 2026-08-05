# 评审报告：`2026-08-05-makeability-repeat-whole`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | `main...b56fdb9`（整分支） |
| Author | local |
| Review Date | 2026-08-05 |
| Status | `APPROVED` |

**审查方式：** 相对 `main` 全量对抗式复审（不沿用上次 APPROVE 结论），覆盖账本防重复、磁盘 CAS、假成功门闩、Critic 协议、GUI 双卡。  
**目的：** 回答「是不是真的没问题了」。

---

## 1. 自动化预检

| 检查项 | 结果 | 备注 |
|--------|------|------|
| `git diff --check main...HEAD` | PASS | |
| makeability 相关 pytest | PASS | 132 |
| GUI 定向测试 | PASS | 9 |
| `npm run typecheck` | FAIL | 仅既有 2 处，与本分支无关 |

---

## 2. 主需求闭环核对

| 用户可见承诺 | 机制 | 证据 | 结论 |
|--------------|------|------|------|
| 答过的意图不因换 gap id 反复问 | `decision_ledger` + suppress +（`gap.*`/空 key 的 path 调和） | `suppress_intent_gaps_by_ledger`、reconcile 测试 | 成立 |
| 同 path 上不同显式 `decision_key` 可再问 | 禁止 path-only alias | M2 reconcile + 测试 | 有意行为，不是漏修 |
| 答案先落盘再调 LLM | `persist_after_record` → `save_session` 必写 session | H1 解耦 + 测试 | 成立 |
| 磁盘没写成功不能宣称已验证 | `_persist_answer_draft_or_mark` + 降级 verified | CAS 假成功测试断言 `ok`/`verified`/`draft_persisted` | 成立 |
| 导出不被脏/未验证状态骗过 | export 前 sync；`ledger_blocks_export` | gate/export 测试 | 成立 |
| Critic checks 不全不静默降级 | `assert_critic_decision_checks_protocol` | 空 checks → HostChatError | 成立 |
| 验证失败可重试 | `repair_gaps`/`repair_answers` + GUI 双卡 | critic conflict 测试 + App 分卡 | 成立 |

---

## 3. Karpathy

| 原则 | 结论 |
|------|------|
| Think Before Coding | PASS：session 耐久与 draft 成功已拆开 |
| Simplicity First | PASS：复杂度与双源问题相称 |
| Surgical Changes | PASS：可追溯到防重复 / 写盘契约 |
| Goal-Driven Execution | PASS：关键反例（CAS 假成功、协议不全、多 path）有测 |

**Score:** 4/4

---

## 4. 安全

CLEAN（无密钥/注入/XSS；happy-dom 仅测试）。

---

## 5. 发现项

### Critical / High

**无。** 未找到可复现的用户可见阻塞缺陷。

### Medium

**无阻塞 Medium。**

### 残留风险（Low / 接受）

| # | 风险 | 为何不阻塞 |
|---|------|------------|
| R1 | Critic 对**同一规则**换显式新 `decision_key` 仍可能再问 | 为避免「同 path 多规则」误合并；换 key 是 Critic 质量问题 |
| R2 | closer 首句可能仍像「已写入」，靠后续「草稿未写入磁盘」纠正 | 状态机与 `ok`/`repair_failed` 已正确 |
| R3 | 双卡文案只取 `assistant_message` 首段 | 卡片本身可操作；细节可再点审查 |
| R4 | answer 成功后再 `brief_cmds` 二次 `persist` 吞异常 | 主路径已在 answer 内强制落盘 |
| R5 | 本机多进程同时改 `brief.draft.json` 的 TOCTOU | 产品场景为单用户 GUI |

---

## 6. 结论（直接回答「还有没有问题」）

**就本分支要解决的问题：可以认为已经没问题了（可合并）。**

更精确地说：

- **High / 假成功 / 答案丢失 / 导出脏数据：** 已关。
- **「绝对永远不再问任何相关问题」：** 做不到，也不该做——同 path 新显式决策仍应可问。
- **未手测的 LLM/真实 fishing 会话体验：** 单元与定向测覆盖契约；建议合并前做一次 2 分钟手测（答卡→看磁盘→故意冲突→再审查）。

### 门禁

| 项 | 状态 |
|----|------|
| 定向自动化通过 | [x] |
| 无未解决 High | [x] |
| 评审完整 | [x] |

- [ ] **BLOCK**
- [x] **APPROVE**

建议：合并本分支；可选 `/anvil:compound` 沉淀「session 耐久 ≠ draft 成功」经验。不必再空转文档 review。
