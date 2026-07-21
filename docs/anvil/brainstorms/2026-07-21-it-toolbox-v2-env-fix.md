# 工程 Spec：IT 工具箱 v2 — 确认后修环境与配置

## 执行元数据

- **Status**：implemented
- **Workflow Stage**：code
- **Created**：2026-07-21
- **Updated**：2026-07-21
- **Source Of Truth Until**：落地后以 CLI/白名单/skill 为准
- **Confirmed By**：user「确认」（2026-07-21）— 危险操作二次确认即可；IT 可扩大修环境/配置；三刀边界认可
- **Change Log**：相对 v1（仅 Provider upsert）扩展为工具链安装、执行器步进、Agent 预设、pipeline heal/reset；仍走 FOUNDRY_TOOL 白名单；code 已落地
- **Requirements Source**：用户要 IT 自愈环境/配置（不改内核/游戏工程）；接受「二次确认」代替过窄分期；澄清 IT=Pi 白名单而非 Hermes/Codex
- **Background Inputs**：[`2026-07-21-it-toolbox-provider-upsert.md`](2026-07-21-it-toolbox-provider-upsert.md)（v1 已落地）；[`cli/pi_foundry_tools.py`](../../../cli/pi_foundry_tools.py)；[`resources/skills/it/diagnose.md`](../../../resources/skills/it/diagnose.md)；setup/executor/pipeline CLI 既有能力
- **Compounded Knowledge**：not yet compounded
- **Supersedes (scope)**：v1 Spec 的「非目标：Agent/执行器/工具链」对本 v2 **不再适用**；v1 写 Key 门闩与脱敏规则继承

## 背景输入

- v1：IT 可经确认 `setup provider upsert`。
- 用户希望 IT 继续解决「环境、配置」类错误，不必过度分期；危险操作二次确认即可。
- IT 默认是 **内置 Pi + 白名单**，不是 Hermes/Codex；扩大白名单仍小于 PM/程序员执行器面，但对「只配 Key」的 Release 用户是主要自愈入口。

## 工程理解

保持方案 A：Pi `--no-tools`，变更一律经 `FOUNDRY_TOOL` → Foundry CLI。  
**突变类**命令必须用户明确确认后才带确认标志执行（与 v1 `--i-confirm` 同模式，或统一 `--i-confirm`）。  
**只读**探测可不确认。  
禁止目标：内核源码树、游戏工程目录、默认批处理花钱跑管线。

## 目标

1. IT 在探测到问题后，能**提议修复** → 用户确认 → **执行**对应白名单命令并回报结果。  
2. 覆盖至少：
   - **账号**：继承 v1 `setup provider upsert`（含切生文）
   - **本机工具链**：`setup install <ffmpeg|godot|dotnet>`、`setup ensure`
   - **执行器**：`setup executor status`（只读）、`setup executor step <id> <step>`（突变，需确认；含 Hermes configure_api、Codex sync_api 等既有 step）
   - **Agent 预设**：写入 `agents.executors`（Pi/Hermes/Codex 默认 provider/model/use_third_party）；Codex 第三方确认后可 `sync_api`
   - **流水线修复**：`pipeline diagnose|status`（只读）；`pipeline heal`、`pipeline reset --task-id …`（需确认）
3. Skill 更新：先 doctor/diagnose，再给出可执行修复清单；确认语约定与 v1 一致。  
4. 日志/工具输出：无完整 API Key；安装类可打进度摘要。

## 非目标

- 不给 Pi 原生任意 shell / 改任意路径文件。  
- **不**修改 Foundry / Electron / 内嵌 Pi **源码**；**不**改 `games/`、项目内玩法工程（`projects/*/game` 等）。  
- **不**默认 `pipeline run` / 生图生视频批处理；若未来要开，须单独 Spec + 强确认 + 费用提示（本 v2 **不做**）。  
- 不替代策划落实 brief、不替代程序员写 C#。  
- 不实现 GUI 专用确认按钮（对话确认即可；GUI 可后续加）。

## 硬边界（三刀）

1. **突变操作二次确认**（安装、写配置、heal、reset、sync、upsert）。  
2. **不碰内核源码与游戏工程**。  
3. **不默认 `pipeline run`**。

## 方案选择

