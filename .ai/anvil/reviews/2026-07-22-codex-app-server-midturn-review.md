# 评审报告：`2026-07-22-codex-app-server-midturn`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `36d82d6`） |
| Author | `/anvil:code` doers（T1–T6） |
| Review Date | 2026-07-22 |
| Status | `APPROVED` |
| Spec | `docs/anvil/brainstorms/2026-07-22-codex-app-server-midturn.md` |
| Plan | `docs/anvil/plans/2026-07-22-codex-app-server-midturn-plan.md`（executed；可能 gitignore） |

**Loaded standards:** Anvil review skill；`docs/solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md`；`docs/solutions/failures/2026-07-22-hermes-acp-permission-bridge.md`；`docs/solutions/patterns/critical-patterns.md`；无额外 frontend/backend domain 规则。

**变更规模：** Large（新建 `codex_app_server_*` ~4 文件 ≈1870 行含测；`main.mjs` +156；CLI 闸；GUI 卡 source；`GUI-CONFIG.md`）

**历史经验 lens：** JSON-RPC method-first + `gaf-c-*` id；禁止假安全/静默回退 exec；本会话≠永久 execpolicy；第三方协议用真实审批探针（T2 风险闸 PASS）。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 项目无统一 lint 门禁 |
| 类型检查 | `cd gui && npx tsc --noEmit` | PASS | |
| 单元测试 CLI | `cd cli && python -m unittest test_agent_turn -q` | PASS | 33 OK |
| Electron node | `node --test codex_app_server_*.test.mjs *_acp_*.test.mjs` | PASS | 68 OK |
| 手测 | Spec 成功标准 1–3 | **PASS** | 用户「没问题」确认 |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec→Plan→Diff | PASS：`sandbox≠danger`→GUI app-server；danger→exec；CLI 拒跑；平行 `codex_app_server_*`；卡复用；失败不静默 exec；不用 daemon |
| 非目标未侵入 | PASS：无共享 daemon；无永久 always/execpolicy 落盘；未抽三家基类；Cursor/Hermes 路径保留 |
| Resume / Verification | PASS：plan `executed` + 验证命令有证据 |
| 并行状态源 | PASS：无第二套 task tracker |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 假安全 / 静默 exec | CLI 非 danger 在 `_run_cmd` 前抛错；GUI catch **return**，无 fallthrough 到 `agent turn` | — | OK |
| 永久放权 | session→`acceptForSession`；单测断言永不 emit `acceptWithExecpolicyAmendment` | — | OK |
| daemon | spawn 仅 `app-server --listen stdio://` | — | OK |
| 跨 instance | Map 隔离；session/turn allow 按 instance；stop IPC 含 Codex | — | OK |
| XSS / 日志 | 卡摘要 `slice(0,500)`；启停日志短结构化 | Low | OK |

**安全结论：** CLEAN（无阻塞）

---

## 3. Karpathy 对抗式原则

| 原则 | 结论 |
|------|------|
| Think Before Coding | PASS：开关复用现有 `sandbox`；默认 workspace-write→GUI 审批为有意跳变；协议风险闸先于 T3 |
| Simplicity First | PASS：平行模块对照 Cursor/Hermes，未过早抽基类；复用 Pi 卡 |
| Surgical Changes | PASS：改动可追溯 T1–T6；Cursor/Hermes 行为未故意改写 |
| Goal-Driven Execution | PASS：CLI 拒跑测、撞车/method-first 测、session argv 测、execpolicy 拒绝测；GUI 手测已签收 |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度（摘要）

### 4.1 设计
平行 `codex_app_server_*` + `main` 分流符合 Spec。`agent-turn` 现有 Cursor/Hermes/Codex 三段同构重复——Spec 明确本期不抽基类，**可接受**（Low 债）。

