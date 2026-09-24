# 架构 Plan：纯 CLI / Workflow 外部 Agent 工具箱

> **删除说明：** 文中出现的桌面客户端、内置会话与品牌专属运行时均为已移除对象，不是当前操作入口。

> **执行要求：** 只在 `codex/pure-workflow-toolkit` 分支实施；禁止修改 `master`。按任务 DAG 逐项执行，每项必须有可验证完成条件。

**目标：** 删除 GUI 和内置 Agent 运行时，把项目收敛为外部 Agent 可直接调用的纯 CLI / Workflow 工具箱；保留 Brief、场景、系统、资产、Production、Pipeline、Godot、验收的核心契约与确定性执行能力。

**架构：** 现有 Python CLI 继续作为唯一执行引擎；新增一层很薄的 `workflow` 命令，只负责上下文发现、阶段执行、状态汇总和结构化报告；不新建第二套 DAG、状态库或 Agent RPC。外部 Agent 通过 CLI + 一份通用 Skill 接管判断与编排。

**技术栈：** Python 3.11+、Click、现有 Pipeline/Godot/Test 模块、JSON/JSONL 文件契约。删除 Electron、React、ACP、Pi RPC 和外部 Agent 执行器适配。

**事实源：**

- [`docs/anvil/brainstorms/2026-09-23-pure-workflow-toolkit.md`](../brainstorms/2026-09-23-pure-workflow-toolkit.md)
- [`docs/ARCHITECTURE-LAYER-INVENTORY.md`](../../ARCHITECTURE-LAYER-INVENTORY.md)
- [`docs/AI-HANDOFF.md`](../../AI-HANDOFF.md)

## 执行元数据

| 字段 | 值 |
|------|----|
| Status | T1–T7、Anvil Stage 5 与 Stage 6 完成 |
| Workflow Stage | Stage 5 `APPROVED`；Stage 6 compound 已完成；等待用户决定是否 commit |
| Code Status | T1–T7 已完成（删除清单、GUI/内置 Agent 收口、Brief、Workflow、Skill、Review Fix A–G、总验收与知识沉淀） |
| Final Tests | 594 tests；0 failures；4 errors；2 skipped |
| Known Baseline Errors | `magic_prince` 缺 fixture 1 个；`visual_target` CJK guard 3 个 |
| T7 Smoke | 六个 `workflow --help` 均退出 0；只读 status 示例为 `ok=true/status=pending/next_action=run`（即 `ok/pending/run`）；合法枚举见 Workflow 合同；示例 Brief `context/validate` 返回已知 `brief_invalid` 结构化结果且只读状态不变 |
| T7 Scans | 当前入口删除扫描仅命中“已移除”说明；GUI/Release 路径不存在；根 CLI help 无 `agent/agents/hermes`；相对链接 12/12 有效 |
| Branch Baseline | `main=f26aa70caa302a64a8ca58f6ccde5dc340c99451`；`origin/main` 相同；无 `master`/`origin/master` ref |
| Created | 2026-09-23 |
| Branch | `codex/pure-workflow-toolkit` |
| Requirements Source | 用户确认：删除 GUI、去内置 Agent、由外部 Agent 接管 |
| Source Of Truth Until | 后续 Plan 取代本范围 |
| Readiness | 每个任务末尾测试；总验收见 §通过条件 |
| Review Status | `.ai/anvil/reviews/2026-09-23-pure-workflow-toolkit-review.md` = `APPROVED`；无未解决 Critical/High |
| Compound Status | `docs/solutions/architecture/external-agent-workflow-replaces-gui-internal-agents-cli-20260924.md` 已通过 YAML schema、章节与交叉引用校验 |
| Resume Point | Anvil 流程完成；等待用户决定是否 commit |

## 全局约束

- `master` 必须保持无改动；所有提交和验证只发生在当前分支。
- 不删除或削弱 Brief/Production/Pipeline/Godot/Test 的确定性能力。
- 不删除 `prompt_craft.py`、生图/抠图校验、CJK 守卫或 Pipeline 自愈分类。
- 不新增通用工作流状态数据库；`pipeline manifest`、`progress`、`handoff` 继续作为权威状态。
- 不为每个外部 Agent 写一套适配器；只提供一份通用工具箱 Skill。
- 删除 GUI 后，CLI 必须能在无 Node、Electron、GUI IPC、ACP 和内置 Agent 进程的环境中运行。
- 所有供外部 Agent 使用的命令必须支持 `--json`，并返回稳定字段。
- `shell`、配置写入、删除和网络请求仍须保留显式确认或白名单边界。
- 说明文字、任务、验收标准使用中文；命令名、文件名、JSON 字段和枚举值使用英文。

