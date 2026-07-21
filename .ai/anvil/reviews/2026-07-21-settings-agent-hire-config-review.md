# 评审报告：`2026-07-21-settings-agent-hire-config`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `main`） |
| Author | `/anvil:code` doers + lead 评审修复 |
| Review Date | 2026-07-21 |
| Status | `APPROVED`（F1/F2 评审中已修；F3–F5 非阻塞） |
| Spec | `docs/anvil/brainstorms/2026-07-21-settings-agent-hire-config.md` |
| Plan | `docs/anvil/plans/2026-07-21-settings-agent-hire-config-plan.md`（executed） |

**Loaded standards:** Anvil review skill；无 `docs/solutions`；frontend/backend domain 规则未装载（空/未用）。

**变更规模：** Large（~551+/720- 计入删除快选；跨 cli + gui + docs + config 契约）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 无统一 lint 门禁 |
| 类型检查 | `cd gui && npx tsc --noEmit` | PASS | 含评审修复后 |
| 单元测试 | `python -m unittest test_agent_auth_resolve test_executor_setup -q` | PASS | 40 tests OK |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| docs/solutions | 不存在 | 无历史 lens |
| 上轮 per-role-provider | 设置勿盖 instances；debounce flush | 设置已不写 instances；ConfigBar 保留 flush |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec → Plan → Diff 可追溯 | PASS（T1–T6 + Codex executors 同步补线） |
| 非目标未膨胀 | PASS（无 Cursor 第三方、无「存为默认」） |
| 验证证据 | PASS（CLI 单测 + tsc）；GUI 手测仍待用户 |
| 并行状态源 | PASS |
| Resume point | PASS（plan Status=executed） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 未发现 | — | OK |
| 注入风险 | Codex sync 写本地配置，用户显式触发 | Low | 接受 |
| XSS | 受控 select/input | — | OK |
| 依赖 CVE | 未改 lock | — | N/A |
| 日志敏感数据 | resolve 仍无 Key 原文 | — | OK |
| 密钥落盘 | `~/.codex/.env` | Medium | 与既有 Hermes 同级；显式保存/同步 |

**安全结论：** ISSUES FOUND（可接受的同步落盘；无硬编码密钥）

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答 | 结论 | 严重级别 |
|------|------------|----------|------|----------|
| Think Before Coding | 无 instances 时 GUI 是否沿用 executors？ | 初版 `resolveInstanceRecord` 忽略 executors，与 CLI 不一致 | **FAIL→Fixed (F1)** | High |
| Simplicity First | Agent 预设 + instances 双层是否过度？ | Spec 明确要求；设置更简单 | PASS | — |
| Surgical Changes | 每行可追溯 Spec？ | 大体可；雇人失败静默偏弱 | PARTIAL | Medium |
| Goal-Driven Execution | 测是否证明？ | CLI 层充分；GUI hire/validate 无单测 | PARTIAL | Medium |

**Karpathy Score:** 3/4（F1 修复后）

---

## 4. 对抗式维度评审

### 4.1 设计

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `agents.executors` | 是否必要？ | 是，对应「工具预设≠角色」 | — |
| Settings 去角色 | 是否更健康？ | 是 | — |

**维度结论：** PASS

### 4.2 功能

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `agentInstances.resolveInstanceRecord` | 无 instance 时是否对齐 CLI？ | 曾忽略 executors | **High→Fixed** |
| `ColleagueConfigBar.applyExecutorPreset` | `pi→codex` 映射？ | 误映射，已改为 `pi` | **Medium→Fixed** |
| `syncCodexApi` / hire confirm | 失败是否对用户可见？ | sync 已改 setError；hire 仍 catch 空 | Medium（残留 F3） |
| 缺配置 hint | 「打开设置」误导 | 已改为不指向角色页 | Low→Fixed |

**维度结论：** FINDINGS（阻塞项已修）

### 4.3 复杂度

| 位置 | 提问 | 判断 |
|------|------|------|
| hireColleague + ConfigBar + executors | 可接受拆分 | PASS |

### 4.4 Naming

| 位置 | 判断 |
|------|------|
| Agent vs 角色 / executors vs instances | PASS |

### 4.5 Comments

| 位置 | 判断 |
|------|------|
| resolve / merge docstring | PASS |

### 4.6 Style

| 位置 | 判断 |
|------|------|
| 与现有 settings 风格 | PASS |

### 4.7 Context

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| 删除角色页 | 系统更易懂？ | 改善 | — |
| 默认花名册同事 | 未走过雇人弹窗 | 靠 ConfigBar + executors 预填（F1 后） | Low |

### 4.8 Tests

| 位置 | 判断 | 严重级别 |
|------|------|----------|
| CLI resolve / codex sync | PASS | — |
| GUI hireColleague.validate / resolveInstanceRecord+executors | 无单测 | Medium（F4） |

**维度结论：** FINDINGS（非阻塞）

---

## 5. 发现汇总

| ID | 严重级别 | 维度 | 摘要 | 建议 |
|----|----------|------|------|------|
| F1 | **High** → Fixed | 功能 | GUI 无 instance 时未读 `agents.executors` | 已修：`resolveInstanceRecord(..., executorsMap)` + ConfigBar 传入 |
| F2 | Medium → Fixed | 功能 | 切换执行器时 `pi` 误映射为 `codex` preset | 已改为 `pi` |
| F3 | Medium | UX | 雇人 `saveConfig` 失败静默 | 可后续 toast；不阻塞 |
| F4 | Medium | 测试 | GUI 无 hire/resolve 单测 | 技术债 |
| F5 | Low | 安全 | Codex `.env` 落 Key | 接受（显式触发） |

---

## 6. 裁决

**Status: `APPROVED`**

初审因 **F1** 可构成用户可见「界面一套、回合另一套」而倾向 BLOCK。已在评审中修复并复跑 `tsc` + 40 单测。

残留非阻塞：F3（雇人保存失败提示）、F4（GUI 单测债）、F5（已知同步落盘）。

---

## 7. 放行条件

- [x] F1/F2 已修 + tsc PASS + unittest PASS  
- [ ] 用户手测附录（建议提交前）  
- [ ] 用户明确要求后 git commit（当前 pause：未自动提交）

---

## 附录：建议手测

1. Agent 页 Pi=DeepSeek 保存 → 不雇人、直接用默认策划对话配置条 → 应显示 DeepSeek  
2. 雇策划选 Provider → 对话改模型 → Agent 页 Pi 预设不变  
3. 雇程序员 Codex+第三方 → 同步成功或可见失败信息  
4. 设置无「角色」Tab；有 Provider | Agent | 本机  
