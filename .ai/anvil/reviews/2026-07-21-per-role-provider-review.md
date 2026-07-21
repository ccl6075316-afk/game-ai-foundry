# 评审报告：`2026-07-21-per-role-provider`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `main`） |
| Author | `/anvil:code` doers + lead 补线 |
| Review Date | 2026-07-21 |
| Status | `APPROVED`（F1/F2 已在评审中修复；F3–F5 非阻塞） |
| Spec | `docs/anvil/brainstorms/2026-07-21-per-role-provider.md` |
| Plan | `docs/anvil/plans/2026-07-21-per-role-provider-plan.md`（executed） |

**Loaded standards:** Anvil review skill；无 `docs/solutions` / critical-patterns；frontend/backend domain 规则未装载（插件域规则空/未用）。

**变更规模：** Large（~1586+/227-，跨 cli + gui + docs + config 契约）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 仓库无统一 lint 门禁于此范围 |
| 类型检查 | `cd gui && npx tsc --noEmit` | PASS | |
| 单元测试 | `python -m unittest test_agent_auth_resolve test_pi_runtime test_executor_setup test_agent_turn test_host_chat -q` | PASS | 84 tests OK |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| docs/solutions | 不存在 | 无历史 lens |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec → Plan → Diff 可追溯 | PASS（T1–T7 + brief instance_id 补线） |
| 非目标未膨胀（生图进角色页等） | PASS |
| 验证证据 | PASS（CLI 单测 + tsc）；GUI 手测仍待用户 |
| 并行状态源 | PASS（无第二套 task tracker） |
| Resume point | PASS（plan Status=executed） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 未发现 | — | OK |
| 注入风险 | Codex/Hermes 同步写本地配置，属产品设计 | Low | 接受（用户显式保存/同步） |
| XSS | 设置/快选为受控 select/input | — | OK |
| 依赖 CVE | 未扫 npm audit（本变更未改 lock） | — | N/A |
| 日志敏感数据 | resolve/status 用 `has_api_key`；Key 走 env | — | OK |
| 密钥落盘 | `~/.codex/.env` 写入 Key | Medium | 与 Hermes 同步同级；须保持用户显式触发 |

**安全结论：** ISSUES FOUND（可接受的同步落盘风险；无硬编码密钥）

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 设置页打开期间聊天快选改 config，保存设置会不会盖回去？ | 未处理：`toPatch` 序列化**打开时**的 `form.agentInstances` 全量 merge | **FAIL** | High |
| Simplicity First | `agent_auth_resolve` 是否过度？ | 纯函数集中解析，值得存在 | PASS | — |
| Surgical Changes | 每行能否追溯 Spec？ | 大体可追溯；`toPatch` 把 brief/it 工种 provider 强制写成 `activeTextProvider` 超出「仅实例覆盖」叙述 | FAIL 边缘 | Medium |
| Goal-Driven Execution | 测试是否证明实例鉴权？ | CLI 有 instance>role>host 与 agent_turn 测；GUI 快选/设置竞态无测 | PARTIAL | Medium |

**Karpathy Score:** 2/4

---

## 4. 对抗式维度评审

### 4.1 设计

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `cli/agent_auth_resolve.py` | 新模块是否必要？ | 是，避免 Pi/agent_turn/Codex 各写一套链 | — |
| `gui/.../agentInstances.ts` | 与 CLI 双端模型？ | 可接受（GUI 序列化 + CLI 解析）；需保持字段对齐 | Low |

**维度结论：** PASS（主体）

