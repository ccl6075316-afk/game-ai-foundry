# gamefactory-toolkit

供外部 Agent 使用的通用工具箱协议。正文使用中文；命令、路径、JSON 字段与枚举值使用英文。

## 读取顺序

1. 读取冻结后的 `brief.json`，以及已有 `production.json`、`manifest.json`、`progress.json`、`handoff`。
2. 运行 `workflow context --brief <brief> --json`，确认路径、文件存在性和当前阶段。
3. 运行 `workflow validate --brief <brief> [--production <production>] [--manifest <manifest>] --json`。
4. `context` 或 `validate` 返回 `ok=false` 时立即停止，按 `failures[].kind` 与 `failures[].message` 修复后再重试，禁止继续 `init`。
5. 两者均 `ok=true`，且 `next_action=derive_production` 时运行 `workflow init`；它只补建缺失状态，不覆盖已有文件。
6. 初始化成功且 `status=pending` 或 `status=running` 时运行 `workflow run --stage assets`。
7. 每轮执行后运行 `workflow status --manifest <manifest> --json`。
8. `status=failed` 时用 `workflow resume --task-id <id>`；`status=done` 且 `next_action=human_review` 后进入资产审查、Godot 与测试。

若输入仍是 Draft JSON，先执行 `brief freeze --input <draft> -o <brief> --json`；冻结后的 Brief 是下游唯一设计契约。

## 六个 Workflow 命令

```bash
python gamefactory.py workflow context --brief <brief> --json
python gamefactory.py workflow validate --brief <brief> [--production <production>] [--manifest <manifest>] --json
python gamefactory.py workflow init --brief <brief> [--manifest <manifest>] --json
python gamefactory.py workflow run --manifest <manifest> --stage assets --json
python gamefactory.py workflow status --manifest <manifest> --json
python gamefactory.py workflow resume --manifest <manifest> --task-id <task_id> --json
```

`run` 当前只支持 `--stage assets`。`--auto-fix` 是现有资产修复策略；`--run-prompts` 仅在需要生成 prompt 时开启；`--jobs` 控制并行度。

## JSON 顶层合同

所有 `--json` 输出是单个 JSON 对象，固定包含：

```json
{
  "schema_version": 1,
  "ok": true,
  "command": "context",
  "stage": "design",
  "status": "done",
  "next_action": "derive_production",
  "inputs": {},
  "outputs": [],
  "summary": {},
  "failures": []
}
```

- `ok`：本命令是否成功；外部 Agent 必须以此决定是否继续。
- `status` 仅允许：`pending`、`running`、`done`、`paused`、`blocked`、`failed`。
- `stage` 仅允许：`design`、`production`、`assets`、`assemble`、`implement`、`validate`。
- `next_action` 仅允许：`none`、`freeze_brief`、`derive_production`、`run`、`resume`、`recraft_prompt`、`fix_input`、`human_review`。
- `failures[].kind` 仅允许：`validation`、`network`、`dependency`、`config`、`unknown`；无法判断时必须使用 `unknown`。
- `inputs`：本次命令解析后的输入路径与选项。
- `outputs`：本次命令写入或引用的文件路径。
- `summary`：命令特有摘要；manifest 状态在 `summary.manifest`。
- `failures`：错误数组；每项必须有 `code`、`kind` 和 `message`，任务失败可带 `task_id`。

## Exit code 与只读边界

- `ok=true`：通常退出码 `0`。
- `ok=false`：退出码 `1`；不要把非零退出码解释成“任务完成”。
- `workflow context`、`workflow status`、`workflow validate` 是只读命令，不修改磁盘。
- `workflow init` 只创建缺失的 `production`、`manifest`、`progress`，并保留已有内容。
- `workflow run`、`workflow resume` 会推进现有任务状态并写入既有状态文件。
- `brief freeze`、`production derive`、`pipeline plan/run`、`godot`、`test` 等命令按各自 `--help` 的输入输出边界执行。

## 权威状态与权限边界

`manifest`、`progress`、`handoff`、`assets-manifest`、`validation report` 是唯一权威状态。禁止另建状态副本、队列、数据库或聊天记忆；外部 Agent 只能读取和更新这些文件已有的状态字段。

只读命令不需要写权限。写入、删除、配置变更、网络请求和 shell 命令必须使用命令本身的显式确认参数或白名单边界；不要伪造 `--i-confirm`，不要把凭据写入报告或日志。

## 失败分类与修复建议

| `code` / 状态 | `kind` | 含义 | 修复建议 |
|---|---|---|---|
| `workflow_error` | `unknown` | 路径、JSON 或未分类错误 | 检查 `inputs` 与文件存在性，修正后重试 |
| `brief_invalid` | `validation` | Brief 结构或引用不完整 | 修正 Draft/frozen Brief 后重新 `brief freeze` 或 `workflow validate` |
| `production_invalid` | `validation` | Production 与 Brief 不一致 | 重新 `production derive`，或修正 Delta 后再校验 |
| `manifest_invalid` | `validation` | DAG、依赖或 task status 非法 | 重新 `pipeline plan`；保留已有状态时使用 `--merge` |
| `unsupported_stage` | `config` | 当前只支持 `assets` | 改用 `--stage assets` |
| `task_failed`、`status=failed` / `next_action=resume` | `unknown` | 某个 manifest task 失败 | 读取 `summary.manifest.failed_ids`，执行 `workflow resume --task-id <id>` |
| `run_failed`、`resume_failed` | `unknown` | 运行器无法继续 | 查看 `summary.runner`、`run_exit_code` 和日志，修复工具链/输入后重试 |
| `exit 2` / validation | 生成或校验被门禁暂停 | 先修 prompt、Brief 或输入，不要强行做抠图/后处理 |
| provider/toolchain | API、FFmpeg、Godot、.NET 缺失 | 运行 `doctor --json`、`setup check --json`，按缺口修复 |

## 后续入口

`status=done` 且 `next_action=human_review` 后按顺序审查和验收：

```bash
python gamefactory.py assets review list --manifest <assets-manifest> --json
python gamefactory.py assets review accept --manifest <assets-manifest> --asset <asset>
python gamefactory.py godot scaffold --production <production>
python gamefactory.py godot assemble --assemble-file <assemble-file>
python gamefactory.py godot validate --project <project>
python gamefactory.py test unit --project <project>
python gamefactory.py test plan --brief <brief> -o <playtest>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>
python gamefactory.py test regression --project <project>
```

## 关键规则

1. `validate` before matting：图像验证失败时只修 prompt/Brief，不做 trim 或 remove-bg。
2. 动画使用原始 still；idle 使用独立 `*_nobg.png`，不要拿第一帧冒充。
3. 视频帧使用 `video matte-frames --engine ai`，不要用 `image remove-bg`。
4. 图片后处理必须使用 `--input` / `--output`。
5. Godot 施工只能实现冻结 Brief 与 Production Delta 声明的范围，不扩展玩法。
6. 每次报告都返回 `command`、`status`、`next_action`、`outputs`、`failures`，不输出凭据或未授权的环境细节。