## 非目标

- 不重写现有 Pipeline DAG 引擎。
- 不引入数据库、队列、RPC 服务或 Web 后端。
- 不设计新的通用 Agent 框架。
- 不改写现有游戏项目和生成资产。
- 不在本轮扩展生图/视频厂商能力。
- 不保留一个“只读 GUI”兼容层。

---

## 模块边界

### 模块：CLI Composition Root

- **职责：** 注册并组合所有确定性命令组，不承载业务策略。
- **输入：** Click 命令行参数、环境变量、`~/.gamefactory/config.json`。
- **输出：** 命令执行结果、退出码、JSON/人类可读输出。
- **依赖：** Brief、Production、Pipeline、Workflow、Godot、Test、Setup 命令模块。
- **不变量：** 不注册 `agent`、`agents`、`hermes`、`host-chat`、GUI 或 ACP 相关命令；模块内部不读取 GUI 状态。

### 模块：Brief Contract

- **职责：** 读取、校验、冻结 Brief，并维护场景、系统、资产、动画分册。
- **输入：** Draft/frozen `brief.json`、`scenes/*.json`、`systems/*.json`、`assets/*.spec.json`。
- **输出：** 校验结果、冻结后的 Brief、分册读写结果。
- **依赖：** `brief.py`、`brief_cmds.py`、`brief_shards.py`、结构校验函数。
- **不变量：** 不依赖聊天 session；不依赖内置 Agent；export/freeze 后 `brief.json` 是唯一设计事实源。

### 模块：Production Contract

- **职责：** 从冻结 Brief 派生工程蓝图，并处理 Production Delta。
- **输入：** `brief.json`、genre preset、可选 makeability sidecar、Delta 文件。
- **输出：** `production.json`、校验结果、合并结果。
- **依赖：** `production.py`、`production_cmds.py`。
- **不变量：** 同一输入产生同一蓝图；所有 `godot_tasks` 和验收标准可独立校验。

### 模块：Pipeline Engine

- **职责：** 构建并执行资产任务 DAG，保留 prompt、图像、视频、抠图、组装和失败恢复。
- **输入：** Brief、Production、manifest、任务参数、Provider 配置。
- **输出：** manifest 状态、`output/`、`assets-manifest.json`、任务结果。
- **依赖：** 现有 `pipeline_*`、`prompt_craft`、media、Godot assembler 模块。
- **不变量：** 不依赖 GUI/ACP；`exit 2` 仍表示可修复校验暂停；同一任务失败分类保持稳定。

### 模块：Workflow Adapter

- **职责：** 为外部 Agent 提供窄入口：发现上下文、初始化、执行阶段、恢复失败、汇总状态。
- **输入：** 项目根目录或 Brief/manifest 路径、stage、task id、执行选项。
- **输出：** 稳定 JSON result；必要时委托现有 Production/Pipeline/Progress 模块。
- **依赖：** Brief Contract、Production Contract、Pipeline Engine、Progress/Handoff。
- **不变量：** 只做组合与格式归一化；不复制 DAG、重试、校验或状态机逻辑；不创建第二份权威状态。

### 模块：Durable Project State

- **职责：** 持久化进度、派工、资产审查和验证报告。
- **输入：** 外部 Agent 提交的任务状态、验收结果、handoff。
- **输出：** `plans/progress_*.json`、`plans/handoffs/*.json`、validation report、asset review。
- **依赖：** 现有 `progress.py`、`handoff.py`、`asset_review.py`、test report。
- **不变量：** 文件可跨会话恢复；不读取聊天记忆；Agent 不能仅靠自述把任务标为完成。

### 模块：External Agent Skill

- **职责：** 说明外部 Agent 如何发现项目、选择阶段、调用命令、解释失败和提交结果。
- **输入：** 用户目标、Workflow JSON、项目文件。
- **输出：** 外部 Agent 的调用序列和最终报告。
- **依赖：** CLI help、Workflow JSON schema、文件契约。
- **不变量：** 只描述协议，不复制实现；不绑定特定 Agent 品牌；不包含凭据或绕过校验的方法。

### 模块：Removal Boundary

- **职责：** 一次性移除 GUI 和内置 Agent 运行时，防止死代码继续被 CLI 引用。
- **输入：** `gui/`、GUI 启动/打包脚本、Agent/ACP/Pi/Hermes/Cursor/Codex 运行时模块。
- **输出：** 无运行时依赖的仓库和测试集合。
- **依赖：** 无。
- **不变量：** 删除后不得留下入口、配置、测试或文档要求用户启动 GUI/内置 Agent。

---

## 接口定义

### 通用结果格式

所有 `workflow` 命令的 `--json` 输出使用同一顶层结构：