### 4.2 功能

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| `SettingsPanel.tsx` `toPatch` → `instances: serializeAgentInstances(form.agentInstances)` | 设置保存是否覆盖快选？ | **会。** deepMerge 对同 key 用 patch 覆盖；form 若仍是旧 provider，会盖掉快选刚写入的值 | **High** |
| 同上 `brief`/`it` provider: `form.activeTextProvider` | 每次保存设置是否改写工种默认？ | **会**强制为生文当前选中，可能不符合「工种默认独立」预期 | Medium |
| `PiProviderQuickSwitch` 模型 debounce 400ms | 切换同事前未 flush？ | 有清理 timer，但未在 unmount 时强制 flush 最后一次 model | Low |
| `configure_codex_api` `wire_api = "responses"` | OpenRouter/DeepSeek 是否都该用 responses？ | 未用真实 Codex 冒烟证明；可能部分 provider 需 `chat` | Medium |
| Brief `--instance-id` | 策划快选是否打到 Pi？ | lead 已补 `brief_cmds`/`host_chat`/`main.mjs` | 已缓解 |

**维度结论：** FINDINGS（含 High）

### 4.3 复杂度

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| executor_setup Codex TOML 手写 | 能否更简单？ | Spike 最小路径可接受 | — |

**维度结论：** PASS

### 4.4 Naming

| 位置 | 提问 | 判断 |
|------|------|------|
| `resolve_agent_auth` / `use_third_party` / `agents.instances` | 是否清晰？ | PASS |

### 4.5 Comments

| 位置 | 提问 | 判断 |
|------|------|------|
| Codex docstring 版本假设 | 有 | PASS |

### 4.6 Style

| 位置 | 提问 | 判断 |
|------|------|------|
| 与现有 Settings/CLI 风格 | 一致 | PASS |

### 4.7 Context

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| 双入口改同一 config | 系统更易用但引入竞态 | 健康度：功能正，**竞态伤可信度** | High（同上） |

### 4.8 Tests

| 位置 | 提问 | 判断 | 严重级别 |
|------|------|------|----------|
| CLI resolve/turn/sync | 行为测充分 | PASS | — |
| GUI agentInstances / 快选 | 无单测 | 技术债 | Medium |
| Codex 真实写入 | 仅 mock | 可接受 + 手测门禁 | Low |

**维度结论：** FINDINGS

---

## 5. 发现汇总

| ID | 严重级别 | 维度 | 摘要 | 建议 |
|----|----------|------|------|------|
| F1 | **High** → Fixed | 功能/竞态 | 设置保存覆盖快选 | 已用 dirty + mergeDirtyInstances 修复 |
| F2 | Medium → Fixed | 功能 | brief/it 强制 activeTextProvider | 已停止写入工种 provider |
| F3 | Medium | Codex | `wire_api=responses` 一刀切 | 保留，建议手测 |
| F4 | Medium | 测试 | GUI 无竞态单测 | 技术债 |
| F5 | Low | UX | model debounce 未 flush | 可后续 |
| F6 | Low | 安全 | Codex `.env` 落 Key | 接受 |

---

## 6. 裁决

**Status: `APPROVED`**

初审曾因 **F1** BLOCKED。已修复：

- F1：`dirtyInstanceIds` + 保存前 `getConfig` + `mergeDirtyInstances`；无 dirty 时**不写** `agents.instances`，避免盖掉快选  
- F2：`toPatch` 不再把 `brief`/`it` 的 provider 强制写成 `activeTextProvider`  

残留非阻塞：F3（Codex `wire_api`）、F4（GUI 单测债）、F5（model debounce flush）。

---

## 7. 放行条件

- [x] F1 已修 + tsc PASS  
- [x] F2 已修  
- [ ] 用户手测附录步骤（建议合并前做）  
- [ ] F3 真实 Codex 第三方冒烟（可选）

---

## 附录：建议手测

1. Provider 页配置 OpenRouter + DeepSeek  
2. IT 顶栏切到 DeepSeek，发一句  
3. 打开设置→角色（不要改该 IT），点保存  
4. IT 顶栏 / config 仍为 DeepSeek  
5. 程序员 Codex + 用第三方 → 保存 → 检查 `~/.codex`（关注 F3）