**选定：扩大 IT 白名单 + 统一确认门闩 + 更新 diagnose skill。**

### 白名单增量（在 v1 基础上）

| 前缀 | 确认？ | 说明 |
|------|--------|------|
| 既有 doctor / setup check / setup pi status / pipeline diagnose\|status | 否 | 只读 |
| `setup provider upsert` | 是 | v1 |
| `setup install` | 是 | ffmpeg/godot/dotnet |
| `setup ensure` | 是 | 批量补齐 |
| `setup executor status` | 否 | 只读 |
| `setup executor step` | 是 | 各 step |
| `setup agents executors upsert`（或等价命名，plan 钉死） | 是 | 写 `agents.executors` |
| `pipeline heal` | 是 | 已存在，正式纳入 IT 流程 |
| `pipeline reset` | 是 | 按 task-id |

CLI 若缺「写 agents.executors」专用命令，plan 中新增，对齐 GUI Agent 页字段；禁止开放任意 `config set` 密钥旁路。

### 确认机制

- 会话内：复述将执行的操作（无完整 Key）→ 用户「确认」→ 工具带 `--i-confirm`（或 step 级等价标志）。  
- 未确认调用突变命令 → CLI 拒绝（能加标志的命令一律要求；对暂无法改签名的旧命令：仅 skill 约束 + 白名单仍允许，但 skill **强制**确认——plan 优先给 install/ensure/executor step/heal/reset 补齐 `--i-confirm` 或包装命令）。

## 被排除方案

- 无确认自动安装/写配置。  
- Pi 原生改盘。  
- v2 纳入 `pipeline run`。  
- 继续只做「指路不去设置页」而不给执行手段。

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| 安装失败（网络/权限） | 回报 error；提示手动环境面板或重试 |
| executor 本机未装 CLI | step 失败；IT 说明下载/安装入口 |
| 用户确认后取消不了已开始的长时间下载 | 尽量可超时/可报告；不保证中途取消（可记已知限制） |
| heal/reset 误伤 | 确认时列 task id；仅白名单子命令 |
| 试图改 games/ | 无此工具；拒绝 |

## 工程代价

- 扩 `pi_foundry_tools` 白名单 + IT 协议文案。  
- 必要时包装 `setup install|ensure|executor step|pipeline heal|reset` 的 `--i-confirm`。  
- 新 CLI：`agents.executors` upsert（若尚无）。  
- 单测：白名单、无 confirm 拒绝、executors 写入。  
- Skill + TOOLS/AGENT-ROUTING 短更。  

预估：中等，跨 cli + skill + docs；需 `/anvil:plan`。

## 显式假设

1. 「内核」= 本仓库 cli/gui/electron 及内嵌 runtime 源码，不是用户 config。  
2. 「游戏工程」= `games/`、brief 导出的 Godot 工程目录。  
3. v1 upsert 行为保持不变。  
4. Codex/Hermes 仍可比 IT 更强；不因此缩小 IT，只强调确认门闩。

## 验收标准

1. 缺 FFmpeg：IT 确认后 `setup install ffmpeg`（或 ensure）成功或可读失败原因。  
2. 用户确认后可跑至少一条 `setup executor step`（如 status 只读不确认；mutate step 需确认）。  
3. 确认后可写 `agents.executors.pi.provider`（或等价）且不泄露 Key。  
4. 确认后 `pipeline heal` / `reset` 可执行；未确认则 skill 不发工具（及 CLI 门闩若已加）。  
5. 白名单仍无 `pipeline run`；无法经 IT 改 `games/`。  
6. Provider upsert v1 回归仍通过。

## 安全

- 突变确认 + Key 脱敏。  
- 白名单前缀精确，禁止 `;|&&` 拼接。  
- 不开放通用任意路径写文件。

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | 二次确认即可扩大；三刀边界；v2=工具链+执行器+Agent 预设+heal/reset；不默认 pipeline run；继续白名单方案 A |
| 已排除 | 过窄只做 A；Pi 原生改盘；v2 含 pipeline run |
| 默认 | 突变命令尽量统一 `--i-confirm` |

## Resume

- **下一步**：可选 `/anvil:review`；用户要求时 commit/push。  
- **Deferred**：GUI 确认按钮；pipeline run；改工程。