```json
{
  "schema_version": 1,
  "ok": true,
  "command": "status",
  "stage": "assets",
  "status": "paused",
  "next_action": "resume",
  "inputs": {
    "brief": "projects/demo/brief.json",
    "production": "plans/production_demo.json",
    "manifest": "pipeline/demo.json"
  },
  "outputs": [],
  "summary": {},
  "failures": []
}
```

稳定枚举：

- `status`: `pending`、`running`、`done`、`paused`、`blocked`、`failed`
- `stage`: `design`、`production`、`assets`、`assemble`、`implement`、`validate`
- `next_action`: `none`、`freeze_brief`、`derive_production`、`run`、`resume`、`recraft_prompt`、`fix_input`、`human_review`
- `failures[].kind`: `validation`、`network`、`dependency`、`config`、`unknown`

### Workflow 命令

```bash
python gamefactory.py workflow context --brief <path> --json
python gamefactory.py workflow init --brief <path> [--manifest <path>] --json
python gamefactory.py workflow run --manifest <path> --stage assets [--auto-fix] [--run-prompts] --jobs 4 --json
python gamefactory.py workflow resume --manifest <path> --task-id <id> [--recraft-prompt] --json
python gamefactory.py workflow status --manifest <path> --json
python gamefactory.py workflow validate --brief <path> [--production <path>] [--manifest <path>] --json
```

接口职责：

- `context`：只读发现 Brief、Production、manifest、progress、handoff、最近 validation。
- `init`：派生 Production、初始化 progress、生成 pipeline manifest；已有且一致的文件不重复覆盖。
- `run`：委托现有 Pipeline/Host 自愈逻辑执行一个阶段；不自行实现重试。
- `resume`：委托 `reset_task_cascade` + `run_pipeline`，并按失败类型决定是否 `--run-prompts`。
- `status`：聚合 manifest、progress 和 validation，不写状态。
- `validate`：串行执行 Brief/Production/Pipeline 契约校验，返回全部错误。

### Brief 确定性接口

删除聊天会话依赖后，保留：

```bash
python gamefactory.py brief validate --brief <path> --json
python gamefactory.py brief freeze --input <draft.json> -o <brief.json> --json
python gamefactory.py brief shard migrate --brief <path> --json
python gamefactory.py brief shard read --brief <path> --json
```

`freeze` 只做结构校验和 `brief_meta` 冻结；创意补全由外部 Agent 完成。

### Progress / Handoff 接口

```bash
python gamefactory.py project progress show --brief <path> --json
python gamefactory.py project progress sync --production <path> --progress <path> --json
python gamefactory.py project handoff create --brief <path> --task-id <id> --assignee <external-agent-id> --json
python gamefactory.py project handoff list --brief <path> --json
```

`assignee` 只表示外部执行方标识，不触发任何内置 Agent。

---

## 日志规范

### stdout JSON

- `--json` 时 stdout 只允许一个完整 JSON 对象。
- JSON 对象必须包含 `schema_version`、`command`、`ok`、`status`、`next_action`。
- stdout 不混入进度条、stderr 文案或子进程日志。

### stderr 人类日志

- 非 `--json` 模式允许中文提示。
- 错误必须包含模块、阶段、任务 id、错误类别和下一步。
- 不打印 API Key、代理凭据、完整环境变量。

### 状态文件日志

- Pipeline 子进程结果继续写入 manifest `task.result`。
- Progress 只记录阶段状态、最后错误和验收结果。
- Handoff 只记录输入、输出、目标和状态。
- 不新增带随机 `run_id` 的第二套状态文件。

### 确定性映射

| 发射点 | 关键字段 | 允许变化 |
|--------|----------|----------|
| `workflow context` | 路径、存在性、stage | 文件是否存在 |
| `workflow run` | stage、任务计数、exit code | 任务状态与结果 |
| `workflow resume` | task id、reset ids、是否 recraft | 输入参数与失败类型 |
| `workflow validate` | schema、errors[] | 校验错误内容 |
| `workflow status` | summary、failures[] | manifest/progress 当前状态 |

同一输入和同一文件状态必须产生相同字段结构、相同阶段分类和相同 `next_action`。

---

## RTK Filter Presets

推荐用 `rtk gain` 记录以下命令，只保留失败行、测试摘要和耗时，避免吞掉大段测试输出：

```bash
rtk gain -- python -m unittest discover -s cli -p 'test_*.py'
rtk gain -- python cli/gamefactory.py workflow --help
rtk gain -- python cli/gamefactory.py workflow context --brief resources/asset-brief.example.json --json
rtk gain -- git diff --check
```

过滤策略：

