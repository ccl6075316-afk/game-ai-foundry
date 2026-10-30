# 单图集鱼资产：从已定型模型到可编辑源与最终导出 SOP

适用：鱼的身体、嘴、眼、鳍形和基础蒙皮已经定稳，需要把静态材质/补色与绘制分件整理进 Blender 源和完整 GLB。也供下一条低面 B 新鱼在建模阶段预留相同交付结构。只做本地旧 Godot 装配迁移时，先按[生产SOP第0.2节](production-sop.md)选择检查点；本节的正式完成门不自动套到该临时例外。

本方法已在尼罗罗非鱼 B R11完成实际源冷导出、Godot、全部专项和九阶段SOP。**方法可以复用；当前工具尚非任意鱼一键流水线。** 先完成第2节兼容性检查，再使用命令。本文不授权开始另一条鱼、全批替换或修改既有验收阈值。

## 目录与执行顺序

0. 确定任务边界与输入 → 1. 冻结实际基线 → 2. 检查工具适配 → 3. 图集/单surface候选 → 4. 回写可编辑源 → 5. 新进程源冷导出 → 6. 冻结最终依赖 → 7. 一次完整验证 → 8. 实际看图与入口 → 9. SOP账本 → 10. 清理交接。

有新形体/鳍厚度/拓扑问题时先返回相应制作阶段，局部验证稳定后再继续；不在源固化任务里顺带减面、减骨、烘焙动作、重做嘴或重跑性能矩阵。

## 0. 下一条鱼的开工卡

把以下内容写入该鱼已有 manifest/handoff、物种profile或新一轮recipe；不要另建平行任务状态。缺失项明确写未知/待准备，不填罗非鱼默认值。

| 必须确定的输入 | 要记录的实际内容 |
|---|---|
| 工作范围 | 仅静态合并检查点、定型鱼材质固化，或新建B完整交付；安装入口、保留基线、用户已接受部位与禁改项 |
| 物种与规模 | species ID、学名、游戏整鱼长度/缩放、体积依据、预计同时数量、三角面优选/硬上限；实测与艺术代理分开 |
| 来源 | 已接受源图/风格/生成审核回执、原尺寸像素、各方向供体及SHA；不补造旧接受记录 |
| 编辑源与实际基线 | 当前真实 `.blend`、实际显示的完整GLB或引擎装配、材质/纹理/必要引擎资源；路径、SHA、工具版本 |
| 解剖部件 | 身体外皮、口内、独立眼/附层、每片鳍的名字/角色/来源surface；允许的独立组件、根线和封边 |
| 鳍与尾部约束 | 按物种×部位查鳍型、厚度/截面/刚柔区、完整根基；尾鳍保持独立完整轮廓、小量根插入与尾柄连续过渡，不能把整片尾鳍吸附到身体 |
| 颜色与透明 | 身体/鳍/口内的原材质、RGBA、linear factor、sampler、裁切、剔除、PBR、shader；描边与内部补色所有权 |
| 骨架与动作 | 骨名/父级/rest/IBMs、蒙皮、全部原生clip/原始通道、当前实际控制器和物种motion profile；动作范围与切换 |
| 验证约束 | 本鱼完整鳍根/自由面计划、身体/头型约束及负例、源图对照、实际LOD、相机/水环境；工具脚本SHA |

新鱼尚无定型身体时，先执行[参考图低面B重建](reference-cage-rebuild-sop.md)。从原图控制笼、独立鳍、真实嘴切口和安全二维供体开始；在源制作阶段保留部件选择ID，待部件局部通过后再作最终打包。无需为了使用本流程先制作高模或复制罗非鱼模型。

材质制作仍遵守[嘴部像素接续](mouth-material-continuity.md)和[补皮](source-surface-repair.md)：先分离活动鳍/原描边，补全身体二维皮肤供体，再贴到体积表面；身体背腹、上下嘴和鳍侧壁都不能用原图外黑边当内部组织颜色。真正唇线单独保留。最小笔触按本鱼原画的二维像素簇确定，不把一列色带沿曲线复制；罗非鱼6px不是统一常数。

