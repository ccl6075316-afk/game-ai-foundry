# 评审报告：`2026-07-22-cursor-acp-midturn`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `fd7e870`） |
| Author | `/anvil:code` doers + lead 热修（JSON-RPC id） |
| Review Date | 2026-07-22 |
| Status | `APPROVED` |
| Spec | `docs/anvil/brainstorms/2026-07-22-cursor-acp-midturn.md` |
| Plan | `docs/anvil/plans/2026-07-22-cursor-acp-midturn-plan.md`（executed；gitignore） |

**Loaded standards:** Anvil review skill；无 docs/solutions；frontend/backend domain 空/未用。

**变更规模：** Large（~512+ 已跟踪 + 新建 adapter/session；跨 Electron/CLI/GUI）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | |
| 类型检查 | `cd gui && npx tsc --noEmit` | PASS | |
| 单元测试 | `python -m unittest test_agent_turn test_tool_permission -q` | PASS | 40 OK |
| ACP node | `node --test cursor_acp_*.test.mjs` | PASS | 15 OK |
| 手测 | 用户确认「没问题了」 | PASS | 批准卡可见 |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec→Plan→Diff | PASS（Cursor only；非 force→ACP；仅 GUI；Pi 卡复用） |
| 非目标未侵入 | PASS（无 Hermes/Codex ACP；无永久 always 落盘） |
| Resume | PASS |
| 热修 trace | PASS：id 撞车根因已写入实现与单测 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| docs/solutions | 不存在 | 本轮将 compound「JSON-RPC id 撞车」 |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 假安全 | CLI 非 force 拒跑；GUI 非 force 不走 capture_output | — | OK |
| 永久放权 | session→allow-always 仅进程内 | — | OK |
| XSS | 卡文案来自工具摘要截断 | Low 可接受 | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 结论 |
|------|------|
| Think Before Coding | PASS（mode 分流 + ACP 并行路径） |
| Simplicity First | PASS（复用 Pi 卡；adapter/session 分层合理） |
| Surgical Changes | PASS |
| Goal-Driven Execution | PASS（CLI gate + collision 单测 + 用户手测） |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度（摘要）

### 4.1 设计
并行 ACP vs one-shot 符合 Spike；`record-turn` 补持久化可接受。

### 4.2 功能
已修：`handleRpcLine` 先 method；客户端 id `gaf-*`；`clientCapabilities`；`session/set_mode`。纯闲聊无工具仍无卡——符合上游行为，文档已说明。

### 4.3–4.7
复杂度与命名可接受；未引入第二套卡片。

### 4.8 测试
碰撞回归测已加；无 E2E 自动化（手测覆盖）— Medium 债不阻塞。

---

## 5. 发现项摘要

### Critical / High
（无）

### Medium
| # | 描述 | 动作 |
|---|------|------|
| F1 | 无 GUI E2E 自动测「真 agent 弹卡」 | 后续可选；本版手测已过 |

### Low / Nit
| # | 描述 |
|---|------|
| F2 | `auto_review`→ACP `agent` 模式，依赖上游仍发 request_permission（本机 shell 探针已验证） |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 自动化检查 | [x] |
| 安全扫描 | [x] |
| Karpathy 4/4 | [x] |
| 无 Critical/High | [x] |
| Spec 可追溯 | [x] |

### 结论

- [x] **APPROVE** — 允许 commit/push；下一步 compound 后开 Hermes ACP req

### 评审备注

- 勿提交 `tmp-acp-midturn-probe.txt`（已删）。
- `plans/` 仍 gitignore。
