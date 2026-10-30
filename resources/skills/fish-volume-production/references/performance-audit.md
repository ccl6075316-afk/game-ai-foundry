# 鱼模型性能审计：检查实际装配，再分开测加载与游动

触发：用户询问模型是否过重、无效面/材质/骨骼是否影响性能，或准备扩展到大量同种鱼。先审计，不以缓存命中、原GLB面数、绑定/外观通过推断群体性能；不在审计期间擅自减面、焊接、删附层、降贴图或恢复已拒绝LOD。

## 可复用入口

Foundry `resources/scripts/volume-fish/audit_runtime_performance.gd` 在目标游戏项目下直接调用当前 `VolumeFishExhibit` 工厂；依次检查原导入和实际最终身体/眼/嘴/鳍/材质，统计顶点、三角面、隐藏部件、surface、骨骼、实际LOD、未引用顶点、零面积/重合候选、材质/shader/纹理对象。使用自带合成退化/重合/未引用顶点反例检查计数器；这不是解剖或视觉验收。

```powershell
# <review>须是当前游戏 plans/reviews 下已核对的绝对目录。
<godot> --path <game> --rendering-method gl_compatibility --windowed --resolution 1280x720 --log-file <review>/inventory.log --script <Foundry绝对路径>/resources/scripts/volume-fish/audit_runtime_performance.gd -- --mode=inventory --output=<review>
# 每种鱼单独子目录，避免覆盖记录。
<godot> --path <game> --rendering-method gl_compatibility --windowed --resolution 1280x720 --log-file <review>/<species>/benchmark.log --script <同上脚本> -- --mode=benchmark --species=<id> --samples=180 --output=<review>/<species>
```

对照分别是空场、1/10/50条同种鱼的静止/原控制器游动，关闭VSync，60帧预热后采180帧。记录整帧、直接动作调用、renderer CPU/GPU区间、绘制批次与primitive中位数/P95。各鱼全部放入可见网格，使用固定1/60模拟步长，摆放不参与路径成本；没有鱼缸/水/阴影/碰撞/寻路。不同数量的屏幕覆盖不同，不能当纯三角面线性测试；不能据此承诺正常游戏FPS或一万六千条容量。

配套 `summarize_runtime_performance.py --game <game> --review <review>` 目前汇总黑鲷、带鱼、蓝鳍金枪鱼三组标准对照，生成逐鱼CSV、中文审计和validation report。检查各轮实际输入哈希一致、当前仍匹配、反例通过、无引擎错误。需要其他标准物种时显式扩展汇总列表；不能把未测鱼性能按面数直接推算。

## 如何解释，避免误修

- 进场准备、节点/骨骼初始化、每帧动画和绘制分别报告。提前固化不会自动减少现有面数、绘制批次或动作计算。
- 原GLB只是供体时，必须看最终替换身体、独立唇带、眼片和鳍资源。2026-10-25实际28鱼审计中，黑鲷原导入64278面，最终218104面；梭鲈仅唇带138720面，蓝鳍唇带65280面。它们是该版本数据，不是新物种预算。
- 三角面密集不等于全部是无效面。零面积按静止/原数组检查，随不同蒙皮权重可能展开；相同几何可能服务双面/叠材质。未做同姿态/动作及语义分类前，不自动删除。近零面按包围盒对角线平方乘1e-12分类，也不是删除阈值。
- 唇带独立是当前原像素/浅凸/单独UV迭代方案，不要求进场装配；允许源模型阶段完整集成。合到同一个GLB、焊接拓扑、合并材质是三件不同的事。不能为了合并取消真正口裂、薄带或原画接续；优化后按实际影响走局部与最终门。
- 有些鳍保留LOD，不代表身体、唇、眼有整鱼多层级；没有视觉验过的自动LOD不能直接启用。制作预算先按游戏标准化实体体积、预计同时数量、物种结构与实际减面对照决定；不要拿屏幕像素替代用户要求的体积依据。运行时距离/屏幕误差LOD与其切换是另一个问题。
- 动画开启的差值包括控制器、骨骼更新和蒙皮绘制；不全部归因于某一脚本或GPU。检查逐骨骼重复路径求导/系数字典、临时检查记录、分级更新与可共享动画。
- 纹理字节为每鱼独立纹理对象对应Image数据之和，不是实测VRAM；不同对象可能像素相同，同种实例又可能共享。不能乘以鱼条数报显存，也不能凭尺寸相同断言内容重复。
- Shader取图调用数只是源码出现次数；GPU时间区间可能包含驱动/队列空闲，不直接当纯着色计算时间。确认测试期间其他游戏窗口与负载，不擅自关闭用户或其他任务窗口。

