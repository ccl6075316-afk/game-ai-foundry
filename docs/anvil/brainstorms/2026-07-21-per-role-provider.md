# 工程 Spec：对话角色按实例配置 Provider / 模型 / 第三方

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-21
- **Updated**：2026-07-21（增补：策划/IT 聊天顶栏 Provider+模型快选，持久写 instances）
- **Source Of Truth Until**：本 Spec 已确认；实现以 [`docs/anvil/plans/2026-07-21-per-role-provider-plan.md`](../plans/2026-07-21-per-role-provider-plan.md) 为准（含快选 T5.1）
- **Confirmed By**：user explicit「确认」（2026-07-21）；快选方案 A 于同日确认
- **Change Log**：2026-07-21 用户确认聊天顶栏快选（持久写入 `agents.instances`），非会话临时覆盖
- **Requirements Source**：用户 Grill 选择（全角色可配 / Codex 混合第三方 / Provider+模型+开关 / 角色页四同事 / 保存时同步 Codex / 按实例 / config.json `agents.instances`）+ 用户接受的默认建议（Cursor 第三方 v1 不做、工种默认继承、Key 仅在 provider_accounts）
- **Background Inputs**：既有多 Provider 账号库 UX；Hermes `hermes_provider` 同步先例；内置 Pi 鉴权现状；聊天花名册多实例
- **Compounded Knowledge**：not yet compounded

## 背景输入

- 用户可在 Provider 页配置多家账号，但内置 Pi（策划 / IT）当前**不按角色/实例**解析，且全局偏向 OpenRouter。
- 「角色」页仅项目经理 / 程序员选执行器；运维不出现，用户无法理解如何为 IT 选账号。
- 已存在：`provider_accounts`、`agents.hermes_provider`、Hermes「同步 API」、聊天 `ColleagueInstance`（含 `executor`）、`agent turn --instance-id`。
- Codex CLI 支持订阅登录与第三方模型；Foundry 目前几乎不接 Codex 第三方。

## 工程理解

产品需要：**账号库多家 + 执行器选择（Pi / Hermes / Codex / Cursor）+ 按同事实例覆盖 Provider/模型** 三者同时成立。  
配置权威在 `~/.gamefactory/config.json`；GUI 花名册只持有实例身份（id、显示名等），LLM 相关覆盖写入 `agents.instances.<id>`。  
鉴权解析必须按「当前实例 → 工种默认 → 生文回退」链执行，禁止再写死「永远优先 OpenRouter」。

## 目标

1. 四个对话工种（策划 / IT / 项目经理 / 程序员）均可在 **设置 → 角色** 为**每个同事实例**选择：执行器（工种允许范围内）、Provider（账号库 id）、模型（可选覆盖）、（仅 Codex）用第三方开关。
2. 内置 Pi 回合使用该实例解析出的 Provider Key + 模型。
3. Hermes 继续可同步 API；Codex 在「用第三方」开启且保存时，把选定账号写入/同步到 Codex 第三方配置（行为对齐 Hermes 同步）。
4. 用户能在 UI 上看到运维/策划与 Provider 的绑定关系，不再误以为「只能配生文共用」。
5. **策划 / IT（内置 Pi）** 可在**聊天界面**对当前同事实例快速切换 Provider + 模型；变更**立即持久化**到 `agents.instances.<id>`，下一条消息生效（与设置页同一数据源）。

## 非目标

- 原画师 / 动画师 / Godot 组装等流水线岗位不进「角色」页；仍用 Provider 页生图/视频配置。
- 不修改 `@earendil-works/pi-coding-agent` 源码；不把图像/视频生成迁到 Pi。
- Cursor：**v1 不实现**第三方 Key 注入；选 Cursor 时隐藏或禁用「用第三方」，仅本机登录/订阅。
- 不为每个实例复制 API Key；Key 只存 `provider_accounts`。
- 不在本 Spec 解决 Electron Node 20 vs Pi 引擎版本（另轨）；本功能假设 Pi 运行时已可用。

## 当前架构约束

| 证据 | 含义 |
|------|------|
| `gui/src/chat/roles.ts` | 对话工种仅 `brief` / `product_host` / `programmer` / `it` |
| `gui/src/chat/roster.ts` | 实例已有 `id`、`executor`；配置未进 config |
| `cli/pi_runtime.py` `resolve_pi_api_auth` | 全局 OpenRouter → DeepSeek → host，无实例维度 |
| `cli/executor_setup.py` | Hermes 已有按 Foundry provider 同步 |
| `resources/config.example.json` `agents.*` | 工种级 executor/skill；`hermes_provider` 顶层 |
| `gui/src/components/SettingsPanel.tsx` | 角色页无策划/IT；无实例选择器 |

## 方案选择

**选定：config 内 `agents.instances` + 角色页按实例编辑 + 解析链覆盖。**