- 测试：保留 `FAILED`、`ERROR`、失败测试名、pass/fail 汇总。
- CLI smoke：保留退出码和完整 JSON，不保留人类提示冗余。
- 删除扫描：保留仍命中的 GUI/Agent/ACP 引用路径。
- Git：只保留 diff 摘要和 whitespace 错误。

---

## Critical Patterns Check

已扫描 `docs/solutions/patterns/critical-patterns.md`。

- ❌ 旧 ACP JSON-RPC id 匹配逻辑不得迁入 Workflow。
- ✅ ACP、permission bridge 和 Hermes 运行时整体删除；Workflow 不使用 JSON-RPC。
- ❌ 不得通过隐式 GUI permission card 放行危险命令。
- ✅ `shell`、删除、配置写入继续使用显式确认或白名单；外部 Agent 使用自身权限体系。
- ❌ 不得复制 Pipeline 失败分类。
- ✅ Workflow 复用 `pipeline_heal`、`reset_task_cascade` 和 `run_pipeline`。
- ❌ 不得穿透模块边界直接改 manifest 内部字段。
- ✅ Workflow 只调用各模块公开函数，状态由原模块保存。

---

## Simplicity Audit

### 50% 删除测试

本方案仍可进一步删除而满足需求：

- 不建立独立 Workflow 状态库，复用 manifest/progress。
- 不建立通用 DAG，复用 Pipeline manifest。
- 不建立每家 Agent 的适配器，只提供一份 Skill。
- 不建立 GUI 替代品，不保留只读面板。
- 不建立 RPC/队列/微服务。
- `workflow` 只保留 `context/init/run/resume/status/validate` 六个窄命令。

若实现阶段出现以下情况，删除而不是扩展：

- 新状态文件与 manifest/progress 重复。
- Skill 内出现业务公式或失败分类表。
- GUI 代码以“兼容层”形式残留。
- 每种外部 Agent 出现独立命令或 Prompt 分支。
- Workflow 复制 Pipeline 的重试、级联 reset 或校验逻辑。

### 可删除范围

- 整个 `gui/`。
- `start-gui.sh`、`start-gui.bat` 及 GUI Release 脚本。
- `agent` / `agents` / `hermes` 命令组和对应运行时模块。
- `host_chat`、brief chat session、Pi RPC、ACP session manager。
- executor 安装、同步、实例 roster、GUI-only Provider 编排。
- 只服务于内置同事的测试、文档、Skill 和配置。

### 必须保留

- Brief/分册/场景/系统/资产结构与校验。
- Production derive/validate/delta。
- Pipeline plan/run/status/reset/retry/heal。
- Prompt craft、image/video/matting、Godot assemble/scaffold/validate。
- Progress、Handoff、Asset Review、Test。
- Provider/API Key 配置和本机工具链检测。
- 通用 External Agent Skill。

---

## 任务 DAG

```text
T1 基线测试与删除清单
        │
        ├──────────────┐
        ▼              ▼
T2 删除 GUI        T3 删除内置 Agent 运行时
        │              │
        └──────┬───────┘
               ▼
T4 Brief 确定性入口与 CLI 收口
               │
               ▼
T5 Workflow 六命令与 JSON 合同
               │
               ▼
T6 通用外部 Agent Skill + 中文文档
               │
               ▼
T7 全量测试、删除扫描、端到端 smoke
```

## 并行执行计划

| Layer | Parallel Group | Tasks | 执行方式 | 原因 |
|-------|----------------|-------|----------|------|
| 1 | G1 | T1 | 串行 | 先冻结基线 |
| 2 | G2 | T2、T3 | 可并行 | GUI 与 Agent 运行时写集基本分离，但共享 CLI 注册点须在 T4 收口 |
| 3 | G3 | T4 | 串行 | 依赖 T2/T3 后的剩余入口 |
| 4 | G4 | T5 | 串行 | 依赖稳定 CLI 合同 |
| 5 | G5 | T6 | 串行 | 依赖最终命令 |
| 6 | G6 | T7 | 串行 | 总验收 |

## 任务列表

### 任务 T1：基线测试与删除清单

- **Layer**：1 · **Parallel Group**：G1 · **Execution**：串行
- **Ownership**：只读扫描 + 本 Plan 元数据
- **Read Set**：`gui/`、CLI 命令注册、测试、文档、脚本
- **Write Set**：本 Plan 执行元数据；不改业务代码
- **状态**：已完成
- **描述**：记录当前测试入口、GUI/Agent 引用清单、必须保留的 Pipeline/Brief 测试集合。
- **验收**：
  - [x] 已确认当前分支为 `codex/pure-workflow-toolkit`，工作区初始仅包含本 Plan 与 Brainstorm 两份未跟踪文档，未触碰 `master`。
  - [x] 已形成可检索的删除、保留与共享注册风险清单。
  - [x] 已运行只读 CLI 基线命令；未联网、未生成资产。
  - [x] `git diff --check` 通过；除本 Plan 外未修改任何文件。