## 收尾

实际报告位置：目标游戏 `plans/reviews/fish-performance-audit-v1/`，正式结论见 `performance-review.md`。本轮未改鱼资产、阈值或接受状态。保留紧凑原始指标、必要日志和三张不同物种布局证据；不导出全顶点JSON、录像逐帧或复制完整游戏。每轮核对输入变化、日志错误、保留清单和实际体积。

## 用户授权的减面调查：独立候选，不直接启用旧LOD

2026-10-25梭鲈调查记录位于目标游戏 `plans/reviews/fish-reduction-v1/reduction-review.md`。确认唇带生成器硬性257纵向样本×17横向点；每片实际8160面，`repair_lip_contact140.py`为避免T接缝对整条带均匀四分，两轮可到130560面。必须按实际脚本和当前资源分别取证，不能把某一历史物种参数套给全部鱼。身体体素重建、眼片均匀环扇区和接触补面也要按部件统计；独立部件并不必然高面，合GLB不等于减面。

窄范围复现实验工具：

- `probe_lip_reduction.gd -- --output=<游戏plans/reviews绝对目录>`：Godot headless生成梭鲈唇带候选；不改生产配置。ImporterMesh非索引属性必须与原数组一致；压紧顶点时UV/UV2/法线/颜色/骨骼及权重对应保留，拒绝依赖VERTEX_ID的shader和未解析custom字节布局。参数比例是最近可用LOD比例，须报告实际面数。
- Blender background运行 `check_reduced_lip_contact.py -- <目录>`：原版和候选全顶点/面心/边中点对实际闭合身体做有符号距离，保持原−0.00003静态阈值；不能用平均误差掩盖少数穿入。
- 实际GPU运行 `render_lip_reduction.gd -- --output=<目录>`：新进程载候选，原工厂整鱼A/B，仅换唇带。检查四权重长度/非负和求和误差；存储资源约1/65535的量化误差应与原版同口径报告，不能放宽原生严格门或声称其已通过。统一相机，不以自动像素差替代实际看图。
- `.venv` Python运行 `finish_lip_reduction.py --review <目录> --cleanup`：137项输入绑定检查、记录通用原因/逐鱼参数/实际证据，删除明确列表中的失败候选与可重建采样，保留唯一候选和代表性A/B。当前工具是梭鲈专用调查，不自动跨鱼推广。

本次138720→34680唇面，整鱼212360→108320（约49%）且静态接触通过；17340唇面已有4个采样穿入，4604有630个且含退化面，均拒绝。只完成静态接触、多视图与单姿态观察，不是完整动作/最终鱼验收，没有替换生产资源或测FPS收益。下一步需要屏幕误差/曲率驱动的局部重拓扑与完整门；不靠降低接触阈值通过。外部Planet Zoo第三方上传模型的面数只作来源明确的参考，LOD/毛发全成本不明时必须保留限制。

## V2：用户明确1–3千整鱼预算，不能以十万或减半作为完成

用户随后拒绝十万面目标。整鱼预算应先探索1–3千，远景数百另试；不能用旧高模接触约束诱发整带加密再反推“必须十万”。当前梭鲈独立候选992/2991/6000面，详见游戏`plans/reviews/fish-lowpoly-v2/lowpoly-review.md`。正常展示尺寸大部分像素外观保留；近景下唇折硬/UV折痕和唇体穿入仍未解决，全部不是生产接受。

