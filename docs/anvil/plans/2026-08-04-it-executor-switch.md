# IT 可切换执行器（Pi → Codex / 第三方 LLM）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 **IT** 工种可从内置 Pi 切到 Codex（含第三方模型 sync），Pi 仍作开箱默认与装机员；**策划 brief 继续锁 Pi**。

**Architecture:** 今日阻塞几乎全是「Pi 锁定」策略，不是缺 Codex 回合路径。`agent turn` 已支持 IT + `executor=codex|hermes|cursor`；解锁后 GUI 顶栏/雇人即可选执行器，Codex 用原生工具跑 `python gamefactory.py …`，不再走 `FOUNDRY_TOOL`。Pi 实例保留 `FOUNDRY_TOOL` 白名单做简单运维。

**Tech Stack:** Python CLI（`agents_instances_upsert` / `agent_turn` / `executor_setup`）、GUI React（`hireColleague` / `ColleagueConfigBar` / `HireColleagueModal`）、Codex CLI + `use_third_party`/`sync_api`。

**Confirmed by user (2026-08-04):**  
- IT：简单题留 Pi；重排查切 Codex；Pi 负责装 CLI / 同步第三方。  
- 策划：不上 Codex CLI（改动大、吃的是 LLM 能力不是工具环）。  
- 本计划范围 = **IT 能切执行器/LLM**；不含策划解锁、不含 Pi 原生工具环大改。

## Global Constraints

- `brief` **保持** Pi 锁定（`isPiLockedRole` / `_PI_LOCKED` 仅剩 `brief`）。
- 新雇 IT **默认仍为 `pi`**（开箱只配 Key）；Codex 为可选升级，非强制。
- Codex 第三方：须 `use_third_party=true` + `setup executor step codex sync_api`（或 GUI 保存时已有 sync）；不偷偷改用户 ChatGPT 订阅态。
- IT + Codex **不**注入 `FOUNDRY_TOOL` 协议；skill 指引用仓库内 `cli/gamefactory.py`。
- 不改权限产品语义：Codex sandbox 走现有实例/执行器安全字段。
- 提交前跑相关单测；不 force-push；不改 git config。

## 文件地图

| 文件 | 职责 |
|------|------|
| `cli/agents_instances_upsert.py` | CLI 写入实例时解除 IT 的 Pi 锁 |
| `gui/src/settings/hireColleague.ts` | `isPiLockedRole` 仅 brief；雇人校验 |
| `gui/src/settings/agentInstances.ts` | IT 默认执行器仍可 pi；允许读回非 pi |
| `gui/src/components/ColleagueConfigBar.tsx` | 解锁后已有执行器下拉（验证/微调文案） |
| `gui/src/components/HireColleagueModal.tsx` | 雇 IT 可选 Codex + 第三方 |
| `resources/skills/it/diagnose.md` | Pi 装机员 vs Codex 排查分工 + 切执行器剧本 |
| `cli/agent_turn.py` | IT 非 Pi 时 prompt 追加「用 gamefactory CLI」硬约束 |
| `docs/AGENT-ROUTING.md` / `docs/TOOLS.md` | 文档：IT 可切执行器 |
| `cli/test_agents_instances_upsert.py` 等 | 回归 |

---

### Task 1: CLI — IT 允许非 Pi 执行器

**Files:**
- Modify: `cli/agents_instances_upsert.py`
- Modify: `cli/test_agents_instances_upsert.py`（或新建断言）

**Interfaces:**
- Consumes: `upsert_agent_instance(..., executor=...)`
- Produces: `role_kind=it` + `executor=codex` 写入成功；`brief` 仍拒绝非 pi

- [ ] **Step 1: 写失败测试**

在 `cli/test_agents_instances_upsert.py` 增加：

