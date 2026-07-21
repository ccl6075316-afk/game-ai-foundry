# 工程 Spec：执行器模型档位与目录切换（A）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-21
- **Updated**：2026-07-21（用户书面 Spec「确认」）
- **Source Of Truth Until**：实现以 [`docs/superpowers/plans/2026-07-21-executor-model-tiers.md`](../plans/2026-07-21-executor-model-tiers.md) 为准
- **Confirmed By**：用户「确认」（2026-07-21）
- **Change Log**：初稿 — 方案 A（档位 + 执行器模型目录；Codex/Cursor 登录态隐藏 Provider）
- **Requirements Source**：用户选择「先 A 后 B」；Codex/Cursor 需切换具体型号（如 5.5 / auto / opus）；UI 选项 1（隐藏厂商）
- **Background Inputs**：现有 `ColleagueConfigBar`、`agents.instances`、Hermes 已传 `-m`；Codex/Cursor 几乎不传 Foundry model
- **Deferred**：**B** Agent 权限批准 UI → 见 [`2026-07-21-pi-tool-permission-ui-design.md`](./2026-07-21-pi-tool-permission-ui-design.md)（Pi 变更工具 GUI 批准，v1）

## 背景

聊天配置条已有自由文本「模型」与 Provider 选择，但对 **Codex / Cursor 本机登录** 不合适：厂商账号库与订阅模型不是一套概念；且 CLI 侧未稳定吃到实例 `model`。用户要：

1. **档位**（高 / 中 / 低）一键落到默认模型  
2. **目录切换**到该执行器具体型号（Codex `gpt-5.3` / `gpt-5.5`…；Cursor `auto` / `opus` / `grok-…`）  
3. 登录态 **不显示「厂商 Provider」**

## 目标

1. 按执行器切换配置条形态（见下表）。  
2. 档位与目录选择均**持久写入** `agents.instances.<id>.model`（与现有权威一致）。  
3. Codex / Cursor 回合把该 `model` **传入 CLI**（与 Hermes `-m` 对齐意图）。  
4. Pi / Hermes / Codex「第三方」路径行为不回退。

## 非目标

- B：GUI 内批准/拒绝 Agent 工具权限。  
- 运行时向官方 API **动态拉取**模型列表（首期用静态目录）。  
- 为每个档位复制 API Key 或改 `provider_accounts`。  
- Cursor 第三方 Key（既有 v1 不做约定不变）。

## UI 形态（选项 1）

| 执行器状态 | 显示 | 隐藏 |
|------------|------|------|
| `pi` / `hermes` | Provider + 模型（文本或后续同构目录，首期可保留文本） | — |
| `codex` + **未**开第三方 | **档位** + **Codex 模型下拉** | Provider |
| `codex` + 第三方 | Provider + 模型（沿用账号库） | 档位目录可降为辅助或隐藏 |
| `cursor` | **档位** + **Cursor 模型下拉** | Provider |

交互：

- 点档位 → 写入该执行器档位对应的默认 `model`，下拉同步选中。  
- 改下拉 → 写入具体 `model`；若与某档位默认一致则高亮该档，否则档位显示为「自定义」或不选中。  
- 仍允许「高级 / 自定义」：下拉最后一项或旁路输入任意 ID（避免目录滞后卡死）。

## 数据与权威

- **权威**：`~/.gamefactory/config.json` → `agents.instances.<id>.model`（及既有 `executor` / `provider` / `use_third_party`）。  
- **档位本身不落盘**（可由 model 反推）；可选在 instance 上存 `model_tier: high|mid|low|custom` 便于 UI，非 CLI 必需。推荐首期 **只存 model**，UI 反推档位。  
- Agent · 执行器预设（`agents.executors.*`）继续作雇人/无实例时的默认；保存 Pi 预设同步实例的既有逻辑不变。

## 静态模型目录

位置建议：`gui/src/settings/executorModels.ts`（纯常量 + 小函数）。

结构示例：

```ts
type ModelTier = { high: string; mid: string; low: string };
type ExecutorModelCatalog = {
  tiers: ModelTier;
  options: Array<{ id: string; label: string }>;
};
```

- `codex` / `cursor` 各一份 `options` + `tiers`。  
- ID 以当前官方 CLI 可识别字符串为准；标签可中英短名。  
- 注释写明「随上游更新手改」；不在首期做自动同步。

## CLI 接线

| 执行器 | 现状 | 目标 |
|--------|------|------|
| Hermes | 已有 `-m` | 保持 |
| Pi | 已有 `--model` | 保持 |
| Codex | `run_codex_turn` 基本不传 model | 从 `resolved_auth.model` 传入（如 `codex exec -m …` / 文档确认的等价 flag） |
| Cursor | 基本不传 | 从 `resolved_auth.model` 传入 Agent CLI 支持的 model 参数 |

若某 CLI 版本不支持 flag：失败信息可读，并回退为「仅写 config、本轮未应用」的明确文案（不静默忽略）。

## 错误与边界

| 场景 | 期望 |
|------|------|
| 目录无匹配、用户选自定义 | 允许任意字符串写入 model |
| Codex 第三方开启 | 恢复 Provider UI；model 仍可手填/目录（第三方 slug） |
| 实例无 model | 用该执行器 `tiers.mid` 或 executors 预设 |
| 旧配置只有 OpenRouter provider + 空 model | Codex/Cursor 登录态忽略 Provider 展示，用 mid 默认 |

## 测试

- GUI：切换 Codex 登录态隐藏 Provider；选档位/型号后 config 中 instance.model 正确。  
- CLI 单测：mock `resolved_auth.model` 时 Codex/Cursor argv 含对应参数。  
- 回归：Pi/Hermes/Codex 第三方路径不破。

## 实施顺序（本 Spec 范围）

1. `executorModels.ts` 目录 + 档位映射  
2. `ColleagueConfigBar` 条件 UI  
3. `agent_turn` Codex/Cursor 传 model  
4. 单测 + 轻量文档一句（HOST-CHAT / GUI-CONFIG）

## 后续（B，非本 Spec）

Agent 工具权限在 GUI 内批准 — 依赖各执行器是否暴露可桥接的审批通道；另开 Spec。

## 相关路径

- `gui/src/components/ColleagueConfigBar.tsx`  
- `gui/src/settings/agentInstances.ts`  
- `cli/agent_turn.py`（`run_codex_turn` / Cursor）  
- `cli/agent_auth_resolve.py`
