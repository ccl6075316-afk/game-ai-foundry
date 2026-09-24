# 工具、配置与排错

> 读者：需要准备环境、配置 Provider 或排错的外部 Agent。
> Workflow 协议见 [`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md)；字段与文件契约见 [`AI-HANDOFF.md`](AI-HANDOFF.md)。

## 1. 能力边界

| 层 | 负责 | 不负责 |
|---|---|---|
| 外部 Agent | 判断、编排、修复 Brief/Production、解释失败 | 不伪造文件状态 |
| `workflow` CLI | 发现、校验、初始化、执行、恢复、状态汇总 | 不新增第二套 DAG/状态库 |
| 确定性模块 | Brief、Production、Pipeline、Godot、Test | 不依赖聊天记忆 |
| 文件契约 | `manifest`、`progress`、`handoff`、review、validation | 不建数据库副本 |

## 2. 首次准备

```bash
cd cli
pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json

python gamefactory.py setup check --json
python gamefactory.py doctor --json
python gamefactory.py workflow --help
python gamefactory.py workflow context --brief ../resources/asset-brief.example.json --json
```

`setup check` 检查 FFmpeg、Godot、.NET；`doctor` 检查配置、Provider、能力与本机路径。两者都优先用 `--json`。

## 3. 配置

配置文件：`~/.gamefactory/config.json`。

### 3.1 常用字段

| 字段 | 用途 |
|---|---|
| `provider_accounts.<name>.api_key` | 文本/视觉模型凭据 |
| `provider_accounts.<name>.text_model` | 文本模型 |
| `provider_accounts.<name>.image_model` | 图像模型 |
| `provider_accounts.<name>.api_base` | 自定义兼容端点 |
| `image.provider` / `image.model` | 生图路由 |
| `video.provider` / `video.model` | 生视频路由 |
| `prompt.model` / `prompt.api_base` | Prompt 生成 |
| `test.vision_model` | 视觉验收 |
| `godot.engine_path` | Godot 可执行文件 |
| `toolchain.bin_dir` | 工具链目录 |
| `matting.*` | trim、color key、video frame 抠图参数 |

凭据只保存在本机配置；不要写入 Brief、manifest、handoff、报告或日志。

### 3.2 读取与受限写入

```bash
python gamefactory.py config get --key <allowlisted-key>
python gamefactory.py config set --key <allowlisted-key> --value <value> --json
python gamefactory.py setup provider upsert --provider <provider> --i-confirm --json
```

只允许 `config set` 的 allowlist 键；不要直接编辑不受支持的嵌套结构。网络请求、删除与 shell 执行必须走命令本身的确认或白名单。

## 4. 本机工具链

| 工具 | 用途 | 检查/安装 |
|---|---|---|
| FFmpeg | 视频、拆帧、音频 | `setup check`、`setup install ffmpeg` |
| Godot .NET | 导入、构建、运行 | `setup check`、`setup install godot` |
| .NET SDK | C# build / unit test | `setup check`、`setup install dotnet` |
| Python 3.11+ | CLI 与确定性模块 | 当前运行环境 |
| Provider API | prompt、图像、视频、vision | `doctor --json` |

```bash
python gamefactory.py setup ensure
python gamefactory.py setup install ffmpeg
python gamefactory.py setup install godot
python gamefactory.py setup install dotnet
```

安装命令会写本机工具链目录；执行前确认目标和网络权限。

## 5. 常用只读命令

```bash
python gamefactory.py doctor --json
python gamefactory.py setup check --json
python gamefactory.py workflow context --brief <brief> --json
python gamefactory.py workflow validate --brief <brief> --json
python gamefactory.py workflow status --manifest <manifest> --json
python gamefactory.py pipeline ready --manifest <manifest> --json
python gamefactory.py pipeline show --manifest <manifest> <task_id>
python gamefactory.py project progress show --progress <progress> --json
python gamefactory.py project handoff list --json
python gamefactory.py assets review list --manifest <assets-manifest> --json
python gamefactory.py inspect list --path <path> --json
```

## 6. 写入与执行命令

```bash
python gamefactory.py workflow init --brief <brief> --json
python gamefactory.py workflow run --manifest <manifest> --stage assets --json
python gamefactory.py workflow resume --manifest <manifest> --task-id <task_id> --json

python gamefactory.py pipeline plan --brief <brief> -o <manifest>
python gamefactory.py pipeline reset --manifest <manifest> --task-id <task_id> --cascade
python gamefactory.py production apply-delta --delta <delta> --production <production> --dry-run
python gamefactory.py godot validate --project <project>
python gamefactory.py test unit --project <project>
```

`workflow context/status/validate` 只读；`workflow init/run/resume` 只写已有权威状态文件。其他命令按 `--help` 明确输入输出。

## 7. 排错手册

### 7.1 环境

| 症状 | 诊断 | 修复 |
|---|---|---|
| Provider 不可用 | `doctor --json` 的 `capabilities` / `provider` | 修正 `provider_accounts`、`image`、`video` 或 `prompt` |
| FFmpeg 缺失 | `setup check --json` | `setup install ffmpeg` |
| Godot 缺失 | `setup check --json` | `setup install godot` 或设置 `godot.engine_path` |
| .NET 缺失 | `setup check --json` | `setup install dotnet` |
| 配置键被拒绝 | `config set` 返回错误 | 只用 allowlist 键并显式确认 |

### 7.2 Workflow / Pipeline

| 症状 | 修复 |
|---|---|
| `brief_invalid` | 修 Draft/frozen Brief，重新 `brief freeze` / `workflow validate` |
| `production_invalid` | 重新 `production derive` 或修 Delta |
| `manifest_invalid` | 重新 `pipeline plan`；保留状态用 `--merge` |
| `unsupported_stage` | 当前只允许 `--stage assets` |
| `task_failed` | 读取 `failed_ids` 和 task result，修输入后 `workflow resume` |
| 磁盘输出缺失 | `pipeline status` reconcile，再决定是否重跑 |
| image validation `exit 2` | 修 prompt/Brief，不进入 matting |
| 网络超时 | 读取 `summary.runner.run_exit_code`，按失败分类重试 |

### 7.3 Godot / Test

| 症状 | 修复 |
|---|---|
| import / build 失败 | `godot validate`，检查 Godot、.NET 与 Production |
| 主场景不启动 | 核对 `production.scenes`、InputMap、路径 |
| unit test 失败 | 读取 test output，只修 `godot_tasks[]` 对应范围 |
| playtest 不匹配 | 对照 Brief acceptance criteria 与截图证据 |
| regression 失败 | 记录退化项；通过 Production Delta 修复，不能静默放宽验收 |

## 8. 最小接入清单

```text
□ 读取 gamefactory-toolkit Skill 与 CLI --help
□ 创建本机 config，运行 setup check / doctor
□ 运行 workflow context / validate
□ 缺失状态时运行 workflow init
□ 运行 workflow run / status；failed 才 resume
□ status=done 且 next_action=human_review 后 assets review → godot → test
□ 报告只包含 JSON 合同字段与验证证据
```

相关文档：[`AI-HANDOFF.md`](AI-HANDOFF.md)、[`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md)、[`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)、[`README.md`](README.md)。