```python
def test_it_can_switch_to_codex(self) -> None:
    # 预备：config 里已有 it 实例 id
    result = upsert_agent_instance(
        config_path,
        instance_id=it_id,
        executor="codex",
        use_third_party=True,
    )
    self.assertTrue(result["ok"], result)
    entry = load_config()["agents"]["instances"][it_id]
    self.assertEqual(entry["executor"], "codex")
    self.assertTrue(entry["use_third_party"])

def test_brief_still_locked_to_pi(self) -> None:
    result = upsert_agent_instance(
        config_path,
        instance_id=brief_id,
        executor="codex",
    )
    self.assertFalse(result["ok"])
    self.assertIn("Pi", result.get("error") or "")
```

- [ ] **Step 2: 跑测确认失败**

```bash
cd cli && python -m unittest test_agents_instances_upsert -v
```

Expected: IT→codex 相关断言 FAIL（仍被 `_PI_LOCKED` 拦住）。

- [ ] **Step 3: 最小实现**

```python
# agents_instances_upsert.py
_PI_LOCKED = frozenset({"brief"})  # was {"brief", "it"}
```

错误文案可改为仅针对 brief：`策划固定使用内置 Pi…`。

- [ ] **Step 4: 再跑测**

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add cli/agents_instances_upsert.py cli/test_agents_instances_upsert.py
git commit -m "$(cat <<'EOF'
feat: allow IT instances to switch off embedded Pi

Keep brief Pi-locked; IT may use codex/hermes/cursor via instances upsert.
EOF
)"
```

---

### Task 2: GUI — 解锁 IT 雇佣与顶栏执行器

**Files:**
- Modify: `gui/src/settings/hireColleague.ts`
- Modify: `gui/src/components/HireColleagueModal.tsx`（若文案写死「IT 只能 Pi」则改）
- Modify: `gui/src/components/ColleagueConfigBar.tsx`（确认 `!piLocked` 分支对 IT 可用；必要时补一句说明）
- Test: 若有现成 TS 测则加；否则手工验收清单写入本 Task 验证节

**Interfaces:**
- Consumes: `isPiLockedRole(roleKind)`
- Produces: `isPiLockedRole("it") === false`；`isPiLockedRole("brief") === true`；雇 IT 可选 `codex` 且可勾 `use_third_party`

- [ ] **Step 1: 改锁定函数**

```typescript
// hireColleague.ts
export function isPiLockedRole(roleKind: ChatAgentRole): boolean {
  return roleKind === "brief";
}
```

同步检查：

- `defaultExecutorForHire("it", …)` → 仍默认 `"pi"`（开箱），不要默认成 codex。
- `validateHireForm`：IT 非锁后走「须选执行器」分支；若雇人表单允许保留 pi，把 `pi` 纳入 IT 可选执行器列表（顶栏已有 `executor === "pi" ? "" : executor` 模式——雇人 modal 需能选 Pi **或** Codex）。

- [ ] **Step 2: 雇人 modal — IT 执行器选项**

确保 IT 雇佣可选：`pi | hermes | codex | cursor`（至少 `pi` + `codex`）。  
选 `codex` 时展示「用第三方」开关（现有 `!piLocked && form.executor === "codex"` 即可亮起）。

若 `HIRE_AGENT_EXECUTORS` 不含 `pi`，为 IT 增加分支：

```typescript
// 伪代码：IT 可选含 pi
const executorsForRole =
  roleKind === "it" ? (["pi", "hermes", "codex", "cursor"] as const) : HIRE_AGENT_EXECUTORS;