### 4.2 功能
- 分流与 return 路径正确：非 danger 无 fallthrough 到 `runCli agent turn`。
- `resolveCodexSandbox` 与 CLI 实例→全局→默认 `workspace-write` 对齐。
- 删同事：`App.tsx` → `stopAgentAcpInstance` → `main` stop Cursor/Hermes/**Codex**（相对 Hermes 评审 F2 已闭合）。
- **F1**：`item/permissions/requestApproval` 的 deny 在 adapter 显式 throw（有单测）；用户点「拒绝」可能使 `respondPermission` 抛错、回合挂起。主竖切为 command approval（手测已过）；permissions 为次要种类。
- **F2**：`decidePermission` 签名为对象 `{ permissionId, decision }`，与 Cursor/Hermes 位置参数不一致——`main` 已适配，但增加认知成本。

### 4.3 复杂度
可接受。`pathWithCommonNodeBins` 与 ACP session 重复——平行模块代价。

### 4.4–4.6 命名 / 注释 / 风格
`source: codex_app_server`、`gaf-c-`、adapter 方法表注释充分。无阻塞风格问题。

### 4.7 上下文
文档写明默认 sandbox 跳变。提交时勿漏 untracked `codex_app_server_*` 与 Spec brainstorm；plan 若 gitignore 可只留本地。

### 4.8 测试
Adapter/session mock 覆盖充分；CLI 闸覆盖。无 GUI E2E 自动化——手测已补证据。

---

## 5. 发现项

### 🔴 Critical

（无）

### 🟠 High

（无）

### 🟡 Medium

| ID | 发现 | 证据 | 建议 |
|----|------|------|------|
| F1 | `item/permissions/requestApproval` deny 编码 throw，用户拒绝可能挂起回合 | `codex_app_server_adapter.mjs` `encodePermissionsApprovalDecision` deny 分支；test「throws for permissions deny」 | follow-up：映射安全 deny（若 schema 无 decline，则 JSON-RPC error 回写或文档写明「权限类卡勿点拒绝、用取消回合」） |

### 🟢 Low

| ID | 发现 | 建议 |
|----|------|------|
| L1 | `agent-turn` 三家 mid-turn 持久化块重复 | 三家都稳后再抽 |
| L2 | Codex `decidePermission` 对象签名 vs ACP 位置参数 | 保留并注释；或后续统一为双形兼容 |
| L3 | `ensureThread` 不因 model 变化重建 thread（turn/start 可带 model） | 观察即可；若模型切换无效再修 |

---

## 6. Spec 追溯

| Spec / Plan 项 | Diff | 状态 |
|----------------|------|------|
| `sandbox≠danger` → GUI app-server | `main.mjs` Codex 分流 | done |
| `danger-full-access` → exec + stop | stop + `runCli agent turn` | done |
| CLI 拒跑文案 | `_codex_cli_non_danger_error` | done |
| 平行模块 + 探针风险闸 | `codex_app_server_*` + T2 PASS | done |
| 卡四键 / 本会话不落盘 | 复用 IPC + `acceptForSession` | done |
| 永不 execpolicy 永久修订 | adapter 映射 + 单测 | done |
| 失败不静默 exec | catch return | done |
| 删同事 / 关窗停进程 | stop IPC + disposeAll | done |
| GUI 手测 | 用户「没问题」 | **done** |
| 文档默认跳变 | `GUI-CONFIG.md` | done |

非目标（daemon、永久 always、抽基类、假安全）未被破坏。

---

## 7. 修改建议

1. **可合并后 follow-up**：F1 permissions deny 路径。  
2. **Commit 范围**（需用户说「提交」）：  
   - `cli/agent_turn.py`、`cli/test_agent_turn.py`  
   - `gui/electron/codex_app_server_{adapter,session}.mjs` + tests  
   - `gui/electron/main.mjs`  
   - `gui/src/{App,components/ChatView,chat/types,vite-env}.tsx|ts`  
   - `docs/GUI-CONFIG.md`、`docs/anvil/brainstorms/2026-07-22-codex-app-server-midturn.md`  
   - 本 review：`.ai/anvil/reviews/2026-07-22-codex-app-server-midturn-review.md`  
   - plan 若被 ignore 可不进仓  

---

## 8. 修复记录

| 轮次 | 说明 | 验证 |
|------|------|------|
| — | 本轮无 Critical/High，未派 doer 热修 | — |

---

## 9. 最终结论

- [x] **PASSED / APPROVED** — 允许提交（Medium F1 不阻塞；主路径手测已过）
- [ ] **FAILED** — 提交前必须修复

**Gate：** 自动化绿；安全 CLEAN；无未解决 Critical/High；Spec 主路径可追溯；手测签收。

**Commit 策略：** 按用户规则 **暂不自动 commit**——需要时请说「提交」或「commit」。

**下一步建议：** 说「提交」→ 可选 push → 可选 `/anvil:compound`（Codex app-server 方法表 / permissions deny 边界）→ follow-up F1。
