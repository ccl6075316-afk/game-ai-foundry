# 评审报告：Pi 常驻 RPC 独立 Agent（IT + 策划）

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | `a2645e7..d4315ad`（含 `f3c5c64` 功能收口） |
| Author | `/anvil:code` doers + lead |
| Review Date | 2026-09-11 |
| Status | `BLOCKED`（CHANGES REQUESTED）→ **已由复审关闭**：见 [`2026-09-11-pi-rpc-independent-agent-rereview.md`](./2026-09-11-pi-rpc-independent-agent-rereview.md)（`APPROVED`） |
| Spec | [`docs/anvil/brainstorms/2026-09-11-pi-rpc-independent-agent.md`](../../docs/anvil/brainstorms/2026-09-11-pi-rpc-independent-agent.md) |
| Plan | [`docs/anvil/plans/2026-09-11-pi-rpc-independent-agent-plan.md`](../../docs/anvil/plans/2026-09-11-pi-rpc-independent-agent-plan.md) |

**Loaded standards:** Anvil review skill；`docs/solutions/patterns/critical-patterns.md`；无额外 frontend/backend domain 文件加载。

**Scope:** IT/策划 Pi 从空心壳改为常驻 `--mode rpc`；SessionManager；host-chat `--assistant-raw`；LEGACY 门闩；skills/docs。

**非目标确认（diff 未越界）：** 顾问仍弱工具；未做假 ACP / MCP 工具注册 / GUI 脱离化。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | — | N/A | 仓库无统一 lint script |
| 类型检查 | — | N/A | Electron `.mjs` 无 tsc 门禁 |
| 单元测试 | `python -m unittest test_agent_turn test_pi_runtime test_host_chat -q` | **PASS** 204 | |
| 单元测试 | `node --test pi_rpc_session.test.mjs pi_rpc_contract.test.mjs` | **PASS** 16 / skip 1 | live spawn 需 Key |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| critical-patterns（JSON-RPC id 分流） | 查 `pi_rpc_session.handleLine` 是否先 `type===response` | **PASS**：先匹配 pending response，再 `extension_ui_request`，再 event；测覆盖撞车 |
| Hermes 审批桥失败 | S1 不接 permission | **N/A**（有意 YOLO） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 未见；Key 经 env 注入 | — | OK |
| 注入风险 | `--assistant-raw` 大段模型输出进 argv | Medium | 见 High/Medium #3 |
| XSS | GUI 未新增 HTML 渲染路径 | — | OK |
| 依赖 CVE | 未扫 npm audit | Low | 本轮不阻塞 |
| 日志敏感数据 | `buildPiRpcAuthEnv` 不把 key 打进 onLog | — | OK |
| S1 YOLO | `extension_ui_request` 自动 `confirmed: true` | 产品已确认 | 文档已披露 |

**安全结论：** ISSUES FOUND（argv 体量 + S1 有意信任，非密钥泄露）

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | C1「Pi session 为聊天真相」是否真落地？ | 仅返回 `pi_session_path`；App 未同步/重载 | **FAIL** | High |
| Simplicity First | SessionManager + assistant-raw 双路径是否必要？ | 保留 draft 闸门需要 apply 路径；合理 | PASS | — |
| Surgical Changes | 每行可追溯 Spec？ | IT/LEGACY/契约可追溯；brief prompt 过简偏离策划事实源 | **FAIL** | High |
| Goal-Driven Execution | 测是否证明功能？ | mock NDJSON / 门闩测强；缺「brief 带 draft payload」与 C1 GUI 同步测 | **FAIL** | High |

**Karpathy Score:** 1/4

---

## 4. 对抗式维度评审

### 4.1 设计

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `pi_rpc_session.mjs` | 是否应存在？ | 是，对齐常驻 Codex/Hermes 形态 | — |
| `buildBriefPiRpcPrompt` | 是否应用短 system 替代 `_system_prompt`+session payload？ | **否**：丢掉 draft/focus/历史，破坏策划状态机输入 | High |

**维度结论：** FINDINGS

### 4.2 功能

| 位置 | 遗漏 | 严重级别 |
|------|------|----------|
| `main.mjs` `buildBriefPiRpcPrompt` ~509–511 | Pi 只收到短 system + 用户句；**不**注入 `host_chat._build_user_payload`（draft/focus/会话）。随后 `--assistant-raw` 仍按 JSON skill 解析 → 高概率 `json_parse_failed` / draft 不更新 | High |
| `pi_session_path` 返回值 | GUI `App.tsx` / preload **零消费**；重启后无法从 Pi session 还原聊天（Spec C1） | High |
| `main.mjs` `--assistant-raw` + `out.text` | 大回复经 CLI argv；Windows 命令行长度风险 | Medium |
| `piRpcActiveAuthEnv` 全局 | IT 与 brief 并发回合可能串 Key/env | Medium |
| `ensurePiSession` ~379–385 | `get_state` 的 `sessionId` 是否可作为 `switch_session` 的 `sessionPath` 未用 live 验证 | Medium |

**已检查关键边界：**
- [x] 空输入（prompt 空串仍发送）
- [ ] 最大尺寸（argv）— **缺口**
- [x] 外部依赖失败（缺 Key / manager null 有错误返回）
- [ ] 并发访问 — **缺口**（全局 auth env）

