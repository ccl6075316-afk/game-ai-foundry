# Game AI Foundry — CLI 与文件契约手册

> 读者：使用本仓库的外部 Agent 与维护者。
> 入口：先读 [`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md)；环境问题读 [`TOOLS.md`](TOOLS.md)。
> 本文只写确定性命令、文件契约、失败处理与验收规则。

## 1. 主路径

```text
Draft JSON
  → brief freeze
  → workflow context / validate / init
  → workflow run --stage assets
  → workflow status / resume
  → assets review
  → production / progress / handoff
  → godot scaffold / assemble / validate
  → test unit / play / regression
```

六个 Workflow 命令的 JSON 合同、只读边界和失败分类见通用 Skill。所有面向外部 Agent 的命令优先加 `--json`。

## 2. 项目与文件状态

```text
projects/<slug>/
  brief.json                 # 冻结后的设计契约
  scenes/*.json              # 场景分册
  systems/*.json             # 系统分册
  assets/*.spec.json         # 资产分册
  output/                    # 生成资产
  plans/
    production.json          # 工程蓝图
    progress.json            # 施工续作状态
    handoffs/*.json          # 任务交接包
    changes/*.json           # Change Request / Production Delta
  game/                      # Godot 工程
pipeline/
  manifest.json              # 资产 DAG 与任务状态
```

外部路径可由 `project external` 登记。`manifest`、`progress`、`handoff`、`assets-manifest`、`validation report` 是唯一权威状态，不建立第二份状态库。

## 3. Brief 契约

### 3.1 冻结

- 外部 Agent 直接补全 Draft JSON；创意判断、议题取舍与字段修订都在外部完成。
- `brief freeze --input <draft> -o <brief> --json` 执行完整门禁并写 `brief_meta`。
- 冻结后的 `brief.json` 是下游只读设计契约；修改需求必须生成新版本或走 Delta，不依赖会话记忆。
- 示例：`resources/asset-brief.example.json`。

```bash
python gamefactory.py brief freeze --input ../projects/my-game/brief.draft.json -o ../projects/my-game/brief.json --json
python gamefactory.py brief validate --brief ../projects/my-game/brief.json --json
```

### 3.2 场景 / 系统 / 资产

| 分册 | 作用 | 与 Production 的关系 |
|---|---|---|
| `scenes[]` | 空间、入口、主流程、视觉边界 | 派生场景树、主场景、关卡任务 |
| `systems[]` | 玩法机制、规则、状态与交互 | 派生脚本职责、信号、输入与验收 |
| `assets[]` | 可生成/可装配的视觉与音频资源 | 派生 Pipeline task、尺寸、用途、依赖 |
| `animation_graphs[]` | 动作状态、帧序列、转换条件 | 派生 still / video / frame tasks |

推荐薄 Brief：主文件只放 `id`、`title|name`、`path`，正文放分册。外部 Agent 用 `brief search` / `brief shard load` 按需读取。

```bash
python gamefactory.py brief shard migrate --brief ../projects/my-game/brief.json
python gamefactory.py brief search --brief ../projects/my-game/brief.json --q "jump" --json
python gamefactory.py brief shard load --brief ../projects/my-game/brief.json --kind scene --id <scene_id> --json
```

### 3.3 核心字段

- `project`：标题、类型、玩法循环、会话目标、控制、风格、验收条件。
- `scenes[]`：`id`、`title` 必填；场景流程与引用可选。
- `systems[]`：`id`、`title` 必填；摘要与规则可选。
- `assets[]`：`id/name/type/usage`、生成规格、交付路径、场景/系统弱引用。
- `animation_graphs[]`：动作、帧数、转换与输入条件。
- `art_tokens`、`visual_reference`：风格锚点与视觉目标。

尺寸区分 `source_size`、`display_size`、`runtime scale`；个体差异、布局缩放与碰撞盒不要写进通用 Brief 规则。

## 4. Production 与续作账本

```bash
python gamefactory.py production derive --brief <brief> -o <production> --json
python gamefactory.py production validate --production <production> --brief <brief> --json
python gamefactory.py project progress init --production <production> --brief <brief>
python gamefactory.py project progress show --progress <progress> --json
python gamefactory.py project handoff list --json
```

- `production.json`：把 Brief 转成场景、系统、资产、`godot_tasks[]`、输入映射与验收条件。
- `progress.json`：记录施工任务、验证阶段、备注与回归快照。
- `handoff`：把一次任务的输入、范围、权威来源和完成条件写成可恢复文件。
- Change Request 先用 `production delta` 形成局部变更，再用 `production apply-delta --dry-run` 检查，最后合并并同步 `progress`。

## 5. Pipeline DAG

```bash
python gamefactory.py pipeline plan --brief <brief> -o <manifest>
python gamefactory.py pipeline ready --manifest <manifest> --json
python gamefactory.py pipeline run --manifest <manifest> --jobs 4
python gamefactory.py pipeline status --manifest <manifest> --json
```

建议优先使用 Workflow 六命令；底层 Pipeline 命令用于诊断、dry-run 和定点维护。

- `plan` 根据 Brief 建立 prompt、生成、裁剪、抠图、拆帧、组装依赖。
- `run` 按 wave 执行 ready tasks，并把结果写回同一 `manifest`。
- `status` 汇总 counts、ready、failed；`pipeline status` 可 reconcile 磁盘缺失输出。
- `reset` 只在输入已修正后定点恢复；`suggest-retry` 可输出白名单命令。
- 简报变化后重新 `plan`；需要保留 task 状态时使用 `--merge`。

## 6. 资产审查

```bash
python gamefactory.py assets review list --manifest <assets-manifest> --json
python gamefactory.py assets review accept --manifest <assets-manifest> --asset <asset>
python gamefactory.py assets review replace --manifest <assets-manifest> --asset <asset> --file <new-file>
python gamefactory.py assets review regenerate-plan --pipeline-manifest <manifest> --asset <asset> --json
```

- `list` 展开 Brief 每项资产；`icon_kit` 按 `items[]` 逐项展开。
- `accept` 是软标注，只写 `review.status`，不改图像文件。
- `replace` 显式替换文件并更新路径；`regenerate` 生成定点重跑计划。
- 审查失败时保留失败证据，不用未审查文件继续 Godot 组装。

## 7. Matting 与动画铁律

1. **Validate before matting**：生成结果未通过 `--validate` 时，先修 prompt 或 Brief；禁止 trim、remove-bg 或继续拆帧。
2. 图片后处理必须写 `--input` / `--output`，不要依赖短参数。
3. 动画输入使用**原始 still**，不要先裁剪；参考图需纯白背景和单一主体。
4. idle 使用独立 `*_nobg.png`，不要拿动画第一帧充当 idle。
5. 视频先 `video split-frames`，再：

```bash
python gamefactory.py video matte-frames --input <frames-dir> --output <output-dir> --engine ai
```

6. 不要用 `image remove-bg` 处理视频帧。
7. 一张图不能包含多个动作帧；spritesheet 必须走显式 slice 流程。

## 8. Godot 与测试

```bash
python gamefactory.py godot scaffold --production <production> --project <project> --validate
python gamefactory.py godot assemble --assemble-file <assemble-file> --validate
python gamefactory.py godot validate --project <project>

python gamefactory.py test unit --project <project>
python gamefactory.py test plan --brief <brief> -o <playtest>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>
python gamefactory.py test regression --project <project>
```

验收至少覆盖：

| 层 | 命令 | 证明 |
|---|---|---|
| L0 | `godot validate` | 导入、C# build、主场景启动 |
| L1 | `test unit` | 纯逻辑与系统规则 |
| L2 | `test play` | 控制、胜负、核心循环、截图 |
| L3 | `godot validate` + 视觉审查 | 画面符合 Brief / visual target |
| L4 | `test regression` | Change 后旧验收未退化 |

Godot 只实现冻结 Brief 与已应用 Production Delta；不得自行扩展场景、系统或玩法。

## 9. 失败处理

Workflow 合法 `status` 为 `pending|running|done|paused|blocked|failed`；`failures[].kind` 为 `validation|network|dependency|config|unknown`。

| 场景 | 下一步 |
|---|---|
| `ok=false` 或 `next_action=fix_input` | 读取 `failures[].kind/code/message`，修 Brief/Production/manifest，再 `workflow validate` |
| `status=blocked` 且 `next_action=derive_production` | `workflow init`，检查 `summary.created` / `preserved` |
| `run` 返回 `failed` | 读取 `summary.manifest.failed_ids` 与 task result |
| validation pause / `exit 2` | 修 prompt、Brief 或输入；不要做后处理 |
| network timeout / API size | 按失败分类定点 `workflow resume` 或 `pipeline reset` |
| toolchain missing | `doctor --json` + `setup check --json` |
| Godot / test failed | 记录 verification evidence；只改 Production Delta 允许的范围 |

## 10. 操作原则

1. 文件与 `--json` 是事实源；会话记忆不是契约。
2. 先 `context` / `validate`，再写状态或执行。
3. 同一任务失败时读 `failures`，不要盲目重跑整条 DAG。
4. 只读与写入边界按 Skill；shell、配置写入、删除、网络请求需显式权限。
5. 最终报告包含 `status`、`next_action`、`outputs`、`failures` 与验证证据。

相关文档：[`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)、[`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md)、[`TOOLS.md`](TOOLS.md)、[`README.md`](README.md)。
