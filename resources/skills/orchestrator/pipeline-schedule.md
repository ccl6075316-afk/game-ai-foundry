# Pipeline Schedule

这是资产阶段的确定性执行顺序。外部 Agent 负责选择阶段、解释失败和修复输入；Pipeline runner 负责按 DAG 执行。

## 0. 前置

```bash
python gamefactory.py workflow context --brief <brief> --json
python gamefactory.py workflow validate --brief <brief> --json
python gamefactory.py workflow init --brief <brief> --json
```

- `context`、`validate`、`status` 只读。
- `init` 只补建缺失的 `production`、`manifest`、`progress`。
- 冻结 Brief 变化后必须重新 `pipeline plan`；保留任务状态时使用 `--merge`。

## 1. Build DAG

```bash
python gamefactory.py pipeline plan \
  --brief <brief> \
  -o <manifest> \
  --output-dir <output-dir> \
  --plans-dir <plans-dir>
```

典型依赖：

```text
prompt.craft
  → image.generate / video.generate
  → image.validate
  → trim / remove-bg / split-frames / matte-frames
  → assemble
  → godot.assemble（可选）
```

动画依赖与 layer 顺序由 Brief 的 `animation_graphs[]`、`assets[]` 决定。

## 2. Dry run 与 Ready

```bash
python gamefactory.py pipeline ready --manifest <manifest> --json
python gamefactory.py workflow run --manifest <manifest> --stage assets --no-auto-fix --jobs 4 --json
```

需要先检查 wave 时：

```bash
python gamefactory.py pipeline run --manifest <manifest> --jobs 4 --dry-run
```

Runner 规则：

1. 取依赖已完成的 `ready` tasks。
2. 最多并行 `--jobs` 个 subprocess。
3. 解析退出码和输出 JSON，写回同一 `manifest`。
4. 按 wave 继续，直到 `complete`、`failed`、`paused` 或 `blocked`。
5. 不把任务状态写入另一份状态文件。

## 3. Prompt 阶段

默认跳过 `prompt.craft`，前提是 `plans/*.json` 已存在。需要生成或重建 prompt 时：

```bash
python gamefactory.py workflow run --manifest <manifest> --stage assets --run-prompts --json
```

单资产调试：

```bash
python gamefactory.py prompt craft --brief <brief> --asset <asset> -o <plan>
```

Prompt 失败通常是输入/模型问题；不要通过跳过验证来“修好”任务。

## 4. 图像阶段

```text
image.generate
  → image.validate
  → image trim
  → image remove-bg
  → image slice / layer output
```

**Validate before matting**：

- `exit 2` 或 validation failure → 修 prompt / Brief。
- 未通过前禁止 trim、remove-bg、slice、assemble。
- 图片后处理必须使用 `--input` / `--output`。

```bash
python gamefactory.py image generate --plan-file <plan> --output <raw> --validate
python gamefactory.py image trim --input <raw> --output <trimmed>
python gamefactory.py image remove-bg --input <trimmed> --output <nobg>
```

## 5. 动画与视频阶段

```text
raw still
  → video generate
  → video split-frames
  → video matte-frames --engine ai
  → walk_frames_nobg / idle_nobg
  → assemble
```

规则：

1. 动画输入使用原始 still，不要先 trim。
2. idle 使用独立 `*_nobg.png`，不要拿第一帧充当 idle。
3. 视频帧使用 `video matte-frames --engine ai`，不要用 `image remove-bg`。
4. 一张图不能包含多个动作帧。

```bash
python gamefactory.py video split-frames --input <video> --output <frames-dir> --frames 8
python gamefactory.py video matte-frames --input <frames-dir> --output <nobg-dir> --engine ai
```

## 6. 组装与 Godot

```bash
python gamefactory.py assets review list --manifest <assets-manifest> --json
python gamefactory.py assets review accept --manifest <assets-manifest> --asset <asset>
python gamefactory.py godot assemble --assemble-file <assemble-file> --validate
python gamefactory.py godot validate --project <project>
```

只有通过 review 的资产才能进入组装。Godot 只实现 Brief / Production Delta 范围。

## 7. Status 与 Resume

```bash
python gamefactory.py workflow status --manifest <manifest> --json
```

| `status` | `next_action` | 动作 |
|---|---|---|
| `pending` | `run` | 运行 ready tasks |
| `running` | `run` | 继续观察，不重复启动 |
| `failed` | `resume` | 读取 `failed_ids`，定点恢复 |
| `paused` | `resume` | 检查阻塞原因后恢复 |
| `blocked` | `fix_input` / `derive_production` | 按 `failures[]` 修输入或补建缺失状态 |
| `done` | `human_review` | 资产审查、Godot、test；无后续时为 `none` |

合法 `status` 仅为 `pending`、`running`、`done`、`paused`、`blocked`、`failed`；合法 `next_action` 为 `none`、`freeze_brief`、`derive_production`、`run`、`resume`、`recraft_prompt`、`fix_input`、`human_review`。

定点恢复：

```bash
python gamefactory.py workflow resume --manifest <manifest> --task-id <task_id> --json
```

需要改 prompt 后恢复时：

```bash
python gamefactory.py workflow resume --manifest <manifest> --task-id <task_id> --recraft-prompt --json
```

底层诊断可用：

```bash
python gamefactory.py pipeline diagnose --manifest <manifest>
python gamefactory.py pipeline suggest-retry --manifest <manifest> --asset <asset> --json
python gamefactory.py pipeline reset --manifest <manifest> --task-id <task_id> --cascade
```

## 8. 验收

```bash
python gamefactory.py test unit --project <project>
python gamefactory.py test plan --brief <brief> -o <playtest>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>
python gamefactory.py test regression --project <project>
```

失败时保存 report、截图和 task result；根据 Brief/Delta 决定修复方向，不修改 manifest 状态冒充完成。

## 9. 输出要求

外部 Agent 报告至少包含：

- `command`、`status`、`next_action`。
- `outputs` 中实际写入/引用的路径。
- `failures[]` 的 `code`、`message`、可选 `task_id`。
- 本轮验证证据与下一步。

不输出凭据，不建立第二份 Pipeline 状态。