## 1. 冻结当前实际基线

1. 先看 manifest/progress/handoff/assets-manifest/validation report，确认哪一版是当前成品，旧失败轮次仅作历史。已有最终源及完整有效报告时不重新开工。
2. 列出实际 mesh、primitive/surface、material/image、导出顶点、三角面、骨数、原始动画通道；比较实际引擎装配与原GLB，排除骨骼显示辅助物和缓存假象。
3. 保留原形体/嘴/鳍的原生循环及代表动作同相位画面。临时关闭活动鳍看身体残影；记录颜色/缺块是否本来就存在，不把历史问题归因于新合并。
4. 计划独立新输出目录，解析为仓库 `work/`、`output/` 或目标项目 `experiments/` 内的绝对路径。输入、recipe、输出源/GLB及固定名称的报告必须不重名，拒绝覆盖。

## 2. 先核对工具能力，不靠换species试错

工具位于 Foundry `resources/scripts/volume-fish/`。CLI `volume/workflow` 子命令按要求带 `--json`；下表独立 Python/Blender/Godot helper 以自己的参数输出JSON文件，**不支持时不要添加 `--json`**。

| 入口 | 当前能力/限制 | 下一条鱼要做的事 |
|---|---|---|
| `pack_fish_material_atlas.py` | 普通支持范围内PBR、nearest无mip；拒绝未知纹理扩展/不兼容状态；输出MASK和诊断OPAQUE候选 | 先审材质语义，核对源UV wrap/factor/剔除/扩展；不是任意shader转换器 |
| `build_packed_fish_source.py` | R11实证实现：8个源mesh、1465顶点/1710三角/18骨；身体`Closed_body_B`+口内、目标源对象`Anal`及当前单位变换 | **新鱼必须先适配。** 读取本鱼recipe的真实数量/部件/变换/rig；不能删断言或直接改名通过 |
| `export_packed_fish_source.py` | 读已正确制作且通过guard的单mesh源；要求明确UVMap、三角面、源ID/完整连续分区；当前材质合同固定为R11 MASK | 本鱼满足同一合同可复用；不同材质/层/UV/变换需明确新增受测分支，不盲重签源 |
| `verify_packed_fish_parity.py` | 当前仍校验1710面、18骨、54通道、9分区及身体840/口内64；保持相同源顶点身份，非任意重排比较器 | **新鱼必须先适配期望值及身份映射。** 保留有向三角、rest父级/skin root与材质验证 |
| `packed_fish_parts.py` / `PackedFishValidation.gd` | 当前为身体外皮+口内两分区、7鳍，共9源分区→8逻辑部位；必须全覆盖且互斥 | **其他库存先适配。** 不给鲨鱼、鳐、鲸类或有独立眼/附层的鱼伪造七鳍/九分区 |
| `prepare_packed_fish_validation.py` | 从该鱼已有约束计划生成新模型绑定的part/fin/runtime/head计划；不运行门 | 使用本鱼新约束；绝不能把罗非鱼R9根线、头宽或旧通过报告换SHA冒充本鱼 |
| `validate_packed_fish_import.gd` | 当前smoke写死身体904、7 fin tracks、54原始通道等罗非鱼断言 | **先适配本鱼库存和实际动作映射**；raw GLB通道与引擎优化后的轨道数分开 |
| `validate_fin_*` / `validate_standalone_body.py` | 现有packed分支接上述part合同，普通旧分件分支保持 | 对应本鱼库存/选区；身体0缺像素、物理容差不因打包改变 |
| `capture_standalone_fish_review.gd`、`open_nile_ab_review.py`、`preview_nile_three_live.gd` | 当前罗非鱼相机/近景/物种绑定与三鱼入口；源证据要求绝对路径，capture输出为`.../final-sop/review` | **先适配本鱼相机/比例/入口**；不替换其他鱼，不把旧标线图贴到新图集 |
| R11 `assemble_review.py/make_sheets.py/finish_checkpoint.py` | 本次证据组装样例，含固定SHA、路径、124图/288帧和罗非鱼观察 | **不能直接换species运行。** 为本鱼实际证据建立绑定/观察，不复制“passed”或用户接受 |

