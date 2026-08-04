# 评审报告：`2026-08-04-it-executor-switch`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | `848fbea..88b42fd`（已合入 `main`） |
| Author | chenzilong |
| Review Date | 2026-08-04 |
| Status | `APPROVED（整体复审）` |

**范围：** 修复 IT 外置执行器 ACP prompt 接线，并从 IT 能力矩阵移除 Hermes；策划继续锁 Pi。  
**Loaded standards：** `AGENTS.md`、Anvil review、`rules/domains/frontend.md`（内容为 TBD，无附加规则）、`docs/solutions/patterns/critical-patterns.md`。  
**事实源：** 用户确认 + 本地 `docs/anvil/plans/2026-08-04-it-executor-switch.md`（该路径被 `.gitignore` 的 `plans/` 规则忽略）。

---

## 最终整体复审（2026-08-04 20:39）

### 修复闭环

- IT 实例配置优先于 stale roster；无实例记录的新雇人仍可使用 roster override。
- 非 ACP CLI 路径只传主进程解析后的 `effectiveExecutor`。
- CLI 最终 executor 与鉴权 preset 一致；跨 executor 临时切换时，不再继承旧实例绑定的 provider/model。
- IT 显式选择 Hermes 会报错；仅旧磁盘配置兼容回退 Pi。
- `agent prompt` 已收窄为 IT 专用，不再形成不完整的 product_host 公共契约。
- ACP prompt、非 ACP turn 参数、执行器优先级、失败/空 prompt、并发保存门闩均有自动化覆盖。
- 配置保存采用活动计数；全部并发保存结束前，App 同步 ref + state 阻止发起新回合。

### 最终证据

| 检查项 | 结果 |
|--------|------|
| CLI 路由/实例/鉴权 | PASS（65） |
| Electron | PASS（84） |
| GUI TypeScript 单测 | PASS（35） |
| GUI 构建 | PASS（81 modules） |
| Diff hygiene | PASS |
| GUI typecheck | 2 个既有基线错误；本次改动文件无新增诊断 |

### 门禁

- [x] 无未解决 Critical / High / Medium
- [x] IT 实际 executor、prompt、auth preset 一致
- [x] Hermes 能力矩阵和旧配置兼容一致
- [x] 保存竞态有门闩与并发测试
- [x] 安全扫描干净

**Karpathy Score：4/4**

**结论：APPROVE。** 当前整体改动可提交；typecheck 两个既有基线错误独立处理。

---

## 整体复审（历史，修复前，2026-08-04 20:28）

### 自动化证据

- CLI 路由/实例/鉴权：PASS（63）
- Electron：PASS（82）
- GUI TypeScript 单测：PASS（34）
- GUI 构建：PASS
- Diff hygiene：PASS
- Typecheck：2 个既有基线错误

### 新发现

#### H1 — 顶栏切换执行器后，旧 roster executor 覆盖实例配置（阻塞）

- `ColleagueConfigBar` 保存时只更新 `agents.instances` 与组件本地 state，没有更新 `chatStore.roster`。
- `App.tsx:2005-2012` 每次发送仍把 `colleague.executor` 作为显式 override 传入 IPC。
- `main.mjs:1226-1235` 又优先采用该 override，而不是刚保存的实例配置。

默认 IT roster 为 Pi；用户在顶栏切到 Codex/Cursor 后，实际回合仍可能继续跑 Pi。新雇佣时 roster 与配置一致，但后续切换会复现。

**必须动作：** 发送回合时不要用 roster executor 覆盖实例配置，或保存执行器时同步更新 roster；增加 App → IPC → executor resolve 的回归测试。

#### H2 — CLI executor override 与鉴权 preset 脱节（阻塞）

`run_turn` 先按磁盘实例调用 `resolve_agent_auth`，随后才用 `--executor` override 计算 `chosen`。例如配置 IT=Pi、命令传 `--executor codex` 时，可得到 `chosen=codex`、`resolved_auth.executor=pi`，并把 Pi preset 的 model/provider 交给 Codex。

