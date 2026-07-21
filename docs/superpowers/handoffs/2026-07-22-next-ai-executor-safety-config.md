# 交接：下一台电脑 AI 要做的事（2026-07-22）

> **给另一台机器上的 Agent 读。** 用户目标：按本文实现 → 本地验证 → `commit` → `push` 到 `origin/main`（或先 feature 分支再合 main，见文末 Git 约定）。  
> **仓库**：`game-ai-foundry`（远程 `origin`，默认分支 `main`）  
> **写本文时的 HEAD**：`1def344`（Pi 工具权限 GUI / Feature B v1 已合入）

---

## 0. 一句话任务

**实现 Feature B v2「配置层安全旋钮」（Spike 选项 1）**：让 Codex / Cursor / Hermes 的沙箱与放行策略可在 GUI 配置并写入 config，且 `agent turn` 的 argv 真正吃到这些配置。  
**不要**在 one-shot `capture_output` 路径上假装做 mid-turn 审批（禁止「去掉 `--yolo`/`--force` 却仍阻塞子进程」）。

若用户改口要做选项 2（ACP 试点）或 3（Codex app-server），以 Spike 文档为准另开 Spec，**不要**与选项 1 混在同一 PR。

---

## 1. 已经做完（勿重复）

| 项 | 状态 | 关键提交 / 文档 |
|----|------|----------------|
| Electron 39 + Pi 共用 Node 22.19+ | ✅ main | `1e11f8d` |
| 执行器模型档位 A（Codex/Cursor 高中低 + CLI `-m`/`--model`） | ✅ main | `585d854` 一带 |
| Feature B v1：Pi 变更类 `FOUNDRY_TOOL` 内联批准卡 | ✅ main | `1def344` / `c3784ee` |
| B v1 Spec | ✅ | `docs/superpowers/specs/2026-07-21-pi-tool-permission-ui-design.md` |
| B v2 Spike（结论：先配置层，ACP/app-server 后置） | ✅ 待入库 | `docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md` |

B v1 行为摘要（回归时别弄坏）：

- Electron `tool_permission_bridge.mjs` 本机 HTTP + token  
- `cli/tool_permission.py` + `pi_foundry_tools` 变更前缀门闩  
- GUI `ChatView` 卡片：一次 / 本回合 / 本会话 / 拒绝；超时 300s → deny  
- 无 `GAMEFACTORY_TOOL_PERMISSION_URL` 时保持旧 `--i-confirm` CLI 行为  

冒烟（可选）：`python cli/scripts/smoke_tool_permission_bridge.py`

---

## 2. 明天要实现：B v2 选项 1（配置层）

### 2.1 必读

1. `docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md`（产品选项与硬约束）  
2. `docs/superpowers/specs/2026-07-21-pi-tool-permission-ui-design.md`（B v1 边界，勿回退）  
3. `cli/agent_turn.py`（Hermes `--yolo`、Cursor `--force`、Codex `--sandbox` 组装处）  
4. `gui/src/components/ColleagueConfigBar.tsx` / Settings 执行器相关 UI  
5. `docs/GUI-CONFIG.md`（配置字段写法对齐现有文档）

### 2.2 目标行为

| 执行器 | 可配项（建议默认） | 写入位置（建议） | `agent_turn` 行为 |
|--------|-------------------|------------------|-------------------|
| **Codex** | `sandbox`: `read-only` \| `workspace-write`（默认）\| `danger-full-access` | `agents.executors.codex.sandbox` 或 instance 覆盖 | `codex exec --sandbox <value>` |
| **Cursor** | `permission_mode`: `force`（默认，兼容现状）\| `auto_review` \| `plan` \| `ask` | `agents.executors.cursor.permission_mode`（名字可微调，文档写清） | `force`→`--force`；`auto_review`→`--auto-review` 且**不要** `--force`；`plan`/`ask`→`--mode plan\|ask` 且不要 force |
| **Hermes** | `yolo`: `true`（默认）\| `false` | `agents.executors.hermes.yolo` | `true`→保留 `--yolo`；`false`→**不要静默去掉后仍 capture**：GUI/CLI 应拒绝开跑并报错「未接 ACP 前不可在 GUI 关 yolo」，或仅允许在明确标注的实验开关下使用（Spec 里写死一种，推荐：**关 yolo → 报错禁用**） |

成功标准：

