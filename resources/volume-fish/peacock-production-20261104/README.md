> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# 孔雀鲈当前生产参数与恢复入口

**最终冻结升级为r6（2026-11-05）**，不是下文眼部修正r5。仍1842tri；GLB `48ebacb1a051170a6ae3f1bc1dd73c87aa847f2b3b0ffaaf2345e939d2331d00`。`right-root-wall-r6.parameters.json` 给出本鱼唯一后续修复：16右胸根壁面重连成沿完整既有根链的16短段，所有顶点/UV/权重/原根域/动作不动。旧r5虽全部身体/根/厚度门通过，动态有限封边仍穿入内cap；因此已撤销其完整候选地位。

当前全部8鳍×490实际姿态、完整正反面/封边已由double-AABB+有限平面/线段+共面面积核通过，原真实负例仍拒绝，合法点/边缝不误判；不以法线厚度或身体间隙代替自交。报告与7控制例在实验 `fin-self-audit-r6-20261104`，SOP当前55证据/21角色九阶段通过，最终入口 `candidate-r6/catalog.json`。只读核 `check_paired_fin_self_intersection.py` 与参数化例 `-- candidate-r6 fin-self-audit-r6-20261104`；采用实际矩阵从公共 `portable/export_fin_skin_matrices.gd` 以 `full-fin peacock_bass --membranes` 导出，按同名完整surface库存核对（本鱼每鳍恰1surface）。可再生的密集数据已按精确清单清理，完整结论/样本/失败证据保留。

执行策略：先完整盘点当前候选所有问题并集中修，改后只复验问题及实际影响项；清零冻结后才统一完整验收。本轮r6既定门已实跑完成，纯参数说明、文件清理不重复总验。公共方法见 `references/fin-shell-self-intersection.md`。

**最新眼库存修正：最终为r5、1842tri。** r4仅保眼纹、未保旧浅眼体积，旧SOP该项结论已撤回。本轮私有 `restore_integrated_eye_volume.py` 以12扇区、.55/1两环和原三角边约束，向闭合身体嵌入浅凸眼，不增重复层/开洞；74点/148面，全部当前门另行重验。`integrated-eye-parameters.json` 保存当前原眼位、旧足迹/高度、完整来源SHA、支持面、预算及自身配置。实际有限面法向凸高约1.639mm、边界回到原支持；与旧实际1.591mm相近。原完整眼圈RGBA/UV保留。旧177/flat-r4/restored-r5真实同机位图、旧接受范围和误判纠正详见原HANDOFF新增眼部节。

本目录是 2026-11-04 本鱼采用方法的 Foundry 入口；不代表用户已接受整鱼。最终候选与完整证据在 `projects/fishing-2d/experiments/four-fish-current-standard-20261101/peacock_bass/candidate-r5`，逐鱼账本仍为上级 `sop-review.json`。

## 实际资产与来源

当前 `fish.blend` 是可独立编辑的普通 Blender 源，`fish.glb` 可直接加载，均有完整身体、真实口内、18 骨、8 个逻辑鳍，整鱼 1842 三角面，展示 50 cm，优选 1500 / 硬限 2000。资产与方法输入 SHA 见 `production-parameters.json` 和最终 SOP 快照。

原画为1817×805孔雀鲈已接受侧图；它决定原侧轮廓、鳍、头、眼和唇的来源权。`body-clean-native-size.png` 是同画布的派生材质输入：只采用本鱼单独工作流得到的干净身体条带与喉底供体，头部 x>0.74W 的 RGBA 字节完全保持，74442 个完整原唇域 texel 不混入辅助供体。SOP 的 `source_image` 指实际作者材质输入；`original_source_image` 保存原画来源权和原接受链。两者不可交换，不把派生供体或本候选升级为用户接受。

本地 OrinocoPeacockBass 是身份未实证的同属 Cichla 游戏艺术参考，按身体鼻端—尾柄轴归一化、剔除分离眼球；FishShapes 同种6记录/5个体只提供全身宽度参照，嘴宽为颌关节宽而非唇开口。头部包络见 `head-envelope.json`，容差为工程假设，不是目标物种局部生物测量。没有按单个俯视观感强行加宽头。

## 实际采用顺序

所有物种私有脚本在 `resources/scripts/volume-fish/peacock-20261104/`，公共数值内核在其上级目录。`production-parameters.json` 固定主方法、采用配置与公共依赖 SHA；上级实验 `method-preservation.validation.json` 逐脚本证明移入 resources 时仅改 ROOT/BASE 路径前缀，算法、阈值和实际输入相同。

