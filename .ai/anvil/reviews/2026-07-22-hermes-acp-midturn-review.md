# 评审报告：`2026-07-22-hermes-acp-midturn`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `882969f`） |
| Author | `/anvil:code` doers（T1–T6） |
| Review Date | 2026-07-22 |
| Status | `APPROVED` |
| Spec | `docs/anvil/brainstorms/2026-07-22-hermes-acp-midturn.md` |
| Plan | `docs/anvil/plans/2026-07-22-hermes-acp-midturn-plan.md`（executed；可能 gitignore） |

**Loaded standards:** Anvil review skill；`docs/solutions/failures/2026-07-22-acp-jsonrpc-id-collision.md`；`docs/solutions/patterns/critical-patterns.md`；无额外 frontend/backend domain 规则。

**变更规模：** Large（新建 hermes_acp_* ~四文件；`main.mjs` +141；CLI 文案；GUI 卡 source；文档）

**历史经验 lens：** JSON-RPC 必须先 `method` 再 pending；客户端 id 命名空间隔离 → 已在 adapter/session 与撞车单测中落实。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 项目无统一 lint 门禁 |
| 类型检查 | `cd gui && npx tsc --noEmit` | PASS | |
| 单元测试 | `python -m unittest test_agent_turn test_tool_permission -q` | PASS | 40 OK |
| ACP node | `node --test hermes_acp_*.test.mjs cursor_acp_*.test.mjs` | PASS | 39 OK |
| 手测 | Spec 成功标准 1–3 | **PENDING** | 用户尚未确认 GUI 弹卡 |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec→Plan→Diff | PASS：`yolo=false`→GUI ACP；CLI 拒跑；`--accept-hooks`；平行 `hermes_acp_*`；卡复用；失败不静默 YOLO |
| 非目标未侵入 | PASS：无 Codex app-server；无永久 always；无大抽基类；Cursor 路径保留 |
| Resume / Verification | PASS：plan `executed` + 验证命令有证据 |
| 并行状态源 | PASS：无第二套 task tracker；`docs/solutions` 为 compound 知识库（可接受） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 假安全 / 静默 YOLO | GUI `yolo=false` 仅 ACP；失败 return，不回退 `agent turn`；CLI 仍拒跑 | — | OK |
| `--accept-hooks` | 扩大 hooks 静默面；文档已写明；工具仍走卡 | Medium 产品面 | 已文档化 OK |
| 永久放权 | session→`allow_always` 仅进程内 | — | OK |
| 跨 instance | session/turn allow 按 instance Map | — | OK |
| XSS | 卡摘要 `slice(0,500)` | Low | OK |

**安全结论：** CLEAN（无阻塞）

---

## 3. Karpathy 对抗式原则

| 原则 | 结论 |
|------|------|
| Think Before Coding | PASS：开关用现有 `yolo`；GUI/CLI 边界清晰；禁止假安全 |
| Simplicity First | PASS：平行模块对照 Cursor，未过早抽基类；复用 Pi 卡 |
| Surgical Changes | PASS：改动可追溯 T1–T6；Cursor ACP 行为未故意改写 |
| Goal-Driven Execution | PASS：CLI 拒跑测、撞车测、session argv/`--accept-hooks` 测；缺 GUI 手测见 F1 |

**Karpathy Score:** 4/4（手测缺口记为 Medium，不降原则分）

---

## 4. 对抗式维度（摘要）

### 4.1 设计
平行 `hermes_acp_*` + `main` 分流符合 Spec。`main.mjs` 中 Cursor/Hermes 两段几乎同构 ACP 块增加重复——Spec 明确本期不抽基类，**可接受**（Low 债）。

### 4.2 功能
- 分流顺序与 return 路径正确：`yolo=false` 无 fall-through 到 `agent turn`。
- `resolveHermesYolo` 与 CLI 实例→全局→默认 `true` 对齐。
- **F2**：删同事未调用 `hermesAcpSessionManager.stop`（Cursor 同期亦缺）；仅关窗 `disposeAll` / 切回 YOLO 时 stop → 可能残留进程至退出。
- **F3**：`getAuthMethodId` 默认 `"openrouter"`，`main` 未注入 Foundry Hermes provider；非 OpenRouter 配置下 authenticate 可能硬失败（符合「硬失败」但不接线）。