适配发生在冻结前，先做原始数组/材质对照和一次实际导入小样，正例与有意义负例通过后再完整门。只改文档或viewer控件而不改冻结模型/控制器/检查器时，不重跑无关物理门。未完成适配就如实记录阻断点，不用连续失败去“摸”硬编码。

## 3. 制作图集与单surface候选

1. 冻结一份最终实际装配GLB作为几何/材质基线。普通材质可按真实UV域提取图块、加padding、无缩放打包；按原repeat/clamp展开越界UV，不能一律夹到边缘。
2. 按原baseColorFactor/顶点色的**实际引擎生效状态**处理颜色。常色口腔可用独立图块；linear RGB按标准分段sRGB编码为RGBA8，记录量化误差。不能假设存在 `COLOR_0` 就会参与Godot着色；R10白嘴负例正是该错误。
3. 身体不透明语义必须保留；独立鳍透明边界在MASK中保留。合为一个材质/primitive不要求焊接身体与鳍，也不影响骨骼独立驱动。
4. 对比POS、NORMAL、UV重寻址、骨名权重、同向三角、rig rest/父级/IBMs、clips、贴图RGBA与材质状态。无缩放图集不等于float32边界取样完全无差异，报告实际误差。
5. 新Godot进程实际看嘴部/两侧/背腹/鳍边，检查导入材质和正常动作；先挡住白嘴、黑块、透明身体等低成本可见错误，再进入源构建。

工具调用形式（先用已核对的绝对路径替换尖括号；不是直接粘贴模板）：

```bash
<venv-python> resources/scripts/volume-fish/pack_fish_material_atlas.py --model <完整基线.glb> --output <全新打包目录> --padding 3
```

padding=3为已测起点，不授权缩小原生像素。若一个材质无法等价承载特殊shader/叠层/剔除语义，可保留必要材质分组，说明原因；不能为“必须一材质”改坏颜色/身体完整性。

**默认不重复36项性能矩阵。** 本次已确认合并值得采用；只有新的性能问题或不同renderer/材质机制需要比较时，另立有范围的实验，按[性能审计](performance-audit.md)记录有效工作量。R10测得的是带同步读回的受控总步骤，不能当普通游戏FPS、纯GPU时间或下一鱼预估。

## 4. 回写真实可编辑源

优先在该鱼自己的原源里保留rig、rest、动作与对象变换，只整理静态mesh/UV/图集/材质。一次性源作者过程可以读取已审候选；**日常源导出不得再读取候选GLB来填源缺失数据**。

源需实际拥有：

- 打包图像字节、明确色彩/alpha解释，UV→Image Color/Alpha→BSDF→Output的有效节点链；真实Use Nodes、mute、投影、剔除和sampler等设置。
- 完整源mesh、原骨架/动作、JOINTS/WEIGHTS；normal/UV精度有需要时使用受签名保护的源角点属性。
- `_FOUNDRY_NORMAL_GLTF`（FLOAT_VECTOR/CORNER）、`_FOUNDRY_UV_GLTF`（FLOAT2/CORNER）、`_FOUNDRY_PART_ID`和`_FOUNDRY_SOURCE_VERTEX`（POINT），以及`foundry_logical_part_id`（INT/FACE）。这些是R11支持导出合同；其他源方案需同等实际证明，不强行套属性名。
- 完整部位表、每顶点/面归属、来源身份、图像/材质/几何/UV/蒙皮/rig签名。输出GLB `extras.geometry_parts` 必须由实际导出的ID和indices重新核对，不盲复制旧区间。

Blender创建新CustomData属性层后，**重新按名称取得所有属性和UV句柄**，再写数据并逐loop核对。旧RNA引用会失效；R11首轮3889行/UV错写就是此因，不能用法线量化/焊点去掩盖。

