# 评审报告：`2026-08-06-export-soft-makeability-gates`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 工作区未提交 diff（相对 `origin/main` @ `5e82a5b`） |
| Author | local |
| Review Date | 2026-08-06 |
| Status | `APPROVED` |

**审查范围：** 今日未提交改动（导出软闸门 + 验写入降噪 + Critic `write_paths` 自愈）。不含已合并的 PR #1 防重复主干。  
**事实源：** `docs/anvil/brainstorms/2026-08-06-export-soft-makeability-gates.md`  
**Loaded standards：** 无额外 domain skill（Python CLI + React GUI 局部）

---

## 1. 自动化预检

| 检查项 | 结果 | 备注 |
|--------|------|------|
| CLI `test_makeability_gate` / `decisions` / `critic` / `host_chat` | PASS | 133 |
| GUI `briefPreviewFormat` + `makeabilityCardStatus` | PASS | 19 |
| 安全扫描 | PASS | 无密钥/注入面新增 |

---

## 2. 主需求闭环核对

| 用户可见承诺 | 机制 | 证据 | 结论 |
|--------------|------|------|------|
| 导出只硬拦结构/生图契约 | `_compute_ready_to_export` / `export_brief` 仅 `_audit_draft_gaps` | `host_chat.py`；gate 测试改为允许无审查/过期指纹/开放 intent | 成立 |
| 产品逻辑可选继续审 | GUI `briefMakeabilityExportReady` / GateHint 改为 advisory | `briefPreviewFormat.ts` + 测试 | 成立 |
| 验写入少整卡误杀 | `apply_whole_card_verifier_results` 按 key 过关 | 单测：缺一行只 fail 缺的那条 | 成立 |
| 多路径别轻易 repair_failed | `required_write_paths_from_gap` 优先 `target_paths`；spec 仍带全量 `write_paths` 给模型 | decisions + 测试 prefer target | 成立 |
| 后补丁别打回 verified | `invalidate_verified_ledger_for_patches` → no-op | chat-patch 测试 keep verified | 成立 |
| Critic 漏 write_paths 别整次挂 | `_validate_fresh_critic_intent_gaps` 自愈 union | critic heal 测试 | 成立 |

---

## 3. 对抗式发现

### Critical / High

无。

### Medium（产品残留，已按 spec 接受，不挡合并）

| ID | 说明 | 为何不挡 |
|----|------|----------|
| M1 | 可在意图未关 / 审查过期时导出，产品矛盾可能进 pipeline | 用户明确要求；结构 audit 仍硬拦 |
| M2 | Verifier 只盯 `target_paths`，多位置漂移可能残留 | 有意降噪；Closer 仍收到全量 write_paths |
| M3 | 不再因 path 碰触降级 verified；需靠下次 Critic 发现真实冲突 | 有意去掉级联假失败 |

### Low / Nit

| ID | 位置 | 说明 |
|----|------|------|
| L1 | `cli/host_chat.py` import | `ledger_blocks_export` 导入后未再使用（导出路径已不用） |
| L2 | `export_brief` → `assert_makeability_exportable` | 现为几乎空操作，可删调用或真正返回 soft warnings |
| L3 | `apply_whole_card_verifier_results` | 函数名仍叫 whole_card，行为已是 per-decision |
| N1 | `briefMakeabilityGateHint` | 中间分支布尔稍绕，可读性一般 |

---

## 4. 八维摘要

| 维度 | 结论 |
|------|------|
| Design | 与 brainstorm 对齐：硬结构 / 软产品 |
| Correctness | 单测覆盖导出放行、部分 verify、自愈、不降级 verified |
| Complexity | 净删多于增；no-op invalidate 比复杂打回更简单 |
| Naming | L3 名实不符（Low） |
| Comments | 关键 WHY 注释到位 |
| Style | 与周围一致 |
| Context | 减轻策划卡死；残留 M1–M3 可接受 |
| Tests | 旧硬闸门用例已改口径，新行为有断言 |

---

## 5. 门禁结论

- [x] 相关自动化检查通过  
- [x] 安全扫描干净  
- [x] 无未解 Critical / High  
- [x] 变更可追溯到工程 brainstorm  

**决策：APPROVED（允许提交）。**  
按用户规则：未自动 commit；需要时再说一声我帮你提交。
