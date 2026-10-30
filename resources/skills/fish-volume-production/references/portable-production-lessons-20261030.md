# 蓝鳃实鱼后的工具收敛

后续：鲫鱼原blocked两项已完成修复并通过当前九阶段SOP/完整门（用户外观待审），最新方法与失败边界见[材质与局部自动化](portable-material-lessons-20261030.md)。下文“第二条已实跑”保留上一轮停点，不是当前状态。

蓝鳃完成源固化/冷读、七鳍490/072、077闭体/GPU、头型正负例、动作、多视/水下/24秒录像及9阶段SOP。实际1980三角面、1671顶点、18骨、54原生通道、9逻辑分区、1mesh/1surface、2048×1024图集；满足2000硬上限，高于1500优选。**用户尚未整体接受，未替换正式蓝鳃。**状态读目标项目 `experiments/bluegill-portable-trial-20261030/{manifest.json,sop.validation.json,delivery/manifest.json,handoff.md}`。

## 可复用确定性工作

- `build_fish.py`/CLI新增显式非均匀body.ring_positions和fin.interior_grid，两端校验，旧默认不变。从独立原画轮廓控制笼建起，不先高模减面。先计完整装配并给有限接触留面额；本鱼3960/2024被拒，1870起步，局部修正后1980。
- `author_trial_pbr.py`显式新候选哑光PBR/nearest/身体OPAQUE/鳍MASK，mesh和骨同名时只改mesh名；不是旧35%自发光外观的等价迁移。骨/权重/动作不改。
- 跨宿主JSON明确UTF8。Windows默认GBK写而UTF8读会失败；中文部位名回归已加入。
- `portable/prepare_trial_spec.py`从实际GLB/packing取计数、完整TL缩放、唯一原生clip；调用者声明身体surfaces、全部鳍节点和精确骨名alias。Swim不能照抄旧Animation，实际骨没有_2就必须明确适配。它不推断解剖、根选区或颜色。
- `prepare_fin_validation.py`绑定同鱼source_t完整鳍基、新model/profile/实际分区和显式mesh重命名；`export_fin_poses.gd`沿用原177/490调度与物理核，只适配加载。diagnostic/envelope子集不得称完整门。
- `diagnose_fin_envelope.py`/`apply_fin_envelope.py`收齐失败点、边四分点/面探针，排除完整根、合并UV别名，测实际LBS外推增益；只移动失败所需非根源顶点，回写blend/GLB和签名法线。本鱼两胸约.197/.288mm是逐鱼数据，不是默认；根缝.5mm/自由面.02mm不放宽。
- `portable/logical_document.py`重新freeze manifest后作只读逻辑投影，进入既有头型/闭体核。`prepare_gate_adapters.py`以严格匹配生成加载适配，旧Nile冻结工具不改，原077/头型/动作断言保留。
- `run_delivery_checks.py`配置驱动实际导入→五组×96动作/切换→077闭体/GPU→头型/故意变窄负例→多视/七鳍隔离/288帧录像/水下→完整490→当前490内072登记。失败即停，保留日志，以短阶段JSON和manifest减少重复读报告。当前只支持明确一个身体+七鳍、既有核能处理的库存，不是任意物种自动验收器。

本鱼八阶段实际25.91秒（本机RTX5080、当前工具、4个物理分区），不含准备、修模、看图、生成、视频编码或SOP整理；不是从零总成本或其他鱼速度保证。没有测量就不报token节省百分比。

## 补皮反例必须前移

旧ShaderMaterial导出的source_texture仍带活动胸鳍。名称、alpha、保护区RGB和独立鳍存在，都不证明旧patch/chart/rest逻辑已烘入。首个clean-source/final-source-run命名误导，隐藏鳍后实际失败，不能作为推荐输入。旧UV shader补皮离线复现又出现纵向拉纹；`bake_existing_skin_patches.py`仅留作审计负例，不推荐生产使用。

最终采用完整连续生成身体供体，本鱼472特征内点配准、nearest映射、原头/眼/嘴/鳃与身体连接标记保护；独立鳍仍原图。生成内容标合成来源，不冒称原RGB或真实解剖。看完整二维纹样、隐藏全部鳍、侧/俯/腹和保护区接头后再冻结，避免整门通过后才发现残影。大块连续供体优于单行/小条平铺；补纹自然、吻型、展开、画风仍需看图与物种证据。

可进一步自动的前置检查是：列出完整shader分支、实际节点/clip/预算、自动出纯身体/七鳍检查包；不能硬编码“外观通过”。

## 下一鱼的调用顺序

1. 已接受源图/物种资料→材料与低面参数→先看局部、纯身体、整鱼和七鳍。
2. 稳定后prepare_spec→run_source→prepare_validation→prepare_fin_validation，源实际拥有静态形体/UV/权重/纹理，后续加载冷导出成品。
3. `run_delivery_checks.py --config <逐鱼配置> --output <新目录> --godot <本机工具> --blender <本机工具>`。蓝鳃delivery-config.json仅作字段例子，不复制形态值/根选区/外观结论。
4. 实际图审与逐鱼记录后运行volume sop-check --json；执行器不自动填写图审/SOP/用户接受。正式安装按该鱼授权处理。
5. 先归档失败、参数/输入、源/成品及唯一证据，再按绝对路径+SHA清理稠密样本、重复帧、备份。清理收据区分报告历史库存与实际保留子集。蓝鳃清理571.48MB/2772文件，核心归档约169.2MB，所有唯一源/GLB/报告保留。

下一条鱼用于检验工具复用，独立确定嘴裂、截面、鳍根/展开/间隙；不复制本鱼增益、通过结果或用户接受。

## 第二条鲫鱼已实跑：新增可复用边界

鲫鱼独立原画/22环×12控制笼、自己的083b横向艺术目标、7鳍根，得到1526tri/1327v/18bone/54channel/9parts。prepare_trial_spec无需改代码就解析原生Swim/骨名与TL，源保存/冷导出、实际导入和查看器smoke通过。现有volume replan已提供hash验证归档复用，先找现有能力，不为缺raw另造绕门。

新发现旧diagnostic把3.75秒写死，鲫鱼14秒周期只采Static；不能把“进程成功”称动态检查通过。`run_local_diagnostic.py`改用原调度内实际clip12/25、周期6/16和24/64，连Static共4姿态，并核对标签/时间；不改被冻结完整490 exporter。native分母猜成24的首版被断言拒绝；完整根核拒绝四姿态的覆盖守卫保留。当前脚本只作四姿态鳍膜局部诊断，不给072通过。

实际纯身体/嘴端近景提前发现残鳍与端面取色问题，故鲫鱼仍blocked/fix_input，不跑最终完整门、不装正式资产。完整实证与失败/下一步读游戏 `experiments/crucian-portable-trial-20261030/handoff.md`。该轮试验完成不等于第二条鱼正式完成。