导出器引入的重复行，仅同一源ID且最终POS/NORMAL/UV/JOINTS/WEIGHTS及part完全相同时可压缩。不同源ID、不同接缝/法线/权重不能焊接；压缩前后记录行数与有向三角。R11为1468→1465，不是通用期望值。

编辑参考Empty若不渲染、不受动画、不属于既有rig/mesh祖先，可明确保留；不要为无害编辑辅助物重建鱼。实际渲染计数只看真正mesh。

## 5. 保存源后，新进程冷导出

适配后的源作者与已支持的导出/对照命令形状为：

```bash
<blender> --background --python <Foundry>/resources/scripts/volume-fish/build_packed_fish_source.py -- --recipe <本鱼recipe.json> --output <全新作者目录/final-artifacts>
<blender> --background --python <Foundry>/resources/scripts/volume-fish/export_packed_fish_source.py -- --blend <已保存fish.blend> --output <全新cold目录/fish.glb> --report <全新cold目录/export.validation.json>
<venv-python> resources/scripts/volume-fish/verify_packed_fish_parity.py --reference <已审单surface候选.glb> --candidate <冷导出fish.glb> --output <全新parity.validation.json>
```

第一、三条当前有第2节的物种限制；第二条只适用于已满足其guard合同的源。输出目录事先明确建立，不覆盖原源/已审报告；模型与报告不可互相别名。

必须核对：源SHA未因只读导出改变、输出真实可读、原生动画时刻/值/插值、骨名权重、IBMs、原命名节点rest变换/父级/skin.skeleton/mesh attachment、同向三角、NORMAL与UV、嵌入RGBA和PBR/alpha/sampler。不要仅看位置或骨数。

同工具链/同受支持源的确定性导出，比较“保存后的源第一次导出”和“新进程冷导出”的字节一致；一次作者过程读入的已审候选可因新metadata/节点表示而SHA不同，必须另作完整语义对照，不混淆这两个比较。不同工具版本导致非语义元数据差异时，解释差异并完整语义比较，不伪改SHA。普通Blender File Export未证明等价时，交付中明确指定支持程序。

使用当前工具的既有guard负例作为代码依据；本鱼编辑/新适配时，用隔离副本验证有实际改变的风险，如UseNodes/UV/部位/rig父级。源改坏应被拒绝。不要对当前通过源直接造负例，也不要只重算签名让旧报告“通过”。

## 6. 冻结一次最终候选与part映射

1. 保存最终blend、GLB、atlas、recipe及当前实际runtime/导入设置/LOD；冻结工具版本和源代码SHA。材质/静态部件固化在这一步之前结束。
2. 按本鱼新约束建立fin/runtime/head计划。准备器把新GLB与分区manifest绑定进去，**只准备输入，不授予任何旧验收通过**。

```bash
<venv-python> resources/scripts/volume-fish/prepare_packed_fish_validation.py --model <最终fish.glb> --reference-fin-plan <本鱼fin约束.json> --reference-runtime-plan <本鱼runtime约束.json> --reference-head-plan <本鱼head约束.json> --output <全新final-plans目录>
```

3. 分区manifest须覆盖每个顶点、每个index恰好一次，不能漏鳍、重复或空选区；身体外皮/口内逻辑合并仍需保持闭合身体。
4. Godot实际导入可能重排/复制顶点、量化法线和权重。按POS/UV/NORMAL、骨名权重和完整**有向三角多重集**建立对应，不能使用源顶点顺序；验证同一全局绕向转换，消耗所有三角且保留缝重复次数。物理阈值不随数组匹配容差放宽。
5. 仅验鳍、身体GPU或隐藏部位截图时，可从已验证的实际导入数组/skin/material构造诊断子网格；正常入口/整鱼动作视频恢复真实单mesh/surface。不得在游戏进场时重建静态造型。

