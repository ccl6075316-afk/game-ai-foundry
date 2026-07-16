# Game AI Foundry — 施工体系（Construction System）

| | |
|--|--|
| **读者** | Host、维护者、接手的 AI Agent |
| **侧重** | **brief → 工程蓝图 → 壳 → 写码 → 验收 → 进度** 的目标架构与落地顺序 |
| **姊妹文档** | 设计/施工契约 → [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md) · 角色路由 → [`AGENT-ROUTING.md`](AGENT-ROUTING.md) · CLI → [`AI-HANDOFF.md`](AI-HANDOFF.md) · Hermes → [`HERMES-CODEX.md`](HERMES-CODEX.md) |

---

## 1. 背景：brief 不够写代码

`brief.json` 是 **Design Doc**（玩家体验、资产表、controls、animation_graphs），不是施工蓝图。直接交给 coding Agent 会导致：

- 场景树、脚本划分、碰撞层、物理参数靠 **genre 惯例脑补**
- 资产绑定较清楚（`runtime_bindings`），玩法逻辑不清楚
- 换 session 后进度与决策丢失

行业成熟做法（Godogen、GodotMaker、Godot AI Builder 等）共性：**Spec 先于 Code**——先把工程真相写成可版本化文件，再 scaffold，再分任务施工，再分层验收。

Foundry 不照搬某家的 Markdown 协议，而是走 **JSON + CLI** 路线，与现有 `brief export`、`pipeline run`、`dev-context` 对齐。

---

## 2. 四条支柱

### 2.1 工程文档：brief → 可代码化的蓝图 → 壳

**要求**

- brief 保持 Design，不膨胀成工程文档
- 显式 **转化步**：`brief export` → `production derive` → `production validate`
- 蓝图至少能生成 **可编译的工程壳**（`project.godot`、主场景 stub、InputMap、目录、占位脚本）

**建议产物：`production.json`**

| 层级 | 内容 |
|------|------|
| L0 | genre preset（重力、跳跃、tile_size 等，可追溯 preset id） |
| L1 | `scenes[]`、`systems[]`（场景树、脚本职责、信号） |
| L2 | InputMap、碰撞层、动画状态机（对齐 brief.controls / animation_graphs） |
| L3 | `godot_tasks[]`（依赖 + 每任务 `verify[]`） |
| L4 | `validation.acceptance_criteria` / `regression_checks` |

**壳**：`godot scaffold` 或扩展 `godot assemble`，在 Pass 3 产出可打开的 Godot 项目，Pass 4 只填逻辑。

### 2.2 写码 Agent：统一 Godot skill + 代码规范

**要求**

- 无论 Hermes / Codex / Cursor，共用 **`resources/skills/godot-developer/`** 源
- skill 分两层：
  - **契约**（读什么、不读什么、validate 门禁）— 今天 `implement.md` 已有
  - **规范**（C# / Godot 4 .NET 惯用写法、genre 模板、常见坑）— **待补**

**分工**

- `production.json` = 这个项目要建什么
- godot-developer skills = 在 Godot C# 里通常怎么建

### 2.3 完整验收流程

**验收金字塔**（标准写在 `production.validation`，不由 Agent 自说自话）：

| 层级 | 手段 | 今天 |
|------|------|------|
| L0 编译/静态 | `godot validate` | ✅ |
| L1 功能单测 | `test unit`（`dotnet test` + PlayerStats） | ✅ |
| L2 模块/场景 | `test play` + playtest JSON + `assert_*` | ✅ |
| L3 视觉/行为 QA | `test analyze` / vision | ⚠️ 有，非硬门禁 |
| L4 回归 | `test regression`（通过 plan 快照） | ✅ |

**原则**：Agent **不能**自证 task 完成；CLI 验收通过后才更新进度。

### 2.4 进度文档

**要求**

- 上下文压缩或换 session 时，Agent 读文件续作，不读聊天记忆
- 建议产物：`plans/progress_<slug>.json`

```json
{
  "brief": "resources/my-game-brief.json",
  "production": "plans/production_my-game.json",
  "phases": {
    "production_derived": { "status": "done" },
    "scaffold": { "status": "done" },
    "pipeline_run": { "status": "done" },
    "godot_tasks": [
      { "id": "player_controller", "status": "done" },
      { "id": "collectibles", "status": "in_progress" }
    ],
    "validation": {
      "validate": "pass",
      "unit": "not_run",
      "playtest": "fail",
      "last_failure": "..."
    }
  },
  "memory": ["踩坑与 workaround 条目"]
}
```

新 session 起手：`project progress` → `dev-context` → 读 production → 动代码。

---

## 3. 与现有文档的映射

| 概念 | 今天 | 目标 |
|------|------|------|
| Design Doc | `brief.project` + export 冻结 | 保持 |
| Production Doc | 挤在 brief 里 / ITERATIVE 示例 JSON | 独立 `production.json` |
| 工程壳 | `godot assemble` 部分骨架 | scaffold 对齐 production |
| 施工 handoff | `plans/dev_*.json` | 引用 production + progress |
| Change Request | ITERATIVE 有定义 | `production delta` CLI（待做） |

