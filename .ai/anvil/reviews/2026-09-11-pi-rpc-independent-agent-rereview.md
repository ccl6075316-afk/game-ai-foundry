# 评审报告：Pi 常驻 RPC 独立 Agent（IT + 策划）— 复审

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 初审 `a2645e7..d4315ad`；修复未单独 commit（本会话 working tree） |
| Author | `/anvil:code` doers + review remediation |
| Review Date | 2026-09-11（初审）/ 复审同日 |
| Status | `APPROVED`（复审：H1–H3 / M1–M3 已修） |
| Spec | [`docs/anvil/brainstorms/2026-09-11-pi-rpc-independent-agent.md`](../../docs/anvil/brainstorms/2026-09-11-pi-rpc-independent-agent.md) |
| Plan | [`docs/anvil/plans/2026-09-11-pi-rpc-independent-agent-plan.md`](../../docs/anvil/plans/2026-09-11-pi-rpc-independent-agent-plan.md) |
| 初审 | [`2026-09-11-pi-rpc-independent-agent-review.md`](./2026-09-11-pi-rpc-independent-agent-review.md)（保留 BLOCK 记录） |

**Loaded standards:** Anvil review skill；critical-patterns（JSON-RPC id 分流）。

---

## 1. 自动化预检（复审）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| CLI | `unittest BriefExecutorRoutingTest test_agent_turn test_pi_runtime` | **PASS** 64 |
| Electron | `node --test pi_rpc_session.test.mjs` | **PASS** 12 |
| GUI | `tsx --test src/chat/piSessionSync.test.ts` | **PASS** 2 |

---

## 2. 发现项关闭

| # | 状态 | 修复要点 |
|---|------|----------|
| H1 | **Fixed** | `brief chat prepare-prompt` → `build_turn_llm_prompt`（system+draft/focus/历史）；GUI 不再用薄 system |
| H2 | **Fixed** | `ChatSession.piSessionPath` 持久化；turn 回写；`piRpcListMessages` + 激活时 IT 从 Pi 拉历史 |
| H3 | **Fixed** | `test_build_turn_llm_prompt_*`；`resolvePiSessionPathFromState` / `listMessages` / authEnv 测；`piSessionSync.test.ts` |
| M1 | **Fixed** | `--assistant-raw-file` + 临时文件，避免大 argv |
| M2 | **Fixed** | 去掉全局 `piRpcActiveAuthEnv`；`prompt({ authEnv })` 按实例绑定，变更则重启子进程 |
| M3 | **Fixed** | `get_state` 优先 `sessionFile`，协议文档已注明 |

---

## 3. Karpathy（复审）

| 原则 | 结论 |
|------|------|
| Think Before Coding | PASS（C1 有 path + sync） |
| Simplicity First | PASS |
| Surgical Changes | PASS |
| Goal-Driven Execution | PASS（测覆盖 H1/H2/M2/M3） |

**Karpathy Score:** 4/4

---

## 4. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 自动化检查通过 | [x] |
| 无未解决 Critical / High | [x] |
| Spec C1 / B1 可追溯 | [x]（brief 仍双记忆：Pi 上下文 + Foundry draft 闸门，符合 B1） |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 建议可进入 `/anvil:compound`（若需知识沉淀）或按需 commit

### 残余风险（非阻塞）

- Brief 在 GUI 已有对话气泡时不覆盖拉 Pi 历史（避免冲掉 choice 卡）；IT 始终以 Pi 为准。
- Live spawn 仍依赖 `GAMEFACTORY_PI_RPC_LIVE=1` 手测。