**维度结论：** FINDINGS

### 4.3 复杂度

| 判断 | 严重级别 |
|------|----------|
| SessionManager 体量与 Hermes ACP 对照，可接受 | — |
| brief 用「RPC + assistant-raw」两跳合理 | — |
| 无投机 MCP/假 ACP | PASS |

**维度结论：** PASS

### 4.4 命名

| 项 | 判断 |
|----|------|
| `createPiRpcSessionManager` / `gaf-pi-` | 清晰 |
| `piRpcActiveAuthEnv` | 暗示全局可变状态 — 可接受但需防并发 |

**维度结论：** PASS（Nit：manager 名偏泛，与仓库 ACP manager 一致）

### 4.5 注释

| 项 | 判断 |
|----|------|
| T3 注释、LEGACY 文档 | 解释 WHY，OK |
| skills 逃生说明 | OK |

**维度结论：** PASS

### 4.6 风格

与现有 `hermes_acp_session` / `main.mjs` 模式一致；功能与文档分 commit，OK。

**维度结论：** PASS

### 4.7 上下文

空心壳默认退役 + RPC 主路径改善方向正确；但 **C1 名存实亡** + **brief 上下文丢失** 使系统对用户可能「能聊但不能稳更 draft」。

**维度结论：** FINDINGS

### 4.8 测试

| 项 | 判断 | 严重级别 |
|----|------|----------|
| NDJSON 分流 / 崩溃重建 / LEGACY 门闩 | 强 | — |
| brief Electron 路径无集成测（payload 注入） | 缺口 | High |
| C1 GUI 同步无测 | 缺口 | High |
| live spawn skip | 可接受，须手测 | Medium |

**维度结论：** FINDINGS

---

## 5. 发现项摘要

### Critical（阻塞提交）

无。

### High（阻塞合并本功能为「Spec 完成」）

| # | 维度 | 位置 | 描述 | 必须动作 |
|---|------|------|------|----------|
| H1 | 功能 / Spec | `main.mjs` `buildBriefPiRpcPrompt` | 策划 Pi 回合未注入 host_chat 会话 payload（draft/focus/历史），与旧 `_call_llm` 输入不对等 | 拼装与 CLI 同等的 system+user（可临时文件/`brief chat` 只读导出 prompt），再送 Pi RPC |
| H2 | Spec C1 | `pi_session_path` 全链路 | 返回字段无 GUI 持久化/重载/`get_messages` 同步；聊天真相仍是渲染层 Foundry store | 实现最小 C1：持久化 path + 重进会话时从 Pi 拉历史，或修订 Spec 降级 C1 并再确认 |
| H3 | 测试 | — | 无测证明 H1/H2；现有测在 mock 协议层绿，不能证明策划产品行为 | 为 H1 加单测（prompt 含 draft 关键字段）；为 H2 加「path 写回/可读」契约 |

### Medium（强烈建议）

| # | 维度 | 位置 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 功能 | `host-chat-turn` `--assistant-raw` | 大模型输出经 argv | 改 stdin/临时文件传 raw，与 Pi 长 prompt 文件策略一致 |
| M2 | 功能 | `piRpcActiveAuthEnv` | 全局可变，并发串扰 | 按 instance 绑 env 或 prompt 期间锁 |
| M3 | 功能 | `ensurePiSession` | `sessionId` vs 文件 path 语义 | live 或契约测确认 `switch_session` 可用该值 |

### Low / Nit

| # | 描述 |
|---|------|
| L1 | `resolveBriefExecutor` 与 CLI `pi_status.ready` 判定不完全同构（Electron 用 auth+embed）— 文档对齐即可 |
| L2 | Plan 标 `executed` 但 Spec 成功标准 4（C1 恢复）未满足 — 应改 plan Code Status 或修代码 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [ ]（M1 argv；S1 有意） |
| Karpathy score = 4/4 | [ ] 1/4 |
| 无未解决 Critical | [x] |
| 无未解决 High | [ ] H1–H3 |
| Spec 可追溯且非目标未破 | [ ] C1 未兑现 |
| 评审文档完整 | [x] |

### 结论

- [x] **BLOCK** — 合并前必须解决 **H1–H3**（或回 `/anvil:req` 正式降级 C1 / 接受 brief 弱上下文并改 Spec 成功标准）
- [ ] **APPROVE**

### 评审备注

- IT 接线、SessionManager、LEGACY 门闩、契约测方向正确，是可保留基线。
- 阻塞点集中在 **策划输入完整性** 与 **C1 产品承诺**，不是「RPC 起不来」。
- 建议下一动作：fix H1（优先）→ 明确 C1 修或 Spec 降级 → 补测 → 复审。

### Spec 对齐表

| Spec 项 | Diff | 结论 |
|---------|------|------|
| A/T1 常驻 RPC | SessionManager + spawn | 满足 |
| P 原生工具 | 去掉 --no-tools 主路径 | 满足（进程内工具） |
| S1 YOLO | auto-confirm UI | 满足 |
| R2 IT+策划 | 两分支 | 满足（入口） |
| B1 export | skill + assistant-raw 门闩 | 满足（闸门保留） |
| C1 Pi session 真相 | path 未接入 GUI | **不满足** |
| 空心壳退役 | LEGACY 门闩 | 满足 |