**共享MASK身体分支**：只有身体全部引用的纹理域alpha255、factor alpha=1、支持的透明/PBR/nearest无mip语义明确、同姿态GPU0缺像素且透明负例有效，才允许与鳍共享MASK。R11用整个身体/口内UV包围矩形的所有texel作保守覆盖，不是只抽顶点；仅顶点不透明、强制opaque参考或闭合网格均不足。其他情况保留身体独立不透明材质。

## 7. 冻结后集中跑一次最终门

下面路径均为已适配本鱼的绝对路径。Godot Mono需要的 `.NET` 按本机已配置路径传入子进程，先查现有工具配置，不重新下载已有Blender/Godot。R11实测工具为Blender4.5.3、Godot4.7.1 mono，下一机器重新核实。

完整根/鳍面（具备此门的物种计划），一次导出490姿态后允许按相同检查器分4个CPU区间；不改采样和限值：

```bash
<venv-python> resources/scripts/volume-fish/validate_fin_membrane_clearance.py --plan <final-plans/fin-gate.plan.json> --game <Godot工程> --godot <godot> --blender <blender> --species <本鱼ID> --output <final-sop/full490> --membrane-workers 4
<venv-python> resources/scripts/volume-fish/validate_fin_completion.py --plan <同一fin计划> --game <同一Godot工程> --godot <godot> --blender <blender> --species <本鱼ID> --output <final-sop/root-completion> --reuse-full490-completion <final-sop/full490/completion.validation.json>
```

第二条核对当前完整490覆盖177及所有依赖；不是另跑177，模型/控制器/检查器/计划变了就不能复用。鳍根微小缝与自由鳍膜分别判，根点通过不代表长边/面内部通过；失败按[有限鳍面修复](finite-fin-contact-repair.md)收齐包络，局部验证后再冻结。罗非鱼.5mm根缝/.02mm自由面为本次冻结限值，不能擅改为别鱼默认或为通过放宽。

其他专项按同一最终模型执行并保存独立报告：

| 门 | 实际入口与要看什么 |
|---|---|
| GLB机械 | `cli.volume_fish.glb_checks`；完整闭合/有限值/权重/原生循环/纹理实际来源和nearest/PBR/root motion。传实际作者图集，不冒称派生图集等于原始RGBA |
| 身体077 | 普通实际入口用既有`validate_body_integrity.py`；完整独立GLB分支调用`validate_standalone_body.validate(game,godot,plan,output)`。检查闭合、全部身体供体、实际GPU同机位同姿态和透明负例；当前packed适配为两姿态×八视，零缺像素 |
| 动作 | Godot `--headless --path <game> --script <Foundry>/resources/scripts/volume-fish/validate_motion_controls.gd -- <绝对motion报告.json> --standalone-plan <candidate.plan.json>`；实际五组×96、零幅度、独立频率/幅度、支点和切换，原生clip另外保留 |
| 头型 | `check_head_form.py --plan <head.plan.json> --output <positive.json>`，再以`--baseline`检查本鱼尖头负例；正例退出0，负例被拒绝应退出1。无头型约束资料时先补本鱼约束，不套罗非鱼曲线 |
| 新进程视觉 | 非headless Godot：`--path <game> --rendering-method gl_compatibility --script <Foundry>/resources/scripts/volume-fish/capture_standalone_fish_review.gd -- <candidate.plan.json> <绝对final-sop/review>`；使用已适配相机/物种的入口，记录真实水环境和静态数组前后digest |

只同时运行一个GPU捕获/性能进程，CPU数值分区可并行；日志错误、超时、缺报告、错SHA都不得解释为通过。首次完整门新发现失败，记录为下一批问题；不每修一处重跑全套。已通过且依赖未变就继续收尾。

## 8. 实际看图、动作与交互入口

看接受源图/风格与成品同姿态、整体八向灰模/贴图、头嘴近景、左右眼、隐藏全部活动鳍的身体、每片鳍展开与装回、尾柄连接、背腹与鳍厚度端面、原生/四动作/真实切换、实际水环境。检查正常游戏尺寸和近景，不用纯灰模或数值代替颜色审核。

