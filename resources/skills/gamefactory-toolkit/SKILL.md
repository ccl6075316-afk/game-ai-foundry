# gamefactory-toolkit

供外部 Agent 使用的通用工具箱协议。正文使用中文；命令、路径、JSON 字段与枚举值使用英文。

## CLI 入口（必读）

不要依赖系统 PATH 里的裸 `python`（Windows 常落到 Microsoft Store 占位程序）。首次在本仓库执行：

```bash
# 任选一个真实 Python 3.11+ 引导一次（python.org / py launcher）
py -3 cli/gamefactory.py setup ensure-python --json
# 之后一律用仓库 launcher：
.\gamefactory.cmd workflow --help
.\gamefactory.cmd doctor --json
```

Unix：`./gamefactory setup ensure-python --json`，之后 `./gamefactory …`。

`doctor --json` 的 `python_env` 字段会报告当前解释器是否为 Store stub、`.venv` 是否可用。

## 读取顺序

1. 读取冻结后的 `brief.json`，以及已有 `production.json`、`manifest.json`、`progress.json`、`handoff`。
2. 运行 `workflow context --brief <brief> --json`，确认路径、文件存在性和当前阶段。
3. 运行 `workflow validate --brief <brief> [--production <production>] [--manifest <manifest>] --json`。
4. `context` 或 `validate` 返回 `ok=false` 时立即停止，按 `failures[].kind` 与 `failures[].message` 修复后再重试，禁止继续 `init`。
5. 两者均 `ok=true`，且 `next_action=derive_production` 时运行 `workflow init`；它只补建缺失状态，不覆盖已有文件。
6. 初始化成功且 `status=pending` 时，短超时宿主用 `workflow run --stage assets --detach`；长超时可用同步 `workflow run`。
7. 每轮执行后运行 `workflow status --manifest <manifest> [--job-id <id>] --json`。
8. `next_action=poll` 时继续查同一 `job_id` / manifest，禁止再开一轮 `run`；`status=failed` 时用 `workflow resume --task-id <id>`；`status=done` 且 `next_action=human_review` 后进入资产审查、Godot 与测试。

若输入仍是 Draft JSON，先执行 `brief freeze --input <draft> -o <brief> --json`；冻结后的 Brief 是下游唯一设计契约。

## 六个 Workflow 命令

```bash
.\gamefactory.cmd workflow context --brief <brief> --json
.\gamefactory.cmd workflow validate --brief <brief> [--production <production>] [--manifest <manifest>] --json
.\gamefactory.cmd workflow init --brief <brief> [--manifest <manifest>] --json
.\gamefactory.cmd workflow run --manifest <manifest> --stage assets --detach --json
.\gamefactory.cmd workflow status --manifest <manifest> [--job-id <job_id>] --json
.\gamefactory.cmd workflow resume --manifest <manifest> --task-id <task_id> --json
```

（Unix 将 `.\gamefactory.cmd` 换成 `./gamefactory`。）

`run` 当前只支持 `--stage assets`。`--auto-fix` 是现有资产修复策略；`--run-prompts` 仅在需要生成 prompt 时开启；`--jobs` 控制并行度。

长耗时命令有两种用法（**对任何外部 Agent 通用，不绑定某一家 IDE**）：

### 模式 A — 同步阻塞（默认无 `--detach`）

`workflow run` / `pipeline run` / `image generate` / `video generate` 会阻塞到进程退出。宿主允许长超时（≥ 数十分钟）时可用。

### 模式 B — 文件 Job 轮询（**短超时宿主的推荐默认**）

真相在磁盘上的 job 文件，不在聊天记忆里：

```bash
# 1) 立刻返回 job_id（不要把这一步当成任务完成）
.\gamefactory.cmd workflow run --manifest <manifest> --stage assets --detach --json
# 等价底层：pipeline run --detach，或任意命令：
.\gamefactory.cmd pipeline job start --jobs-dir <dir> --json -- <argv...>

# 2) 轮询直到 status 为 done / failed（建议间隔 15–60s）
.\gamefactory.cmd workflow status --manifest <manifest> --job-id <job_id> --json
# 或仅查 job：
.\gamefactory.cmd pipeline job status --jobs-dir <dir> --job-id <job_id> --json
```

