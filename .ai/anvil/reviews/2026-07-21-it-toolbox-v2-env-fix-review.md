# 评审报告：`2026-07-21-it-toolbox-v2-env-fix`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `main`） |
| Author | `/anvil:code` 实现 + review 中 High 修复 |
| Review Date | 2026-07-21 |
| Status | `APPROVED`（F1 评审中已修；F2–F4 非阻塞） |
| Spec | `docs/anvil/brainstorms/2026-07-21-it-toolbox-v2-env-fix.md` |
| Plan | `docs/anvil/plans/2026-07-21-it-toolbox-v2-env-fix-plan.md`（本地 / gitignored） |

**Loaded standards:** Anvil review skill；历史 lens 来自 settings/per-role reviews + IT v1/v2 spec（`docs/solutions` 为空）。无 frontend/backend domain 规则适用。

**变更规模：** Medium（~276+/31-；跨 cli 白名单/CLI/skill/docs）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 无统一 lint 门禁 |
| 类型检查 | N/A | N/A | 纯 Python CLI |
| 单元测试 | `python -m unittest test_provider_upsert test_agents_executors_upsert test_pi_foundry_tools -q` | PASS | 20 tests OK（含 F1 后） |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| IT v1/v2 Spec | 突变须 `--i-confirm`；无 `pipeline run`；brief 不写 Key | 已核对；F1 补硬门闩 |
| settings-agent-hire review | executors 字段与解析链一致 | upsert 字段对齐 provider/model/use_third_party |
| per-role / settings | Key 不进 resolve 输出；sync 副作用须知情 | agents upsert 无 Key；executor step 仍靠 skill 复述 |
| 白名单沙箱 lens | `;|&` 与 strip/keep 分流 | 保留；install 测覆盖 strip |

**使用规则：** 历史 learning 仅作 lens；下列 finding 均引用当前 diff。

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec → Plan → Diff 可追溯 | PASS（白名单增量、agents upsert、skill、确认门闩） |
| 非目标未膨胀 | PASS（无 `pipeline run`、无改 games/、无 GUI 确认按钮） |
| 验证证据 | PASS（CLI 单测）；GUI IT 对话手测仍待用户 |
| 并行状态源 | PASS |
| Resume point | PASS（Spec Status=implemented；下一步 commit/push 由用户触发） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 未发现 | — | OK |
| 注入风险 | 白名单拒 `;|&`/`$(`；无通用 shell | — | OK |
| XSS | 无 GUI 面 | — | N/A |
| 依赖 CVE | 未改 lock | — | N/A |
| 日志敏感数据 | upsert 结果无完整 Key；`--api-key` 仍可进 argv/进程列表（同 v1） | Low | 接受 |
| 越权 | brief 与 IT 曾共用允许前缀，v2 扩大 install/heal/reset 后风险上升 | High | **Fixed (F1)** |

**安全结论：** CLEAN（F1 修复后）

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答 | 结论 | 严重级别 |
|------|------------|----------|------|----------|
| Think Before Coding | brief 是否只靠 prompt 禁写？突变门闩是否双层？ | 初版仅 skill + 共享白名单；CLI upsert 有 `--i-confirm`，install 仅 Pi 层 | **FAIL→Fixed (F1)** | High |
| Simplicity First | strip/keep 两套集合是否多余？ | 旧 Click 无 `--i-confirm` 时必须 strip，否则 GUI/CLI 炸 | PASS | — |
| Surgical Changes | 每行可追溯 Spec？ | 可；profile 硬门闩补齐 v1 已写「仅 IT」 | PASS | — |
| Goal-Driven Execution | 测是否证明？ | 有/无 confirm、strip、brief 拒 IT、pipeline run 拒 | PASS | — |

**Karpathy Score:** 4/4（F1 修复后）

---

## 4. 对抗式维度评审

### 4.1 设计

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `pi_foundry_tools` `_MUTATE_*` / `_KEEP_*` | 为何不给 install 真正加 Click flag？ | Spec 允许包装/剥离；避免改动 GUI 直调路径 | PASS | — |
| `agents_executors_upsert` | 为何专用 CLI 非通用 config set？ | Spec 禁止旁路 secrets | PASS | — |

**维度结论：** PASS

---