当前捕获实现为124PNG及24秒/12fps的288帧绕看和动作序列；这是本次工具的证据规格，不是所有新鱼必须恰好124图的产品要求。镜头/鳍库存改变时说明对应覆盖。原始PNG保留，用nearest缩略图生成拼图便于审阅，不能重绘证据。视频须查时长/帧数并实际看代表帧/需要的连续段，报告所看范围，不把离散样本称连续时间证明。

安装入口必须明确：完整独立GLB/实验B查看器，或用户授权的正式游戏场景。仅导出成品不能声称已替换主展厅。

交互入口冷启动一次，实际验环绕、滚轮缩放、平移、同步视图和四动作/切换，检查实际全鱼surface数。旧分件隐藏开关要通过可信part映射工作或明确禁用；旧R8标线1961×1024贴图不能套到2048新图集。自动烟测结束退出，不留窗口；没有要求时不额外打开预览。

## 9. 逐鱼SOP账本与通过条件

```bash
<venv-python> cli/gamefactory.py volume sop-init --species <本鱼ID> --output <final-sop/production-review.json> --json
<venv-python> cli/gamefactory.py volume sop-check --review <final-sop/production-review.json> --output <final-sop/sop.validation.json> --json
```

已有账本继续填，不为覆盖旧接受记录重新init。按[正式导出收尾](final-asset-export.md)填写`runtime.finalization`、当前全部candidate角色、实际冷读`fish_final_asset_cold_load`及完整`bound_inputs`。角色包含源图、最终模型、profile、runtime manifest、motion config，另绑定blend、atlas、导出/验证helper、part manifest、recipe和实际引擎资源。

每阶段写本鱼实际观察和证据ID。新增模型专项报告绑定当前SHA；旧来源/解剖/已接受嘴部证据可按未变依赖明确复用，不修改成新模型通过。用户只接受嘴部，不能扩写整鱼接受；操作者图审/技术通过与用户接受分开。

SOP通过只检查证据合同，必须已有实际冷导出/专项/看图。代码改动按仓库适用review要求执行；R11独立复核检查了源guard、part覆盖、真实GPU、当前依赖及清理收据，不能只找第二模型重复摘要。

## 10. 每轮产物收尾与继续条件

先确认本轮进程结束、没有后台GPU/未完成job，再提炼源/成品、方法/参数、失败原因、来源SHA、代表图/视频与复现命令。按明确路径+SHA清单清理：

- 通过的490稠密样本：完整报告、原export哈希表、代表证据保留后，可用`validate_fin_completion.discard_passing_samples(export,directory)`，生成逐文件收据；失败样本不套此成功清理。
- 视频编码及全部原帧哈希验证后，保留视频、代表原帧和清理表，再删冗余JPEG。124等实际部位PNG是否精简按唯一性/引用决定，不按体积直接删。
- 重复冷导出GLB、Blender备份、未采用候选/临时日志先查引用。若与唯一当前成品相同且可重建，在收据明确原输出SHA、替代源和历史报告解释；当前proof直接引用的唯一证据不悬空。
- 源操作交接与最终handoff分开时，引用各自稳定文件；修改handoff后刷新assets清单中的哈希，不能让source资产清单仍签旧文本。

清理后核对实际体积、保留清单、Git/LFS状态、candidate/evidence当前哈希及`git diff --check`；不因更新清理统计重跑模型物理门。用户要求提交才对Foundry和游戏独立仓库commit+push，分别确认；未要求时如实保留未提交改动。

最终交接最少回答：用了哪个源/导出程序；实际入口；计数/材质/鳍库存；通过/失败/未测；用户接受范围；保留与删除；下一步能否开始另一条鱼。下一鱼开工先看第0/2节，不从旧聊天或旧“pending”状态重做已通过鱼。

## 11. 本次实证索引与失败处理速查

实证根：目标游戏`experiments/nile-dorsal-route-trial/`。R9为定型形体/接受嘴部及有限鳍面基线；R10为单材质候选与有效性能实验；R11为源固化及最终实际验证。以R11 manifest/progress/handoff/assets-manifest和validation report为当前状态。