- 花名册（GUI）与 `agents.instances`（config）通过 **instance id** 关联。
- 工种块（`agents.brief` / `it` / `orchestrator` / `godot-developer`）保留为**默认模板**；实例字段覆盖默认。
- Codex 第三方：保存设置（及可选「同步到 Codex」按钮）时同步；默认关=订阅登录。
- Cursor 第三方：v1 不做。
- **Pi 工种聊天快选（方案 A）**：当前同事为策划/IT 时，聊天顶栏（或输入区旁）提供 Provider + 模型快选；写入同一 `agents.instances`；设置页仍可深配。项目经理/程序员 v1 可不做聊天快选（仍以设置页为主），避免与执行器/第三方开关挤在一处。

## 被排除方案

- 仅共享「生文」Provider（无法满足多角色多账号）。
- 配置只存在 GUI roster 本地状态（CLI/`doctor`/多机不一致）。
- 按工种共享、禁止实例差异（用户已明确要按实例）。
- 每次发消息临时注入且永不写 Codex 配置（用户要求保存时同步）。
- 角色页纳入生图/视频岗位（与 Provider 页重复）。
- **仅本会话临时覆盖 Provider/模型且不写 config（方案 B）**——与 config 权威冲突，已排除。

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| 实例无 `agents.instances` 条目 | 继承工种默认 + 生文当前 Provider/模型；不报致命错 |
| 实例选了未填 Key 的 Provider | UI 警告；回合失败信息指向 Provider 页补 Key |
| Codex `use_third_party=false` | 不写第三方；不覆盖用户订阅态 |
| Codex `use_third_party=true` 但同步失败 | 保存可成功记配置，但明确报同步失败；回合前 `doctor`/状态可见 |
| 删除同事实例 | 应清理或标记对应 `agents.instances.<id>`（避免僵尸配置） |
| 策划 executor | 固定 Pi（或 host 回退既有逻辑）；UI 不提供 Hermes/Codex |
| IT executor | 固定 Pi；同上 |
| 项目经理 / 程序员 | 可选 hermes / codex / cursor（保持现有集合） |
| 多实例同工种不同 Provider | 各用各的；handoff 的 target_instance_id 已存在，回合必须带 instance id |

## 工程代价

- **配置契约**：扩展 `agents.instances`；兼容旧配置（无 instances 时行为=继承）。
- **CLI**：`resolve_*_auth` / Pi / `agent turn` 按 `--instance-id` 解析；Codex 同步步骤（新或扩展 `setup executor`）。
- **GUI**：角色页增加实例选择 + 四工种卡片字段；保存写入 instances；删人清理；**策划/IT 聊天顶栏快选**（持久写同一 config）。
- **测试**：解析链单测；保存/同步契约；迁移无 instances 的旧 config。
- **文档**：设置说明、TOOLS/AGENTS 短注。

预估：跨 `cli` + `gui` 多文件；共享配置 schema；需 `/anvil:plan` 拆 DAG。

## 显式假设

1. 同事实例 id 在 GUI 与 config 间稳定；雇人时生成的 id 即 config 键。
2. Provider 页的 `textModel`（及账号级默认模型）在实例未填 `model` 时作为回退。
3. Pi 支持的 provider 名与 Foundry `provider_accounts` id（openrouter/deepseek/…）可映射到现有 env Key 注入方式。
4. Codex 第三方同步的具体文件/CLI 以 Codex 当前公开能力为准，实施阶段在 plan 中钉死命令；失败须可诊断。
5. 「生文」Provider 页仍表示**默认/回退**与账号库编辑入口，不再是唯一生效源。

## 领域语言

| 术语 | 含义 |
|------|------|
| 账号库 | `provider_accounts` 多家 API 账号 |
| 工种 | `brief` / `it` / `product_host` / `programmer` |
| 同事实例 | 花名册中一个具体同事（含唯一 `instanceId`） |
| 实例覆盖 | `agents.instances.<instanceId>` 中的 executor/provider/model/use_third_party |
| 用第三方 | Codex 下用账号库 Key 而非订阅登录 |
| 生文回退 | Provider 页当前生文选中账号 |

## 功能需求

1. **配置 schema（权威）**  
   - `agents.instances.<instanceId>` 至少支持：  
     `role_kind`（冗余便于校验）、`executor`、`provider`（账号库 id）、`model`（string，可空）、`use_third_party`（bool，仅 Codex 有意义）。  
   - 工种默认保留在现有 `agents.brief` / `agents.it` / `agents.orchestrator` / `agents.godot-developer`（可增加同名可选 `provider`/`model` 字段以作默认）。  
   - 废弃「仅靠全局 OpenRouter 优先」作为 Pi 唯一策略；改为解析链。

2. **解析链（CLI）**  
   对给定 `instanceId` + `role_kind`：  
   1) `agents.instances[id]` 覆盖；  
   2) 否则工种默认；  
   3) 否则生文回退（`host` / 当前 text provider）。  
   Pi / Hermes / Codex（第三方开）均走此链取 provider+model；缺 Key 返回明确错误。

