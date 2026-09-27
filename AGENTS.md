# Game AI Foundry — External Agent One-pager

本仓库是给外部 Agent 使用的纯 CLI / Workflow 工具箱。不要假设任何桌面客户端、内置会话或品牌专属运行时。

## 读取顺序

1. 读取 [`resources/skills/gamefactory-toolkit/SKILL.md`](resources/skills/gamefactory-toolkit/SKILL.md)。
2. 运行 `python cli/gamefactory.py workflow --help` 和需要的子命令 `--help`。
3. 按 `context → validate → init → run → status → resume` 调用，全部加 `--json`。
4. 只把 `manifest`、`progress`、`handoff`、`assets-manifest`、`validation report` 当作状态。

## 最小命令

```bash
.\gamefactory.cmd workflow context --brief <brief> --json
.\gamefactory.cmd workflow validate --brief <brief> --json
.\gamefactory.cmd workflow init --brief <brief> --json
.\gamefactory.cmd workflow run --manifest <manifest> --stage assets --detach --json
.\gamefactory.cmd workflow status --manifest <manifest> [--job-id <job_id>] --json
.\gamefactory.cmd workflow resume --manifest <manifest> --task-id <task_id> --json
```

首次若无 `.venv`：`py -3 cli/gamefactory.py setup ensure-python --json`，之后不要用裸 `python`（Windows Store stub）。

## 行动规则

1. `ok=false` 或 `next_action=fix_input` 时读取 `failures[].kind/code/message`，先修输入，不继续执行。
2. `status=blocked` 按 `next_action` 处理；`status=failed` 才用 `resume`；`status=paused` 用 `resume`；`pending` 且 `next_action=run` 时再 `run`；`status=running` / `next_action=poll` 时只查同一 job/manifest，禁止再开一轮 `run`。
3. 只有 `status=done` 且 `next_action=human_review` 才进入 assets review、Godot、test。
4. `validate before matting`；图像失败先修 prompt/Brief。
5. 长任务：短超时宿主默认 `workflow run --detach` + `workflow status --job-id`；长超时可用同步阻塞。动画拆帧默认 **24**（3–4s 视频；`duration×6` 可上调；Brief `sprite_frames` 可覆盖）。
6. 动画原始帧、idle 独立 `*_nobg.png`；视频帧用 `video matte-frames --engine ai`；`split-frames` 默认 `optimize_loop`。
7. **导入保清晰**：静帧/动画导入不压到 `display_size`；游戏内大小用 `real_length_cm` / runtime scale。
8. 图片后处理使用 `--input` / `--output`。
9. Godot 只实现 Brief / Production Delta 范围。
10. shell、配置写入、删除和网络请求必须显式确认或走白名单。

## 文档

| 需要 | 文档 |
|---|---|
| 外部 Agent 协议 | [`resources/skills/gamefactory-toolkit/SKILL.md`](resources/skills/gamefactory-toolkit/SKILL.md) |
| CLI 与字段 | [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) |
| 工具链与配置 | [`docs/TOOLS.md`](docs/TOOLS.md) |
| 施工与验收 | [`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md) |
| 迭代 Delta | [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md) |
| Pipeline 阶段 | [`resources/skills/orchestrator/pipeline-schedule.md`](resources/skills/orchestrator/pipeline-schedule.md) |
