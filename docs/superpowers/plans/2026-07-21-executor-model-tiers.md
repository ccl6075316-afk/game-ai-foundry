# Executor Model Tiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codex/Cursor 登录态在聊天配置条用「高/中/低 + 模型目录」切换型号，并写入 `agents.instances`、传入 CLI；Pi/Hermes/Codex 第三方不回退。

**Architecture:** 静态目录 `gui/src/settings/executorModels.ts`；`ColleagueConfigBar` 按执行器条件渲染；CLI `run_codex_turn` / `run_cursor_turn` 读取 `resolved_auth.model` 加 `-m`/`--model`。档位不单独落盘，由 model id 反推。

**Tech Stack:** TypeScript/React GUI、Python `agent_turn.py`、unittest、既有 `agents.instances` config

**Spec:** [`docs/superpowers/specs/2026-07-21-executor-model-tiers-design.md`](../specs/2026-07-21-executor-model-tiers-design.md)

## Global Constraints

- 首期只做 **A**（档位+目录+CLI 传 model）；**B 权限 UI 不做**
- Codex/Cursor **本机登录**：隐藏 Provider；**Codex 第三方**：仍显示 Provider
- 权威字段：`agents.instances.<id>.model`（不强制落盘 `model_tier`）
- 模型目录静态手维护；下拉保留「自定义」任意 ID
- Codex CLI：`codex exec -m <id>`（与 `--model` 等价）
- Cursor Agent：优先 `--model <id>`；实现时若本机 `--help` 无该 flag，报可读错误，不静默丢弃
- 不改 Electron / Pi 运行时

## File map

| File | Responsibility |
|------|----------------|
| Create `gui/src/settings/executorModels.ts` | Codex/Cursor 目录、档位、反推/解析 helper |
| Modify `gui/src/components/ColleagueConfigBar.tsx` | 条件 UI：档位按钮 + 模型 select / Provider |
| Modify `cli/agent_turn.py` | `run_codex_turn` / `run_cursor_turn` 接 `model`；`run_executor_turn` 下传 |
| Modify `cli/test_agent_turn.py` | argv 含 model 的单测 |
| Modify `docs/GUI-CONFIG.md`（或 `HOST-CHAT-PRODUCT.md`） | 一句说明聊天栏模型切换 |

---

### Task 1: `executorModels.ts` catalog + helpers

**Files:**
- Create: `gui/src/settings/executorModels.ts`
- Test: `gui/scripts/test-executor-models.mjs`（纯 JS 镜像关键逻辑 smoke；或与现有 `gui/scripts/test-*.mjs` 同风格）

**Interfaces:**
- Produces:
  - `export type ModelTier = { high: string; mid: string; low: string }`
  - `export type ExecutorModelCatalog = { tiers: ModelTier; options: Array<{ id: string; label: string }> }`
  - `export const CODEX_MODEL_CATALOG: ExecutorModelCatalog`
  - `export const CURSOR_MODEL_CATALOG: ExecutorModelCatalog`
  - `export function catalogForNativeExecutor(executor: "codex" | "cursor"): ExecutorModelCatalog`
  - `export function tierForModel(catalog: ExecutorModelCatalog, model: string): "high" | "mid" | "low" | "custom"`
  - `export function modelForTier(catalog: ExecutorModelCatalog, tier: "high" | "mid" | "low"): string`
  - `export function resolveNativeModel(catalog: ExecutorModelCatalog, savedModel: string): string` — 空则 `tiers.mid`

- [ ] **Step 1: Create catalog module**

```ts
/** Static catalogs — update by hand when upstream renames models. */

export type ModelTier = { high: string; mid: string; low: string };

export type ExecutorModelCatalog = {
  tiers: ModelTier;
  options: Array<{ id: string; label: string }>;
};

export const CODEX_MODEL_CATALOG: ExecutorModelCatalog = {
  tiers: {
    high: "gpt-5.5",
    mid: "gpt-5.3",
    low: "gpt-5.3-codex",
  },
  options: [
    { id: "gpt-5.5", label: "GPT-5.5" },
    { id: "gpt-5.3", label: "GPT-5.3" },
    { id: "gpt-5.3-codex", label: "GPT-5.3 Codex" },
    { id: "gpt-5.4-mini", label: "GPT-5.4 mini" },
    { id: "o3", label: "o3" },
  ],
};

export const CURSOR_MODEL_CATALOG: ExecutorModelCatalog = {
  tiers: {
    high: "opus-4.5",
    mid: "auto",
    low: "composer-2",
  },
  options: [
    { id: "auto", label: "Auto" },
    { id: "opus-4.5", label: "Opus 4.5" },
    { id: "grok-4.5", label: "Grok 4.5" },
    { id: "composer-2", label: "Composer 2" },
    { id: "sonnet-4.5", label: "Sonnet 4.5" },
  ],
};

export function catalogForNativeExecutor(
  executor: "codex" | "cursor",
): ExecutorModelCatalog {
  return executor === "codex" ? CODEX_MODEL_CATALOG : CURSOR_MODEL_CATALOG;
}

export function modelForTier(
  catalog: ExecutorModelCatalog,
  tier: "high" | "mid" | "low",
): string {
  return catalog.tiers[tier];
}

export function tierForModel(
  catalog: ExecutorModelCatalog,
  model: string,
): "high" | "mid" | "low" | "custom" {
  const id = String(model || "").trim();
  if (!id) return "mid";
  if (id === catalog.tiers.high) return "high";
  if (id === catalog.tiers.mid) return "mid";
  if (id === catalog.tiers.low) return "low";
  return "custom";
}

export function resolveNativeModel(
  catalog: ExecutorModelCatalog,
  savedModel: string,
): string {
  const id = String(savedModel || "").trim();
  return id || catalog.tiers.mid;
}
```

