# 全局评审报告：`2026-08-06-advisor-and-soft-export-slice`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| 范围 | 今日切片：`0519501` 导出软闸门 + `21f6543` 顾问工种 + **未提交** 发送串线路由修复 |
| Base | `origin/main` @ `21f6543`（软闸门/顾问已上 main；串线修复仍在工作区） |
| Review Date | 2026-08-06 |
| Status | `APPROVED_WITH_FOLLOWUPS` |
| 子审查 | 串线路由已单独 `APPROVED`（`.ai/anvil/reviews/2026-08-06-advisor-send-route-review.md`）；软闸门曾 `APPROVED`（同日 export-soft review） |

**Loaded standards：** 整仓账本 `docs/solutions/reviews/2026-08-04-whole-project-review-ledger.md`（不重报 Fixed/Accepted）；并行 explore：顾问注册 / 软闸门残留 / 多同事串台。

---

## 1. 自动化预检

| 检查项 | 结果 |
|--------|------|
| `test_pi_foundry_tools` + `test_makeability_gate` | PASS |
| `colleagueSendRoute.test.ts` + `briefPreviewFormat.test.ts` | PASS（16+3） |
| 安全扫描（本切片） | PASS：顾问只读白名单；软闸门无新注入面 |

---

## 2. 主需求闭环

| 承诺 | 状态 | 证据 |
|------|------|------|
| 导出只硬拦结构/生图契约（GUI / `export_brief`） | **成立** | `host_chat._compute_ready_to_export`；GUI `briefMakeabilityExportReady` |
| 制作审查/intent/ledger 不挡存 | **大体成立** | GUI 已放行；见下方 **H1** Pi 磁盘旗标残留 |
| 可雇顾问、锁 Pi、只读工具 | **成立** | `tool_profile=advisor` + `_ADVISOR_ALLOWED_PREFIXES` + 单测 |
| 顾问发言不进策划 host-chat | **工作区已修，未上 main** | `routeColleagueSend`：仅 brief→brainstorm |
| 两同事并发不串气泡 | **主路径已修；长任务无 target 仍残留** | 见 F2 / 账本式 Deferred |

---

## 3. 对抗式发现（全局）

### Critical

无。

### High（须跟进；不挡「串线修复」合入）

| ID | 说明 | 证据 | 建议 |
|----|------|------|------|
| **H1** | 软闸门后 **GUI/`export_brief` 已按结构算就绪**，但 Pi 导出仍读磁盘 `session.ready_to_export`；enrich/验写入失败等会把旗标打成 `False` 且不重算 → **策划 Pi「存」与 GUI 存不一致** | `cli/pi_foundry_tools.py:503-517`；`host_chat.py` Pi `allow_export = … ready_to_export`；enrich/`_answer_makeability_failure` 写 False | **已修（后续 commit）**：`_session_allows_export` / Pi `allow_export` / 若干写盘点改为 `_compute_ready_to_export` |
| **H2** | 长任务大量 `append` **无 sessionTarget**（北极星 / pipeline run / safeAction / doctor…）。切同事 mid-flight 仍可能把结果写进当前窗 | `App.tsx` handleRun / VT / handleSafeAction 等（既有债，非顾问引入） | Deferred 专案：长任务强制 target；可记入整仓账本 Deferred |

### Medium（顾问注册 / 产品文案）

| ID | 说明 | 证据 |
|----|------|------|
| M1 | `syncPiLockedInstancesToPreset` 仍只同步 `brief\|it`，漏 advisor | `agentInstances.ts:270` |
| M2 | `handleAgentTurn` 仍角色白名单（与 send-route「非 brief→agent」不对称） | `App.tsx:2084-2086` |
| M3 | 文档/技能仍写 makeability **阻塞** export | `AI-HANDOFF.md`、`ITERATIVE-PRODUCTION.md`、`commit-brief.md` |
| M4 | hostChat 辅助入口（export/autofix/…）多数无 brief 角色闸；气泡 chips 可在顾问窗点出「生成北极星/跑资产」 | `App.tsx` handleSend 特殊指令在路由前；`ChatView` 历史 chips |
| M5 | `pendingSafeActions` 切同事不清理 | `App.tsx` handleSelectColleague |
| M6 | upsert 拒非 Pi 文案只写「策划」；CLI help 缺 advisor | `agents_instances_upsert.py`；`agent_cmds` / `conversations_cmds` |

### Low

| ID | 说明 |
|----|------|
| L1 | `brainstormActive` 全局；切同事不清（路由已安全） |
| L2 | `assert_makeability_exportable` / `ledger_blocks_export` import / whole_card 命名名实不符 |
| L3 | 顾问等待文案仍像 Hermes/Codex；`agentStatus` 类型缺 it/advisor |
| L4 | host-chat 与 agent 共用扁平 `sess-*`（历史脏会话风险） |

---

## 4. 与整仓账本关系

- **不重开** F1–F11 / A1–A5。
- **H2** 属多同事并发正确性，接近 D6（App 过大）的下游症状；建议升为新 Deferred：`D9 长任务 append 必须带 sessionTarget`。
- **H1** 是今日软闸门切片的 **遗漏闭环**，应优先于文档打扫。

---

## 5. Gate Decision

| 子项 | 结论 |
|------|------|
| 未提交串线修复 | **允许合入**（已单独 APPROVED；默认值已反转为「仅 brief→策划」） |
| 已上 main 的软闸门 + 顾问 | **维持可用**；H1 已在后续 commit 对齐；H2 仍为 Deferred |
| 全局切片 | **`APPROVED_WITH_FOLLOWUPS`**（剩余：H2 长任务 target、顾问 Medium 注册） |

**合入顺序建议**

1. ~~提交并 push 串线修复~~（`eccd000`）
2. ~~修 H1（Pi/`ready_to_export` 与结构就绪对齐）~~
3. 顾问 Medium（M1/M2）与文档 M3 可随后。
4. H2 长任务 target 专案，勿塞进热修。

**不自动 compound**；H1 修完后再沉淀 solutions。