轮询停止条件：`status` ∈ {`done`,`failed`}，或 `next_action` ≠ `poll`。  
`jobs_dir` 默认在 manifest 同级的 `jobs/`。Job 文件字段：`job_id`、`status`、`pid`、`exit_code`、`argv`、`log_file`。

`next_action` 增加枚举值 `poll`：表示「不要开新阶段，继续查同一 job / manifest」。`status=running` 时 `next_action` 为 `poll`（勿再 `run`）。

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
- `next_action` 仅允许：`none`、`freeze_brief`、`derive_production`、`run`、`resume`、`recraft_prompt`、`fix_input`、`human_review`、`poll`。
- `failures[].kind` 仅允许：`validation`、`network`、`dependency`、`config`、`unknown`；无法判断时必须使用 `unknown`。
- `inputs`：本次命令解析后的输入路径与选项。
- `outputs`：本次命令写入或引用的文件路径。
- `summary`：命令特有摘要；manifest 状态在 `summary.manifest`。
- `failures`：错误数组；每项必须有 `code`、`kind` 和 `message`，任务失败可带 `task_id`。

## Exit code 与只读边界

- `ok=true`：通常退出码 `0`。
- `ok=false`：退出码 `1`；不要把非零退出码解释成“任务完成”。
- `workflow context`、`workflow validate` 是只读命令，不修改磁盘。
- `workflow status` 无 `--job-id` 时只读；带 `--job-id` 时可能刷新并写回 job 文件状态字段。
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

侧面图重建实体鱼、Blender 骨骼动作和 Godot 3D 展示缸使用 [鱼类实体建模与游戏展示](../../../docs/FISH-VOLUME-WORKFLOW.md)。新鱼先通过 Foundry 生图与资产审核，使用已有游戏像素鱼作为风格参考；已有已接受源图可经过相同来源与审核检查复用。源图生成完成且审核接受后，再执行 `volume plan → build → validate → render`，完成视觉审核后 `volume accept --handoff <handoff> --note <实际审核说明> --json`，全部加 `--json`；先读各子命令 `--help`。计划必须明确像素画风、风格参考及源图哈希，缺失时先修输入，不绕过门禁直接调用 Blender。

通用建模器位于 `resources/scripts/volume-fish/build_fish.py`，物种 profile 位于 `resources/volume-fish/`。通过 CLI 传入 profile，不把游戏仓库内的实验脚本当作长期唯一生产入口。相近物种可复用方法，跨体形物种重建几何。导入后检查真实骨骼/鱼鳍播放与目标场景日志，不把视频预览当作游戏运行结果。

当前四条已接受 3D 鱼只增加 `Swim/Turn/Ascend/Dive` 时，使用 `volume motion-plan → motion-build → motion-validate`（均 `--json`），复用正式 GLB 与既有模型审核报告，固定控制器及四鱼配置由 Foundry `resources` 提供。先读三个子命令 `--help`；plan 冻结模型/profile/helper/审核来源哈希，build 只生成固定 Godot helper 和动作 JSON。技术检查仍返回 `human_review`，最终需真实 Godot 的 16 组动作与操作者画面审核报告。不得给旧模型补造新生图阶段，也不得把包络校验当作动作质量通过；具体命令、字段与证明格式见上述指南的 042 节。

需要正面头部纹理时，使用独立 `project.view="front"` 的 frozen Brief 经 Foundry workflow 和资产审核生成辅助原画。`volume plan` 的 `--front-assets-manifest`、`--front-asset` 必须成对且与 profile 的 `head_projection` 同时存在；侧面、正面来源均检查生成完成、资产接受及哈希。渲染对照应同时检查侧面/正面原画、风格参考和模型，不能把单侧纹理强行扭曲视为正面原画。字段和命令示例见上述指南。

保留原图像素尺寸，3D 贴图与展示视口使用 nearest 采样，避免平滑过滤和额外金属高光改写像素画风。过滤设置不能把不合格的光滑源图变成合格像素画。`volume validate` 的几何、权重、循环和贴图检查只能证明技术条件；风格仍需源图/风格参考/三视对照及实际 Godot 画面审核，`style_visual_review=pending` 不能当作风格通过。`volume accept` 要求构建、渲染和四张审核图仍对应当前输入，记录审核说明、时间及哈希并把 handoff 的 `style_visual_review` 设为 `accepted`，返回 `next_action=none`。外部 Agent 需先实际查看源图/风格参考/三视和游戏画面，不能把自己的审核写成用户本人接受；自动构建/验证仍不做视觉批准。构建与渲染结果继续使用 handoff 和 validation report，不另建状态库。