通用机制：跨几何重复接缝焊接后按整鱼预算collapse，逐原surface重心运输UV/UV2/颜色/法线/骨权重和材质参考；明确重绑rest114、eye、mouth136 stride记录和material130定位表，保持UV护栏。`export_lowpoly_source.gd → build_whole_lowpoly.py → LowPolyFishTransport.gd/render_whole_lowpoly.gd → check_whole_lowpoly.py → cold_load_lowpoly.gd → finish_whole_lowpoly.py --cleanup`提供窄范围样例。当前导出器/分配表/渲染器明确只服务梭鲈，不作为无检查跨鱼一键工具。

物种参数在`resources/volume-fish/zander-lowpoly-study-v2.json`，由构建器实际读取；身体66%、唇8%、眼6%、8鳍20%仅本轮起点。2991面、1712顶点的SCN新进程无外部依赖，四动作0/1.25秒骨骼确有变化；这不是最终导出/连续动作证明。三个候选身体闭合、无退化面，但静态唇接触失败79/85/51采样。下一步低面身体和薄带须共同布面并保留特征边，不能只各自减面。14surface/原shader仍保留，未承诺FPS或显存收益。只保留一份有用SCN和紧凑图/数据，其余可重建候选及二进制按报告清单清理。

## 外部游戏面数查证

2026-10-26资料位于目标游戏`plans/reviews/fish-game-comparison-v1/reference-fish-counts.validation.json`。开发者Twice Circled在GOG官方帖子和Steam Workshop公开Nurse Shark；下载其2019源FBX实测294顶点、584三角面，ASCII中584个多边形全已是三角形。计数器`count_reference_fbx.py`验证数组长度、索引和终止标记；Blender默认FBX导入器拒绝ASCII时直接读格式，不因此虚构计数。保留小型原始FBX/档案SHA/计数报告，未解析TC3D删除；不能把源FBX数写成当前游戏所有鱼LOD0预算。

ABZU原作者Bryce Warner公开Eagle Ray约1.4k；Thresher shark展示约6.7k还含pilot fish/remora，不能写作单条鲨鱼。Subnautica第三方提取样本需标明上传者工具声明及未知LOD；Fox3D的Sand shark为2014展示，不等于最终发行版。Dave the Diver官方Unity案例只明确2D/3D混合且未给单鱼面数，不按画面猜3D预算。带游戏标签的同人、商店模型、未说明来源上传均不得冒充原版资产。

## V3：按标准体积和预计数量做多物种对照

2026-10-26用户纠正：小鱼数量多要更严，大鱼特别鲸鲨数量少可放松；不按屏幕像素或体长档位定制作上限。体积不直接等比换面数，仍须预计同时数量和结构质量约束，整缸几何量为各物种数量×三角面之和。此前1000/1500/3000/5000只是讨论值，不作为已接受预算。

目标游戏`plans/reviews/fish-volume-budget-v3/volume-budget-review.md`为本轮结论。实际蓝鳃289/593/1196，梭鲈799/1598/3200，大双髻鲨2000/4000/8000，鲸鲨3998/7998/16000；原版与各档同机位GPU对照。配置`resources/volume-fish/volume-budget-study-v3.json`明确每鱼部位预算，不把梭鲈8鳍均分套给双髻头翼。`export_budget_source.gd → build_budget_study.py → render_budget_study.gd → check_budget_study.py → finish_budget_study.py --cleanup`提供本批有限入口；未知物种须先定结构/来源及索引shader分支，不能自动批量安装。

体积从当前闭合身体按077缝身份精度统一绕向、逐组件算四面体体积，再乘实际游戏变换行列式。排除鳍/眼/唇附层，分离头翼相加未做重叠域并集，故仅为制作模型体积近似，不是生物实测体积或真实放养密度。原生四权重和18/19/17/21骨保留；没有测FPS或声称大量鱼容量。所有候选身体闭合且无零面，不代表唇/鳍支持已过关。蓝鳃300档丢背鳍棘形；普通鱼正/斜近景唇带/低面身体不贴合、纹理折叠；双髻头翼正面材质边界也有波折。加总面数未必单调消除接头问题，下一批应共同布面并保护特征，不能靠抬面数或放宽接触容差。