> 若上游 ID 与上表不符，实现时可按本机 `codex debug models` / Cursor 文档微调，但保持 `tiers` + `options` 形状不变。

- [ ] **Step 2: Add smoke script**

Create `gui/scripts/test-executor-models.mjs` that duplicates `tierForModel` / `resolveNativeModel` assertions（与 catalog 常量同步注释），或用 `npx tsx` 若仓库已有：优先最小依赖——复制关键函数到 mjs 测一遍。

Run: `node gui/scripts/test-executor-models.mjs`  
Expected: `ok: executorModels`

- [ ] **Step 3: Commit**（若用户允许提交）

```bash
git add gui/src/settings/executorModels.ts gui/scripts/test-executor-models.mjs
git commit -m "feat(gui): add static Codex/Cursor model catalogs and tiers"
```

---

### Task 2: ColleagueConfigBar native UI

**Files:**
- Modify: `gui/src/components/ColleagueConfigBar.tsx`
- Consumes: `catalogForNativeExecutor`, `tierForModel`, `modelForTier`, `resolveNativeModel` from Task 1

**Interfaces:**
- Produces: UI 行为 — `useNativeModelUi = (executor==="cursor") || (executor==="codex" && !useThirdParty)`
- 写入仍走现有 `persist(..., { model })`

- [ ] **Step 1: Derive native UI flag**

在组件内：

```ts
const useNativeModelUi =
  !piLocked &&
  (executor === "cursor" || (executor === "codex" && !useThirdParty));
const nativeCatalog =
  useNativeModelUi && (executor === "codex" || executor === "cursor")
    ? catalogForNativeExecutor(executor)
    : null;
const activeTier = nativeCatalog
  ? tierForModel(nativeCatalog, model)
  : null;
const selectModel = nativeCatalog
  ? resolveNativeModel(nativeCatalog, model)
  : model;
```

- [ ] **Step 2: Conditional render**

- 当 `useNativeModelUi && nativeCatalog`：
  - **不渲染** Provider `<select>`
  - 渲染三个按钮/分段：`高` / `中` / `低`，`activeTier===…` 时高亮；点击 → `persist({ model: modelForTier(catalog, tier) })`
  - 渲染模型 `<select>`：`options` + 末项 `{ id: "__custom__", label: "自定义…" }`；若当前 model 不在 options，选中 `__custom__` 并显示旁路 `<input>`（复用现有 model input）
- 当非 native：保持现有 Provider + 文本 input（及 Codex 第三方 checkbox）

CSS：复用 `pi-model-chip`；档位可用 `pi-model-chip__tier` 小按钮（在 `App.css` 加 10 行内样式）。

- [ ] **Step 3: Manual check**

Run: `cd gui && npm run typecheck`  
Expected: exit 0

- [ ] **Step 4: Commit**

```bash
git add gui/src/components/ColleagueConfigBar.tsx gui/src/App.css
git commit -m "feat(gui): native Codex/Cursor model tier + catalog in chat bar"
```

---

### Task 3: Wire model into Codex / Cursor CLI

**Files:**
- Modify: `cli/agent_turn.py` — `run_codex_turn`, `run_cursor_turn`, `run_executor_turn`
- Test: `cli/test_agent_turn.py`

**Interfaces:**
- Consumes: `resolved_auth: dict | None` with optional `model`
- Produces: argv includes `-m` / `--model` when model non-empty

- [ ] **Step 1: Write failing tests**

在 `cli/test_agent_turn.py` 增加（mock `_run_cmd` / `_which_executor_bin`）：

