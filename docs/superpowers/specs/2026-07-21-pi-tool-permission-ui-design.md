# 工程 Spec：Pi 变更工具 GUI 批准 UI（Feature B v1）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：implement
- **Created**：2026-07-21
- **Updated**：2026-07-21（用户「实现吧」）
- **Source Of Truth Until**：实现以 [`docs/superpowers/plans/2026-07-21-pi-tool-permission-ui.md`](../plans/2026-07-21-pi-tool-permission-ui.md) 为准
- **Confirmed By**：用户「确认」（2026-07-21）；用户「实现吧」（2026-07-21）
- **Change Log**：初稿 — 方案 A；实现：loopback HTTP bridge + CLI gate + 内联卡片
- **Requirements Source**：模型档位 Spec 延后的 B；用户选型：变更类 only / 全部 Pi 角色 / 内联卡片 / 范围可选（一次·本回合·本会话）/ 架构 A
- **Background Inputs**：`cli/pi_foundry_tools.py`（`_MUTATE_PREFIXES`、`--i-confirm`）、`run_pi_agent_turn`、GUI one-shot `agent-turn` IPC；探查结论：Hermes/Cursor YOLO·force，Codex 仅静态沙箱
- **Deferred**：Hermes / Codex / Cursor 工具级审批；永久放权；只读工具弹窗；通用流式 Agent 协议

## 背景

GUI Agent 回合今日是 **一次性阻塞子进程**（`agent turn` → 等完整回复）。Hermes / Cursor 启动即 `--yolo` / `--force`；Codex 仅 `--sandbox workspace-write`。三者均 **无** 可桥接的 mid-turn 审批通道。

内置 Pi 关闭原生工具，改由 Foundry `FOUNDRY_TOOL` 白名单执行；变更类要求 argv 含 `--i-confirm`（模型在对话里「确认」后自带），**不是** GUI 按钮。用户要在应用内明确批准/拒绝写盘与配置变更。

## 目标

1. 凡走 **Pi** 的角色（IT、策划 brief、以及日后默认/选用 Pi 的岗），对 **变更类** `FOUNDRY_TOOL` 在执行前挂起，经 GUI **内联卡片** 取得用户决定后再跑。  
2. 卡片提供：`允许一次` | `本回合允许` | `本会话允许` | `拒绝`。  
3. 允许路径：注入或保留 `--i-confirm` 后执行白名单命令。  
4. 拒绝 / 超时：不执行该工具；把结果写回工具环，回合不崩，模型可继续回复。  
5. 只读白名单工具（status / validate 等）**不**弹批准。

## 非目标

- Hermes / Codex / Cursor 的通用工具级 approve/deny（仍维持现有 auto / 沙箱；待上游可机读审批通道另开 Spec）。  
- **永久**放权或设置页「永远允许所有变更」。  
- 只读工具弹窗。  
- 用假安全方式去掉 `--yolo`/`--force` 却仍 `capture_output`（会挂死）。  
- 把整产品改成通用流式多执行器 Agent 协议（v1 **只**把 Pi 工具环改成可续跑）。

## 架构（方案 A）

Electron **分步驱动** Pi 工具环，而不是一次 `subprocess.run` 跑完整 `agent turn`。

```text
用户发消息
  → Electron 启动可续跑的 Pi 回合
  → 模型输出 / 提出 FOUNDRY_TOOL
  → 只读：立即执行，结果回灌
  → 变更类：挂起 → IPC → GUI 内联卡片
  → 用户决定 → Electron 续跑工具环
  → 回合结束或下一工具再门闩
```

推荐边界：

| 层 | 职责 |
|----|------|
| `pi_foundry_tools` / `pi_runtime` | 识别变更类；执行前调用「审批回调」；拒绝时合成工具结果 |
| Electron `main` | 持有回合状态机；`permissionId`；超时；会话记忆；IPC |
| GUI React | 渲染内联卡片；回传决定；更新卡片终态 |

CLI 可另暴露同语义的续跑入口以便单测，但 **v1 产品路径以 Electron IPC 为主**（不必先做完整 JSONL stdin 协议；那是方案 B，可后补）。