保留12配方、多视同姿态图、局部诊断与真实四鱼Viewer；删可重建源二进制及重复控制台日志，不保留多份大SCN。Viewer复用已验证的根视口输入，但8m鲸鲨相机距离需随长度变，并同步修正光标缩放的目标平面；不能固定2m导致正面相机进入身体。`viewer-test.validation.json`是四鱼切换/四动作两个时间点/近景局部导航烟测，`navigation.validation.json`是蓝鳃实际输入事件回归，均不是完整鱼门。未做正式静态回写和冷读，不能称成品或宣称通过`sop-check`。

## 2026-10-26：先把现有鱼群成本和分层收益分开测

目标游戏`plans/reviews/fish-school-v1/validation-report.json`汇总22个成功案例及原始`benchmark.validation.json`，来源哈希均匹配。当前Apple M4、Godot Forward+/Metal、1280×720、关闭VSync，30帧预热后采120帧；不能与旧RTX报告直接横比。独立Viewer调用现有最终装配、真实体长、原生骨骼及控制器，没有改鱼几何、材质、源图或接受状态。

实际渲染仅25种：三种双髻鲨被现有137导入快照门阻断，明确排除`scalloped_hammerhead,great_hammerhead,smooth_hammerhead`，没有关闭来源门。模拟也传同一25种名单。每物种在不同路点起步，同种成员聚集于同一路点附近；50条/25种初始化有24组同种邻居，避免把完全分散个体误当局部鱼群负载。

| 实际鱼数量 | 全频帧中位/P95 ms | 分层帧中位/P95 ms |
|---:|---:|---:|
| 25 | 8.071 / 8.490 | 5.195 / 11.844 |
| 50 | 15.314 / 15.826 | 7.824 / 8.676 |
| 100 | 29.868 / 30.600 | 15.248 / 16.502 |
| 200 | 59.526 / 60.394 | 30.589 / 32.498 |

仅模拟CPU中位：2000代理全频16.331ms、分层7.397ms；16000代理128.212/59.819ms。这些是当前实现的成本，不能推断实际渲染16000条鱼容量。25条分层P95高于全频，不能只用中位数承诺稳定收益；持续关注P95、工作量与其他并行进程。

方法：保持来源、随机种子、名单和固定1/60步长一致，分别测`static`、`motion`、`school-full`、`school-tiered`，另用headless隔离模拟。一次只跑一个案例；来源或设置改变必须重跑。空间哈希每鱼最多96候选访问/24接受邻居，遍历起点轮换，报告截断和紧急约束次数；稠密负载有非零截断/接触，不能把上限下的便宜成本当完整邻居解。

分层是固定20%/30%/50%工作量分组，非距离/可见性LOD。决策60/20/10Hz，每固定tick仍积分所有代理；原生骨骼60/15/5Hz，间隔内保持姿态，累计时间推进下次动作，无插值。一引擎帧只跑一个固定tick，无墙钟追赶；帧间隔不是正常游戏FPS保证，也不是独立GPU时间。固定0.18m点代理不代表不同体长或完整鳍部碰撞；当前路点绕球/反应避障不是正式寻路或仿生游动。未计水、玻璃、阴影、完整物理和玩法AI，也未过正式鱼资产门；真实体长使小鱼画面很小，不据此称视觉质量通过。

复现前把已核对的Godot、游戏、.NET及review绝对路径代入；review必须恰为`<game父目录>/plans/reviews/fish-school-v1`。成功报告默认仅在来源/设置仍匹配时复用；明确重测才加`--rerun`：

```bash
.venv/bin/python resources/scripts/volume-fish/run_fish_school_experiment.py --godot "<godot>" --game "<game>" --review "<review>" --dotnet "<dotnet>" --group all --rerun
DOTNET_ROOT="<dotnet>" "<godot>" --path "<game>" --rendering-method forward_plus --rendering-driver metal res://scenes/fish_school_review.tscn -- --count=50 --exclude-species=scalloped_hammerhead,great_hammerhead,smooth_hammerhead
```

核心行为25项、runner回归7项通过，分别保留`core-test/test.validation.json`和`unit-test.validation.json`；交互UI另验，不能用这些测试替代操作或视觉审核。runner逐案例记录环境/来源并增量更新根报告，180秒超时杀本次进程组后停止，拒绝脚本、shader、资源加载和断言错误；仅精确识别macOS系统CA证书查询噪声为环境警告。

