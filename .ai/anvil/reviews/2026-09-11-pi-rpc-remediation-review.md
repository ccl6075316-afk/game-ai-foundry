# 评审报告：Pi RPC review remediation（H1–H3 / M1–M3）

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| Scope | 初审 BLOCK 后的修复 diff（相对 `d4315ad`，未 commit） |
| Author | review remediation |
| Review Date | 2026-09-11 |
| Status | `APPROVED`（附 Medium 跟进项，不阻塞） |
| Spec | [`docs/anvil/brainstorms/2026-09-11-pi-rpc-independent-agent.md`](../../docs/anvil/brainstorms/2026-09-11-pi-rpc-independent-agent.md) |
| 初审 | [`2026-09-11-pi-rpc-independent-agent-review.md`](./2026-09-11-pi-rpc-independent-agent-review.md) |
| 上轮复审 | [`2026-09-11-pi-rpc-independent-agent-rereview.md`](./2026-09-11-pi-rpc-independent-agent-rereview.md) |

**Loaded standards:** Anvil review skill；无额外 frontend domain 硬约束。

**Change size:** Large（~+522 / −43，跨 CLI + Electron + GUI）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 |
|--------|------|------|
| Lint | — | N/A |
| 类型检查 | — | N/A（`.mjs` / 局部 TS） |
| 单元测试 | `BriefExecutorRoutingTest` + `test_agent_turn` + `test_pi_runtime` | **PASS** 64 |
| 单元测试 | `pi_rpc_session.test.mjs` | **PASS** 12 |
| 单元测试 | `piSessionSync.test.ts` | **PASS** 2 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| critical-patterns（JSON-RPC 分流） | SessionManager 是否仍先匹配 response | **PASS**（本 diff 未改 handleLine 顺序） |
| 初审 H1–H3 / M1–M3 | 逐项对照关闭条件 | **PASS**（见 §2） |

---

## 2. 初审项关闭核对

| # | 关闭证据 | 结论 |
|---|----------|------|
| H1 | `build_turn_llm_prompt` + `brief chat prepare-prompt`；`main.mjs` 用 `prompt_text` | Fixed |
| H2 | `ChatSession.piSessionPath`；turn 回写；`pi-rpc-list-messages`；App sync effect | Fixed（见 M-new-1 竞态） |
| H3 | CLI / Electron / `piSessionSync` 测 | Fixed |
| M1 | `--assistant-raw-file` + temp unlink | Fixed |
| M2 | 去掉全局 auth；`authEnv` 按实例 | Fixed |
| M3 | `sessionFile` 优先 + 协议说明 + 单测 | Fixed |

---

## 3. 安全扫描

| 类别 | 发现 | 严重级别 |
|------|------|----------|
| 密钥 | auth 仍经 env；未入 log | OK |
| 临时文件 | `assistant-raw-*.txt` finally unlink；异常崩溃可能残留 | Low |
| XSS | 同步文本进聊天气泡，无 HTML | OK |
| S1 YOLO | 未改（既有产品决策） | 披露即可 |

**安全结论：** CLEAN（仅 Low 残留）

---

## 4. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 结论 | 严重级别 |
|------|------------|------|----------|
| Think Before Coding | C1 sync 在 path 首次写入时与 turn 收尾竞态？ | 存在，见 M-new-1 | Medium |
| Simplicity First | prepare-prompt 是否必要？ | 是（与 host payload 对齐） | PASS |
| Surgical Changes | 每行可追溯 Spec？ | 可追溯；brief 双记忆符合 B1 | PASS |
| Goal-Driven Execution | 测是否证明关闭条件？ | 是；缺 sync 竞态测 | Medium |

**Karpathy Score:** 3/4（Medium 未升 High）

---

## 5. 对抗式维度（聚焦本修复）

### 5.1 功能边界

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `App.tsx` ~407–465 | IT 首次写入 `piSessionPath` 时 effect 与 `append` 并发；`chatStore` 依赖导致 cleanup `cancelled` | 可能短暂错序/重复拉历史；稳态后 key 门闩可收敛 | Medium |
| `host_chat.build_turn_llm_prompt` | `maybe_compress_session` 可能在 prepare 阶段打 **host** LLM | Pi 路径上的隐含计费/延迟；无 Key 则截断 | Medium |
| Brief C1 | `hasConv` 时不覆盖 GUI | 有意保留 choice 卡；Pi path 仍用于 `switch_session` | Low（与 B1 双记忆一致） |

### 5.2 测试

| 缺口 | 严重级别 |
|------|----------|
| 无「path 写入后 busy 期间不同步」回归测 | Medium（与 M-new-1 同项） |
| 无 prepare→raw-file→turn 的 Electron 集成测 | Low（CLI 单测已覆盖 payload） |

---

## 6. 发现项摘要

### Critical / High

无。

### Medium（强烈建议，不阻塞本次 APPROVE）

| # | 描述 | 建议动作 |
|---|------|----------|
| M-new-1 | C1 sync effect 依赖整份 `chatStore`，path 首次出现时与 turn 收尾竞态 | `busy` 时跳过 sync；deps 收窄为 session id/path；或仅在切换会话且非 busy 时拉历史 |
| M-new-2 | `prepare-prompt` → `maybe_compress_session` 可能触发 host 压缩补全 | compress 改为纯截断，或显式文档/开关；避免 Pi 回合隐式打 host |

### Low / Nit

| # | 描述 |
|---|------|
| L1 | `--assistant-raw` 与 `--assistant-raw-file` 同时存在时文件优先，未 UsageError |
| L2 | 临时 raw 文件崩溃残留 |
| L3 | Brief 每回合把整包 host payload 再注入 Pi，上下文膨胀（B1 可接受，宜日后压缩） |

---

## 7. Spec 对齐（Merge Gate）

| Spec | 本修复后 | 结论 |
|------|----------|------|
| H1 等价 payload | prepare-prompt | 满足 |
| C1 Pi session 真相 | path 持久化 + IT sync；brief 展示侧保留 Foundry 气泡 | 满足最小 C1 + B1 |
| M1 argv | raw-file | 满足 |
| M2/M3 auth / sessionFile | 已落地 | 满足 |
| 非目标 | 未扩顾问/假 ACP | 满足 |

---

## 8. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 自动化检查通过 | [x] |
| 无未解决 Critical/High | [x] |
| Spec 可追溯 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 可 commit；**M-new-1 / M-new-2** 建议作为 follow-up（可同 commit 小修或另开）
- [ ] BLOCK

### 评审备注

相对初审 BLOCK，关闭项均有代码与测证据。剩余 Medium 是「稳健性」而非「Spec 未兑现」。若要求零 Medium 再合，先修 M-new-1（成本低：busy 跳过 + 收窄 deps）。
