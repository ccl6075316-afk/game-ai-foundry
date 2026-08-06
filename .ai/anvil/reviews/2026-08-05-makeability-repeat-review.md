# 评审报告：`2026-08-05-makeability-repeat`（复审）

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | `main...HEAD`（含 H1–H4 / M1–M4 修复） |
| Author | local |
| Review Date | 2026-08-05 |
| Status | `APPROVED` |

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| 单元测试 | `cd cli && python -m pytest test_makeability_decisions.py test_makeability_critic.py test_makeability_gate.py test_host_chat.py -q` | PASS | 128 passed |
| GUI 测试 | `npx tsx --test …MakeabilityGapCard.test.tsx …makeabilityCardStatus.test.ts` | PASS | 8 passed；retry 现为 happy-dom 真实 click |

---

## 2. 发现项闭环

| # | 修复 |
|---|------|
| H1 | `export_brief` 先 `sync_session_draft_from_disk`；双改冲突拒绝导出 |
| H2 | `persist_project_draft` 三方指纹 CAS；无指纹仅允许更丰富会话覆盖 |
| H3 | `decision_key_alias_map_from_checks` 禁用路径子集猜 alias |
| H4 | Critic `decision_checks` 协议不全 → `HostChatError`，不静默降级 ledger |
| M1 | `validate_occurrences_strict`：非法 relation 直接拒绝 |
| M2 | Verifier 缺 key 记为 protocol_error，不进入 closer 修复轮 |
| M3 | 无 snapshot 旧账本用 `_synthesize_gap_from_ledger_entry` 恢复 |
| M4 | `MakeabilityGapCard` happy-dom 点击「重试写入」触发 `onRetry` |

---

## 3. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有定向自动化检查通过 | [x] |
| 无未解决 Critical / High | [x] |
| Karpathy（并发/语义/可测） | [x] |

### 结论

- [ ] **BLOCK**
- [x] **APPROVE**