### 4.3 复杂度
可接受。`pathWithCommonNodeBins` 与 Cursor 重复——平行模块代价。

### 4.4–4.6 命名 / 注释 / 风格
`source: hermes_acp`、`gaf-h-` 前缀清晰。adapter 方法表注释充分。无阻塞风格问题。

### 4.7 上下文
系统能力对齐 Cursor 试点；文档去掉「未接 ACP」过时表述。工作区另含先前 `docs/solutions` compound 与 Cursor brainstorm 小改，**提交时应分拣**，勿与本功能无关文件混绑。

### 4.8 测试
Adapter/session 含撞车、spawn argv、跨 instance；CLI 文案。**缺 GUI E2E / 手测证据**（F1）。

---

## 5. 发现项

### 🔴 Critical

（无）

### 🟠 High

（无）

### 🟡 Medium

| ID | 发现 | 证据 | 建议 |
|----|------|------|------|
| F1 | 无 GUI 手测：关 YOLO → 工具调用 → 批准卡 → 继续 | Spec 成功标准 1–3；预检 PENDING | 合并前用户手测；回归注意 auth/provider |
| F2 | 删除同事不 stop Hermes（及 Cursor）ACP | Spec 边界「删除同事→停 ACP」；`App.tsx` removeColleague 未调 `getHermesAcpSessionManager().stop` | follow-up：卸同事 IPC 调 stop；可 Cursor/Hermes 一并修 |
| F3 | Hermes ACP auth `methodId` 默认 `openrouter`，未接 config provider | `hermes_acp_session.mjs` 默认 `getAuthMethodId`；`main.mjs` 创建 manager 未传入 | follow-up：从实例/executors Hermes provider 映射注入；或文档写明仅 OpenRouter 默认可预期 |

### 🟢 Low

| ID | 发现 | 建议 |
|----|------|------|
| L1 | `agent-turn` Cursor/Hermes ACP 持久化块重复 | 两家都稳后再抽 |
| L2 | Hermes `permissionMode`/`set_mode` API 镜像 Cursor，GUI 路径未传 mode（恒 agent） | 可保留；勿误接 Cursor permission_mode 到 Hermes |

---

## 6. Spec 追溯

| Spec / Plan 项 | Diff | 状态 |
|----------------|------|------|
| `yolo=false` → GUI ACP | `main.mjs` hermes 分流 | done |
| `yolo=true` one-shot + stop ACP | stop + `runCli agent turn` | done |
| CLI 拒跑文案 | `_hermes_cli_yolo_off_error` | done |
| `--accept-hooks` | `HERMES_ACP_SPAWN_ARGS` + session spawn | done |
| 平行模块 + 撞车防护 | hermes_acp_* + tests | done |
| 卡四键 / 本会话不落盘 | 复用 IPC + adapter session→allow_always | done |
| 失败不静默 YOLO | catch return | done |
| 删同事停进程 | 未接线 | **partial（F2）** |
| GUI 手测 | — | **pending（F1）** |

非目标（Codex、永久 always、抽基类）未被破坏。

---

## 7. 修改建议

1. **提交前**：GUI 手测 F1（建议）。  
2. **可合并后 follow-up**：F2 stop-on-remove；F3 auth methodId 接线。  
3. **Commit 范围**：本功能相关文件 + 本 review；`docs/solutions` 若属先前 Cursor compound，可同交或分 commit；勿漏 `hermes_acp_*` 新文件。

---

## 8. 修复记录

| 轮次 | 说明 | 验证 |
|------|------|------|
| — | 本轮无 Critical/High，未派 doer 热修 | — |

---

## 9. 最终结论

- [x] **PASSED / APPROVED** — 允许提交（Medium F1–F3 不阻塞；F1 强烈建议手测）
- [ ] **FAILED** — 提交前必须修复

**Gate：** 自动化绿；安全 CLEAN；无未解决 Critical/High；Spec 主路径可追溯。

**Commit 策略：** 用户历史规则为「未明确要求不 commit」。本 review **批准提交**，但 **暂不自动 commit**——需要时请说「提交」或「commit」。

**下一步建议：** 手测 F1 → 按需 commit/push → 可选 `/anvil:compound`（Hermes optionId 下划线 / auth 默认等差异）→ follow-up F2/F3。
