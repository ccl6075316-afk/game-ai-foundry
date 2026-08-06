# 评审报告：`2026-08-06-append-busy-pin`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | `f41bf17`（已上 `origin/main`） |
| Author | local |
| Review Date | 2026-08-06 |
| Status | `APPROVED` |

**审查范围：** H2 — 长任务无显式 `sessionTarget` 时，切同事不把气泡写进当前窗。  
**事实源：** 全局审查 H2（`.ai/anvil/reviews/2026-08-06-advisor-and-soft-export-global-review.md`）  
**Loaded standards：** lightweight scoped（小 diff，纯函数 + App 接线）

---

## 1. 自动化预检

| 检查项 | 结果 | 备注 |
|--------|------|------|
| `npx tsx --test src/chat/appendTarget.test.ts` | PASS | 4 |
| 安全扫描 | PASS | 无新 I/O / 无密钥面 |
| 手工 E2E | N/A | 建议：策划跑流水线 → 切顾问 → 结果应回策划窗 |

---

## 2. 主需求闭环

| 承诺 | 机制 | 证据 | 结论 |
|------|------|------|------|
| 单长任务 + 切同事，气泡回发起窗 | `markBusy` 钉住 `sessionTargetForInstance`；无 target 的 `append`/`appendAssistant` 走 `resolveAppendTarget` | `App.tsx` markBusy/append*；`appendTarget.ts` | 成立 |
| 显式 target 不被钉住覆盖 | `resolveAppendTarget` 优先 explicit | 单测 + 实现 | 成立 |
| 不重写全部 handler 调用点 | 钉住 + 解析隐式 target | diff 仅 +112 行量级 | 成立（设计正确） |

---

## 3. 对抗式发现

### Critical / High

无。

### Medium（接受，不挡）

| ID | 说明 | 为何不挡 |
|----|------|----------|
| M1 | 两个同事同时 busy，且当前窗都不在钉住集合 → `resolve` 返回 `null` → 仍写 **active** | 罕见；单测已锁该语义；真并发需显式 target 或 fan-out，另案 |
| M2 | `markBusy` 之前的同步预检 `append`（无 manifest 等）仍写 active | 正确：此时用户还在发起窗；钉住尚未开始 |

### Low

| ID | 说明 | 建议 |
|----|------|------|
| L1 | `markBusy` 用 `loadSessionStore()` 而非 React `chatStore`；依赖 `patchChatStore` 同步 `saveSessionStore` | 现状一致即可；若日后异步持久化需改钉住源 |
| L2 | 删同事 / 卸载未显式清 `appendOriginByBusyRef` | `clearBusy` 正常路径会清；残留 key 无会话时 `updateSessionMessages` 风险极低 |
| L3 | `appendAssistant` 在写回 active 时仍可能 `setBrainstormChoices`（含非策划角色） | 既有行为，非本 diff 引入 |

---

## 4. Karpathy 四问

| 原则 | 结论 |
|------|------|
| Think Before Coding | 避免对几十处 `append` 做脆弱正则改写；钉住语义对准真实 bug（单任务切窗） |
| Simplicity First | 纯函数 `resolveAppendTarget` + 两处接线，可测 |
| Surgical Changes | 未改 pipeline/VT 业务逻辑 |
| Goal-Driven Execution | 单测覆盖：explicit / 单 pin 跨窗 / 多 pin 偏好 active / 歧义回退 null |

---

## 5. Gate Decision

- [x] 自动化检查通过
- [x] 无未解决 Critical / High
- [x] 审查文档已写

**结论：`APPROVED`**

已随 `f41bf17` 合入 main；本审查为事后确认，无需再 commit 代码。可将本报告随下次文档整理一并入库，或单独 `docs/chore` 提交（可选）。
