# Pipeline — 外部 Agent 路由

本 Skill 只负责把外部 Agent 的判断路由到确定性 `workflow` 与 Pipeline CLI。它不创建单独会话，也不假设任何品牌专属运行时。

## 读取顺序

1. 读取 [`../gamefactory-toolkit/SKILL.md`](../gamefactory-toolkit/SKILL.md)。
2. 运行 `python gamefactory.py workflow --help` 与需要的子命令 `--help`。
3. 需要阶段细节时读取 [`pipeline-schedule.md`](pipeline-schedule.md)。
4. 只读取 `brief.json`、`production.json`、`manifest`、`progress`、`handoff` 与 validation report。

## Workflow 路由

```bash
python gamefactory.py workflow context --brief <brief> --json
python gamefactory.py workflow validate --brief <brief> --json
python gamefactory.py workflow init --brief <brief> --json
python gamefactory.py workflow run --manifest <manifest> --stage assets --json
python gamefactory.py workflow status --manifest <manifest> --json
python gamefactory.py workflow resume --manifest <manifest> --task-id <task_id> --json
```

| `status` | `next_action` | 路由 |
|---|---|---|
| `pending` | `run` | 执行或等待 `--stage assets` |
| `running` | `run` | 只读观察当前执行，不重复启动 |
| `done` | `human_review` | 进入资产审查、Godot 与测试 |
| `paused` | `resume` | 恢复暂停任务 |
| `blocked` | `fix_input` / `derive_production` | 读取 `failures[]` 修输入，或补建缺失状态 |
| `failed` | `resume` | 读取 `failed_ids`，修因后恢复指定 task |

合法 `next_action` 集合仅为：`none`、`freeze_brief`、`derive_production`、`run`、`resume`、`recraft_prompt`、`fix_input`、`human_review`。不得把命令名当成 `next_action` 枚举。

## 确定性阶段

这些是 CLI 步骤，不是内置协作角色：

### Prompt

```bash
python gamefactory.py prompt craft --brief <brief> --asset <asset> -o <plan>
```

`workflow run --run-prompts` 可让现有 runner 调用同一 prompt 模块。

### Image

```bash
python gamefactory.py image generate --plan-file <plan> --output <raw> --validate
python gamefactory.py image trim --input <raw> --output <trimmed>
python gamefactory.py image remove-bg --input <trimmed> --output <nobg>
```

`image validate` 未通过时只修 prompt/Brief，禁止 trim、remove-bg 或组装。

### Video

```bash
python gamefactory.py video generate --plan-file <plan> --reference-image <raw-still> --output <video>
python gamefactory.py video split-frames --input <video> --output <frames-dir>
python gamefactory.py video matte-frames --input <frames-dir> --output <nobg-dir> --engine ai
```

动画输入使用原始 still；idle 使用独立 `*_nobg.png`；视频帧不使用 `image remove-bg`。

### Godot

```bash
python gamefactory.py assets review list --manifest <assets-manifest> --json
python gamefactory.py assets review accept --manifest <assets-manifest> --asset <asset>
python gamefactory.py godot assemble --assemble-file <assemble-file> --validate
python gamefactory.py godot validate --project <project>
```

Godot 只实现冻结 Brief 与已应用 Production Delta 声明的范围。

### Test

```bash
python gamefactory.py test unit --project <project>
python gamefactory.py test plan --brief <brief> -o <playtest>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>
python gamefactory.py test regression --project <project>
```

## 失败分类

| 证据 | 修复方向 |
|---|---|
| `brief_invalid` / `production_invalid` / `manifest_invalid` | 修输入后重新 `workflow validate` |
| `unsupported_stage` | 使用 `--stage assets` |
| `task_failed` | 读取 task result，修因后 `workflow resume` |
| validation pause / `exit 2` | 修 prompt、Brief 或输入，不进入 matting |
| provider / toolchain | `doctor --json`、`setup check --json` |
| Godot / test failure | 对照 Brief、Delta 与 validation report 修复 |

## 输出要求

每轮报告必须包含：

- `command`
- `status`
- `next_action`
- `outputs`
- `failures[]`
- 下一步验证证据

`manifest`、`progress`、`handoff`、`assets-manifest`、`validation report` 是唯一权威状态；不建立第二份状态副本。