```python
def test_codex_passes_model_flag(self) -> None:
    captured = {}
    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")
    with (
        patch("agent_turn._which_executor_bin", return_value="codex"),
        patch("agent_turn._run_cmd", side_effect=fake_run),
    ):
        from agent_turn import run_codex_turn
        run_codex_turn(
            "hi",
            executor_session_id=None,
            timeout=30,
            model="gpt-5.5",
        )
    self.assertIn("-m", captured["argv"])
    self.assertIn("gpt-5.5", captured["argv"])

def test_cursor_passes_model_flag(self) -> None:
    captured = {}
    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")
    with (
        patch("agent_turn._which_executor_bin", return_value="agent"),
        patch("agent_turn._run_cmd", side_effect=fake_run),
    ):
        from agent_turn import run_cursor_turn
        run_cursor_turn(
            "hi",
            executor_session_id=None,
            timeout=30,
            model="opus-4.5",
        )
    self.assertTrue(
        "--model" in captured["argv"] or "-m" in captured["argv"]
    )
    self.assertIn("opus-4.5", captured["argv"])
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd cli && python -m unittest test_agent_turn.TestCodexModel test_agent_turn.TestCursorModel -q`  
（按实际类名调整）  
Expected: FAIL — unexpected keyword `model` 或 argv 无 `-m`

- [ ] **Step 3: Implement**

```python
def run_codex_turn(
    prompt: str,
    *,
    executor_session_id: str | None,
    timeout: int,
    sandbox: str = "workspace-write",
    model: str | None = None,
) -> tuple[str, str | None, str]:
    ...
    model_id = (model or "").strip()
    # both resume and fresh branches: after "exec" (and resume id if any), before "--sandbox"
    if model_id:
        argv.extend(["-m", model_id])
```

```python
def run_cursor_turn(
    prompt: str,
    *,
    executor_session_id: str | None,
    timeout: int,
    model: str | None = None,
) -> tuple[str, str | None, str]:
    ...
    argv = [agent, "-p", "--output-format", "text", "--force", "--workspace", str(_REPO_ROOT)]
    model_id = (model or "").strip()
    if model_id:
        argv.extend(["--model", model_id])
```

在 `run_executor_turn`：

```python
    if executor == "codex":
        return run_codex_turn(
            prompt,
            executor_session_id=executor_session_id,
            timeout=timeout,
            model=(resolved_auth or {}).get("model"),
        )
    if executor == "cursor":
        return run_cursor_turn(
            prompt,
            executor_session_id=executor_session_id,
            timeout=timeout,
            model=(resolved_auth or {}).get("model"),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd cli && python -m unittest test_agent_turn -q`  
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add cli/agent_turn.py cli/test_agent_turn.py
git commit -m "feat(cli): pass instance model to Codex and Cursor agent turns"
```

---

### Task 4: Docs + empty-model default for native UI

**Files:**
- Modify: `docs/GUI-CONFIG.md`（若无对应段则 `docs/HOST-CHAT-PRODUCT.md`）
- Modify: `ColleagueConfigBar.tsx` load 路径 — native 且 `model===""` 时展示 `tiers.mid`（写入可在首次选档或 blur 时 persist，避免未操作就写盘；展示用 `resolveNativeModel`）

- [ ] **Step 1: Doc blurb**

在 GUI 配置文档加 3–5 行：

> 项目经理/程序员：Codex（非第三方）与 Cursor 在聊天顶栏用「高/中/低」与模型目录切换；写入 `agents.instances.<id>.model`，回合时传给 CLI。第三方 Codex 仍选 Provider。

- [ ] **Step 2: typecheck + unittest**

Run:

```bash
cd gui && npm run typecheck
cd ../cli && python -m unittest test_agent_turn -q
```

Expected: both OK

- [ ] **Step 3: Commit**

```bash
git add docs/GUI-CONFIG.md gui/src/components/ColleagueConfigBar.tsx
git commit -m "docs: note executor model tiers in chat config bar"
```

---

## Spec coverage check

| Spec 要求 | Task |
|-----------|------|
| 隐藏 Provider（Codex 登录 / Cursor） | Task 2 |
| 档位高/中/低 | Task 1+2 |
| 模型目录切换 | Task 1+2 |
| 自定义 ID | Task 2 |
| 写入 instances.model | Task 2（既有 persist） |
| Codex/Cursor CLI 传 model | Task 3 |
| Pi/Hermes/第三方不破 | Task 2 条件分支 + Task 3 仅改 codex/cursor |
| 静态目录 | Task 1 |
| 文档一句 | Task 4 |
| B 权限 | 明确不做 |

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-21-executor-model-tiers.md`.

**两种执行方式：**

1. **Subagent-Driven（推荐）** — 每任务新开子代理，任务间复查  
2. **Inline Execution** — 本会话按 `executing-plans` 连续做完  

选哪个？
