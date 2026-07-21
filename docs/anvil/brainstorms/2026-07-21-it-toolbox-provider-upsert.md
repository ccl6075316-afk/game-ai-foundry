# 工程 Spec：IT 内部工具箱 v1 — 白名单写 Provider 账号

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-21
- **Updated**：2026-07-21
- **Source Of Truth Until**：实现以 [`docs/anvil/plans/2026-07-21-it-toolbox-provider-upsert-plan.md`](../plans/2026-07-21-it-toolbox-provider-upsert-plan.md) 为准（executed）
- **Confirmed By**：user 连续选择 A（方案 A 白名单工具；写 Key 二次确认；v1 仅账号库；写入后自动切当前生文）
- **Change Log**：从「IT 只读 diagnose」扩展为可经确认写入 `provider_accounts`；code 已落地
- **Requirements Source**：用户目标「IT=内部工具箱，除内核与游戏工程外」；首期收敛为配 API；架构选 Foundry `FOUNDRY_TOOL` 白名单（不给 Pi 原生改盘）
- **Background Inputs**：[`resources/skills/it/diagnose.md`](../../../resources/skills/it/diagnose.md)；[`cli/pi_foundry_tools.py`](../../../cli/pi_foundry_tools.py)；[`docs/superpowers/specs/2026-07-20-executor-storage-it-design.md`](../../superpowers/specs/2026-07-20-executor-storage-it-design.md)；设置 Agent 预设 Spec（二期可衔接）
- **Compounded Knowledge**：not yet compounded

## 背景输入

- Release 用户常把 API Key 丢给 IT，期望直接配好；现状 IT 仅能 `doctor` / `setup check` / `pipeline diagnose|status|heal` 等探测，**不能写配置**。
- 根因主要是**权限闸门**（Pi `--no-tools` + 白名单），其次缺「安全写账号库」CLI。
- 产品方向：IT 做内部工具箱；**不碰内核代码与游戏工程**；其余逐步放开。v1 先打通「丢 Key → 确认 → 写入 → 可聊」。

## 工程理解

保持 Pi 会话内核不变：`--no-tools`，工具经 `<<<FOUNDRY_TOOL>>>` 由 Foundry 执行。  
v1 新增 **写账号库** 命令，列入 IT 白名单；写入前必须有**用户确认**；成功后将该 Provider 设为**当前生文**（`host` / active text 对齐），便于下一句策划/IT 立刻可用。  
Key 永不进日志原文；工具回传与模型复述须脱敏。

## 目标

1. 用户在 **IT** 对话中提供厂商（或可推断）+ API Key → IT 复述将写入的目标 → 用户明确「确认」→ 调用白名单工具写入 `provider_accounts`。
2. 写入成功后：该 provider 成为当前生文账号（更新与 GUI「生文当前选中」一致的字段，含 `host.provider` / 账号库 active 约定，与现 `saveConfig` 行为对齐）。
3. 可选同次写入：`api_base`、账号默认 `text_model`（用户提供或沿用厂商默认）。
4. 既有只读能力保留：`doctor`、`setup check`、`setup pi status`、`pipeline diagnose|status|heal`。
5. 日志与工具 stdout：**禁止**完整 Key；仅 `has_api_key`、provider id、ok/error。

## 非目标（v1）

- 不给 Pi 原生 filesystem / shell tools（方案 B 排除）。
- 不写 `agents.executors` / `agents.instances`（Agent 预设、雇人配置 — 二期）。
- 不代跑 `setup executor step` / toolchain 安装（二期）。
- 不跑 `pipeline run`、不改 `games/`、不改 Godot C#、不落实 brief（仍归策划/PM/程序员）。
- 不通过 IT 改任意 `config set` 密钥旁路；专用 provider 写命令，不开放通用 secrets 写入。
- 视频账号库（Seedance 等）v1 **可不做**；若实现成本低可同命令支持 `video_accounts`，否则明确二期。

## 方案选择

**选定：方案 A — 扩 `FOUNDRY_TOOL` 白名单 + Foundry CLI。**

### 确认门闩

1. IT 收集：`provider` id（openrouter/deepseek/…）+ `api_key`（及可选 base/model）。  
2. 向用户复述：**将写入 Provider X**（Key 只显示前后各 2～4 字符或 `****`），请回复「确认」/「取消」。  
3. 仅当本会话用户明确确认后，才允许发出写工具；CLI 须带 **确认令牌或 `--i-confirm`**（二选一，plan 钉死），禁止「无确认直接写」。  
4. 取消或未确认：不落盘。