- **依赖**：无

#### T1 删除清单（待 T2/T3 执行）

- **GUI / Electron / React / Vite / ACP / Pi RPC / roster / executor 整链**：删除 `gui/**`（141 个 tracked 文件，含 34 个 `*.test.mjs|*.test.ts|*.test.tsx`，覆盖 `gui/electron/*` 的 ACP、Pi RPC、Codex/Hermes/Cursor session、roster/executor UI、React/Vite 源码、`gui/package.json`、`package-lock.json`、`vite.config.ts`、installer 与 GUI 测试）；删除根目录 `start-gui.sh`、`start-gui.bat` 和 `gui/start-gui.*`。
- **GUI Release 链**：删除 `scripts/build-release.sh`、`scripts/build-release.bat`、`scripts/electron-after-pack.mjs`、`scripts/prepare_embedded_pi.mjs`；清理 `.gitignore` 的 `gui/node_modules/`、`gui/dist/`、`gui/runtime/`、`gui/release/`。本机未跟踪的 `gui/node_modules/`、`gui/runtime/`、`gui/release/` 随目录删除。
- **内置 Agent/Host/Pi/Hermes/executor 运行时**：删除 `cli/agent_auth_resolve.py`、`agent_cmds.py`、`agent_routing.py`、`agent_turn.py`、`agents_executors_upsert.py`、`agents_instances_upsert.py`、`executor_models.py`、`executor_setup.py`、`hermes_cmds.py`、`hermes_pack.py`、`host_chat.py`、`host_cmds.py`、`cli/host/`、`pi_foundry_tools.py`、`pi_runtime.py`、`conversations_cmds.py`、`conversations_ops.py` 及其直接测试 `test_agent_*`、`test_agents_*`、`test_executor_*`、`test_hermes_portability.py`、`test_host_chat.py`、`test_host_retry_asset.py`、`test_host_run_assets.py`、`test_pi_*`、`test_topic_brainstorm.py`。
- **Agent 会话型 Brief 入口（T4 收口）**：审查并删除 `brief chat`、`brief brainstorm` 的 session/turn/export 注册，以及 `brief_brainstorm.py`、`topic_brainstorm.py` 和对应 session 测试；保留同一文件中的 `validate`、`shard`、`search`、`related`、`visual-target`、`ui-wireframe` 等确定性入口。
- **配置与探测中的 executor 分支**：从 `cli/setup_cmds.py` 删除 `setup agents`、`setup executor`、`setup pi`，从 `cli/doctor_cmds.py` / `env_discover.py` 删除 Hermes/Codex/Cursor executor 探测；保留 `setup check|ensure|install`、`setup provider`、Toolchain/Provider/`capabilities` 探测。
- **当前操作文档与品牌专属资源**：删除或改写 `docs/GUI-CONFIG.md`、`docs/HOST-CHAT-PRODUCT.md`、`docs/HERMES-CODEX.md`、`docs/AGENT-ROUTING.md`、`docs/RELEASE.md`、`resources/agents.example.json`、`resources/hermes/**`、`resources/skills/orchestrator/host-chat.md`；历史 Release/Anvil 文档仅迁入 archive 或标注“已移除”，不继续作为操作说明。根 `README.md`、`AGENTS.md`、`ROADMAP.md`、`docs/README.md`、`docs/TOOLS.md` 和架构文档改写为外部 Agent 入口。

#### T1 保留清单