---

## 4. 推荐总流程

```text
1. brief brainstorm → brief export（Design 冻结）
2. production derive + validate（工程蓝图）
3. godot scaffold（壳）+ pipeline plan/run + assemble（资产）
4. progress init（从 production.godot_tasks 展开）
5. 循环每个 godot_task：
     dev-context（含 production）
     → coding Agent（统一 godot-developer skills）
     → godot validate → test unit → test play
     → CLI 更新 progress + memory
6. test run 全量 → Validation Report
```

---

## 5. 行业参考（简表）

| 项目 | 架构做法 | Foundry 借鉴 |
|------|----------|--------------|
| Godogen | `STRUCTURE.md` + `PLAN.md` + 每任务 VQA | 工程信息密度、任务验收 |
| GodotMaker | GDD + hook 门禁 + acceptance | 不能跳过验收 |
| Godot AI Builder | Phase 0 PRD + genre template | preset 填默认值 |
| Spec Kit | constitution → plan → tasks → implement | JSON 契约 + CLI 门禁 |

**不采纳**：整套 Markdown 协议替换 brief/pipeline；ECS 重写；以编辑器 MCP 为主路径（可作可选增强）。

---

## 6. 落地顺序（建议）

1. **`production.json` schema + `production derive` + scaffold 能出壳**
2. **`progress.json` + `dev-context` 引用 production**
3. **godot-developer skill 加厚**（C# 规范 + 至少一个 genre 模板）
4. **验收**：playtest 绑 production → 再上 unit test → 回归清单

---

## 7. 相关命令（今天已有 / 待建）

| 状态 | 命令 / 产物 |
|------|-------------|
| ✅ | `brief export`、`pipeline run`、`godot assemble`、`godot dev-context` |
| ✅ | `godot validate`、`test plan`、`test play`、`test run` |
| ✅ | `production derive`、`production validate` |
| ✅ | `godot scaffold`、`project progress` |
| ✅ | `test plan --task`、`assert_*`、`test regression`、`test unit` |
| 📋 | GdUnit4 / 子场景 isolation（L3） |

```bash
cd cli
python gamefactory.py production derive --brief ../resources/asset-brief.example.json
python gamefactory.py project progress init --brief ../resources/asset-brief.example.json --production ../plans/production_asset-brief.example.json
python gamefactory.py godot scaffold --production ../plans/production_asset-brief.example.json --progress ../plans/progress_forest-platformer.json
python gamefactory.py test unit --project ../games/forest-platformer --progress ../plans/progress_forest-platformer.json
python gamefactory.py test plan --brief ../resources/asset-brief.example.json --task player_controller
python gamefactory.py test play --project ../games/forest-platformer --plan ../plans/playtest_asset-brief.example_player_controller.json --progress ../plans/progress_forest-platformer.json --skip-analyze
python gamefactory.py test regression --progress ../plans/progress_forest-platformer.json
```

---

## 8. Harness（验收执行层）— 现状与缺口

**Harness** = 可重复执行的验收脚本 + runner + 报告，不是 Hermes/Codex 执行器。

### 8.1 今天有什么

| 组件 | 路径 / 命令 | 能力 |
|------|-------------|------|
| Playtest plan | `test plan` → `plans/playtest_*.json` | 从 **brief** 推导 smoke：按 controls 按键 + 截图 |
| Runner | `resources/godot-tools/playtest_runner.gd` | headless：加载主场景、`wait_frames` / `press` / `screenshot` |
| 执行 | `test play` / `test run` | `godot validate` → runner → vision `visual_checks` |
| 报告 | `output/<slug>/validation/report-*.json` | build + playtest + 视觉分析汇总 |
| Schema | `playtest-schema.md` | 仅 3 种 op |

### 8.2 相对四条支柱，harness 还缺什么

| 缺口 | 说明 |
|------|------|
| **GdUnit4** | 当前 L1 走 `dotnet test` + 纯 C# `PlayerStats`；未接 GdUnit4 场景树单测 |
| **L3 模块/集成** | 无「只加载子场景」「只测 PlayerController」的隔离 harness |
| **动态场景** | runner 默认跑 `main_scene`；`change_scene` op 未实现 |
| **reference 对比** | `visual_reference` 仅 analyze 时可选传入，playtest 无帧序列 / 动态 VQA |
| **plan craft** | `playtest_plan.py` 注释提到 `--craft`，**CLI 未实现** LLM 写复杂场景 |

### 8.3 目标 harness 金字塔（待建）

```text
L0  godot validate                    ← 已有
L1  test unit（dotnet test）           ← 已有
L2  test play（production + assert_*） ← 已有
L3  test integration（子场景 / 模块）   ← 待建
L4  test regression（快照 plan）        ← 已有
```

**原则**：验收标准来自 `production.validation`；harness **只执行、只出报告**，不修复代码。

---

*最后更新：2026-07-16（施工骨架可测；待做：Delta / 编排 / 视觉硬门禁）*
