# 评审报告：`2026-08-06-advisor-send-route`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 工作区未提交 diff（相对 `origin/main` @ `21f6543`） |
| Author | local |
| Review Date | 2026-08-06 |
| Status | `APPROVED` |

**审查范围：** 顾问发言误走策划 `hostChatTurn` 的串线修复。  
**事实源：** 用户缺陷报告 + 顾问工种 brainstorm（`docs/anvil/brainstorms/2026-08-06-advisor-colleague-role.md`）  
**Loaded standards：** lightweight scoped（小 diff）；无额外 domain skill

---

## 1. 自动化预检

| 检查项 | 结果 | 备注 |
|--------|------|------|
| `npx tsx --test src/chat/colleagueSendRoute.test.ts` | PASS | 3 |
| 安全扫描 | PASS | 无密钥 / 无注入面 |
| App 端到端 GUI | N/A | 手工：重启 GUI 后顾问发言应走 agent turn |

---

## 2. 主需求闭环核对

| 用户可见承诺 | 机制 | 证据 | 结论 |
|--------------|------|------|------|
| 顾问窗不出现策划式回复 | `handleSend` 经 `routeColleagueSend`；非 brief → agent | `App.tsx` + `colleagueSendRoute.ts` | 成立 |
| 策划路径不被误触 | brainstorm start/turn 增加 `roleKind === "brief"` 守卫 | `App.tsx` | 成立 |
| 顾问执行器仍锁 Pi | Electron `resolveExecutorForAgentTurn` 对 advisor 强制 `pi` | `main.mjs` | 成立 |
| 类型与 IPC 对齐 | `vite-env.d.ts` `agentTurn.role` 含 `advisor` | 类型文件 | 成立 |

---

## 3. 对抗式发现

### Critical

无。

### High（审查中已修）

| ID | 说明 | 处置 |
|----|------|------|
| H1 | 初版路由是「枚举 agent 角色，默认 brief」——与本次 bug 同类脚枪；再加新工种会再漏 | **已改**：仅 `brief` 走 brainstorm，其余一律 `agent`；测试遍历 `CHAT_AGENT_ROLES` |

### Medium

无。

### Low（不挡合并）

| ID | 说明 | 建议 |
|----|------|------|
| L1 | `brainstormActive` 仍是全局 React state；切到顾问后标志可能仍为 true（路由已安全，但芯片/状态心智仍共享） | 后续可按 `activeInstanceId` 隔离；本轮不必 |
| L2 | 无 App.tsx 集成测；单测只证明纯函数 | 可接受；接线点极短 |
| L3 | brainstorm 守卫静默 `return`：若将来直接调用且已 append user，会只见用户气泡无回复 | 当前仅 brief 路由可达；可接受 |

---

## 4. Karpathy 四问

| 原则 | 结论 |
|------|------|
| Think Before Coding | 根因是 `handleSend` 白名单漏 advisor，不是「回写用了 active」竞态 |
| Simplicity First | 抽出小纯函数合理；审查后默认值反转比白名单更简单 |
| Surgical Changes | 改动限于 GUI 发送路由 + Electron advisor→pi；无 scope creep |
| Goal-Driven Execution | 测试在 `brainstormActive=true` 下断言顾问/非 brief → agent；故意回退会红 |

---

## 5. Gate Decision

- [x] 自动化检查通过（针对本 diff）
- [x] 安全扫描干净
- [x] 无未解决 Critical / High
- [x] 审查文档已写

**结论：`APPROVED` — 允许提交。**

建议 commit message：`fix: route advisor sends to agent turn, not brief chat`