**必须动作：** 鉴权解析必须使用最终 chosen executor（或接收显式 override）；测试覆盖 Pi→Codex、Codex→Cursor 等 override，断言 executor/provider/model 来源一致。

#### M1 — 显式选择 IT Hermes 被静默改跑 Pi

CLI Click 仍接受 `agent turn/prompt --role it --executor hermes`，运行时静默归一成 Pi；但实例 upsert 明确拒绝 Hermes。旧配置兼容回退和用户显式输入应区分。

**建议动作：** 旧磁盘配置可回退 Pi，但显式 override Hermes 应报清晰错误。

#### M2 — 通用 `agent prompt` 对 product_host 不完整

命令允许所有 `ROLE_KINDS`，却未暴露 `--roster-json` / `--target-instance-id`，因此 product_host prompt 与 `agent turn` 不一致。当前 Electron 只为 IT 调用，暂不影响本轮 GUI，但公共 CLI 契约会误导后续调用者。

**建议动作：** 要么把命令约束为 IT 专用，要么补齐 turn 的 roster/target 参数。

#### M3 — 真实 IPC 优先级缺少测试

helper 测试覆盖了 prompt 构建和失败路径，但没有覆盖 App 传参、主进程 override 优先级和实际 ACP 分支，因此未发现 H1。

### 整体门禁

- [ ] 顶栏切换后实际 executor 与实例配置一致
- [ ] executor override 与 auth preset 一致
- [x] ACP brief/progress prompt 一致
- [x] IT UI/配置不再暴露 Hermes
- [x] 旧 Hermes 配置的 auth 回退 Pi
- [ ] 无未解决 High

**Karpathy Score：2/4**

**结论：BLOCK。** 自动化测试均通过，但未覆盖到上述跨层状态/鉴权不一致；暂不建议 commit。

---

## 最终复审（阻塞项修复后）

### 修复确认

- **ACP 完整上下文**：`buildAgentPromptArgs` 现同时转发 `briefArg` 与 `progressArg`；Electron 使用与普通 CLI 路径相同的 `cliArgForRel` 规则。
- **旧 Hermes 鉴权回退**：`agent_auth_resolve._resolve_executor` 对 IT 的 Hermes 配置归一为 Pi，随后选择 Pi preset；route/auth executor 与 provider/model 来源一致。
- **Electron 桥接测试**：新增共享 prompt 成功、命令失败、`ok:false`/空 prompt 失败覆盖；无裸消息静默回退。
- **IT Hermes 能力矩阵**：GUI、CLI upsert、运行时解析和文档均只保留 Pi / Codex / Cursor。

### 最终自动化证据

| 检查项 | 结果 |
|--------|------|
| CLI 路由/实例/鉴权测试 | PASS（63） |
| Electron 全量测试 | PASS（82） |
| GUI TypeScript 单测 | PASS（34） |
| GUI 构建 | PASS |
| Diff hygiene | PASS |
| GUI 类型检查 | 仍有 2 个既有基线错误；本次改动文件无新增诊断 |

### 最终门禁

- [x] H1：ACP 与 CLI 使用相同 brief/progress 角色上下文
- [x] H2：IT 不再暴露 Hermes，旧配置安全回退 Pi
- [x] M1：共享 ACP prompt 桥接成功/失败路径有自动化覆盖
- [x] 安全扫描干净
- [x] 无未解决 Critical / High

**Karpathy Score：4/4**

**结论：APPROVE。** 当前改动可提交；全量 typecheck 的两个既有基线错误建议独立修复。

---

## 第一次复审（历史，修复前）

### 自动化预检

| 检查项 | 命令 | 结果 |
|--------|------|------|
| Diff hygiene | `git diff --check` | PASS |
| CLI 单元测试 | `python -m unittest test_agent_turn test_agents_instances_upsert test_agent_auth_resolve -q` | PASS（62） |
| Electron 单元测试 | `node --test electron/*.test.mjs` | PASS（80） |
| GUI TypeScript 单测 | `npx --yes tsx --test src/**/*.test.ts` | PASS（34） |
| GUI 构建 | `npm run build` | PASS |
| GUI 类型检查 | `npm run typecheck` | FAIL（2 个既有基线错误，均不在本次改动文件） |