1. 从已归档且 SHA 核对的本鱼源和 mouth-r1 开放口候选恢复，`resume_native_lip.py` 使用斜率 .25 的保守曲线包络保留22px上唇、30px下唇、6px羽化域，解决尖锐取色曲线越界，先通过全域二维预检。
2. 公共 `author_front_mouth_chart.py` 按采用的 r5 / body-material-r1 配置处理完整原生唇、头顶供体、干净喉底；`restore_articulated_jaw.py` 恢复原 jaw_lower 枢轴、117 个下颌权重点和原18°功能。没有独立唇层。
3. `prepare_paired_clearance.py` / `clear_paired_local.py` 只处理明确配对自由鳍面，随后 `conform_paired_root_caps.py` 将全部根区映射真实有限身体及当地身体权重。公共 `repair_source_fin_volume.py` 使用本目录 **fin-volume-repair-r2.config.json**，中位根表偏移 +.05mm；不要把 prepare_fin_volume.py 生成的首轮 r1 默认值冒充采用值。根带/原轮廓始终不变，尾鳍完整基部与身体截面匹配。
4. `prepare_clean_body_skin.py` 将本鱼辅助图按明确身体条纹/轴测位注册，修复胸鳍旧影；`prepare_body_rebake.py` 与 `graft_body_material.py` 将采用的作者 UV/材质嫁接回完整鳍与活动下颌源，保持身体物理数组。
5. `prepare_skin_fit.py` / `fit_peacock_proximal_skin.py` 复用通用实际490姿态 minimax 权重内核，先以17个完整实际姿态证明紧凑矩阵重建相等，再用本鱼显式8鳍域拟合165个近根点。脚本历史内核名称含 shark 不代表继承鲨鱼解剖或接受。
6. `refine_failed_root_edges.py` 对本鱼右胸、左右腹的失败有限根边各细分两层，共6新点/12三角面；新点投向实际身体并采用当地权重。软背鳍单独按实证上移 .08mm，未统一推移全部鳍。原根点通过不能证明根边中段通过，这是本轮采用修复的原因。
7. **finalize_cutout_material.py** 在六个共享鳍材质的普通源节点中插入 TextureAlpha → GREATER_THAN(.5) → Principled Alpha，保存 `foundry_export_contract_json`。原 PNG/UV/蒙皮/物理数组完全不变；普通 Blender glTF 导出自动产生 MASK，glTF 省略的默认 alphaCutoff=.5。此步骤修正 BLEND 材质在实际水体屏幕采样中的漏鳍/背景洞；不是运行时补丁。详见公共方法 `docs/FISH-VOLUME-WORKFLOW.md#cutout-water-preflight`。
8. 公共 `cold_export_ordinary_fish.py` 在新 Blender 进程直接导出普通源，确认113数组误差0、像素/节点/蒙皮/动作/材质绑定精确相等，并显式 nearest 采样。最终 r4 的源与 GLB 可脱离前述实验构建链独立加载。

恢复历史输入前先看实验 `cleanup.validation.json`。完全相同的 blend/GLB 已按 SHA 去重，`exact_alias_recovery` 给出原路径到保留副本的恢复映射；中间 GLB 可由保留普通 blend 及 nearest 政策重导。密集姿态/矩阵可由冻结计划与实际控制器重建；完整报告、每姿态结论、少量真实采样与采用权重仍保留。不要直接重跑会拒绝覆盖的生产入口；在本鱼隔离工作副本按配置新建输出。

## 正常运行及复核

`resources/runtime/godot/peacock-final-20261104/PeacockMotion.gd` 只实现正常动作，继承现有 `FoundryFishMotion.gd`，独占一个原 `FoundryJawMotion.gd` 实例。profile 采用本目录 `motion.json`。原 jaw_lower Blender 枢轴为 (.4166207314,0,-.0811777413)，上限18°，默认量1，`set_jaw_amount(0..1)` 保留开合功能；每次 step/seek 重施加。正式 VolumeFishExhibit 接入本包装时不能再添加独立 jaw configure/apply 链，以免将18°当rest后再次叠加。

最终 `candidate-r5/catalog.json` 是紧凑完整列表条目，绑定真实 spec、9mesh/10surface GLB、私有正常动作包装、profile、公共父控制器及 jaw helper 的 SHA。父任务负责集中查看器及公共入口集成；本任务未替换已安装鱼。

本鱼最终已实跑：完整490姿态鳍根/整面、072同当前490精确复用、077完整不透明供体/同姿态GPU/零alpha负例、原生循环/四动作/切换/独立控制5×96、12组0/9/18°颌与24切换、头包络/尖头负例、口开口/旧横缝负例、实际法向厚度/完整尾基截面/等厚负例、冷导出和真实列表交互。最终 SOP 九阶段54条证据通过。离散时间/有限表面采样不证明所有连续时刻无碰撞。整鱼外观仍待用户接受。
