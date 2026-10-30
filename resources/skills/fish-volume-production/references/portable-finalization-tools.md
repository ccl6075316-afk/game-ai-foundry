# 配置驱动的单材质源工具：下一鱼执行入口

实鱼扩展：蓝鳃已执行显式完整根/490适配、077闭体/GPU、头型正负例、动作和多视；新入口与原工具边界见[蓝鳃经验](portable-production-lessons-20261030.md)。新增prepare_trial_spec/run_delivery_checks需要逐鱼明确解剖与配置，当前仅支持既有七鳍核，不把本页旧capabilities的任意库存不支持改写成普遍通过。

本页对应 `resources/scripts/volume-fish/portable/` 的已执行实现，不再要求逐鱼修改面数、骨数、动画通道或七鳍常量。既有罗非鱼R11及其旧工具保留原字节；新工具是独立入口。它接在定型模型/单图集候选之后，不自动完成解剖建模、二维补皮或用户视觉审核。

完整制作/固化顺序仍见[生产SOP](production-sop.md)和[单材质源固化SOP](single-material-source-finalization.md)。后者第2节描述的是冻结旧工具的限制；新任务优先按本页选择新入口，不去修改旧文件。

## 1. 已经通用化的内容

| 操作 | 入口 | 物种差异从哪里来 |
|---|---|---|
| 自动计数、SHA、输入绑定和spec生成 | `prepare_spec.py` | 实际GLB/packing report及显式部位表；不推断解剖 |
| 输入、材质和完整分区预检 | `fish_asset_spec.py` | spec和冻结基线的实际库存；错计数/过期文件先失败 |
| 保存源→新进程冷导出→完整语义对照→最终model绑定 | `run_source.py` | spec、Blender路径、全新输出目录 |
| 源回写、受保护导出、独立语义检查 | `build_source.py`、`export_source.py`、`verify_parity.py` | 任意受支持顶点/三角/骨/clip/分区数量，原rig/动作保留 |
| 任意显式部位、实际引擎数组对应 | `parts.py`、`PackedFishParts.gd`、`validate_import.gd` | 完整源surface表；body可多surface，fin/aux等数量不固定 |
| 验证计划和能力声明 | `prepare_validation.py` | 当前模型、spec、引用计划；不复制旧通过结果 |
| 离散身体GPU透明覆盖 | `validate_body_gpu.py`、`capture_body_gpu.gd` | 实际身体分区、显式原生clip，两姿态八视零缺像素及透明负例 |
| 冷读、环绕/平移/缩放、原生/可选控制器、声明式镜头捕获 | `view.py`、`FishAssetViewer.gd` | bbox自动构图、spec里的比例/镜头/动作引用 |
| 证据清单、文件哈希、nearest拼图 | `evidence.py` | 实际查看器报告声明的图片；永远不自动写视觉通过 |

主要回归：不同1/2/3/4骨的小样、不同顶点/三角/分区、1或3身体surface、不同鳍/辅助角色、1或2clip、不同动画通道与图像尺寸。合成数据只证明工具行为，不是新鱼制作或解剖通过。

## 2. 输入：只把必须逐鱼判断的内容交给配置

先有自己的 `.blend`、已审单surface候选GLB、原像素atlas和`pack_fish_material_atlas.py`的packing report。新鱼身体/鳍仍按B制作方法完成，不为使用本工具制造旧模型。

另写一个部位/展示输入JSON。例如以下名字只是示意，必须取实际packing report中的node和surface：

```json
{
  "species": "实际物种ID",
  "game": "projects/实际项目/game",
  "parts": [
    {"name":"外皮", "logical_name":"身体", "role":"body_skin", "source_node":"实际身体对象", "source_surface":0},
    {"name":"口内", "logical_name":"身体", "role":"mouth", "source_node":"实际身体对象", "source_surface":1},
    {"name":"独立鳍", "role":"fin", "source_node":"实际鳍对象", "source_surface":0}
  ],
  "viewer": {
    "model_scale": 1.0,
    "native_clip": "实际clip名",
    "focuses": {
      "head": {"mode":"bbox_relative", "position":[0.85,0.5,0.5]}
    },
    "captures": [
      {"name":"side", "yaw_degrees":0, "pitch_degrees":0},
      {"name":"oblique", "yaw_degrees":35, "pitch_degrees":15}
    ]
  }
}
```