### 安全扫描

无新增密钥输出、shell 拼接、HTML 注入或依赖变更。共享 prompt 仍通过 `spawn(..., shell: false)` 参数化传递。结论：**CLEAN**。

### 复审发现

#### H1 — ACP prompt 未转发当前项目 progress（阻塞）

- `gui/src/App.tsx:2005-2012` 明确把 `progressRel` 传给 `agentTurn`。
- 普通 CLI 路径会在 `gui/electron/main.mjs:2990+` 把 `opts.progress` 转成 `--progress`。
- 新增 ACP prompt 桥只在 `gui/electron/main.mjs:2661-2680` / `gui/electron/agent_prompt.mjs:20-38` 转发 brief，没有 progress。

因此 IT 使用默认 Codex app-server 或 Cursor ACP 时，`prepare_turn_prompt` 会回退 `_find_default_progress()`，可能注入另一个项目的 progress。实际测试中未显式传 progress 时已读到 `plans/progress_forest-platformer.json`，与当前 fishing 项目不一致。H1 的“与 CLI 相同角色 prompt”仍未完全闭合。

**必须动作：** 给 `buildAgentPromptArgs` 增加 `progressArg`，Electron 使用与普通 CLI 路径一致的 `cliArgForRel(opts.progress)`；测试同时断言 brief/progress 均被转发。

#### H2 — 旧 Hermes 配置仅路由回 Pi，鉴权层仍读取 Hermes preset（阻塞）

- `cli/agent_turn.py:153-166` 把 IT 的 Hermes executor 归一为 Pi。
- 但 `run_turn` 在 `cli/agent_turn.py:1046-1048` 先调用 `resolve_agent_auth`，后者仍按磁盘里的 `executor=hermes` 选择 Hermes preset。
- 复现实测：`route=pi`，同时 `auth_executor=hermes provider=deepseek model=hermes-model`。

这会让旧 IT Hermes 实例表面回退 Pi，却携带 Hermes 的 provider/model/auth 运行，不能称为安全回退。

**必须动作：** 在共享鉴权解析层对 IT Hermes 做同一归一化，或显式迁移/拒绝旧配置；增加测试断言 route 与 auth executor/provider preset 一致。

#### M1 — Electron 接线测试仍只验证参数构造（非阻塞）

`gui/electron/agent_prompt.test.mjs` 只覆盖 `buildAgentPromptArgs` 和 executor 归一化，没有证明 `main.mjs` 在 Codex/Cursor ACP 分支把 CLI 返回的完整 prompt 交给 session manager，也未覆盖 prompt 命令失败/空输出。

**建议动作：** 抽出可注入 `runCli` 的小型桥接函数，覆盖成功、非零退出、`ok:false`、空 prompt 四种情况。

### Karpathy 复审

| 原则 | 结论 | 原因 |
|------|------|------|
| Think Before Coding | FAIL | 忽略了已有 `progress` 上下文和 auth 层 executor 解析 |
| Simplicity First | PASS | 新增桥接规模合理 |
| Surgical Changes | PASS | 改动基本限定在 prompt 路由和 IT executor 能力 |
| Goal-Driven Execution | FAIL | 测试未证明完整 ACP 上下文与旧配置端到端回退 |

**Karpathy Score：2/4**

### 复审门禁

- [x] 原 H2“IT UI 暴露 Hermes”已解决
- [ ] 原 H1“ACP 与 CLI 使用相同完整 prompt”完全解决
- [ ] 旧 Hermes 配置端到端安全回退
- [x] 安全扫描干净
- [ ] 无未解决 High

**结论：BLOCK。** 暂不建议 commit / 发布；先修复 progress 转发与 auth 归一化，再复审。

---

