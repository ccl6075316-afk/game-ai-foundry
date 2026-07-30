# 工程 Spec：Pi 同事实例 Thinking 档位

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-30
- **Updated**：2026-07-30
- **Source Of Truth Until**：本 Spec 已确认；实现以 [`docs/anvil/plans/2026-07-30-pi-thinking-level-plan.md`](../plans/2026-07-30-pi-thinking-level-plan.md) 为准（plan 仍待用户确认）
- **Confirmed By**：user「确认」（2026-07-30）
- **Requirements Source**：engineering spec derived from user Grill（需要 LLM thinking 开关 → 挂实例 → 不影响 Agent → Pi 缺高中低故缺 Think → 多档 → 仅 Pi `--thinking`）
- **Background Inputs**：会话中关于各方模型未适配 thinking 的讨论；上游 Pi CLI 已支持 `--thinking`；Codex/Cursor 已有高中低模型档位
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：确认 plan 后 `/anvil:code`

## 背景输入

- 用户需要针对「有 thinking 能力的 LLM」控制思考强度；**不需要在 UI 展示思考过程**。
- Codex / Cursor 原生已通过模型 **高 / 中 / 低** 档位间接区分能力与成本；用户明确 **不要** 再给这类 Agent 加独立 think 协议适配。
- Pi 路径当前只有厂商 + 模型，**没有**高中低，也 **没有** thinking 控件；内置 Pi（`@earendil-works/pi-coding-agent`）CLI 已支持 `--thinking <level>`，Foundry `pi_runtime` 未传该参数。

## 工程理解

本需求是 **Pi 调用底层 LLM 时的 thinking 档位配置**，不是 Agent 工具（沙箱 / 权限 / YOLO）能力。

- 配置权威：`agents.instances.<id>`（与现有同事配置条一致）。
- 生效面：仅当该实例实际走 **嵌入式 Pi** 发起模型请求时，向 Pi argv 追加 `--thinking <level>`。
- 非生效面：Codex / Cursor 原生（继续只用模型高中低）；Hermes；Host `chat_text_completion` 直连（含 Pi 失败后的 Host fallback、enrich、prompt craft 等）— **本期一律不传** 厂商私有 reasoning 参数。

## 目标

1. 在 **Pi 同事配置条**上提供与「高中低」同级的 **Thinking 多档控件**（关 / 低 / 中 / 高）。
2. 档位持久化到同事实例；对话内修改只写该实例，不回写 Agent 工具预设。
3. 所有经 `pi_runtime` 拉起的 Pi 文本调用（含策划 brief Pi 路径、IT Pi、其它选用 Pi 的实例）读取该实例档位并传入 `--thinking`。
4. 默认行为与今日一致：未配置或显式「关」→ `--thinking off`（或等价不启用思考）。

## 非目标

- 不在聊天 UI 展示 thinking / reasoning 正文。
- 不改 Codex / Cursor 高中低模型档位语义；不为它们新增 thinking 开关。
- 不为本期 Host / OpenRouter / DeepSeek 等直连 `chat/completions` 适配 `reasoning_effort`、`thinking.budget_tokens` 等厂商参数。
- 不上游扩展 Pi 的 `minimal` / `xhigh` / `max` 档（CLI 支持，产品本期不暴露）。
- 不把 thinking 档位做成 Agent 全局预设（`agents.executors.pi`）的必填项；允许雇人表单预填，但不要求设置页 Agent 大改。

## 当前架构约束

- 同事配置：`gui/src/components/ColleagueConfigBar.tsx`；Pi 分支为 Provider + `ModelCatalogPicker`；高中低仅 `useNativeModelUi`（Codex/Cursor 非第三方）。
- 实例模型：`gui/src/settings/agentInstances.ts` → `agents.instances`。
- Pi 启动：`cli/pi_runtime.py` 组装 `--provider` / `--model`，无 `--thinking`。
- 上游 Pi：`--thinking` 合法值含 `off, minimal, low, medium, high, xhigh, max`；亦支持 `model:thinking` 速记（本期用显式 `--thinking`，避免与用户手填 model id 混淆）。
- 策划 `_call_llm`：优先 Pi，失败回落 Host `chat_text_completion`（本期回落路径 **忽略** thinking 档位）。

## 方案选择

**选定：同事实例 Thinking 四档 + 仅 Pi argv 生效。**

| 项 | 选定 |
|----|------|
| 配置位置 | `agents.instances.<id>.thinking_level` |
| 取值 | `off` \| `low` \| `medium` \| `high` |
| UI | Pi 配置条、模型选择旁；标签：关 / 低 / 中 / 高 |
| 默认 | 缺省或非法值 → `off` |
| 运行时 | `pi_runtime` 在 cmd 中加入 `--thinking <level>` |
| Host 直连 | 不读该字段 |

## 被排除方案

