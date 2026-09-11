# 工程 Spec：Pi 常驻独立 Agent（RPC）与 Foundry CLI 能力

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-09-11
- **Updated**：2026-09-11
- **Source Of Truth Until**：requirements are confirmed and replaced by a `/anvil:plan`, or the request is abandoned
- **Requirements Source**：engineering spec derived from user grill decisions 2026-09-11（A/X/P/S1/R2/B1/C1/T1）+ repository evidence（`pi_runtime.py` `--no-tools --no-session`；内嵌 Pi `rpc-entry` / `--mode rpc`；Cursor/Hermes ACP 对照）
- **Background Inputs**：本轮对话（空心 Pi 补全壳 vs 完整 Agent 意图；远期 GUI 脱离化）仅为背景，非正式编码事实源
- **Compounded Knowledge**：not applicable
- **Resume Point**：plan 已落盘 [`docs/anvil/plans/2026-09-11-pi-rpc-independent-agent-plan.md`](../plans/2026-09-11-pi-rpc-independent-agent-plan.md)；下一步 `/anvil:code` 从 T1 起

## 背景输入

- 用户原意：接入 Pi 是为了让其 **尽可能发挥作用**（会话、工具、独立完成工作），不是当无状态 LLM 壳。
- 现状体感：内嵌 Agent 弱于外置 Dev（可读代码/日志/完整工具环）；当前 Pi 集成关掉了原生工具与 session。
- 远期意向（非本轮）：产品可脱离单一 GUI，坍缩为 CLI / skill / 工作流，供各类 Agent 配合使用——本 Spec **不实现**。
- 外置优先排序：本轮 **明确不考虑**。

## 工程理解

1. 今日 `run_pi_text_completion` 显式 `--no-tools --no-session`，工具靠 `FOUNDRY_TOOL` 围栏 + Foundry 白名单；上下文靠 Foundry session JSON 重注入。这与「完整 Pi Agent」目标相反。
2. 内嵌包 `@earendil-works/pi-coding-agent` 自述含 read/bash/edit/write 与 session；并提供 `dist/rpc-entry.js`（`--mode rpc`），具备常驻 RPC 面。
3. Cursor/Hermes 已用常驻 stdio JSON-RPC（ACP）；GUI 已有按实例保活与聊天展示模式，可作体验对照，但本轮 Pi **不用自研假 ACP**，优先官方 RPC。
4. 产品约束「只配 API、工种边界、brief 导出闸门」可由 Foundry 闸门 + skill 维持，**不依赖**挖空 Pi。
5. 直连 `host` LLM 也能满足「补全」；保留 Pi 的价值应来自 **Agent 能力**，否则嵌 Pi 性价比低——本 Spec 纠偏到 Agent 路径。

## 目标

1. **IT** 与 **策划（brief）** 在执行器为 Pi 时，以 **常驻 Pi RPC 进程** 独立完成多轮工作（含原生工具环）。
2. Foundry 领域能力通过 **`gamefactory` CLI + skill** 供 Pi 调用（与「独立 Agent + 可用 Foundry 工具」一致）。
3. **聊天上下文以 Pi session 为真相**；GUI 负责展示与同步，不再以「每次重拼 Foundry JSON → 无状态补全」为主路径。
4. 去掉（或对 IT/策划新路径废弃）以 `--no-tools --no-session` + `FOUNDRY_TOOL` 围栏为主的集成方式。

## 非目标

- GUI 脱离化 / 能力面产品重构（远期）。
- 外置 Dev/Cursor IDE 优先接入排序与 MCP 大一统（延后）。
- 顾问角色迁入新 Pi（仍旧弱工具/只读路径）。
- 自研与 Cursor 同构的 ACP 适配层包住 Pi（T2）。
- Foundry 专用 MCP/扩展工具注册进 Pi（方案 Q）。
- 工作区沙箱硬隔离（S3）作为本轮硬性交付。
- 中途 GUI 批准卡作为 Pi 默认安全模型（用户选 S1 YOLO）。
- 项目经理/程序员执行器改造（Hermes/Codex/Cursor 路径保持，除非共享无害改动）。