- **Brief / 场景 / 系统 / 资产**：保留 `brief.py`、`brief_cmds.py` 的确定性命令、`brief_shards.py`、`brief_localize.py`、`visual_target.py`、`display_size.py`、`asset_sizing.py`、`assets_manifest.py`、`asset_review.py`、`assets_cmds.py`、`asset_pipeline.py`、`genre_presets.py` 及 `test_brief_contract.py`、`test_brief_scenes_systems.py`、`test_brief_shards.py`、`test_brief_animation.py`、`test_brief_transitions.py`、`test_ui_panels.py`、`test_asset_*`、`test_assets_manifest.py`、`test_unknown_asset_type_validate.py`。
- **Production / Pipeline / Prompt craft / media**：保留 `production.py`、`production_cmds.py`、`pipeline_*.py`、`prompt_craft.py`、`prompt_cmds.py`、`media_prompt_profile.py`、`matting_validate.py`、`frame_sequence.py`、`image_cmds.py`、`video_*.py`、`generation_fingerprint.py`、`shared_context.py`、`roles.py`、`skill_loader.py`；保留 `test_production*`、`test_pipeline_*`、`test_prompt_craft*`、`test_media_prompt_profile.py`、`test_matting_validate.py`、`test_frame_sequence.py`、`test_video_*`、`test_visual_target.py`、`test_content_class.py`、`test_style_group.py`、`test_art_tokens.py`。
- **Godot / Progress / Handoff / Asset Review / Test**：保留 `godot_*.py`、`progress.py`、`handoff.py`、`asset_review.py`、`assets_cmds.py`、`test_cmds.py`、`unit_test.py`、`playtest_plan.py`、`task_playtest.py`、`regression.py`、`test_analysis.py`；保留 `test_godot_*`、`test_progress.py`、`test_handoff.py`、`test_asset_review.py`、`test_playtest_plan.py`、`test_task_playtest.py`、`test_regression.py`、`test_analysis.py`、`test_unit_test.py`、`test_e2e_smoke.py`。
- **安全与配置边界**：保留 `config_cmds.py` 的 allowlist、`shell_cmds.py` / `safe_cli.py` / `tool_permission.py` 的显式确认与白名单、Provider/API Key 配置、FFmpeg/Godot/.NET 工具链检测；仅清理其中指向 GUI/executor 的说明。

#### T1 当前 CLI 测试与示例 Brief 基线

| 验证命令 | 结果 |
|----------|------|
| `python cli/gamefactory.py --help` | 通过；当前仍注册 `agent`、`agents`、`hermes`、`host`、`conversations` 等待删除入口，符合 T1 基线记录目的。 |
| `cd cli && python -m unittest discover -s . -p 'test_*.py'` | 基线为 998 tests：1 failure、4 errors、2 skipped。既有失败为 `test_brief_transitions.test_magic_prince_requires_graph`（缺少 `resources/magic-prince-brief.json`）、3 个 `test_visual_target` CJK guard errors、`test_env_discover.test_codex_missing_without_cli`（本机已安装 Codex）。 |
| `cd cli && python -m unittest -q test_brief_contract test_brief_scenes_systems test_brief_shards test_production test_pipeline_manifest test_pipeline_runner test_prompt_craft test_media_prompt_profile test_matting_validate test_godot_scaffold test_progress test_handoff test_asset_review test_analysis test_unit_test` | 通过：158 tests。 |
| `cd cli && python gamefactory.py brief validate --brief ../resources/asset-brief.example.json --json` | 退出码 1；JSON 为 `{"ok": false, "gaps": ["project.visual_reference file not found: resources/forest-platformer-reference.png ..."], "warnings": []}`。该 fixture 基线缺口留给 T4/T7 修复，不在 T1 改业务文件。 |

#### T1 T2/T3 共享注册点与风险

- `cli/gamefactory.py` 是 T2/T3 的共享 Composition Root：`hermes_group`、`agents_group`、`host_group`、`register_agent_commands`、`register_conversations_commands` 需删除；`pipeline`、`brief`、`production`、`project`、`assets`、`godot`、`test`、`prompt` 注册必须保留，T5 再在此注册 `workflow`。
- `cli/brief_cmds.py` 同时导入 `host_chat`、`brief_brainstorm`、`topic_brainstorm` 与确定性 Brief 模块；T3 直接删文件会破坏 import，必须在 T4 同步拆分命令注册，不能只删模块。
- `cli/setup_cmds.py` 同时承载 Toolchain/Provider 与 `agents`/`executor`/`pi`；T3 只删后半段。`roles.py`、`shared_context.py`、`skill_loader.py` 被 Pipeline、Prompt craft、Godot、Visual Target 复用，不能按 `agent` 语义误删。
- T2/T3 虽可并行，但共享根 README、`.gitignore` 和历史文档清理；并行时分别拥有 GUI 路径与 CLI 注册/config 写集，文档冲突统一延后到 T4/T6 合并。

### 任务 T2：删除 GUI 与 GUI Release 链

- **Layer**：2 · **Parallel Group**：G2 · **Execution**：可与 T3 并行
- **Ownership**：`gui/`、`start-gui.*`、GUI 打包脚本、GUI 文档入口
- **Read Set**：T1 清单、`gui/package.json`、构建脚本
- **Write Set**：删除 GUI 目录及直接依赖；更新根 README 的启动方式
- **状态**：已完成
- **描述**：移除 Electron/React/Vite/ACP UI、GUI-only 测试和发布入口。
- **成功标准**：仓库内不存在可运行 GUI；`rg` 不再发现作为入口要求的 `start-gui`；CLI 测试不受影响。
- **依赖**：T1

### 任务 T3：删除内置 Agent 运行时