## 首次评审记录（历史）

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Diff hygiene | `git diff --check 848fbea..88b42fd` | PASS | 无空白错误 |
| CLI 单元测试 | `python -m unittest test_agent_turn test_agents_instances_upsert test_agent_auth_resolve -q` | PASS（60） | 路由、实例 upsert、鉴权 |
| GUI 构建 | `npm run build` | PASS | Vite 80 modules |
| GUI 现有单测 | `npx tsx --test …` | PASS（29） | 未覆盖本次 IT 执行器逻辑 |
| GUI 类型检查 | `npm run typecheck` | FAIL（2） | 两处均在未改文件：`agentReply.test.ts`、`ProviderSettingsView.tsx`，属既有基线问题 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| `critical-patterns.md` | ACP 路径与普通 CLI 路径必须分开审查，不能假设共用 prompt/权限语义 | 命中 H1/H2：GUI ACP 路径绕过新增 prompt |
| `modules/cli.md` | CLI 风格索引 | 无直接适用 finding |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | CLEAN |
| 注入风险 | 未新增命令拼接；Codex/Hermes/Cursor 仍走既有参数化调用 | — | CLEAN |
| XSS 风险 | 未新增 HTML 注入 | — | CLEAN |
| 依赖 CVE | 未改依赖 | — | N/A |
| 日志敏感数据 | 未新增 Key 输出 | — | CLEAN |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 是否审查了 GUI ACP 与 CLI 两条执行路径？ | 计划与测试只覆盖 `agent_turn.build_prompt` | FAIL | High |
| Simplicity First | 是否新增了不必要抽象？ | 主要复用既有实例/执行器结构 | PASS | — |
| Surgical Changes | 每行是否可追溯？ | CLI、GUI、文档基本可追溯；无大范围重构 | PASS | — |
| Goal-Driven Execution | 测试是否证明 GUI 默认 Codex 真拿到 IT 规范？ | 没有；现有测试仅直接调用 `build_prompt` | FAIL | High |

**Karpathy Score:** 2/4

---

## 4. 对抗式维度评审

### 4.1 设计：它是否应该存在？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/agent_turn.py:345-354` / `gui/electron/main.mjs:2838-2870` | IT prompt 为什么只在 CLI 路径构建，GUI app-server 却直接收原始消息？ | 未说明；Electron 文件未进入本次 diff | 架构遗漏，默认路径没有共享 prompt 构建 | High |

**维度结论：** FINDINGS

### 4.2 功能：作者遗漏了什么？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `gui/electron/main.mjs:2838-2870` | IT 选默认 `workspace-write` Codex 后是否收到 `diagnose.md` 和“禁止 FOUNDRY_TOOL”约束？ | app-server 收到的是原始 `message` | 否；核心效果未落到默认 GUI 路径 | High |
| `HireColleagueModal.tsx:65-69`; `agent_turn.py:37-41,535-538` | IT 选择 Hermes 是否真的可运行？ | GUI 暴露 Hermes，但 CLI 明确拒绝 IT；ACP 路径也只传原始消息 | 选项与后端能力不一致 | High |

**已检查关键边界：**
- [x] 默认 Pi
- [x] brief 仍锁 Pi
- [x] Codex 第三方 sync
- [x] Codex 默认 sandbox
- [x] Hermes YOLO / ACP 分支
- [x] Cursor permission 分支
- [x] 外部依赖失败提示

**维度结论：** FINDINGS

### 4.3 复杂度：还能更简单吗？

未发现投机抽象；但执行器能力清单分散在 GUI options、CLI `_HERMES_SKILL`、Electron ACP 分支，缺少单一可用性判断，导致 H2。

**维度结论：** FINDINGS

### 4.4 命名：名字是否撒谎？

`isPiLockedRole` 现在准确表达“仅策划锁 Pi”；`HIRE_IT_EXECUTORS` 却包含当前无法正确工作的 Hermes，集合名称隐含“均可用”。

**维度结论：** FINDINGS

### 4.5 注释：提供价值，还是替坏代码找借口？

`agent_turn.py:40` 已明确“IT 没有 Hermes skill”，但 GUI 同时新增 Hermes 选项；注释暴露了实现矛盾，没有在本次变更中被解决。

