> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# 非洲鲶鱼 90 cm：隔离候选作者入口

唯一当前入口是 `resources/volume-fish/african-catfish-candidate-20261105.json`。该索引绑定完整可编辑低面源、普通 GLB、原画/profile/动作、作者资源及上游 SHA。它是审核候选，不是安装清单。恢复入口 `restore_frozen_source.py --output <本鱼实验目录内的新目录>` 已实际恢复源并冷导，GLB 字节 SHA 与冻结候选相同；不是从退休实验路径重跑整轮的承诺。最终 `.blend` 拥有全部静态几何、UV、packed images、原 emission、MASK、权重、18 骨和原生循环；Godot 仅直接读 GLB 并执行动作/环境。

## 来源及独立参数

目标为 Clarias gariepinus，90 cm 沿原游戏展示长度。FAO/SANBI 支持四对须、扁宽头、长低背/臀鳍和圆尾的部位盘点。库 AfricanSharptoothCatfish OBJ SHA5020ab59…与 NorthAfricanCatfish SHAa8f4fca5…实际检查四视，前者作更接近本原画的艺术体宽参考；俗名不证明同种/年龄/姿态。FishShapes12.8–19.3 cm幼体记录没有冒充90 cm成体标准。裸身体有限切面排须/鳍/眼支路，吻—尾基轴归一；连续 W(s)/Wmax 及实际低控制笼误差见原 `width-target.validation.json` 与 `root-section-r1/continuous-width.validation.json`。本鱼主轴、峰位和全部数值不沿用鲯鳅。

profile 为 `african-catfish-library-complete-fins-20261104.profile.json`。19原控制环/12径向起步，后做独立低面预算重布；不是旧33188tri模型减面。口角U=.946到前部.983真实开口；原上下颌连续体，8段切体、0 bevel，口角gap依次.0002/.0005/.0016/.003。旧吻端面支撑范围.015、退深.003，向原最大前端内重建浅曲面，不加前突尖嘴。12个独立作者圆滑后083横宽站通过，旧尖头负例失败。

## 完整部位与最终预算

完整2000tri：BODY含口腔836、七鳍940、八闭须160、双浅眼64；18mesh/20surface/18bones，优选1500未达到，硬上限2000满足。七鳍是背/臀/尾/双胸/双腹；八须是独立活体辅助部件，不能改称鳍或装饰眼。每须12源控制/20tri，GLTF因法线拆为40render vertices，实权刚性body00、原画四条曲线供色的双侧八根全部保留；随头部动作，无另造独立须动作。双眼各23源点/32tri/12真实开边，body00/01混合，不是闭球；原150接受浅眼高度及原纹理足迹保持。

鳍原完整SOURCE基线/6px域、RGBA和轮廓都保留。尾根9点曲线与实际BODY有限X(Z)帽共同截面，x303及其前支持/UV/权重冻结证明在原报告。背/臀同U根—带真实有限分片；双胸/背/臀各自actual490扫法向约束解源层厚度方向，不改骨/幅度。最终仅臀根—自由四边形两侧长对角线改短对角线，4三角拓扑重连，位置/原UV/权重/外轮廓无变。采用LP参数/向量、失败耳片/根弦负例、独立统计都在原集中报告；公共脚本未被本鱼修改。

## 材质与眼的关键修正

原生像素/nearest/原emission保留。鳍源Alpha使用 Math GREATER_THAN(.5)+`foundry_export_contract_json`，普通新进程导出产生MASK（缺省alphaCutoff=.5）；没有运行时alpha补丁或强制合材质。三BODY供体全alpha255。源图绘制眼、鳃、口缘为保护域；完整上9/下12px唇运输含5px过渡，56896受保护chart texel中front/central权重均0。

旧 native_tile 单列条码与随后 Y/W(u)扇剪分开记录。当前从 `material-source-r2/fish.blend` 真实语义UV重烘，中央生成皮肤 X 固定物理Y span=.179922415611（本鱼头Wmax），Z仍走本鱼真实窗/原ROI；只把419105新旧chart RGB差移入当前图，待改旧RGB逐值差0，其余RGBA与全部alpha精确保留。不是对已烘焙atlas UV二次烘。原生背/腹供体有二维donor坐标；辅助生成只有有限中央皮肤，不代替嘴/眼/鳃形态。M01旧反例、作者最小适配、正面图和供体SHA均可查。

新浅眼按实际BODY三角边共分片；BODY在眼下新增同X有限支持行8控制/+16tri，原顶点/权重不变。旧BODY077因此明确失效；新BODY077独立16视缺像素0、透明负例22137。原150实际1674像素并集覆盖；490×双眼每姿态518/518金虹膜及388/388瞳孔前盖可见，最小正深+.179780/+.753513mm；少量外围皮肤/暗边仍有至.045694mm BODY前景，未宣称整个1674前盖可见。

## 门、测位和结转

原标准完整490首次暴露臀4姿态，旧wholecompletion保持false。新臀完整490 self/root/membrane与实厚实际检查通过；其余6鳍与BODY/辅助部件/材质/骨架/原生通道/运行时精确未变，通过 `validate_retained_domains.py` 逐域结转。七鳍全部完整根的有向有限三角多重集、位置、四权重与原选区/限值精确相同；当前BODY+六鳍逐490重建对旧实际导出最大差6.18912e-8m。不能只换旧model SHA或把旧失败wholecompletion改true。

全七鳍完整壳自交使用实际490、全surface库存断言、double AABB、双向有限段与共面正面积；仅实际共享边/点边界合法，root/alpha不豁免。7853点/层的背完整解析6px根域×2×490另外通过，含近似rung条带差域。八须全根帽490每姿态与BODY相交，最大外距.469340mm。离散采样不等于全连续时域。

尾“实际接合平面”测原独立真实closing-cap：同X/Z宽差.052259mm，原.4mm阈值；pole真实共同高度差.031640mm、0缺截面。整6px斜向root/free膜的同X包络.678743mm是另测位诊断，不能写成小于.4；其完整接触/膜/self/渐薄另过。灰模可见低面facet转折/阴影，无明确背景缝或孤立额外鼓包，不声称完全圆滑。端视整个BODY投影不能反推cap宽。

实际Godot只有base mesh（所有surface额外LOD数量0），近/正常/远六视、原生循环、四动作/真实切换、24帧轨道和实际清/浑水均捕获并实看。新进程普通源冷导及资源恢复入口均字节同GLB，实验静态builder不加载。原SOP已逐文件语义核对当前规则并保完整old snapshot；机械sop-check不替代以上实际图审/数值或用户整鱼接受。

## 清理和重放限制

`anal-diagonal-r1/final-cleanup.validation.json`逐文件列出实际删除字节/SHA和退休原因。密集490 JSON、旧冗余模型/截图/虚拟求解缓存在结论/代表反例/恢复参数保存后清理；原实际矩阵、原完整数值、最终源与当前GLB、真正语义输入、旧M01/眼/尾/根弦最小反例及注册077证据保留。退休路径不是仍可直接读取的输入；完整旧dense重放须用保留旧模型/原计划/冻结exporter重新导出。没有新建大压缩包，不改安装资产/共享入口，不commit/push。