- **Layer**：2 · **Parallel Group**：G2 · **Execution**：可与 T2 并行
- **Ownership**：`agent*`、`host_chat*`、`hermes*`、`pi_*`、ACP/executor 相关模块与测试
- **Read Set**：T1 清单、`gamefactory.py` 命令注册、config/doctor/setup
- **Write Set**：删除运行时模块、命令注册、Agent executor 配置和对应测试；保留 Provider/API 配置
- **状态**：已完成
- **描述**：移除内置同事对话、Agent dispatch、Pi/Hermes/Cursor/Codex 执行器、ACP 权限桥和 roster。
- **成功标准**：CLI help 不再出现 `agent`、`agents`、`hermes`；配置/doctor 不再要求 executor；保留媒体生成所需 Provider 配置。
- **依赖**：T1

### 任务 T4：Brief 确定性入口与 CLI 收口

- **Layer**：3 · **Parallel Group**：G3 · **Execution**：串行
- **Ownership**：`brief_cmds.py`、`brief.py`、`gamefactory.py`、相关测试/文档
- **Read Set**：T2/T3 后入口；Brief 分册和现有验证逻辑
- **Write Set**：删除聊天 session 依赖；增加/恢复 `brief freeze`；保留 validate/shard/visual-target 等确定性命令
- **状态**：已完成
- **描述**：外部 Agent 可直接从 draft JSON 冻结 Brief；不再通过内置对话写设计。
- **成功标准**：示例 Brief 可 `validate`；draft 可 `freeze` 为带 `brief_meta` 的 Brief；CLI help 只暴露确定性命令。
- **依赖**：T2、T3

### 任务 T5：Workflow 六命令与 JSON 合同

- **Layer**：4 · **Parallel Group**：G4 · **Execution**：串行
- **Ownership**：新增 `cli/workflow/`、`workflow_cmds.py`、对应测试
- **Read Set**：Brief/Production/Pipeline/Progress/Handoff 公开接口
- **Write Set**：`context`、`init`、`run`、`resume`、`status`、`validate`；JSON schema 测试
- **状态**：已完成
- **描述**：只做组合和归一化；复用现有状态与失败恢复。
- **成功标准**：六个命令均有 `--json`；相同文件状态返回相同结构和 `next_action`；不新增第二份权威状态。
- **依赖**：T4

### 任务 T6：通用外部 Agent Skill 与中文文档

- **Layer**：5 · **Parallel Group**：G5 · **Execution**：串行
- **Ownership**：`resources/skills/gamefactory-toolkit/SKILL.md`、根 README、`docs/README.md`、`docs/AI-HANDOFF.md`
- **Read Set**：T5 最终命令、JSON 合同、文件契约
- **Write Set**：一份通用 Skill；重写项目定位、Quick Start、外部 Agent 工作流；删除 GUI/同事叙事
- **状态**：已完成
- **描述**：Skill 只写读取顺序、命令、失败分类、权限边界和输出要求；正文使用中文。
- **成功标准**：外部 Agent 可仅凭 Skill + CLI help 完成 context → validate → init → run → status/resume；不含凭据或品牌专属运行时假设。
- **依赖**：T5

### 任务 T7：全量测试、删除扫描与端到端 smoke

- **Layer**：6 · **Parallel Group**：G6 · **Execution**：串行
- **Ownership**：测试清单、本 Plan 状态、必要 README 修正
- **Read Set**：全部改动
- **Write Set**：失败测试、删除残留、Plan 执行状态
- **状态**：已完成
- **描述**：运行保留的 CLI 单测、Workflow JSON 测试、示例 Brief smoke 和删除扫描。
- **成功标准**：见 §通过条件；所有删除扫描为零；`git diff --check` 通过。
- **依赖**：T6

---

## 验收命令

```bash
git branch --show-current
git status --short
git diff --check

cd cli
python -m unittest discover -s . -p 'test_*.py'
python gamefactory.py --help
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json --json
python gamefactory.py workflow context --brief ../resources/asset-brief.example.json --json
python gamefactory.py workflow validate --brief ../resources/asset-brief.example.json --json
```

删除扫描：

```bash
rg -n "start-gui|Electron|electron|ACP|Pi RPC|agent turn|host-chat|executor" \
  README.md docs cli resources scripts -g '*.md' -g '*.py' -g '*.sh' -g '*.bat'
```

允许保留的历史文档引用必须明确标注为“已移除”或迁入 archive；不得仍作为当前操作说明。

## T7 最终验收记录