```

- [ ] **Step 3: 顶栏 ColleagueConfigBar**

解锁后执行器下拉应对 IT 可见。核对保存路径调用 `agents instances upsert` 且 Codex + 第三方时触发 `executorStep("codex", "sync_api")`（文件内已有 `syncCodexApi`——确认 `piLocked` 去掉后仍走）。

- [ ] **Step 4: 手工 / 脚本冒烟**

```bash
# 若有 gui 单测框架则跑相关；否则：
cd gui && npx tsc --noEmit  # 或项目既有 typecheck
```

手测：花名册选 IT → 顶栏执行器改为 Codex → 勾第三方 → 保存 → `~/.gamefactory/config.json` 中该实例 `executor=codex`。

- [ ] **Step 5: Commit**

```bash
git add gui/src/settings/hireColleague.ts gui/src/components/HireColleagueModal.tsx gui/src/components/ColleagueConfigBar.tsx
git commit -m "$(cat <<'EOF'
feat: unlock IT hire/config bar to pick Codex or other executors

Brief remains Pi-only; IT defaults to Pi for onboarding.
EOF
)"
```

---

### Task 3: Codex 路径 — IT skill + agent prompt 分工

**Files:**
- Modify: `resources/skills/it/diagnose.md`
- Modify: `cli/agent_turn.py`（`build_prompt` 在 `role_kind=="it"` 且非 pi 时追加约束）
- Test: `cli/test_agent_turn.py` 对 prompt 片段断言（可 mock session）

**Interfaces:**
- Consumes: `build_prompt(role_kind="it", …)`；`resolve_executor` / 调用方传入的 executor 若不便传入，可在 `run_agent_turn` 里根据已解析 executor 往 user/system 追加一段（二选一，优先改 `build_prompt` 增加可选 `executor=`）。
- Produces: Codex IT 知道用 `cd cli && python gamefactory.py …`；Pi IT 仍用 FOUNDRY_TOOL 剧本

- [ ] **Step 1: 更新 diagnose.md 开篇与速查表**

加入明确分工（中文）：

```markdown
## 执行器怎么选

| 执行器 | 何时用 |
|--------|--------|
| **Pi（默认）** | 开箱、doctor/setup、装 Codex/Hermes、简单白名单运维 |
| **Codex** | 根因排查、对照会话/代码、「只说不写」类诊断、需要强读写与推理时 |
| Hermes/Cursor | 用户已偏好时可选 |

**切到 Codex 前（可用 Pi 完成）：**
1. `setup executor step codex install_cli --i-confirm --json`
2. 实例 `use_third_party=true`（第三方模型）→ `setup executor step codex sync_api --i-confirm --json`
3. GUI 顶栏把本 IT 同事执行器改为 Codex 并保存

**Codex 模式下：** 不要输出 `<<<FOUNDRY_TOOL`；在仓库根用 shell 调：
`python cli/gamefactory.py …`（或 `cd cli && python gamefactory.py …`）。
优先：`conversations show`、`inspect`、`doctor`、读 `cli/host_chat.py`。
用户说「只说不写」时：先读 brief 会话找「落盘/只说/补丁」，**禁止**默认答成「策划不写工程」。
```

- [ ] **Step 2: build_prompt 追加（IT + 非 pi）**

```python
# agent_turn.build_prompt — 增加参数 executor: str | None = None
if role_kind == "it" and executor and executor != "pi":
    parts.extend([
        "",
        "## 本实例执行器约束",
        f"当前 executor={executor}（非内置 Pi）。",
        "禁止输出 FOUNDRY_TOOL 栅栏。",
        "需要 CLI 时在仓库根执行: python cli/gamefactory.py <subcommand> …",
        "查策划「只说不写」：先 conversations show --role brief，再下结论。",
    ])
```

调用 `build_prompt` 处传入已解析的 `executor`。

- [ ] **Step 3: 单测**

```python
def test_it_codex_prompt_forbids_foundry_tool_fence(self) -> None:
    text = build_prompt(
        role_kind="it",
        user_message="查只说不写",
        session={"messages": []},
        executor="codex",
    )
    self.assertIn("禁止输出 FOUNDRY_TOOL", text)
    self.assertIn("gamefactory.py", text)
