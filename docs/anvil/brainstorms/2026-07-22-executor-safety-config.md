# 工程 Spec：Feature B v2 — 执行器安全配置旋钮

## 执行元数据

- **Status**：implemented
- **Workflow Stage**：code
- **Created**：2026-07-22
- **Updated**：2026-07-22
- **Source Of Truth Until**：落地后以 CLI/GUI 为准
- **Confirmed By**：user「开始吧」（2026-07-22）— 接受交接文档推荐默认（Spike 选项 1）
- **Change Log**：自 Spike / handoff 收敛为配置层；不做 ACP / app-server；code 已落地
- **Requirements Source**：[`docs/superpowers/handoffs/2026-07-22-next-ai-executor-safety-config.md`](../../superpowers/handoffs/2026-07-22-next-ai-executor-safety-config.md)；[`docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md`](../../superpowers/specs/2026-07-22-executor-permission-b2-spike.md)
- **Background Inputs**：B v1 Pi 工具权限 GUI；`cli/agent_turn.py` one-shot + capture_output
- **Compounded Knowledge**：not yet compounded

## 工程理解

Foundry 对 Hermes/Codex/Cursor 走 **one-shot CLI + `capture_output`**，无法做 mid-turn 审批。B v2 只提供 **静态安全旋钮**，写入 `agents.executors.*`，由 `agent_turn` 组装 argv。硬约束：禁止「去掉 `--yolo`/`--force` 却仍阻塞等待 TTY」。

## 目标

1. **Codex**：`agents.executors.codex.sandbox` ∈ `read-only` | `workspace-write`（默认）| `danger-full-access` → `codex exec --sandbox <value>`  
2. **Cursor**：`agents.executors.cursor.permission_mode` ∈ `force`（默认）| `auto_review` | `plan` | `ask`  
   - `force` → `--force`  
   - `auto_review` → `--auto-review`，无 `--force`  
   - `plan` / `ask` → `--mode plan|ask`，无 `--force`  
3. **Hermes**：`agents.executors.hermes.yolo` 默认 `true` → 保留 `--yolo`；`false` → **拒绝开跑**并抛错（文案说明未接 ACP 前 GUI/CLI 不可关 yolo），**不**静默去掉 flag 后仍 `capture_output`  
4. GUI：**设置 → Agent** 对应卡片增加控件；保存进 `agents.executors`  
5. 默认与今日行为兼容；Pi B v1 回归绿

## 非目标

- Hermes/Cursor ACP mid-turn 审批卡  
- Codex app-server  
- 实例级覆盖（本版仅 `agents.executors`；实例覆盖可后续）  
- 永久「一律允许」  
- 改 Pi `FOUNDRY_TOOL` 审批协议  

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| 配置缺字段 | 用默认（workspace-write / force / yolo=true） |
| 非法枚举值 | 回退默认 |
| hermes.yolo=false | `AgentTurnError`，不调 hermes 子进程 |
| cursor 未知 mode | 回退 force |

## 工程代价

- `cli/agent_turn.py` + 单测  
- GUI `agentExecutors.ts` + Settings Agent 三卡控件  
- `docs/GUI-CONFIG.md` 短更  
- 可选镜像：`docs/superpowers/specs/2026-07-22-executor-safety-config-design.md`

## 验收标准

1. 单测：改 config → `run_*_turn` / `run_executor_turn` argv 含对应 flag；yolo=false 抛错且不调 `_run_cmd`  
2. 默认 argv 与改前一致（Codex sandbox workspace-write、Cursor --force、Hermes --yolo）  
3. `python -m unittest test_tool_permission test_pi_foundry_tools test_agent_turn -q` 绿  
4. `npx tsc --noEmit` 绿  
5. 白名单仍无假 mid-turn  

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | Spike 选项 1；字段名 sandbox / permission_mode / yolo；关 yolo → 报错禁用 |
| 已确认 | GUI 放设置 Agent 页；本版无 instance 覆盖 |
| 已排除 | ACP、app-server、假安全 |

## Resume

- **下一步**：可选 review；用户要求时 commit/push。  
- **Deferred**：instance 覆盖；ACP 试点。
