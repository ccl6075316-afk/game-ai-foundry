# Host 桥接层收口与流水线可自愈 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把散落在 GUI / Electron / CLI 的「跑资产 → 失败 → 修 → 续跑」收成可测的 `cli/host/`，让用户点一次能跑通，不必靠项目经理聊天分诊。

**Architecture:** CLI 引擎不动；新增薄 Host 包封装 `retry-asset` / `run-assets --auto-fix`；GUI 只调 Host JSON IPC。不删 `prompt_craft`、不削弱 validate。渐进迁移，不做 `cli/core` 大搬家。

**Tech Stack:** Python Click CLI、现有 `pipeline_heal` / `pipeline_retry` / `safe_cli`、Electron IPC、React App（目标模式已有雏形）。

**事实源：**
- [`docs/ARCHITECTURE-LAYER-INVENTORY.md`](../../ARCHITECTURE-LAYER-INVENTORY.md)
- [`docs/ARCHITECTURE-REFACTOR-HANDOFF.md`](../../ARCHITECTURE-REFACTOR-HANDOFF.md)

## 执行元数据

| 字段 | 值 |
|------|----|
| Status | executed |
| Workflow Stage | code |
| Created | 2026-08-20 |
| Executed | 2026-08-21 |
| Requirements Source | 用户确认归属清单 + 架构交接；钓鱼工程「PM 分诊完任务还在」实锤 |
| Readiness | 每 Task 末尾命令；总验收见 §验收 |
| Resume Point | **Plan 完成**。可选 follow-up：`host run-assets` 流式日志；`AssetReviewPanel` retry-asset；P3 `App.tsx` 编排瘦身 |
| Code Status | T1–T5 已合入 main（73aa273…15fd5d0）；T6 文档本 commit |

## Global Constraints

- **禁止**删除或削弱 `prompt_craft.py`、image/matting validate、CJK 守卫。
- **禁止**本轮做 `cli/core` 物理搬家或 `App.tsx` 大拆文件（仅抽编排调用）。
- `safe_cli` 若放行 `prompt craft`：必须带 `--asset`（或等价单资产约束），禁止整 brief 扫。
- Host auto-fix：同 `task_id` + 同 `kind` 连续失败 **最多 2 轮** 则停，交给人。
- validation / CJK craft 失败路径 **必须**带 `--run-prompts`（或显式 `prompt craft --asset`）。
- VT ready **只信** CLI `brief visual-target status`；Electron 不再自维护判定。
- 新 CLI 默认 `--json` 可给 GUI；人工可读文案可选。

## 非目标（本 Plan 不做）

- 动画切分 / 视频厂商扩展。
- 删除 Hermes skill 文件或改七角色枚举值（仅文档降级）。
- 重写 ACP 传输层。
- fishing-2d 业务内容变更（可用作验收靶机）。

---

## 模块边界

### 模块：HostRetryAsset

- **职责：** 对单个 asset（或 task-id）执行 reset → 可选 craft → run（带正确 flags）
- **输入：** manifest Path、asset name 或 task_id、`recraft_prompt: bool`、jobs
- **输出：** `{ok, healed_task_ids, ran, exit_code, summary}` JSON
- **依赖：** `pipeline_runner.reset_task_cascade`、`pipeline_retry`、`prompt craft` 或 `pipeline run --run-prompts`
- **不变量：** 不重跑无关 done 任务；失败不静默吞掉

### 模块：HostRunAssets

- **职责：** `pipeline run` + 失败后 diagnose/heal/`fix_commands` 循环（最多 2 轮）
- **输入：** manifest、jobs、`run_prompts`、`auto_fix: bool`
- **输出：** 最终 status + 每轮 repair 摘要
- **依赖：** `pipeline_heal`、`safe_cli` 执行链、可选调 PM Agent（仅 unknown）
- **不变量：** validation 类不依赖用户再点「项目经理处理失败」