`parts`必须完整覆盖来源surface，不只写示例三项。角色可以是任意明确的非空字符串；`body/body_skin/mouth/oral_cavity`自动纳入身体不透明检查，禁止用`opaque_uv:false`跳过。其他角色可显式`opaque_uv:true`要求不透明。`logical_name`允许多来源surface聚合成同一诊断部位；部位不能漏、重复、重叠或跨所有权引用三角。

相机`focus.mode`支持`model`坐标或`bbox_relative`的0..1位置；比例/局部镜头仍是本鱼参数。没有局部标志点可先用自动bbox整鱼构图，不能把默认头部位置当物种测量。

可选实时动作写在`motion`：`runtime`和`profile`都必须为`{path,sha256}`，`api`为`foundry_motion_v1`，`action`为本鱼实际动作。它只调用已声明控制器，不制作或烘焙新动作。没有controller时播放原生clip。实际动画/鳍连接的最终门另外执行。

## 3. 常用命令

所有命令从Foundry根目录运行，`<py>`用仓库`.venv`，`<tools>`为`resources/scripts/volume-fish/portable`。下列占位路径先换成已核对的实际路径；没有自动发起生图、付费调用、安装或批量推广。

### 自动生成配置，不手抄计数与哈希

```bash
<py> <tools>/prepare_spec.py --source-blend <原源.blend> --reference-glb <已审单surface.glb> --atlas <atlas.png> --packing-report <packing.validation.json> --parts <部位与展示.json> --output <新目录/spec.json> --json
<py> <tools>/fish_asset_spec.py --spec <spec.json> --json
```

源对象名默认来自实际reference owner，必要时显式`--source-mesh-name`。source blend内对象数不凭GLB猜测。输出spec包括四输入SHA、实际库存及声明部位；未知/缺失/不支持先拒绝，不先跑Blender试错。

### 一条命令完成源固化技术链

```bash
<py> <tools>/run_source.py --spec <spec.json> --blender <Blender可执行文件> --output <全新/source-run> --dry-run --json
<py> <tools>/run_source.py --spec <spec.json> --blender <Blender可执行文件> --output <同一尚未创建的/source-run> --execute --json
```

默认仅预检并列命令，只有`--execute`写入。实际阶段顺序固定：预检→保存新源→新Blender进程源导出→`1e-6`完整语义对照→确认源首次/冷导出字节一致→生成`final-spec.json`→manifest/report。原输入不写入。

每Blender阶段默认300秒超时，可显式`--timeout`；失败立即停止，manifest记失败并保留stdout，不自动无限重跑。不要重用已存在输出目录：从报告定位失败原因后修输入/工具，选全新目录重试。当前是有界顺序执行器，没有宣称通用resume或资产正式接受。

成功输出：`source/fish.blend`、`fish.glb`、`final-spec.json`、`validation-report.json`、`cold-export.validation.json`与`manifest.json`。最终展示使用`final-spec.json`，不要默默退回reference候选。

### 实际导入、身体GPU与预览

```bash
<py> <tools>/prepare_validation.py --model <最终fish.glb> --spec <final-spec.json> --output <全新/final-plans> --json
<godot> --headless --path <Godot工程> --script <Foundry绝对路径>/<tools>/validate_import.gd -- <绝对final-plans/parts-manifest.json> <绝对新import.validation.json>
<py> <tools>/validate_body_gpu.py --manifest <parts-manifest.json> --godot <godot> --project <Godot工程> --clip <实际原生clip名> --output <全新/body-gpu> --dotnet <按本机需要的.NET目录> --json
<py> <tools>/view.py --spec <final-spec.json> --output <全新/viewer> --godot <godot> --smoke --json
<py> <tools>/view.py --spec <final-spec.json> --output <另一个全新/captures> --godot <godot> --capture --json
<py> <tools>/evidence.py --report <captures/viewer.validation.json> --output <全新/evidence> --contact-sheet --json
```

Godot命令传绝对脚本/manifest/report路径；工程可来自spec.game或`view.py --game`。Mono工具按已有环境设置`DOTNET_ROOT`。`view.py`不加`--smoke/--capture`时为交互模式，等待用户关闭；有界模式默认45秒，允许显式`--timeout`。正常交付不自动打开交互窗口。

`body_gpu_coverage_discrete`只检查两个实际原生姿态×八视的透明覆盖。姿态不变化、空身体、原图集不透明检查失败、相机/姿态不同、缺像素、无效透明负例或引擎错误都拒绝。辅助探针仅来自实际数组/skin/material，结束删除；不改正常入口mesh。