| 检查 | 结果 |
|------|------|
| 分支 / 基线 | `codex/pure-workflow-toolkit`；`main` 与 `origin/main` 开始/结束 SHA 均为 `f26aa70caa302a64a8ca58f6ccde5dc340c99451`；无 `master` ref |
| 编译 | `python -m compileall -q .` → 0 |
| 全量测试 | `594 tests`、`0 failures`、`4 errors`、`2 skipped`；仅允许的 4 个 T1 基线 errors，且已在独立 `git archive HEAD` 基线复现 |
| Workflow help | `workflow` + `context/init/run/resume/status/validate` 六个子命令均退出 0，均提供 `--json` |
| 只读 smoke | `context/validate/status` 调用前后 `git status` 快照与 brief/临时 manifest SHA 完全不变；status 示例为 `ok=true/status=pending/next_action=run`（`ok/pending/run`） |
| 示例 Brief | `resources/asset-brief.example.json` 缺 `resources/forest-platformer-reference.png`，`context/validate` 按既有 fixture 缺口返回 `brief_invalid`，未修改业务 fixture |
| 删除扫描 | 当前操作文件仅命中“已移除”说明；命令注册无 `agent/agents/hermes`；`gui/`、`start-gui.*`、Release GUI 脚本均不存在 |
| 历史标记 | `docs/README`、Release、solutions、Anvil/Superpowers 索引均标明历史/已移除，不作为当前入口 |
| 文档链接 | README / AGENTS / Skill 相对链接 `12 checked, 0 broken` |
| 根 README | 已明确“供外部 Agent 使用的纯 CLI / Workflow 工具箱” |
| 格式 | `git diff --check` → 0 |

## Review Fix A/B/C 验收

| 修复 | 验收结果 |
|------|----------|
| Fix A — Workflow 合同、真实只读与 `init` 边界 | `status` 仅使用 `pending/running/done/paused/blocked/failed`；`next_action` 仅使用 `none/freeze_brief/derive_production/run/resume/recraft_prompt/fix_input/human_review`；`failures[].kind` 仅使用 `validation/network/dependency/config/unknown`；`context/status/validate` 只读；`init` 中途失败可回滚且报告残留；Quick Start 先校验后初始化 |
| Fix B — shell 与 active Skill 收尾 | `shell run` JSON 失败结果在输出后按 `result.exit_code/result.ok` 返回非零；指定 shell 测试通过；active Skill 删除入口扫描通过；审查 artifact 目录已删除 |
| Fix C — 当前文档合同同步 | AGENTS、Workflow/Pipeline 操作文档与 active Skill 已移除旧状态和旧命令；当前操作文件旧枚举/旧入口扫描为零；六命令 help 与只读 smoke 复验通过 |
| Fix D — Pipeline 分诊去品牌化 | `owner=external_agent`、`needs_external_agent`、`triage_*`；`host.run_assets` 停止原因改为 `needs_external_agent`；当前 runtime 与测试旧词扫描为零 |
| Fix E — Handoff/路径/GUI 幽灵语义清理 | Handoff、project paths、CLI help、brief/visual-target 注释与操作文档均改为外部 Agent/CLI 语义；相关定向测试与入口扫描通过 |
| Fix F — shell 凭据形态补强 | `OPENAI_API_KEY=`、`--token value`、timeout、cwd、JSON/text 输出全部脱敏；`test_shell_run` 9/9 通过 |
| Fix G — validate 状态透传 | 合法 manifest 存在时 `workflow validate` 复用 manifest 状态：pending → `pending/run`，failed → `failed/resume`；不再错误指向 human review |

## 通过条件

- [x] 当前分支为 `codex/pure-workflow-toolkit`，`master` 无改动（仓库无 `master` ref；`main`/`origin/main` SHA 未漂移）
- [x] GUI、Electron、React、ACP、Pi RPC 和内置 Agent 运行时从当前入口移除
- [x] CLI 无 GUI/Node/内置 Agent 依赖即可运行
- [x] Brief、场景、系统、资产、Production、Pipeline、Godot、Test 契约保留
- [x] `workflow context/init/run/resume/status/validate` 六命令和 `--json` 合同完整
- [x] Workflow 不创建第二份权威状态，不复制 Pipeline 恢复逻辑
- [x] 通用 External Agent Skill 为中文协议文档，不绑定具体 Agent 运行时
- [x] 变更范围测试全部通过；全量 594 tests、0 failures、2 skipped，仅保留 4 个已在基线独立复现的 T1 errors；示例 Brief 因既有视觉参考 fixture 缺口按合同返回 `brief_invalid`
- [x] 删除扫描无当前操作入口残留
- [x] 根 README 明确项目是“供外部 Agent 使用的纯 CLI / Workflow 工具箱”

---

Stage 5 已 `APPROVED`，Stage 6 compound 已完成；未经用户明确要求不 commit。