## 当前架构约束

- GUI `agent-turn` / `host-chat-turn` 经 Electron `runCli`；Pi 落在 `cli/pi_runtime.py`、`cli/pi_foundry_tools.py`、`cli/tool_permission.py`。
- 策划权威 brief 现有 draft + export 门闩（`brief chat export` 等）——本轮 **保留**。
- 内嵌 Pi 由 `scripts/prepare_embedded_pi.mjs` 准备；版本与 RPC 能力以 embed manifest 为准，plan 阶段需核实 RPC session/消息 API。
- Release 用户仍期望「只配 API」可用 IT/策划——新路径不得强制安装外置 Cursor。

## 方案选择

| 决策 ID | 选择 | 含义 |
|---------|------|------|
| A | 常驻独立 Agent | 对齐 Codex/Cursor 形态，非 one-shot 补全壳 |
| X | 本轮只修 Pi | 脱离化仅非目标 |
| P | 原生工具 + CLI | 全开 Pi 工具；Foundry 靠 gamefactory |
| S1 | YOLO 信任 | GUI 内默认放行工具；少数产品闸门保留 |
| R2 | IT + 策划 | 顾问不迁 |
| B1 | brief 导出闸门 | 正式 brief 不由 Pi 常规直接写权威文件 |
| C1 | Pi session 真相 | GUI 同步展示 |
| T1 | Pi 官方 RPC | `--mode rpc` / `rpc-entry` |

## 被排除方案

- 继续 `--no-tools --no-session` + 围栏为主（空心壳）。
- R：常驻但仍以 `FOUNDRY_TOOL` 为主。
- S2 中途批准为默认（本轮不选；不禁止日后加开关）。
- C2 Foundry JSON 仍为聊天主真相（与「让 Pi 管上下文」冲突）。
- T2 自研假 ACP 优先。
- R3 顾问一并放开原生写盘。
- B2 Pi 常规直接写权威 brief。

## 边界与失败模式

- **权威 brief**：skill + 产品流程要求经导出闸门；S1 下无硬技术拦网时，失败模式为「模型误写权威文件」——须在 skill/验收中明示，plan 可评估只读挂载或路径约定等弱约束（不升格为 S2）。
- **Pi RPC 能力不足**（无法同步消息/session）：阻塞发布该路径；允许临时回退旧补全壳需在 plan 写明开关与期限，不得默认静默回退无提示。
- **顾问**：行为与工具面保持现状；不得因 IT/策划改动误开顾问写盘。
- **进程崩溃/重启**：GUI 须能重建 RPC 会话并恢复或提示用户；C1 下以 Pi session 持久化为准。
- **危险 bash**：S1 接受 GUI 内风险；文档须对用户可见（设置/IT 说明）。

## 工程代价（供 plan 估）

- **预计触及**：`cli/pi_runtime.py`、`cli/agent_turn.py`、`cli/host_chat.py`（策划接线）、`gui/electron/*`（Pi session manager，对照 hermes/cursor acp session）、IT/brief skills、相关单测。
- **可能退役/降级**：IT/策划路径上的 `FOUNDRY_TOOL` 主循环、对 Pi 的 `--no-tools --no-session` 默认、IT 可变命令 HTTP 桥作为主安全手段（S1）。
- **验证**：嵌入 Pi RPC 探测；IT 多轮读日志/跑 `gamefactory doctor`；策划多轮探查 + 导出闸门仍在；顾问回归只读。
- **迁移**：现有 Foundry conversation JSON 与 Pi session 映射策略由 plan 定（导入一次 / 仅新会话 / 双读过渡）。

## 显式假设

1. 当前 embed 的 Pi 版本 RPC 模式足以支撑：多轮 prompt、工具执行、session 持久、GUI 可获取助手可见文本（plan 首项核实；不足则升版本或记开放问题）。
2. 「YOLO」仅指 Foundry GUI 内嵌 Pi，不改变外置执行器既有审批模型。
3. 策划 GUI 仍可保留 draft/导出 UX；后端推理与工具环改为 Pi RPC，而非必须删掉所有 brief chat IPC。

## 领域语言