### 模块：HostClassifyTighten

- **职责：** 把「Chinese brief text cannot be used…」等 craft 守卫失败归入 `validation` / `reset_and_recraft_prompt`
- **依赖：** `pipeline_heal.classify_failed_task`
- **不变量：** 归类后 `can_auto_fix_without_agent` 为 True（单 validation 项时）

### 模块：GuiHostIpc

- **职责：** Electron IPC + App 按钮改调 Host，删除重复编排
- **不变量：** 权限卡 / ACP 仍在 GUI

### 模块：VtStatusSingleSource

- **职责：** `visual-target-status` IPC 改为 spawn CLI status（或共享 Python 不可行时至少删除 Electron 独立 ready 算法）
- **不变量：** 分册 `visual_reference` 能开闸

---

## 接口草案

```python
# cli/host/retry_asset.py
def retry_asset(
    manifest_path: Path,
    *,
    asset: str | None = None,
    task_id: str | None = None,
    recraft_prompt: bool = False,
    jobs: int = 4,
) -> dict: ...

# cli/host/run_assets.py
def run_assets(
    manifest_path: Path,
    *,
    jobs: int = 4,
    run_prompts: bool = False,
    auto_fix: bool = True,
    max_repair_rounds: int = 2,
) -> dict: ...
```

CLI：

```bash
python gamefactory.py host retry-asset --manifest … --asset char_xxx [--recraft-prompt] --jobs 4 --json
python gamefactory.py host run-assets --manifest … --run-prompts --auto-fix --jobs 4 --json
```

---

## 任务 DAG

```text
T1 classify CJK → validation
    ↓
T2 host retry-asset (CLI + 单测)
    ↓
T3 host run-assets --auto-fix (CLI + 单测)
    ↓
T4 GUI/IPC 接 retry + run（瘦 App 编排）
    ↓
T5 VT status 单源（删 Electron hydrate 副本）
    ↓
T6 文档 / 角色降级（AGENT-ROUTING + skills 短注）
```

并行：T5 可与 T2 后并行于 T3；建议 T1→T2→T3 串行，T4 依赖 T2+T3，T6 任意时刻可做但建议最后。

---

### Task 1: Craft/CJK 失败归类为 validation

**Files:**
- Modify: `cli/pipeline_heal.py`（`classify_failed_task`）
- Modify: `cli/test_pipeline_heal.py`
- 可选: `docs/ARCHITECTURE-LAYER-INVENTORY.md` 验收勾选说明

**Interfaces:**
- Produces: blob 含 `chinese brief text cannot be used` / `secondary-generate english` → `kind=validation`, `remediation=reset_and_recraft_prompt`, `owner=hermes`

- [x] **Step 1:** 写失败单测：伪造 failed task stderr 为澳洲鳕鱼那句 CJK 守卫文案，断言 `kind == "validation"` 且 `cli_hints` 含 `--run-prompts`

- [x] **Step 2:** 实现分类分支（在 exit 2 分支附近，按文案匹配，勿误伤无关中文日志）

- [x] **Step 3:** `cd cli && python -m pytest test_pipeline_heal.py -q` 全绿

- [x] **Step 4:** Commit：`fix: classify CJK prompt-craft failures as validation for auto-fix`

**成功标准：** fishing-2d 同类失败在 `pipeline diagnose` 下 `pm_fit=yes` 且进入 `fix_commands`（带 `--run-prompts`）。

---

### Task 2: `host retry-asset` CLI

**Files:**
- Create: `cli/host/__init__.py`
- Create: `cli/host/retry_asset.py`
- Create: `cli/host_cmds.py`（Click group `host`）
- Modify: `cli/gamefactory.py`（`add_command`）
- Modify: `cli/safe_cli.py`（允许 `host retry-asset`；**不**裸放行任意 `prompt craft`，或仅允许 `prompt craft --asset <id>`）
- Create: `cli/test_host_retry_asset.py`
- Reuse: `pipeline_retry.py`, `pipeline_runner.reset_task_cascade`

