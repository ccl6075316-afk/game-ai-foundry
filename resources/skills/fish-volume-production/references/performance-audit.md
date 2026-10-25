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