输出只允许仓库`work/`、`output/`及`projects/<项目>/experiments/`的子路径，拒绝已有目标、输入别名/包含输入的目录、根外路径。所有源读取refs均绑定SHA，路径按仓库根解析，避免依赖启动工作目录。图表和报告准备不替用户/操作者写视觉接受。

必须使用普通Python运行，`-O/-OO`会明确拒绝，避免必需assert被移除。当前单材质primitive须显式绑定整数索引0；原始joint/weight先检查合法性再按骨名聚合。spec/GLB的解析与SHA取自同一字节快照，成功前复核稳定性，最终spec复用已验证模型digest，不以稍后重新读到的哈希冒充通过。

## 4. 当前明确不支持的部分

- 源作者只支持一个rig、可明确保留的动作、单位mesh/rig世界变换，以及已支持的单surface MASK/nearest/PBR合同。多rig、非单位变换、未知材质图/扩展先拒绝，不能靠删除guard继续。
- 不推断鱼种解剖、宽厚、鳍根、眼嘴归属、二维颜色供体或口型。配置的来源是否符合生物/原图仍需制作与实际看图。
- 通用import只证明数组、骨名权重、有向三角多重集、分区覆盖及原生轨道绑定；不证明完整运动数值或连续时间正确。
- 离散身体GPU不是完整077：闭合身体/逐层结构、全部当前控制器范围和正式门仍需现有流程。
- 任意新解剖库存的完整鳍根/鳍膜/490导出适配仍需逐鱼计划。`prepare_validation.py`在capabilities里明确标不支持；不把旧Nile报告换SHA继承。新的特殊结构若需要新增适配，先记录具体不支持项，再实施，不重做无关材质/源链。
- 不实施Blender/GPU动画烘焙、VAT、骨骼动画纹理或鱼群实例化；不承诺特定同时数量或FPS。

## 5. 回归、收尾与本次实证

快速回归：

```bash
<py> -m unittest discover -s resources/scripts/volume-fish/portable/tests -p 'test_*.py'
<py> -m unittest discover -s resources/scripts/volume-fish -p test_portable_fish_parts.py
```

第二条找到已安装Godot时会做小型headless导入正负例，缺工具明确skip，不下载。完整Blender合成实测可用`portable/tests/run_blender_smoke.py --blender <已安装工具> --output <新测试目录> --json`；它不导出或加载生产鱼，不是490/性能矩阵。

初版42项快速测试、6项部位测试（含两库存共14次实际Godot正负例及输出保护检查）通过；次级审阅修正后55项快速测试通过，另以冻结后的代码重跑相关冷源导出、实际导入和离散身体GPU。最终有效报告及精确版本见验证索引，旧报告保留原版本身份。实际Blender小样为11顶点/9面/3骨/2clip和7顶点/5面/2骨/1clip，源保存/原rig与动作保留、新进程冷导出和最终对照全部0误差。实际GPU覆盖16对照0缺像素，透明负例4278像素；通用查看器的原生、控制器、操作和捕获另有实际证据。它们都是合成小样，未开始下一条鱼。

正式记录见Foundry `docs/anvil/knowledge/2026-10-30-fish-portable-tools.validation.json`与对应review；无上下文接续先读 `docs/FISH-PORTABLE-HANDOFF-20261030.md`，四类校验根因与次级模型经验见 `docs/anvil/knowledge/2026-10-30-portable-validation-guards.md`。原460个工具/成品/运行代码与SOP输入按开工SHA保留未改。原版固化报告不因新入口而重写；每条新鱼按自己的输入生成新报告。

每轮先总结/绑定报告，再清理精确路径清单里的重复候选、失败启动目录、可重建缓存；保留当前合成源/数据、唯一代表图、负例结果和复现脚本。不要每修一个检查器就重跑GPU：先收齐代码问题、局部测试，再对冻结代码做一次最终验证。`visual_review=pending`保留到实际看图，不自动完成整鱼SOP。

### 次级模型调用的用户约定

用户已于2026-10-30明确要求不要人为设置生成token预算；默认不传`max_tokens/max_completion_tokens`，按服务默认容量执行，不伪称服务无限。实测`finish_reason=length`且无最终报告必须记失败，不记审阅通过。具体持续授权与调用规则见[次级模型执行卡](static-merge-secondary-model.md)。本地工具执行失败/超时控制与模型token生成上限分别处理。