保留旧28鱼OpenGL预检`render28-static.engine.log`作为无效性能证据：shader需17/18采样器而平台上限16，另有双髻鲨来源门和3个缺失导入。后者已恢复；没有改shader或绕门。初次runner因Godot JSON的1/60小数精度误判成功报告，已仅对固定步长使用绝对1e-14容差并回归；整数、名单和哈希仍精确比较，该编排缺陷不是性能失败。完整22案例是修正后重测结果。

## 2026-10-26 鱼群动作接线修正 v2

v1是历史来源快照，不能作为当前源码测量。用户指出旗鱼/鲸鲨僵硬后，确认：载体改为鱼群路线，身体却仍按私有椭圆弯曲；相反路线的实际骨骼差值为0。另有交互`min(delta,.05)`丢时间。修正采用独立adapter输入真实航向/俯仰历史，保留原生波形、鳍与物种参数；60Hz固定步每帧最多8步且积压保留，骨骼到期每帧仅算一次。默认全频；分层保持姿态的代价没有由“性能优化”隐去。

实际双鱼Metal近景对照（相同相位/输入、1s预热+8s片段）已看图确认网格转向反向弯曲，骨骼计数不能代替此项。两个视频各192帧/24fps；不是实时FPS或正式鳍根/身体/生物验收。新基准50条全频17.247/18.960ms、分层8.266/8.653ms；200条55.959/60.170ms、33.127/35.357ms（中位/P95，AppleM4 Metal）。包含adapter，仍为每渲染帧固定一tick；不据旧v1直接声称修正加速。

通用防回归：同相位直行/左转/右转残差、8s在60/15/10Hz的耗时守恒、卡顿积压补算、转弯沿骨链延迟、原生鳍/波形保留；记录实际体长和点代理限制。新状态与复现见`projects/fishing-2d/plans/reviews/fish-school-motion-v2/validation-report.json`及`motion-review.md`。runner现在只允许精确v1/v2 review根；来源改变后保护v1历史并要求写v2。正式资产及独立鲸鲨外观工作未被这次原型修正替代。

## V4：不设目标，先区分坏面与人为过密

用户要求先找冗杂的增面，随后明确跳过仍在调整的鲸鲨。`audit_geometry_redundancy_v4.gd`复用既有计数器，当前工厂仅审梭鲈/黑鲷/蓝鳃/旗鱼/蓝鳍金枪鱼，699绑定前后稳定；鲸鲨专用57路径在哈希前排除，共享配置/代码仍核对。结果在游戏`plans/reviews/fish-geometry-redundancy-v4/inventory.validation.json`及`findings.md`，不能把旧390绑定审计已变化的数据直接叫当前值。

当前梭鲈唇带138720面，占整鱼65.3%，surface分别8160/130560，与257×17采样及两轮整带四分机制对应。黑鲷身体186040/85.3%、蓝鳃身体64202/68.1%、旗鱼背帆89526/44.6%、蓝鳍唇带65280/30.1%和双胸鳍52172/24.1%列为优先密度调查部位；后者没有精确绑定的完整后续细分计划，不能指认都是均匀细分所致。

五鱼合942482基础面，未引用顶点和重复索引的必然退化三角形均0；静止零面积14、同surface重合30仍只是候选。静止坐标相等不等于完整属性/蒙皮等价；shader顶点编号查表也使盲目压紧焊点有风险。明确改进方向是保留结构/接缝/变形，将额外采样限制于实际误差和曲率区域，不能以“清垃圾”冒称已大幅减面。本轮只定位，没有设预算、生成减面成品、替换资产或测FPS；无需新的静态固化，保留约小型报告和完整日志，重复日志清理见报告。


## 2026-10-30：九材质到单图集的鱼群对照方法

已选择该方案、准备固化或推广下一条鱼时，转到[单图集源固化完整SOP](single-material-source-finalization.md)。复用本节的实测方法与限制；没有新的性能问题时不逐鱼重跑36案例。源/成品、实际外观和各门仍须按本鱼输入完成，不能继承罗非鱼的验收结论。