### 4.2 功能

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `is_allowed_argv` + `run_tool_round` | brief 能否带 `--i-confirm` 跑 install？ | **初版能** → 加 `profile=brief` + `_BRIEF_ALLOWED_PREFIXES` | Fixed (F1) | High |
| strip 路径 | install 子进程是否仍带未知 `--i-confirm`？ | 单测 `test_install_strips_i_confirm_before_cli` | PASS | — |
| `upsert_agent_executor` | 无字段变更仍写盘？ | 会 save；无害 | Low (F2) | Low |
| heal/reset | 确认文案是否强制 task-id？ | skill 要求；白名单不解析 task-id | Medium (F3) | Medium |

**已检查关键边界：**
- [x] 空/非法 executor/provider
- [x] 无 `--i-confirm`
- [x] brief profile 拒 IT
- [x] `pipeline run` 仍拒
- [ ] GUI 双写 config 竞态（既有限制，非本 diff 引入）
- [x] install 超时 900s

**维度结论：** PASS（F1 已修；F2/F3 非阻塞）

---

### 4.3 复杂度

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| 三套 frozenset | 可内联？ | 职责分离清晰；内联易混 keep/strip | PASS | — |

**过度设计检查：** 无投机抽象；无未使用 hooks。

**维度结论：** PASS

---

### 4.4 命名

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `setup agents executors upsert` | 是否与 Spec 命名一致？ | Spec 钉死该路径 | PASS | — |
| `--i-confirm` | 语义是否清晰？ | 与 v1 一致 | PASS | — |

**维度结论：** PASS

---

### 4.5 注释

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `_MUTATE_PREFIXES` 注释 | 解释 WHY strip？ | 是 | PASS | — |

**维度结论：** PASS

---

### 4.6 风格与一致性

| 行号 | 问题 | 类型 | 状态 |
|------|------|------|------|
| — | 对齐 `provider_upsert` / `setup_cmds` 模式 | — | OK |

**维度结论：** PASS

---

### 4.7 上下文

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| skill/TOOLS/AGENT-ROUTING | 与白名单是否同步？ | 已更新；无 `pipeline run` | PASS | — |
| 相对 v1 | heal 现须 confirm | Spec 要求；破坏旧「随意 heal」是正确收紧 | PASS | — |

**维度结论：** PASS

---

### 4.8 测试

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| 单测 | 故意去掉 confirm / brief 漏门是否失败？ | 会 | PASS | — |
| 集成 | IT 对话全链路？ | 无；同 v1 | Medium (F4) | Medium |

**维度结论：** PASS（CLI 层充分；E2E 债记 F4）

---

## 5. 发现项摘要

### Critical（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| — | — | — | 无 | — |

### High（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| F1 | 功能/安全 | `pi_foundry_tools.is_allowed_argv` / `pi_runtime.run_tool_round` | brief 与 IT 共用白名单；v2 扩大 install/heal/reset 后，策划侧仅靠 prompt 即可带 `--i-confirm` 执行突变 | **已修**：`profile=brief` 仅允许 brief status/validate/export；单测 `test_brief_profile_rejects_it_mutate` |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| F3 | 功能 | skill + whitelist | reset/heal 的 task-id 正确性依赖模型复述，白名单不校验 | 可后续校验 `--task-id` 形态；本轮接受 |
| F4 | 测试 | — | 无 IT GUI/Pi 集成测 | 手测：确认后 install / upsert executors；brief 无法 doctor |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| F2 | 功能 | `agents_executors_upsert.py` | 无字段变更仍 `_save_config` | 可选 early-return |
| — | 安全 | provider upsert argv | Key 进进程 argv（同 v1） | 保持；优先 env 注入可后续 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x]（F1 已修） |
| Spec 可追溯 / 非目标未破 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 所有阻塞门禁通过；建议用户确认后 commit，再视情况 `/anvil:compound`

### 评审备注

- 按用户提交惯例：**未自动 commit**；批准后的 diff 仍在工作区，需显式「提交/push」才落库。
- F1 修复文件：`cli/pi_foundry_tools.py`、`cli/pi_runtime.py`、`cli/test_pi_foundry_tools.py`。
- 手测清单：IT 确认后 `setup install ffmpeg`；`setup agents executors upsert`；无 confirm 被拒；策划会话发 install 应白名单失败。