```

- [ ] **Step 4: 跑测**

```bash
cd cli && python -m unittest test_agent_turn.HostChatTests 2>/dev/null; python -m unittest test_agent_turn -q
```

（按实际测试类名调整。）Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add resources/skills/it/diagnose.md cli/agent_turn.py cli/test_agent_turn.py
git commit -m "$(cat <<'EOF'
docs(it): split Pi bootstrap vs Codex diagnosis; prompt non-Pi IT

Teach Codex IT to use gamefactory CLI and avoid FOUNDRY_TOOL fences.
EOF
)"
```

---

### Task 4: 文档与验收剧本

**Files:**
- Modify: `docs/AGENT-ROUTING.md`（IT 行：默认 Pi，可切 Codex）
- Modify: `docs/TOOLS.md`（§ 执行器：IT 解锁说明一句）
- Optional: `docs/anvil/brainstorms/2026-08-04-it-executor-switch.md` 一页确认记录（若团队要 Anvil 痕迹）

- [ ] **Step 1: 改 AGENT-ROUTING IT 表行**

写明：默认内置 Pi；实例可改 `codex`/`hermes`/`cursor`；策划仍仅 Pi。

- [ ] **Step 2: 端到端手工验收清单（写入 PR / 本计划底部打勾）**

1. 仅配 API Key → IT(Pi) 能 `doctor`。  
2. 对 IT(Pi) 说「帮我装 Codex CLI」→ 走到 `install_cli`（或指引 GUI 环境步进）。  
3. 顶栏切 Codex + 第三方 → sync_api 成功。  
4. 新开 IT 会话问：「策划这个确实又踩了只说不写，是代码原因吗」→ 应去读 brief 会话/host_chat，**不应**只答职责路由/Godot。  
5. 策划顶栏仍无 Codex 执行器切换。

- [ ] **Step 3: Commit**

```bash
git add docs/AGENT-ROUTING.md docs/TOOLS.md
git commit -m "$(cat <<'EOF'
docs: IT may switch executors; brief stays on embedded Pi
EOF
)"
```

---

## 任务依赖（DAG）

```text
Task1 (CLI unlock) ──┬──> Task2 (GUI unlock) ──> Task4 (docs + E2E)
                     └──> Task3 (skill/prompt) ──┘
```

Task1 ∥ 可先做；Task2 依赖 Task1 的语义一致；Task3 可与 Task2 并行；Task4 最后。

## 非目标（本计划不做）

- 策划切 Codex / 解除 brief Pi 锁  
- 把 Pi 改成原生 read/bash 工具环  
- 强制所有 IT 默认 Codex  
- 为 Codex 重做 FOUNDRY_TOOL 桥

## 风险

| 风险 | 缓解 |
|------|------|
| 用户切 Codex 但未 install/sync | GUI sync 失败提示；skill 要求先 Pi 装机 |
| Codex sandbox 读不到仓库外 | IT 工作目录保持仓库根；sandbox=workspace-write |
| 模型仍答歪 | Task3 硬约束 + 验收句「只说不写」回归 |
| 与未提交的「只说不写」宿主门闩混在一起 | 门闩属 brief/host_chat，**分开 commit**；本计划不依赖它落地 |

## 历史决策锚点

- Pi 内置开箱：`docs/superpowers/specs/2026-07-20-executor-storage-it-design.md`
- IT 家庭运维 / 信任会话：`docs/superpowers/specs/2026-07-29-it-expanded-home-ops-design.md`
- Codex 第三方 sync：`cli/executor_setup.py` `configure_codex_api`

---

## Self-review

- [x] Spec 覆盖：解锁 CLI/GUI、默认 Pi、Codex 第三方、skill 分工、brief 仍锁、验收句  
- [x] 无 TBD 占位  
- [x] `_PI_LOCKED` / `isPiLockedRole` 命名前后一致  

**镜像路径：** 同文亦可在 `docs/superpowers/plans/2026-08-04-it-executor-switch.md` 留拷贝供 superpowers 执行器发现（本仓 Anvil 权威路径如下）。
