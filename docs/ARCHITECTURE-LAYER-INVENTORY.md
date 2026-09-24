# 当前架构归属清单

> 读者：维护者与外部 Agent。
> 目标：明确“谁判断、谁执行、谁持有状态”，避免把编排逻辑复制进确定性模块。

## 1. 最终形态

```text
外部 Agent
  ├─ 判断、编排、修复
  ↓
resources/skills/gamefactory-toolkit/SKILL.md
  ↓
cli/workflow_cmds.py
  ├─ context / validate：只读发现与校验
  ├─ init：补建缺失状态
  ├─ run / resume：委托现有执行与恢复
  └─ status：只读汇总
  ↓
brief · production · pipeline · godot · test
  ↓
manifest · progress · handoff · assets-manifest · validation report
```

## 2. 模块归属

| 层 | 主要模块 | 职责 | 不该做什么 |
|---|---|---|---|
| Composition Root | `cli/gamefactory.py` | 注册确定性命令组 | 不承载业务策略 |
| Workflow | `cli/workflow_cmds.py`、`cli/workflow/` | 组合、归一化 JSON、委托执行 | 不复制 DAG/状态机 |
| Brief Contract | `brief.py`、`brief_cmds.py`、`brief_shards.py` | 读取、校验、冻结、分册 | 不保存聊天记忆 |
| Production | `production.py`、`production_cmds.py` | Brief → 工程蓝图、Delta 合并 | 不越 Brief 范围 |
| Pipeline | `pipeline_*.py` | DAG 构建、ready、run、reset、record | 不另建任务数据库 |
| Progress / Handoff | `progress.py`、`handoff.py` | 跨会话任务与验收账本 | 不靠会话自述标完成 |
| Assets Review | `asset_review.py` | review 行、accept/replace/regenerate | 不隐藏未审查状态 |
| Godot | `godot_*.py` | scaffold、assemble、validate | 不扩展玩法 |
| Test | `test_*.py` | unit、play、vision、regression | 不修改设计目标 |
| Environment | `setup_*`、`doctor`、`config` | 工具链、Provider、受限配置 | 不保存凭据到报告 |

## 3. 文件事实源

| 文件 | 权威内容 | 写入者 |
|---|---|---|
| `brief.json` + shards | 冻结设计契约 | `brief freeze` / 明确的 Brief 修改 |
| `production.json` | 工程蓝图 | `production derive` / `apply-delta` |
| `manifest` | 资产 DAG 与 task status | `pipeline plan/run/reset/record` |
| `progress.json` | 施工与验证进度 | `project progress` |
| `handoff` | 一次任务的范围与完成条件 | `project handoff` |
| `assets-manifest` | 资产交付与 review | Pipeline / `assets review` |
| `validation report` | L0–L4 验收证据 | `godot` / `test` |

Workflow 不创建平行状态。所有恢复必须回到这些文件。

## 4. 边界不变量

1. `workflow context/status/validate` 不写盘。
2. `workflow init` 只补缺失文件，不覆盖已有 `production`、`manifest`、`progress`。
3. `workflow run/resume` 只委托现有 asset runner / retry runner。
4. 所有外部 Agent 命令支持 `--json`，顶层字段稳定。
5. `exit 2` 继续表示可修复校验暂停。
6. Brief → Production → Pipeline → Godot → Test 单向派生；下游不能静默改上游契约。
7. shell、配置写入、删除、网络请求保留显式确认或白名单。

## 5. 可扩展方式

- 新增 Workflow stage：扩展 `--stage` 与 JSON 合同，复用对应现有模块。
- 新增失败恢复：在现有 manifest result / retry 分类上增加稳定 `failures.code`。
- 新增文档入口：先更新 [`README.md`](README.md)、[`docs/README.md`](README.md) 与通用 Skill，避免入口分叉。
- 新增状态字段：先确认它是哪份权威文件的自然扩展，不建立新副本。

## 6. 验收标准

- `python cli/gamefactory.py workflow --help` 可用。
- 六个子命令均支持 `--json`。
- 同一文件状态得到相同 `status` / `next_action`。
- 只读命令前后磁盘快照不变。
- 删除扫描无当前操作残留。
- Pipeline/Brief/Godot/Test 核心测试通过。

相关文档：[`ARCHITECTURE-REFACTOR-HANDOFF.md`](ARCHITECTURE-REFACTOR-HANDOFF.md)、[`AI-HANDOFF.md`](AI-HANDOFF.md)、[`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md)。