重建或重渲染会清除旧接受说明并将视觉审核恢复为 `pending`；接受记录绑定当前输入、模型与四张审核图的哈希，后续验证也检查新鲜度。可选双来源接口通过测试不代表某次双来源模型已经生成并接受，必须读取该次资产清单、handoff 和验证报告。

### 一站式 Host Bridge

外部 Agent 优先调用单入口，不要自行拼接六条命令：

```bash
python gamefactory.py host workflow-run --brief <brief> --dry-run --json
python gamefactory.py host workflow-run --brief <brief> --i-confirm --json
```

`--dry-run` 只执行 `context` 与 `validate`；`--i-confirm` 是一次用户确认，确认后内部按 `context → validate → init → validate → run → status → resume` 自动推进。失败时返回同一 JSON 合同中的 `steps`、`failures` 和最终 `next_action`。

`status=done` 且 `next_action=human_review` 后按顺序审查和验收：

```bash
python gamefactory.py assets review list --manifest <assets-manifest> --json
python gamefactory.py assets review accept --manifest <assets-manifest> --asset <asset>
python gamefactory.py godot scaffold --production <production>
python gamefactory.py godot assemble --assemble-file <assemble-file>
python gamefactory.py godot validate --project <project>
python gamefactory.py play <project>
python gamefactory.py test unit --project <project>
python gamefactory.py test plan --brief <brief> -o <playtest>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>
python gamefactory.py test regression --project <project>
```

`play`（别名 `run-game`）用于快捷启动 main 场景做人工试玩。项目参数可省略；当仓库内有多个游戏时必须传项目名或路径。先用 `play <project> --dry-run` 确认工程路径，需要跳过 C# 构建时加 `--skip-build`。

## 关键规则

已有游动的鱼类追加转身时，除下面的连续动作规则，还应读取 [鱼类转向复用流程](../../../docs/FISH-TURN-WORKFLOW.md)，复用相位规划、深度水域边界和当前帧轮廓校正；每条鱼独立确定素材、首尾相位、镜像资格、时长及曝光需求。

1. `validate` before matting：图像验证失败时只修 prompt/Brief，不做 trim 或 remove-bg。
2. 首次动画使用原始 still；同角色已有已验收动画时，后续动作必须使用该动画的稳定动态帧作为参考，避开静图进入运动的前导过渡。转身需显式传入分别匹配切入、回接动画的首尾帧；只有目标方向在运行时也由镜像实现时，尾帧才可镜像目标游动帧，禁止用不匹配的旧转身尾帧延续偏差。参考帧保留原画布和分辨率；idle 仍使用独立 `*_nobg.png`，不要拿动画第一帧冒充。选帧、参数与游戏衔接验收见 [AI-HANDOFF.md](../../../docs/AI-HANDOFF.md#连续动作的首尾帧规则)。
3. 视频帧使用 `video matte-frames --engine ai`，不要用 `image remove-bg`。拆帧默认 **24**（适配 3–4s；Brief `sprite_frames` 或 `duration×6` 可覆盖）。
4. **循环切帧**：`video split-frames` 默认 `--optimize-loop`（帧差搜窗，使循环接缝接近中段运动）；失败时回退固定 lead/trail。可用 `--no-optimize-loop` 关闭。
5. **导入保清晰、放置再缩放**：静帧与动画导入保留抠图/生成原分辨率（或接近原分辨率）；**不要**为了体型把 PNG 压成 Brief `display_size`。游戏内大小由 `real_length_cm` / 放置与 `runtime scale` 决定。`display_size` 是布局/体长意图，不是导入画布必须烤死的像素。
6. 图片后处理必须使用 `--input` / `--output`。
7. Godot 施工只能实现冻结 Brief 与 Production Delta 声明的范围，不扩展玩法。
8. 每次报告都返回 `command`、`status`、`next_action`、`outputs`、`failures`，不输出凭据或未授权的环境细节。
