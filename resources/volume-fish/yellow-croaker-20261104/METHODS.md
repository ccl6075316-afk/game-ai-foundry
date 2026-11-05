> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# 大黄鱼60cm R48采用方法与完整参数入口

这是待用户整鱼审核候选，未安装、未提交。唯一可编辑终态为原trial/batch-repair-r48/fish.blend；仅源冷导终态为r48-cold/fish.glb。源/GLB完整哈希、入口及证据见同trial/manifest.json、HANDOFF.md、原lowpoly-r2.handoff-sop-review.json。构建方法和精确数值从本Foundry resources目录恢复，不依赖Godot静态建造。

- 来源：accepted PNG f58fc023...与style71606d33...实际图审，新existing_pixels receipt绑定source-style-review.png、原历史profile身份和哈希。旧generation-reference7c8b6ae1缺失不继承。正规CLI reviewed-source-plan；历史082h完整字节SHA dcbca01b...不改。未伪造Brief/生成任务/旧模型接受。
- 新控制笼以原画像素注解独立构建，不自动减旧82804面源、不抄库OBJ。整体2000三角：body含口1048、全7鳍880、双眼72；1500优选未达，2000硬限满足，未凑面。完整profile为complete-roots-width-r39.profile.json。
- 嘴：R7完整上下颌/真实切口/口内，源真实末端独立（上2002、下2010）和7射线，最大opening误差.125px；3px重建推断明确。原8px外唇+4pxfade、口内return.75/.75px，R46原唇保护37214texels内front/central权0。body不改shape取色。
- 二维：先clean_body_source.py移除活动胸鳍下方完整旧鳍画纹，保原RGBA边界与true root。private author_front_mouth_chart.py完整最小diff见final-material-author.patch和provenance。限定已接受不规则辅助图只用于额头/下颏，projectionspan.16匹配原6–8px簇。R46 safe native bodyfield从明确本鱼组织取色，1746601 roofsamples、density.740307..1，334539侧保护变化0，108008眼足迹核变化0。争议282线前伸tail组织不作为色彩供体/解剖判定。
- 眼：实际旧eye150终态GLB量得60cm凸高2.608mm，旧接受仅浅眼效果。每眼12sector×2ring=25verts36tri、完整原眼圈、body00/01/02真实支持；全局加宽后以自身body足迹法线重锚。body错误重复眼UV外域57419texels修正，真实cap全POS/NORMAL/UV/tri/权/RGBA未变。正面狭长金黑条由同机eye-only/body-only完整归属证明为真实cap侧投影。
- 横宽：3条Larimichthys_crocea标本W/SL中位.1341168697，bodyY×1.2785876473573983条件比例归一。SL246.02/273.12/263.05mm→60cm展示不冒充成体实测/异速生长。Mouth_width测下颌关节距，不当吻宽。head-envelope-r48.plan.json保原artist局部曲线，当前083实核及源/正俯斜灰模通过；定性Sinica同种吻型不矛盾，局部实测曲线未知。2011KAUM-I16977经2015修订为terengganui已撤同种引用。无须依FAO属级key而非空字段。
- 全鳍：complete-roots-r24.profile冻结完整原始baselines/rootbands；R39仅尾构建支撑角重布，原自由轮廓丢失0px²、原baseline16/17和rootband不缩。所有root种子必须used并有非零有限三角面积；export_complete_fin_poses.gd从实际GLTF/同名全surface库存逐点映射到Godot。本鱼各鳍单surface，无覆盖遗漏。
- R35原body面内支撑重三角避免近共线薄片；R36背鳍仅6cap三角对角重排；R31真实root charts消除腹根9.84mm折层（已灰模原源对照），R32背鳍长边支撑，R39尾12真实rootwall三角接7body截站，R41尾中层重布4预算三角，误差.08mm；完整参数在各具名config/proposal/plan。未挪自由域规避碰撞。
- 实厚：progressive-fin-foils-r40/r42.config分别从原报告恢复，避免旧hardcoded名字覆盖。prox/mid/rim毫米 D .70/.32/.075，A .62/.28/.070，C .95/.42/.095，P .82/.36/.075，Pv最终1.30/.20/.035；median原rootfoil.36mm，tail真截面。R48只将左胸outer basal自身body法向gap设.25mm、左右腹.23mm，inner/自由面/全域/UV/skin不变；R47 .20mm腹根ratio1.35不足为负例。全7实际normalray比最小1.545，prox>mid>dist，不以边沿单点冒充厚度。
- 本鱼最终冻结门：root外浮.5mm（本鱼更严值）、内埋.5mm；rootcollar.5mm、freeface穿入.02mm。不是公共一律±.5。公共helper按mm/10传cm.05/.05，旧无字段默认不变，不改距离核/采样/动作。
- 终验：R46单次完整490+body077/20s视频/水下批审发现3根外浮失败后合修。R48仅3鳍实际490 membrane/self重检，公共root完整490过，actual all490 body及其余4鳍膜/root数据逐字完全相等，旧4鳍self/membrane限定保留。body/嘴/眼/全部材质RGBA/nativeclip/rig全stream精确一致，旧R46实际077/水下/20s只按未变scope结转，未改旧报告冒充新GPU。self采用float64 AABB+双向段/正面积共面，合法共享顶点/边排除，6controls true。072复用当前490，不虚造177。
- 角色：all7 fin MASK/.5、body/eye OPAQUE、nearest；实际Godot SCISSOR2/0；实际游戏water DEFAULT开关同姿态4动作图审，黄/绿蓝染色正常、无黑背景缺口。正常实时动作保留；源GLB无静态运行时补丁。

冷导出（Foundry根，输出新空本鱼实验目录）：
`.venv/Scripts/python.exe`用于CLI；`E:/blender/blender.exe --background --factory-startup --python resources/scripts/volume-fish/yellow-croaker-20261104/export_cold.py -- --blend <savedR48fish.blend> --config resources/volume-fish/yellow-croaker-20261104/frozen-export-r48.config.json --output <fresh-empty-own-output>`。
只读源，无target模型复制。完整源/GLB/current actualmapping/物理报告及SOP-check必须一起看；技术清单不产生用户接受。当前不再运行中间完整组合；后续改动只验修项及实际影响域。