| 实证/经验 | 文件或处理 |
|---|---|
| 本鱼完整参数 | Foundry `resources/volume-fish/nile-tilapia-single-material-finalization-20261030.json`；1710三角/1465顶点/18骨/54原始通道/9分区、2048atlas均非跨鱼常数 |
| 源与成品 | R11 `final-artifacts/fish.blend` SHA `98c18cd9…19ae82`；`fish.glb` SHA `2ec51a58…6e28a`；完整SHA见manifest |
| 源冷导出/防错 | `source-finalization.validation.json`、`source-guard-negative-controls.validation.json`（14源负例）、`rest-negative-controls.validation.json`（2骨架负例）、`packed-target-complete-parity.validation.json` |
| 实际分区与所有最终门 | R11 `validation-work/final-plans/`、`final-sop/`；`production-review.json`、`sop.validation.json`九阶段及`operator-visual-review.validation.json` |
| 入口操作 | `three-interactive-input.validation.json`、`three-live.validation.json`及`validation-work/viewer-smoke/viewer-smoke.validation.json`；默认B=R11，旧主展厅未替换 |
| 源UV/NORMAL错写 | 属性层新增后重取句柄，逐loop断言；不是靠盲压重复顶点修复，见`attempt1-diagnostic.validation.json` |
| 白嘴/COLOR_0不生效 | 原材质实际未启用vertex color；改常色atlas块，保留linear→sRGB8量化说明，见R10报告，不在Godot追加静态补色 |
| 导出行数多 | R11实际1468→1465，仅同源ID+全部最终属性等价；不全局merge by distance |
| 材质guard漏项 | 实际UseNodes/节点链/mute/图像解释/投影/UVMap active与render都要检查；不能只签图像字节 |
| 骨架看似一样 | IBMs/通道相同仍可能改root rest/父级；比较原命名节点rest/parents/skin root并用负例验证 |
| 身体共用MASK | 全身体UV域alpha255+实际16GPU对照0缺像素，透明负例43467缺像素；不等于所有鱼可用MASK身体 |
| 清理与成本 | R11约保留60MB；删490密集姿态、265冗余JPEG和4重复GLB约121MB。没有重跑36case、减面/减骨；未调用PI/DeepSeek/Kimi，不编Codex节省百分比 |

次级模型可承担有限输入事实提取、工具差异表、证据新鲜度/漏项审阅和收尾草稿；用清晰交付合同、可执行检查与失败原因让它定点重做。确定性计数/哈希/几何/图集打包直接交本地工具，视觉判断交有实际看图能力的一方；不因模型便宜就重复整条流水线，也不把普通Codex子代理称作PI/DeepSeek。密钥不进recipe、报告或日志，实际调用和用量单独如实记录。

### 次级模型的小任务交付合同

需要委派时，先给该任务必需的文件白名单、冻结SHA、可修改范围/输出目录、明确成功条件和停止条件；读取当前工程已有授权，已允许范围不反复询问。事实审阅可只交部件计数/材质状态/输入依赖表，不让次级模型擅自开启完整490、GPU或性能矩阵。实现任务先说明第2节硬编码与本鱼差异，完成后要求可运行命令和实际报告。

每次交回至少含：实际读取/修改的文件、关键结论与证据路径/SHA、已执行命令和退出状态、失败根因/仍未知、是否改变冻结依赖、模型实际input/output/cache tokens及重试次数（供应方未给则未知）。主审只核关键不变量/负例和当前实际报告；失败把精确差异交回定点修复，不由主审无提示重做同一整段。重复同类失败先检查输入/工具能力，停止盲重试；需要视觉能力而模型/PI未具备时，文字任务与实际看图分开交付。

成本记录分为确定性工具耗时、次级模型调用、主审、返工、额外收尾；有可核验计量才写Codex实际tokens。脚本运行秒数、账户周额度变化和供应方tokens不能互相折算，也不能直接推出节省百分比。未找到PI/服务配置时如实说明缺口，不伪称委派成功，不为记录SOP重新调用付费模型。