**Interfaces:**
- Consumes: manifest tasks、asset name
- Produces: JSON `{ok, asset, reset_task_id, recraft_prompt, run_exit_code, ...}`

- [x] **Step 1:** 单测：临时 manifest 含一条 failed `foo.prompt.craft` → `retry_asset(..., recraft_prompt=True)` mock run/craft，断言调用了 cascade reset 且 run 带 prompts 或单独 craft

- [x] **Step 2:** 实现 `retry_asset`：解析 asset → `_pick_reset_task_id` → reset cascade → 若 `recraft_prompt` 或 step 含 prompt：`pipeline run --run-prompts`（范围：reset 后 pending 自然只跑相关）或显式 `prompt craft --asset`

- [x] **Step 3:** 注册 `host retry-asset` Click 命令 + `--json`

- [x] **Step 4:** `safe_cli` 增加 `("host", "retry-asset")`；若需内部 craft，优先走 host 命令而非开放裸 craft

- [x] **Step 5:** `pytest test_host_retry_asset.py test_safe_cli.py -q`

- [x] **Step 6:** Commit：`feat: add host retry-asset for single-asset pipeline repair`

**成功标准：**  
`host retry-asset --manifest ../projects/fishing-2d/pipeline/manifest.json --asset <鳕鱼资产名> --recraft-prompt --json` 后该 task 不再 `failed`（或明确报错可诊断）。

---

### Task 3: `host run-assets --auto-fix`

**Files:**
- Create: `cli/host/run_assets.py`
- Modify: `cli/host_cmds.py`
- Create: `cli/test_host_run_assets.py`
- Reuse: `pipeline_heal.build_fix_command_chain`, `can_auto_fix_without_agent`, `diagnose_and_heal_file`

**Interfaces:**
- Produces: JSON 含 `rounds[]`、`stopped_reason` ∈ `complete|max_rounds|needs_agent|error`

- [x] **Step 1:** 单测：mock 第一轮 run 失败 + diagnose validation → 执行 fix_commands → 第二轮 complete

- [x] **Step 2:** 单测：同 task_id+kind 两轮仍失败 → `stopped_reason=max_rounds`，不无限循环

- [x] **Step 3:** 实现 `run_assets`：run →（可选）heal code 类 → 若 `auto_fix` 且 `can_auto_fix_without_agent` 则执行 `fix_commands`（经 safe_cli）→ 再 run；unknown 不自动 Agent（留给 GUI 可选）

- [x] **Step 4:** Click：`host run-assets --auto-fix/--no-auto-fix --run-prompts --jobs --json`

- [x] **Step 5:** `safe_cli` 允许 `("host", "run-assets")`

- [x] **Step 6:** pytest 绿 + Commit：`feat: add host run-assets with auto-fix loop`

**成功标准：** 纯 CLI 可复现 GUI 目标模式主路径（validation），无需开 Electron。

---

### Task 4: GUI / IPC 改调 Host

**Files:**
- Modify: `gui/electron/main.mjs`（IPC `host-retry-asset`, `host-run-assets`）
- Modify: `gui/electron/preload.cjs` + `gui/src/vite-env.d.ts`
- Modify: `gui/src/App.tsx`：`handleRun` / `attemptPipelineAutoRepair` /「项目经理处理失败」优先 Host
- Modify: 看板/资产表「只重跑此资产」入口（`BoardPanel` / `AssetReviewPanel` / `TaskList` 择一最小接线）
- Test: 可加 `gui/electron` 薄测或手动清单

**Interfaces:**
- Consumes: T2/T3 JSON
- Produces: GUI 一次点击 = 一次 Host 调用

- [x] **Step 1:** IPC 封装 spawn `host run-assets` / `host retry-asset`

- [x] **Step 2:** `handleRun`：改为 `host run-assets --auto-fix`（保留日志流若现有 pipeline-run 有 stream，则 Host 先同步版，stream 可 follow-up）