| 术语 | 含义 |
|------|------|
| 空心壳 | `--no-tools --no-session` 仅补全 |
| Pi RPC | 内嵌 Pi `--mode rpc` 常驻通道 |
| Foundry 工具/能力 | 以 `gamefactory` CLI + skill 暴露的领域操作 |
| 权威 brief | 已导出/绑定的正式 brief（非 draft） |
| 聊天真相（C1） | 对话历史以 Pi session 为准 |

## 功能需求

1. IT（executor=pi）经 GUI 发消息时，主进程维护 **每实例常驻 Pi RPC**，在进程内完成工具环后返回/流式同步可见回复。
2. 策划在 Pi 路径下同样使用常驻 RPC + 原生工具；可调用 `gamefactory`；**落实权威 brief 仍走现有导出/门闩流程**。
3. 启用原生工具与 Pi session；IT/策划新路径 **不以** `FOUNDRY_TOOL` 围栏为工具主协议。
4. GUI 聊天展示与 Pi session 同步（C1）；刷新/重进同事后历史仍可还原（依赖 Pi session 持久化 + GUI 同步实现）。
5. 顾问角色行为与工具限制保持现网只读/弱工具语义，不纳入本轮新 Pi。
6. Skill（IT diagnose、策划相关）更新为：引导使用原生探查 + `gamefactory`，并写明勿常规覆盖权威 brief。

## 非功能需求

- 开箱：仍只需配置 API（及已嵌入的 Pi）即可用 IT/策划 Pi 路径。
- 与现有 Hermes/Cursor ACP 会话管理在 Electron 层可并列，但不强制协议统一。
- 失败可诊断：RPC 握手失败、session 丢失须有明确错误回传 GUI。

## 安全关注点

- **S1**：GUI 内嵌 Pi 默认可 read/bash/edit/write——等同高信任本地 Agent；须在 UI/文档披露。
- **B1**：权威 brief 导出闸门保留；无硬拦截时的误写风险需 skill + 测试关注。
- API Key 仍经现有配置注入 Pi，不得写入日志明文。
- 权限 HTTP 桥不再作为 Pi 主安全模型；若残留代码，不得与 S1 行为冲突（plan 清理）。

## 成功标准

1. IT Pi：一次会话内可多轮使用原生读文件/日志类能力，并成功调用至少一条 `gamefactory`（如 `doctor --json`），无需 `FOUNDRY_TOOL` 围栏。
2. 策划 Pi：同样可多轮工具探查；**未经导出闸门时权威 brief 文件不因「常规落实」被 Pi 覆盖**（流程/验收用例覆盖 B1）。
3. 默认调用栈不再对 IT/策划 Pi 使用 `--no-tools --no-session` 补全主路径。
4. GUI 展示的对话在进程重启后能从 Pi session（或文档化的同步层）恢复要点。
5. 顾问相关用例/行为不出现新增写盘白名单放行。
6. 单测或契约测覆盖：RPC session manager 生命周期；旧围栏路径不再被 IT/策划默认调用。

## PR Review 关注点

- 是否回流空心壳默认。
- 是否误伤顾问或 PM/程序员路径。
- C1 是否名存实亡（仍整段重注入 Foundry JSON 当主记忆）。
- B1 是否被实现成「完全拦写」或「完全不管」两极端（应对齐 skill+导出流程）。
- 安全文案是否披露 S1。

## 开放问题（交 `/anvil:plan`）

1. 当前 embed Pi 版本 RPC 的具体帧格式、session 创建/恢复、消息推送 API 探测结果。
2. 策划：保留 `brief chat` IPC 外壳 vs 完全并入 `agent-turn` 的取舍与工作量。
3. 旧 Foundry conversation JSON 迁移/只读归档策略。
4. Pi 升级策略（若 RPC 能力不够）。
5. 是否提供可选「非 YOLO」开关（本轮非必须）。

## 下一阶段

用户确认本文件无修正后，执行 **`/anvil:plan`**：产出可执行任务 DAG（RPC 探测 → session manager → IT 接线 → 策划接线 → skill/文档 → 退役围栏默认 → 验证）。