## 变更类判定

与现有 `_MUTATE_PREFIXES` + 「argv 须含 `--i-confirm`」对齐：

- 命中变更前缀 → **必须**经 GUI 批准（即使模型已写了 `--i-confirm`，也不得静默执行）。  
- 未命中 → 不弹卡片，照旧白名单执行。  
- 批准后：确保执行 argv 满足 CLI 对 `--i-confirm` 的要求（注入或保留）；对外展示可打码 API Key 等敏感参数。

若后续新增变更前缀，同一门闩自动覆盖（不单独开 Spec，除非语义变化）。

## UI：内联卡片

出现在对应同事的消息流中（与「执行器运行中…」同一会话上下文）。

| 元素 | 内容 |
|------|------|
| 标题 | 需要批准的变更 |
| 摘要 | 角色展示名、命令一行摘要、短风险说明 |
| 操作 | `允许一次` / `本回合允许` / `本会话允许` / `拒绝` |
| 终态 | 已允许（注明范围）/ 已拒绝 / 已超时 — **不可再点** |

等待期间继续显示现有「仍在运行 Ns」类计时。

## 范围记忆

| 选择 | 语义 |
|------|------|
| 允许一次 | 仅当前这条工具 |
| 本回合允许 | 同一用户消息触发的 Pi 回合内，后续变更类不再询问 |
| 本会话允许 | 同一 chat `sessionId`（或等价会话键）内有效；**关 App / 新会话清空** |
| 拒绝 | 本工具不执行；不改变已有记忆 |

不做永久记忆。设置页全局开关不在 v1。

## 超时

- 默认 **300s（5 分钟）** 无操作 → **自动拒绝**，卡片标注超时。  
- 超时与拒绝一样：工具不执行，结果回灌，回合可继续或结束（由工具环/模型决定）。

## IPC / 状态（示意）

具体方法名实现时可微调，语义固定：

1. GUI/主进程发起可续跑 Pi 回合（携带 `role`、`sessionId`、`instanceId`、`message`）。  
2. 主进程 → 渲染进程：`agent-tool-permission`（`permissionId`, 摘要, `sessionId`, …）。  
3. 渲染进程 → 主进程：`agent-tool-permission-decision`（`permissionId`, `decision`: `once` \| `turn` \| `session` \| `deny`）。  
4. 进度/日志仍可走现有 `pipeline-log` 类通道；批准事件 **不得** 仅写日志而不阻塞执行。

## 成功标准

1. Pi 角色变更工具未经批准（含超时）**不会**落到真实写盘/改配置。  
2. 批准后行为与今日带 `--i-confirm` 的白名单执行一致。  
3. 拒绝/超时后 UI 与模型侧均有明确结果；进程不挂死。  
4. 本回合 / 本会话记忆符合上表；重启 App 后会话记忆不残留。  
5. Hermes / Codex / Cursor 路径行为不因本 Spec 回退或「假变严」。

## 测试要点

- 单元：变更类挂起回调；一次/回合/会话记忆；超时 → deny；拒绝结果字符串稳定。  
- 集成/冒烟：mock 审批回调跑完一轮 IT 变更工具（批准与拒绝各一）。  
- GUI：卡片四按钮与终态（可用轻量脚本或组件测；全 Electron E2E 可选）。

## 后续（非本 Spec）

- Spike：Codex / Cursor / Hermes 是否暴露可机读 permission prompt → 另开 Feature B v2。  
- 可选配置：Codex `--sandbox` 档位、Hermes 谨慎模式（去掉 `--yolo`）— 属配置层，不是交互审批。  
- 方案 B：CLI JSONL + stdin 对称协议，便于无 GUI 调试。

## 与相关 Spec 的关系

- 承接 [`2026-07-21-executor-model-tiers-design.md`](./2026-07-21-executor-model-tiers-design.md) 中 Deferred 的 **B**。  
- 建立在 [`2026-07-20-executor-storage-it-design.md`](./2026-07-20-executor-storage-it-design.md) 的 Pi + `FOUNDRY_TOOL` 结论之上，不改变「Pi 不管 pipeline」边界。