- Host 全局 `host.enable_thinking`：与「挂实例、对齐同事配置条」不符。
- 仅布尔开关：用户明确要多档（方案 3）。
- Host 直连同步传参（Grill 方案 1）：厂商参数碎片化，本期排除（用户选 2）。
- 给 Codex/Cursor 再加 Think：与「Agent 已用高中低区分」冲突。

## 边界与失败模式

- 模型本身不支持 thinking：Pi 可能忽略或报错；产品侧仍允许选择档位；失败时沿用现有 Pi 错误 / Host fallback 行为，**不**因 thinking 单独发明新 fallback 策略。
- 实例 `executor !== "pi"`（含原生 Codex/Cursor）：UI **不展示** Thinking 档；即便 config 残留字段，Pi 未启动则不生效。
- Codex 第三方（兼容 Provider UI）：本期 **不展示** Thinking（不走 Pi `--thinking`）；字段可保留但不驱动 Codex CLI。
- 旧配置无字段：视为 `off`，行为与现网一致。
- 不在回复中解析或渲染 `reasoning_content` 供展示（可继续仅作 content 空时的既有兜底，但不新增展示）。

## 工程代价

- GUI：`ColleagueConfigBar`（及雇人弹窗若创建 Pi 同事时需可设）读写 `thinking_level`；`agentInstances` 序列化。
- CLI：`pi_runtime` 所有组装 Pi cmd 的入口读取实例档位；鉴权解析链可附带返回 `thinking_level`。
- 测试：实例读写；argv 含 `--thinking`；默认 `off`；非 Pi 不传。
- 文档：`docs/GUI-CONFIG.md` 或 AI-HANDOFF 短述一笔（plan 阶段定）。
- 预估：中小跨模块（GUI + CLI + 测试），无迁移脚本（缺省兼容）。

## 显式假设

1. 用户说的「不影响 Agent」= 不改 Codex/Cursor/Hermes 工具行为；Pi 作为 LLM 运行时传 `--thinking` 属于 LLM 配置，在范围内。
2. 四档足够；`minimal`/`xhigh`/`max` 可后续加，不阻塞本期。
3. 雇人弹窗：Pi 工种可带 Thinking；若工期紧，对话内配置条为 P0，雇人预填可 P1（plan 拆分）。

## 领域语言

| 术语 | 含义 |
|------|------|
| Thinking 档位 | 同事实例上的 `thinking_level` |
| Pi 路径 | 嵌入式 Pi CLI 发起的模型调用 |
| 高中低 | Codex/Cursor **模型**档位，与 Thinking 档位无关 |
| Host 直连 | `chat_text_completion` / OpenAI 兼容 HTTP，不经 Pi |

## 功能需求

1. **FR1** 当同事实例执行器为 `pi` 时，配置条显示 Thinking 四档（关/低/中/高），交互形态对齐现有高中低按钮组。
2. **FR2** 选择后立即持久化到 `agents.instances.<id>.thinking_level`。
3. **FR3** `pi_runtime` 启动 Pi 时传入 `--thinking`，映射：`off|low|medium|high` 原样传递。
4. **FR4** 缺省 / 未知值按 `off` 处理。
5. **FR5** 非 Pi 执行器不展示该控件；Codex/Cursor 高中低行为不变。
6. **FR6** Host 直连路径不读取、不转发 `thinking_level`。

## 非功能需求

- 不增加密钥或把 key 写入 argv。
- 配置变更与现有同事条相同：本地 config 即时保存，无额外网络。
- 中文 UI 标签；存储值为英文枚举。

## 安全关注点

- Thinking 仅影响模型推理强度与费用/延迟，不扩展工具权限。
- 继续禁止 API key 进入 argv（维持 env 注入）。
- 无新 PII 面。

## 成功标准

1. Pi 同事可在配置条切换关/低/中/高，刷新后仍保持。
2. 对应 Pi 进程 argv 含正确 `--thinking`。
3. Codex/Cursor 同事配置条无 Thinking 控件，高中低仍可用。
4. 关闭或未配置时，行为与改动前一致（等价 `off`）。
5. 单元/集成测试覆盖映射与默认值。

## PR Review 关注点

- 是否误把 thinking 传进 Host `chat_text_completion`。
- 是否误改 Codex/Cursor 档位逻辑。
- 所有 Pi cmd 组装点是否都带上 `--thinking`（smoke / brief / tools 等多入口）。
- 序列化是否污染非 Pi 实例或回写 Agent 预设。

## 开放问题

（无阻塞项）

| 项 | 归属 | 触发 | 延期原因 |
|----|------|------|----------|
| Host 直连厂商 thinking 参数适配 | 后续需求 | 用户明确要求直连也开 think | Grill 已选仅 Pi |
| Pi `minimal`/`xhigh`/`max` UI | 产品增强 | 需要更细费用控制 | 本期四档足够 |
| Agent 预设 `executors.pi.thinking_level` | UX | 雇人希望全局默认 | 非必须；实例缺省 `off` 可接受 |
| Codex 第三方是否共用 Thinking UI | 产品 | 第三方也走可 thinking 模型 | 本期不经 Pi argv，暂不展示 |
