# Game AI Foundry — CLI 与文件契约手册

> 读者：使用本仓库的外部 Agent 与维护者。
> 入口：先读 [`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md)；环境问题读 [`TOOLS.md`](TOOLS.md)。
> 本文只写确定性命令、文件契约、失败处理与验收规则。

续做2026-10-29暂停的罗非鱼B路线鳍/材质实验时，先读[无上下文交接](../projects/fishing-2d/docs/3d-fish/HANDOFF-20261029-NILE-B.md)；游戏是独立仓库，需一并拉取。该工作尚未完成，保留现有身体，不重启A/B比较或整鱼重建。

## 1. 主路径

```text
Draft JSON
  → brief freeze
  → host workflow-run（外部 Agent 一站式入口）
  → workflow context / validate / init
  → workflow run --stage assets [--detach]
  → workflow status [--job-id] / resume
  → assets review
  → production / progress / handoff
  → godot scaffold / assemble / validate
  → test unit / play / regression
```

六个 Workflow 命令的 JSON 合同、只读边界和失败分类见通用 Skill。所有面向外部 Agent 的命令优先加 `--json`。

外部 Agent 可直接使用 `host workflow-run --brief <brief> --dry-run --json`，确认写入/生成后使用 `host workflow-run --brief <brief> --i-confirm --json`；不要自行重复拼装状态命令。

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

尺寸分层（勿混用）：

| 层 | 含义 | 谁消费 |
|---|---|---|
| `source_size` / 生成与抠图输出 | 源像素（如 1280×720、1920×1080） | `image` / `video` / matte 产物 |
| `display_size` / `real_length_cm` | 体型与布局**意图**（相对体长、占屏参考） | Brief / Production；**游戏 runtime scale** |
| runtime scale | 节点放置时的缩放 | Godot 游戏代码 |

**规则**：Godot 导入静帧与动画帧时保留源清晰度，**禁止**为表达体型而把 PNG 烘焙成很小的 `display_size`。体型差异在放置时用 `real_length_cm`（及 UiScale 等）缩放。个体差异、布局缩放与碰撞盒不要写进通用 Brief 文案规则。

### 场景背景：母图优先、定尺度拆层

需要天空、远景、水面等独立层的场景，先把完整画面登记为 `type: background` 母图，再给每个拆层资产写：

```json
{
  "id": "lake_water",
  "type": "background",
  "content_class": "scene_layer",
  "scene_master": "lake_plate",
  "scene_box_norm": [0.0, 0.48, 1.0, 0.52],
  "scene_scale": 1.0,
  "scene_z": 1,
  "display_size": {"width": 1920, "height": 562}
}
```

`scene_box_norm` 是母图上的 `[x,y,宽,高]`，`display_size` 必须约等于母图显示尺寸乘这个框；`scene_scale` 是回拼时的额外运行时倍率，默认 1。`scene_z` 是叠放深度；`scene_occludes` 声明要局部遮住的同母图层，校验会要求两个源框确实相交且遮挡层在前。前景树叶、山缘、岩石等用透明不规则轮廓，不用矩形硬边。Godot 组装按导入后实际源像素尺寸先拟合目标框，再乘 `scene_scale`，不会把 PNG 烤小。`usage: parallax_layer` 也必须走这套契约。Foundry 会先生成母图、原像素裁出框作为图生图参考，再生成拆层、验证、按类型抠图，并输出单层以及按 `scene_z` 全部叠放的母图/回拼并排预览；母图与拆层有 DAG 依赖。不要把其他场景独立生成的水、岛、云塞入本场景。真实视觉一致性、地标辨识度、遮挡轮廓与白边仍需在 assets review 和回拼预览中确认。

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
3. **首次动画**输入使用原始 still；已有已验收动画的角色续做动作，必须从已有动画的稳定动态帧取参考，不能重新用静图引入静转动过渡。保留原画布与分辨率，不先裁剪；参考图需纯白背景和单一主体。连续动作按下面的首尾帧规则执行。
4. idle 使用独立 `*_nobg.png`，不要拿动画第一帧充当 idle。
5. 视频先 `video split-frames`，再：

```bash
python gamefactory.py video matte-frames --input <frames-dir> --output <output-dir> --engine ai
```

6. 不要用 `image remove-bg` 处理视频帧。
7. 一张图不能包含多个动作帧；spritesheet 必须走显式 slice 流程。

### 连续动作的首尾帧规则

本规则适用于已有游动、行走或其他循环动画的角色追加转身等动作。原始静图仍保留为设计与独立静态展示资产，后续动作的视觉基准以已验收动态帧为准。

1. **首帧来自切入动画**：检查已有动画，跳过静图到运动的前导帧、变形帧和循环接缝异常帧，选取身份、轮廓、颜色与姿态稳定的动态帧。优先使用对应原视频帧的白底版本；若只有透明帧，合成纯白背景，保留像素、尺寸、画布与锚点，不重新绘制主体。
2. **尾帧来自回接动画**：先确定动作结束后要播放的动画、方向与帧号，再从该动画取稳定动态帧作为目标尾帧。禁止直接使用尚未匹配的旧转身生成结果作尾帧，否则会继承其颜色、体形与画风偏差。
3. **镜像的适用条件**：如果游戏的左向游动就是右向游动的水平镜像，右转左的目标尾帧可以用选定右向游动帧的水平镜像；镜像画布与运行时 `FlipH` 的锚点必须一致。非对称角色或有独立左向动画时，使用真实左向动态帧，不默认镜像。镜像只用于构造目标姿态或完整反向动作，不替代中间转身过程。
4. **首尾都要实际送入模型**：使用 `video generate --reference-image <切入动态帧> --last-frame-image <回接动态帧> --no-loop-align`。Prompt 写明一次转向、身份和材质保持一致；仅在文字中描述结束姿态不算尾帧约束。若当前后端不支持独立尾帧，记录能力限制并更换支持的后端，不能声称已约束首尾。
5. **保留端点**：单次转身 `animation_loop=false`，拆帧用 `--no-optimize-loop --no-trim-lead --no-trim-trail`；导入用 `--pre-trimmed --pre-sampled`，不得再次删除首尾或按显示大小压缩。检查采样后的首尾是否仍对应指定姿态；模型可能偏离参考，传了参数不等于验收通过。
6. **运行时也要匹配**：记录切入与回接的动画名、帧号、朝向、原始像素尺寸、锚点和缩放依据。先让切入动画到达匹配的相位再开始转身，结束后从匹配的回接相位继续播放，禁止从任意游动帧硬切，也不能一律回到游动第 1 帧。缩放与位置应沿用同一身体尺度和锚点，不能用不同片段各自的最大宽度造成切换时大小跳变。
7. **验收包含两个接缝**：审查「游动 → 转身首段」和「转身末段 → 游动」的连续录像，覆盖两个方向及正常游戏速度；对比轮廓、鳍、颜色、像素风格、身体尺寸、位置和朝向。首尾不匹配时修参考、生成或相位接入，不以淡入淡出掩盖。来源与处理步骤写入现有 handoff，接缝结论写入 validation report。

银龙鱼例：选已验收右向游动中的稳定帧 A，首帧输入 A，尾帧输入与游戏左向游动一致的镜像 A；游戏从游动相位 A 切入转身，结束后从左向游动相位 A 继续。若选择另一帧 B 作尾帧，回接相位也必须是 B。

完整的生成、速度、曝光、相位规划、按深度计算边界和逐帧轮廓验收，见 [鱼类转向复用流程](FISH-TURN-WORKFLOW.md)。下一条鱼须单独确定首尾相位、左右策略与时长；不得直接照搬银龙鱼参数。

## 8. Godot 与测试

```bash
python gamefactory.py godot scaffold --production <production> --project <project> --validate
python gamefactory.py godot assemble --assemble-file <assemble-file> --validate
python gamefactory.py godot validate --project <project>
python gamefactory.py play <project>

python gamefactory.py test unit --project <project>
python gamefactory.py test plan --brief <brief> -o <playtest>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>
python gamefactory.py test regression --project <project>
```

`play`（别名 `run-game`）直接启动 main 场景进行人工试玩；省略项目参数时会解析当前工程，多个候选时必须指定项目。`--dry-run` 可先确认解析出的工程路径。

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