3. **设置 → 角色 UI**  
   - 列出花名册中四个工种的实例（选择器或分组列表）。  
   - 编辑字段随 executor 变化：  
     - Pi：Provider + 模型（无第三方开关）。  
     - Hermes：Provider + 模型 +（沿用/并入）同步 API。  
     - Codex：Provider + 模型 +「用第三方」；关则提示走登录。  
     - Cursor：Provider/模型可选作展示或预留，但第三方开关禁用；说明仅登录。  
   - 保存写入 `agents.instances`；提供 Codex「同步到 Codex」（保存时若 `use_third_party` 亦触发同步）。

4. **运行时**  
   - GUI `agent turn` / brief chat / IT 必须传 `instance-id`。  
   - 删除实例时清理对应 config 条目。

5. **可观测**  
   - `setup pi status` / doctor 或等价输出能显示当前解析到的 provider（脱敏）与 node/auth 状态；实例级至少在 debug/json 中可见。

6. **聊天快选（策划 / IT）**  
   - 当活动同事 `roleKind` 为 `brief` 或 `it` 时，聊天 UI 展示 Provider 选择（账号库已配置项）与模型输入/选择。  
   - 变更立即 `saveConfig` upsert 当前 `instanceId` 的 `provider`/`model`（可补齐 `role_kind`/`executor=pi`）。  
   - 未填 Key 的 Provider 可选但须警告。  
   - 与设置 → 角色同一数据；任一方修改后另一方应在下次加载/刷新后一致。

## 非功能需求

- 旧配置无 `agents.instances` 时行为与「全员继承生文/工种默认」兼容，不强制迁移向导。
- 不在日志/错误 argv 中打印 API Key（保持现有 Pi env 注入习惯）。
- 设置保存延迟可接受；同步 Codex 失败不得静默成功。

## 安全关注点

- Key 仍只存本地 config 的 `provider_accounts`；instances 仅引用 provider id。
- Codex/Hermes 同步会把 Key 写入外部工具配置目录——须与现有 Hermes 同步同等对待（用户显式操作/保存触发）。
- 多实例不得误用他实例的 provider 覆盖。

## 成功标准

1. 可为「IT · 运维」实例选 DeepSeek、为「策划」实例选 OpenRouter，各自对话实际打到对应 Key/模型（可用 status/json 或一次受控回合验证）。
2. 两名程序员实例可分别选 Codex 订阅 vs Codex+第三方 OpenRouter；保存后第三方侧配置更新，订阅侧不被误改。
3. 角色页可见运维/策划；用户无需再问「Pi 在哪配」。
3b. 策划/IT 聊天顶栏切换 Provider 后，下一条消息走新账号（config 已更新）；刷新设置页可见同一实例字段。
4. 无 `agents.instances` 的旧配置仍能开聊（回退链）。
5. 单测覆盖解析链优先级与缺 Key 错误；Codex 同步有可测的纯函数/契约层（外部 CLI 可 mock）。

## PR Review 关注点

- 解析链是否仍残留「强制 OpenRouter 优先」。
- 删实例是否漏清理 config。
- Cursor 是否误做了第三方同步。
- 保存时 Codex 同步是否在未开第三方时改写用户配置。
- GUI 是否所有 Pi/Agent 路径都传 `instance-id`。

## 开放问题

- Codex 第三方同步的**具体**目标文件/CLI 子命令：留给 `/anvil:plan` Spike（依赖本机 Codex 版本文档）。
- 实例级 `model` 与 Pi `--model` / Hermes model / `codex exec --model` 的参数映射表：plan 阶段按执行器列齐。
- 花名册尚未写入 config 时，「角色」页如何列出实例：以 GUI roster 为准生成编辑态，保存时 upsert `agents.instances`（已作为假设；若实现发现 roster 未持久化到可恢复 id，plan 须补花名册持久化，不扩大本 Spec 重开 Grill）。

## 决策账本（摘要）

| 项 | 结论 |
|----|------|
| 范围 | 对话四同事均可配 |
| Codex/Cursor | 混合；Cursor 第三方 v1 不做 |
| UI 字段 | Provider + 模型 + Codex 第三方开关 |
| 角色页 | 四同事；生图视频不进 |
| Codex 同步时机 | 保存设置时（+ 可选按钮） |
| 粒度 | 按同事实例 |
| 落盘 | `config.json` → `agents.instances.<id>` |
| Key | 仅 `provider_accounts` |
| 缺省 | 继承工种默认 → 生文回退 |
| Pi 聊天快选 | 方案 A：顶栏持久写 instances；排除会话临时覆盖 |

## 下一阶段

用户确认本 Spec（将 Status 标为 `confirmed`）后进入 `/anvil:plan` 产出可执行任务 DAG。