1. 改设置 → 持久化 config → 下一轮 `agent turn` argv 变化（单测断言 argv）。  
2. 默认行为与今日兼容（Codex workspace-write、Cursor force、Hermes yolo）。  
3. Pi B v1 回归：`python -m unittest test_tool_permission test_pi_foundry_tools` 仍绿。  
4. **禁止**关 yolo/force 却 `subprocess.run(capture_output=True)` 等 TTY 提示。

### 2.3 非目标（本 PR 不要做）

- Hermes/Cursor **ACP** mid-turn 审批卡（选项 2）  
- Codex **app-server**（选项 3）  
- 永久「一律允许」  
- 改 Pi 审批协议  

### 2.4 建议实现顺序（TDD）

1. **写 Spec**（短）：`docs/superpowers/specs/2026-07-22-executor-safety-config-design.md`，用户确认或按本文默认直接实现。  
2. **CLI 单测**：mock 配置 → `run_codex_turn` / `run_cursor_turn` / `run_hermes_turn` 的 argv。  
3. **改 `cli/agent_turn.py`**（及读 config 的 helpers）。  
4. **GUI**：ColleagueConfigBar 或 Settings「执行器」区增加控件；保存进 `agents.executors.*`。  
5. **文档**：`docs/GUI-CONFIG.md` 补字段。  
6. **验证** → commit → push。

### 2.5 关键代码锚点（实现时打开）

```text
cli/agent_turn.py          # 组装 hermes/codex/cursor argv
cli/test_agent_turn.py     # 已有 model 相关测例，照此加 sandbox/mode
gui/src/settings/          # executors / agentInstances 模式
gui/src/components/ColleagueConfigBar.tsx
gui/electron/main.mjs      # 一般不用为选项 1 改 permission bridge
```

---

## 3. 选项 2 / 3（仅记录，默认不做）

完整论述见 Spike。摘要：

- **选项 2**：`agent acp` / `hermes acp` 常驻 + 复用 B v1 卡片；替换 one-shot `agent turn`；工期中。  
- **选项 3**：`codex app-server`；experimental；大 Spec。  

硬约束：`exec --json` / `stream-json` ≠ 审批协议。

---

## 4. 验证清单（实现后必须跑）

```bash
cd cli
python -m unittest test_tool_permission test_pi_foundry_tools test_agent_turn -q
# 若加了新测文件：一并跑
python scripts/smoke_tool_permission_bridge.py   # B v1 回归可选

cd ../gui
npx tsc --noEmit
```

手动（有 GUI 时）：设置里改 Codex sandbox / Cursor mode → 看一次程序员回合日志里的实际 CLI 行。

---

## 5. Git 约定（用户要求 commit + push）

1. **从最新 `main` 开分支**，例如：`feat/executor-safety-config`  
2. **不要提交**：`.superpowers/`、密钥、`gui/runtime/`、本地 Electron 缓存  
3. Commit message 风格（近例）：`feat(cli): honor executor sandbox/permission mode from config`  
4. 合并：`git checkout main && git merge --no-ff feat/executor-safety-config`  
5. Push：`git push origin main`（用户已明确要 push；若策略要求 PR，则 `git push -u origin HEAD` + `gh pr create`）  
6. PowerShell 下 commit 可用：

```powershell
git commit -m @"
feat: executor safety config for Codex sandbox and Cursor/Hermes modes

Persist sandbox/permission/yolo in agents.executors and pass through agent_turn argv; refuse unsafe non-TTY yolo-off.
"@
```

---

## 6. 本机未提交、应随交接入库的文件

写本文时工作区还有（应 **commit + push**，方便另一台直接拉）：

- `docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md`  
- `cli/scripts/smoke_tool_permission_bridge.py`  
- 本文：`docs/superpowers/handoffs/2026-07-22-next-ai-executor-safety-config.md`

**不要**提交：`.superpowers/`

---

## 7. 给 Agent 的开工指令（可复制）

```text
读 docs/superpowers/handoffs/2026-07-22-next-ai-executor-safety-config.md
与 docs/superpowers/specs/2026-07-22-executor-permission-b2-spike.md。
实现 Feature B v2 选项 1（配置层安全旋钮），严格遵守硬约束。
先写/补 Spec，再 TDD 改 agent_turn + GUI，跑第 4 节验证，然后按第 5 节 commit 并 push。
不要做 ACP / app-server。不要破坏 Pi B v1 权限桥。
```

---

## 8. 变更日志

| 日期 | 说明 |
|------|------|
| 2026-07-22 | 初稿：交接 B v2 选项 1；记录 B v1 已交付与 Spike 结论 |