- [x] **Step 3:** 「项目经理处理失败」：先 `host` 执行 fix；仅 `needs_agent` / unknown 再 `agentTurn`

- [x] **Step 4:** 资产/看板加「重跑此资产」→ `host retry-asset --recraft-prompt`（validation 时）

- [x] **Step 5:** 删或大幅缩减 App 内重复的 fix 串跑逻辑（保留 UI 状态/busy）

- [x] **Step 6:** 手动：重启 Electron → fishing-2d 跑资产 / 重试一条

- [x] **Step 7:** Commit：`feat: wire GUI pipeline buttons to host run/retry`

**成功标准：** 验收标准 §8.1–8.2（归属清单）在 GUI 上可演示。

---

### Task 5: VT status 单源

**Files:**
- Modify: `gui/electron/main.mjs` `visual-target-status` → 调 CLI `brief visual-target status --json`（或复用已有 hydrate 后改为 thin wrap）
- Delete or deprecate: `gui/electron/visualTargetHydrate.mjs`（若 CLI 全覆盖）
- Modify: 相关测试

- [x] **Step 1:** IPC 改为 CLI status；对比 fishing-2d：`ready===true` 当 scenes 分册有 VR

- [x] **Step 2:** 移除 Electron 独立 ready 算法 / hydrate 副本

- [x] **Step 3:** Commit：`fix: use CLI visual-target status as single readiness source`

**成功标准：** 不重启逻辑分叉；分册已绑北极星时顶栏「✓ 北极星图」。

---

### Task 6: 文档与角色降级

**Files:**
- Modify: `docs/AGENT-ROUTING.md`
- Modify: `resources/skills/orchestrator/pipeline-schedule.md` / `product-host.md`（短注：prompt-crafter = pipeline 步骤）
- Modify: `docs/ARCHITECTURE-LAYER-INVENTORY.md` / `ARCHITECTURE-REFACTOR-HANDOFF.md`（勾选完成项）
- Modify: `docs/RELEASE-NOTES-UNRELEASED.md`

- [x] **Step 1:** 文档写明用户可见同事 vs pipeline 内部角色

- [x] **Step 2:** 交接文档 P1 勾选 + Resume Point 更新

- [x] **Step 3:** Commit：`docs: demote prompt-crafter to pipeline step; mark host plan progress`

---

## 验收（整包）

| # | 场景 | 期望 |
|---|------|------|
| A | `host retry-asset` 针对 CJK/craft failed | task 离开 failed；含文案重跑 |
| B | `host run-assets --auto-fix` 遇 validation | 无人点 PM 也能续跑或 max_rounds 停 |
| C | GUI「运行资产生成」 | 同 B |
| D | GUI「重跑此资产」 | 同 A |
| E | VT 闸门 | 只认 CLI status |
| F | 回归 | `pytest test_pipeline_heal test_host_* test_safe_cli test_agent_turn -q` |

## 历史经验约束

- 默认 `pipeline run` **不带** `--run-prompts` → Host 必须显式带（归属清单 / 交接文档已强调）。
- PM 分诊完不执行 reset → 用户会反复点「处理失败」；Host 必须先执行再聊天。
- Electron 与 CLI 双份 VT 判定已出过漏绑事故 → T5 强制单源。

## 关键模式检查

- ❌ 在 App 再写第三套 fix 循环  
- ✅ 策略只进 `cli/host/`  
- ❌ 开放无资产约束的 `prompt craft` 白名单  
- ✅ craft 藏在 `host retry-asset` 内  

## Resume / 下一刀

**Plan 已完成**（T1–T6）。可选 follow-up：

- `host run-assets` 流式日志（现 GUI 同步 spawn）
- `AssetReviewPanel` 独立「重跑此资产」按钮
- P3：`App.tsx` 编排函数进一步迁出 / 删除
