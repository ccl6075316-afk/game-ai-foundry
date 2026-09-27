# Game AI Foundry

**供外部 Agent 使用的纯 CLI / Workflow 工具箱**：确定性游戏生产工具，负责 Brief、Production、Pipeline、Godot 与测试验收。

架构入口：

```text
外部 Agent → gamefactory-toolkit Skill → workflow CLI
           → brief / production / pipeline / godot / test
           → JSON 文件状态
```

外部 Agent 负责判断、编排和修复；本项目只提供校验、初始化、执行、恢复与验收。

## Quick Start

```bash
# 1) 准备仓库本地 Python（避开 Windows Store stub）
py -3 cli/gamefactory.py setup ensure-python --json
# 2) 配置
copy resources\config.example.json %USERPROFILE%\.gamefactory\config.json

# 3) 之后一律用 launcher（不要裸调 python）
.\gamefactory.cmd doctor --json
.\gamefactory.cmd workflow context --brief resources/asset-brief.example.json --json
.\gamefactory.cmd workflow validate --brief resources/asset-brief.example.json --json
```

仅当上一条校验通过并返回 `ok=true` 且 `failures=[]` 后才继续 `init`；当前示例 Brief 若缺少视觉参考会返回 `ok=false`，必须先按 `failures` 修复，不能带着失败继续初始化。

```bash
.\gamefactory.cmd workflow init --brief resources/asset-brief.example.json --json
.\gamefactory.cmd workflow run --manifest <manifest> --stage assets --json
.\gamefactory.cmd workflow status --manifest <manifest> --json
.\gamefactory.cmd workflow resume --manifest <manifest> --task-id <task_id> --json
```

`status=failed` 才进入 `resume`；`status=done` 且 `next_action=human_review` 后进入资产审查、Godot 和测试：

```bash
python gamefactory.py assets review list --manifest <assets-manifest> --json
python gamefactory.py godot validate --project <project>
python gamefactory.py test unit --project <project>
python gamefactory.py test regression --project <project>
```

无 GUI 时可直接快捷运行游戏：

```bash
python gamefactory.py play
python gamefactory.py play --project fishing-2d
python gamefactory.py run-game --project projects/fishing-2d/game --skip-build
```

在仓库根目录运行 `python gamefactory.py ...`；也可以进入 `cli/` 后运行 `python gamefactory.py ...`。`play` 与 `run-game` 等价。未传项目时优先使用当前目录工程，再按最新 progress 和唯一候选自动解析；存在多个候选时必须显式指定项目。`--dry-run` 只打印解析结果，不启动 Godot。

## 主要能力

| 能力 | 入口 |
|---|---|
| Brief 冻结与校验 | `brief freeze`、`brief validate`、`brief shard`、`brief visual-target` |
| 工程蓝图 | `production derive`、`production validate`、`production delta`、`production apply-delta` |
| 续作账本 | `project progress`、`project handoff` |
| 资产 DAG | `pipeline plan`、`pipeline run`、`pipeline reset`、`pipeline status` |
| 资产审查 | `assets review list`、`accept`、`replace`、`regenerate` |
| Godot | `play` / `run-game`、`godot scaffold`、`godot assemble`、`godot validate` |
| 验收 | `test unit`、`test plan`、`test play`、`test regression` |

## 文档

- 通用外部 Agent 协议：[`resources/skills/gamefactory-toolkit/SKILL.md`](resources/skills/gamefactory-toolkit/SKILL.md)
- 操作手册：[`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md)
- 工具与配置：[`docs/TOOLS.md`](docs/TOOLS.md)
- 迭代与 Delta：[`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md)
- 文档索引：[`docs/README.md`](docs/README.md)

## Prerequisites

Python 3.11+、LLM / 生图 / 生视频 Provider、FFmpeg、Godot、.NET。环境检测：

```bash
python gamefactory.py setup check --json
python gamefactory.py doctor --json
```

## License

MIT