**维度结论：** FINDINGS

### 4.6 风格与一致性

格式、类型和周边代码风格一致；`git diff --check` 通过。

**维度结论：** PASS

### 4.7 上下文：系统是否更健康？

实例层解锁本身合理，但能力矩阵与实际执行路径未统一。当前用户可以保存“看似有效、实际缺少角色规范或直接报错”的 IT 实例，降低系统可信度。

**维度结论：** FINDINGS

### 4.8 测试：证明有效，还是只是跑起来？

新增 Python 测试证明了：
- IT 实例配置可保存 Codex；
- brief 仍锁 Pi；
- 直接调用 `build_prompt(executor="codex")` 会出现约束。

但它没有证明 GUI 默认的 Codex app-server 分支会调用该 builder；事实上当前代码明确不会。GUI 已有 TS 测试基础设施，却没有覆盖 `hireColleague` / `agentInstances` 的关键行为。

**维度结论：** FINDINGS

---

## 5. 发现项摘要

### Critical（阻塞提交）

无。

### High（阻塞提交 / 发布）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| H1 | 设计/功能/测试 | `gui/electron/main.mjs:2838-2870`; `cli/agent_turn.py:345-354` | GUI 默认 Codex 为 `workspace-write`，走 app-server 并把原始 `message` 直接交给 Codex，绕过 `build_prompt`。因此 `diagnose.md`、会话上下文、仓库路径、“禁止 FOUNDRY_TOOL”及“只说不写”诊断规则均不生效，核心目标未实现。 | 抽出/暴露共享 prompt builder，让 Cursor/Hermes/Codex ACP 路径在调用 executor 前构建与 CLI 相同的角色 prompt；增加 Electron 路径测试，断言 app-server 收到完整 IT prompt。 |
| H2 | 功能/一致性 | `HireColleagueModal.tsx:65-69`; `agent_turn.py:37-41,535-538`; `main.mjs:2752-2771` | GUI 和文档宣称 IT 可选 Hermes，但 Hermes YOLO 路径明确因无 IT skill 而拒绝；非 YOLO ACP 路径虽然能调用，却只收到原始消息，没有 IT 角色规范。 | 二选一：A）本轮只支持 Codex，移除 IT 的 Hermes 选项及相关文案；B）为 Hermes 安装/映射 IT skill，并让 ACP 路径使用完整 IT prompt；覆盖 YOLO 与 ACP 两种路径。 |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 测试 | `gui/src/settings/hireColleague.ts`; `agentInstances.ts`; `ColleagueConfigBar.tsx` | 新增非平凡 GUI 状态/持久化行为，但没有对应自动化测试。现有 GUI 测试框架可用。 | 至少覆盖：IT 默认 Pi、brief 锁 Pi、IT Codex 保存/重载、第三方 sync 判定、roster executor 保留。 |
| M2 | 流程 | `.gitignore:30`; `docs/anvil/plans/2026-08-04-it-executor-switch.md` | 实施计划被通用 `plans/` ignore 规则忽略，已合入范围无法从仓库追溯到计划。 | 将确认结论放入可跟踪的 `docs/anvil/brainstorms/`，或为 `docs/anvil/plans/**` 增加例外。 |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| N1 | 工具链 | `agentReply.test.ts:3`; `ProviderSettingsView.tsx:139` | 全量 typecheck 仍有 2 个既有错误，非本 diff 引入。 | 独立修复基线，使类型检查可作为真实门禁。 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [ ]（typecheck 有既有失败） |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [ ]（2/4） |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [ ] |
| 评审文档完整 | [x] |
| 事实源可在仓库追溯 | [ ]（计划被忽略） |

### 结论

- [x] **BLOCK** — 当前 `main` 不建议发布；先修 H1/H2 并复审。
- [ ] **APPROVE**

### 评审备注

本变更已在评审前合入 `main`，因此本报告的 BLOCK 是发布门禁而非事前提交门禁。无需回滚实例解锁本身；建议优先修共享 prompt 接线，再决定 Hermes 是补齐还是从 IT 能力列表移除。