### CLI（名称 plan 可微调）

建议形态（事实源以 plan 最终命名为准）：

```text
python gamefactory.py setup provider upsert --provider <id> --api-key-env|stdin|--api-key <…> \
  [--api-base …] [--text-model …] [--set-active-text] --i-confirm
```

- `--set-active-text`：v1 **默认开启**（用户已选写入后自动切生文）。  
- Key 优先 **stdin / 环境变量临时注入**，避免进 shell history；若必须 argv，文档警告。  
- 输出 JSON：`{ok, provider, has_api_key, set_active_text, error?}`，**无 key 字段**。

### 白名单

`cli/pi_foundry_tools.py` `_ALLOWED_PREFIXES` 增加：

- `("setup", "provider", "upsert")`（或最终子命令名）

仅 **IT** profile 允许；**brief** profile **不**加入写 Key 命令。

### Skill

更新 `resources/skills/it/diagnose.md`（或拆 `configure.md`）：职责含「经确认配置 Provider」；仍禁止碰工程/内核；仍脱敏。

## 被排除方案

- Pi 原生改 `config.json`（方案 B）。  
- 无二次确认直接写 Key。  
- v1 同时做 Agent 预设 + 执行器安装。  
- IT 只生成草稿仍跳设置页保存（不满足「直接配置」）。

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| 未知 provider id | 工具失败；IT 列出支持的账号库 id |
| Key 为空 / YOUR_ 占位 | 拒绝写入 |
| 未带确认标志 | 拒绝写入；提示需用户确认 |
| 写盘失败 | ok=false；IT 说明，不假装成功 |
| 用户把 Key 贴进聊天 | 模型应尽快转工具写入，**后续回复不再完整复述 Key** |
| 非 IT 角色 | 无此白名单命令（brief 不包含） |
| 并发 GUI 设置同时保存 | 与现 config 深合并行为一致；后写覆盖同字段 |

## 工程代价

- **CLI**：`setup provider upsert`（或等价）+ 单测（写临时 config、无 key 泄漏、无 confirm 拒绝、set-active）。  
- **白名单**：`pi_foundry_tools` + IT 协议文案。  
- **Skill / 文档**：IT diagnose、TOOLS/GUI-CONFIG 短注。  
- **GUI**：v1 可不改（对话经 Pi 工具即可）；若需「确认」按钮可二期。  
- **安全评审**：Key 路径、日志、确认门闩必审。

预估：中小跨 cli + skill；共享 config 契约；需 `/anvil:plan`。

## 显式假设

1. 「当前生文」= 与 GUI Provider 页生文 active + `host.provider`（及必要时 `host.api_key` 镜像策略）与现 `saveConfig` 一致；具体字段以现 `providerAccounts` 序列化为准。  
2. v1 覆盖 `API_PROVIDERS` 文本账号（openrouter/openai/deepseek/…）；视频另议。  
3. 确认语：「确认」「好的写入」「可以」等由 skill 约定；取消：「取消」「不要」。  
4. 内核 = Foundry/Electron/Pi 运行时源码；游戏工程 = `games/`、`projects/*/game` 等玩法产物 — IT 工具不得改。

## 验收标准

1. IT 对话：用户给 DeepSeek Key → IT 请求确认 → 用户确认 → `provider_accounts.deepseek` 有可用 Key。  
2. 同次后 `doctor` / 生文路径视该账号为当前（active text / host 已切）。  
3. 未确认调用写命令 → 失败，config 不变。  
4. 工具 JSON 与日志无完整 Key。  
5. 策划 brief 白名单仍无写 Key 命令。  
6. IT 仍不能 `pipeline run`、不能改 `games/`。

## 安全

- Key：确认门闩 + 脱敏输出 + 禁止 brief 写 Key。  
- 不扩大为通用 config 写。  
- 审计：upsert 记 provider id、ok、set_active，不记 key。

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | 白名单工具（A）；写 Key 二次确认（A）；v1 仅账号库（A）；写入后自动切生文（A） |
| 已排除 | Pi 原生改盘；无确认直写；v1 做 Agent/执行器安装 |
| 默认写入 Spec | CLI 名 `setup provider upsert`；confirm=`--i-confirm`；视频账号 v1 不做 |

## Resume

- **下一步**：用户确认本 Spec 后 → `/anvil:plan` → `/anvil:code`。  
- **Deferred**：Agent 预设写入、executor 安装步进、视频账号、GUI 确认按钮。