单鱼低面数不代表低绘制成本。应分别核对mesh、surface/material、真实骨骼动作、顶点蒙皮与像素负担。把独立鳍合为同一绘制primitive不必焊接几何，独立部位仍可由原骨骼驱动；源制作对象与最终绘制打包是不同层次。原图集按实际UV域裁取、加留边、无缩放打包；超出0..1的UV必须依原sampler的repeat/clamp展开，不能夹到边缘。Source OPAQUE身体与MASK鳍合材质时，身体图块alpha须保持原不透明语义，不得把已有黑透明像素裁成身体洞。

新工具 `pack_fish_material_atlas.py` 只接受当前支持的普通PBR/标量specular0；不同剔除/PBR或未知带纹理扩展拒绝，不把旧纹理索引塞入单纹理输出。通过位置、NORMAL、JOINTS/WEIGHTS、有向indices、骨架/原生动画的精确值验证证明打包未改动几何动作；新UV的最近采样仍有float32边界误差，原图像素不缩放不等于逐屏幕像素完全相同。

真实Godot导入是必须门：首个候选把口内常色放入COLOR_0，数组虽存在，实际材质 `vertex_color_use_as_albedo=false`，白色图块直接渲染白嘴。仅检查GLB颜色数组或机械通过漏掉此错误。修为原linear baseColorFactor按piecewise sRGB编码到专用RGBA8色块；明确记录量化前后数值并重看同姿态正/斜/侧口内，不把“启用顶点色”当未经验证的通用修复。外部贴图factor非白时先拒绝，避免无意改写外皮色。

性能对照按原9组、合1组MASK、同几何合1组OPAQUE，100/300/1000条，静止/真实controller动作各测；两轮变体顺序反转，30帧预热、120帧采样。逐帧核对实际primitives=鱼数×1710、draws=鱼数×9或×1、样本前后窗口可绘制、动作pose实际变化。macOS后台窗口可能停止绘制；`can_draw=false`的案例必须拒绝，不能将等待/看门狗超时解释成模型慢。专用测量窗口always-on-top仅作用于本次进程；失焦本身可合法，只要真实draw持续。不要关闭用户其他窗口。

窗口方案后来在matrix-v2/v3都被macOS不可绘制/最小化阻断；always-on-top不能保证系统不最小化，禁止反复抢用户焦点。整轮部分结果均不采用。替代受控方案为真实OpenGL离屏渲染，关闭自动渲染循环，每样本恰好force_draw(false)一次并get_image同步读回；测controlled_step/motion_call/forced_draw_readback，包含固定读回成本，不能叫正常FPS或纯GPU时间。新schema与实测有效性仍以本次最终报告为准。

完成后用 `summarize_fish_material_matrix.py` 重新核验采用矩阵的源码/资源/报告哈希、36案例全部raw，以及真实工作量；合并两轮实际原始样本算P50/P95，同时保留各轮范围和controller直接调用时间。GPU计时未提供时明确缺测；总帧alpha差不是纯GPU成本。零增面的OPAQUE控制会暴露原透明边界，只能帮助定位，不能代替“增加N面保同画质”的实测。实验文件在游戏 `experiments/nile-dorsal-route-trial/round10-material-performance/`，本鱼参数在 `nile-tilapia-material-performance-20261030.json`；以最终validation-report数据为准，不能用该方法段落预先宣布性能收益或正式鱼验收。


本轮最终受控36案例/2160raw与独立审核已通过，实际1000条游动原9组→合1组MASK总步骤P50为2228.378→485.876ms（含完整同步读回，不是游戏FPS），直接controller调用220.930→219.927ms基本未变。MASK→OPAQUE合并P50只下降0.64%，两轮-0.66%/+2.20%，未测得关闭裁切稳定收益；现阶段不支持为此盲增面，并非证明增面一定更贵。全部原始数据、每轮范围和限制见本轮performance-review/validation-report；不跨机器/renderer外推。第二轮最后三case按明确retry2映射替代一次窗口后置条件失败，原33成功保留，原失败execution仍存；不是选取较快成绩。独立审核核验全部36case/2160raw/72GPU PNG及当前输入，完成后按逐路径SHA清单删旧captures的168张PNG约45.99MB，保留当前证据与唯一失败负例。
