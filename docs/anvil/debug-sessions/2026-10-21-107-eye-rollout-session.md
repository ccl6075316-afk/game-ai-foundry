# 107 眼睛独立投影推广

## 入口与范围

- 时间：2026-10-21，Asia/Shanghai。
- 用户确认106黑鲷试修效果，要求推广到其他有问题模型看看。
- Normal mode：已有102逐鱼真实GPU47图、源图、105保留工程、106最终GPU/代码门与当前正式game，可复现。
- 范围：筛查21条当前安装鱼，另核真鲷预览、106黑鲷。只有确证重复眼纹/眼归属错误的鱼进入独立试修，不把一般头顶拉伸、原描边、鼻孔、物种斑点混作眼纹。不扩到全身材质或几何重塑。
- 使用fish-volume-production、anvil debug/code/review；实现委派source_ink_sampler_doer，独立审核material_repair_review。
- 保留106全部代码、参数、报告、失败原型与正式game。当前没有新增commit/push请求。

## Phase1 证据清单与初筛

读取根AGENTS、toolkit、workflow help、鱼类制作技能及105总结。当前Foundry/Fish有106未提交变更，不清理或覆盖。

已看102共22鱼头顶与侧头，临时联系图`/tmp/fish107-eyes-{0,1,2}.png`及`/tmp/fish107-top-audit.jpg`；原始图位于Fish实验`surface-mouth-audit-102/{installed,red-preview,black-preview}`。这些是历史观察，须绑定当前实际输入或重捕，不能当新验收。

初筛：黑鲷106已明确解决左右眼圈连接；梭鲈中央仍疑似有旧眼圈/清理供体残留。鲤鱼眼前深色特征要查源，不能先认定额外眼；多数其他鱼有头顶拉伸但并未见明确左右眼连接。真鲷104已证明一组黑梯条来自原头顶描边，不属于新眼层可直接消除的问题。银龙、双髻鲨已有独立眼结构，不能盲目替换。

既有head-source多数鱼已有source_eye_footprint × (1-source_eye_keep)清理，故“没有106”不意味着“尚未分眼”。旧眼清理、friendly缩放、口部/secondary_feature分支及fallback来源须逐鱼追踪。

下一步：只读实际GPU五视与当前绑定/网格/来源提取；独立Phase1审核后选择确证鱼种，再定Phase2/3。未实施任何107修复。

### 独立筛查与来源校对

material_repair_review实际查看22鱼及关键源图：黑鲷适用且106已处理；下一条只优先追梭鲈（上白眼圈与中央旧清理供体），不授权批量擦眼。鲤鱼眼前黑金小圈在原图本有，必须保护；真鲷是104确证描边；银龙为独立眼几何；两鲨未见连接；带鱼需要专门近景；其余14鱼本轮没有明确连眼证据。该意见先批准继续梭鲈追溯，未批准修色或整批验收。

当前正式Hall为21鱼，含大黄鱼，不含红/黑鲷；102为20正式鱼（缺黄）加红/黑预览，共22。107新捕获完整21正式鱼，预览另查，不能漏黄或把23个检查对象写成22。

head-source.eye.source_image_sha256与102提取PNG文件字节哈希不同，但13个可核物种的完整解码RGBA哈希均与记录一致，尺寸一致；差别来自内嵌PNG重编码，不能误报为源画已换。梭鲈082 context、validate均ok，源资产review.status=accepted，沿用已有接受来源，不重新生成或补造接受。

### 当前真实GPU与梭鲈来源反查

`current-audit/capture.validation.json`完成21鱼210图，后台GPU日志无ERROR/WARNING；所有实际材质uniform/原shader/来源配置/采样器RGBA已冻结，梭鲈另存原base+6LOD、骨绑定packed证据。主线程实际查看新三组侧/顶联系图，加入大黄鱼后没有新增同等级明确连眼名单。

梭鲈正式model SHA `c1b10d96c7aa83e41129df16170d7302f4c4335b226785c5f5b5bd562b6e0aef`；11672顶点、base22941面、六LOD分别11469/5733/2865/1431/715/439面。原shader旧眼清理启用，mouth_enabled=false，gap约[.004223706,.009503339]。

真实蒙皮/相机像素射线反查，`top-pixel-trace.validation.json`与标点图记录：GPU(620,350)→source(1856,345)，GPU(660,360)→(1879,351)，均为原眼上白圈，旧清理weight=0且CPU/GPU逐RGB零差。控制GPU(770,400)→source(1945,379)为普通吻端白皮，不能清除；GPU(600,400)旧cleanup约.915，灰暗色来自旧供体。9点CPU/GPUmax差≤2，6点零差。其余点的离散/量化误差保留，不声称全图精确重现。

追溯时发现直接把Hall世界骨矩阵加权会因本鱼weights和约.9999847放大平移误差；107临时export改为mesh-local矩阵加权后再一次mesh.global_transform。没有修改106或鳍验证器，也没有据此宣称旧检查无效。

源瞳孔threshold48连通分量中心(1864.0829,378.0989)，base实际预像restXY约(.42098957,-.003507365)，Z±.019362609。最粗LOD5的旧UV预像在负侧有两个而缺正侧，属风险证据，不能直接推导新restXY一定失败或授权删LOD。

## Phase2 最小提案（待独立裁决）

仅107梭鲈；106与正式game冻结。当前正式模型/材质为独立baseline，105只改donor的候选不能当原版。复制Closed_body0材质，绑定GLB/source/fallback/原shader+include/config/顶点顺序，保留全6LOD、数组、skin/骨骼、鳍/口内。

只在mode1/2把原眼cleanup项置0，后续secondary/mouth/rim原逻辑保留；mode0逐RGBA身份。独立RGB探针除source/opaque清理和新眼层，还须覆盖退役旧眼cleanup的真实空间weight，包含源mask外的原供体染色，不用after反推允许域。

新restXY眼层取未改source RGB×alpha×紧眼mask×侧别owner。旧清理mask和完整眼层mask分开；保持pupil X及经本模型校准的尺寸，gap/位移按左右/base+全部6LOD求解，不照搬黑鲷22像素或删除其最粗档。最粗LOD若无法支持，明确保留失败与局部试版边界，不能以本轮眼睛可看冒充整鱼验收。

7117像素手工大polygon全部source alpha255，可作为旧清理域proposal，完整圈入上白/黑/白rim，但仍有灰皮padding；紧眼层另提案，未冻结为new eye。供体native[1780,335,1808,360)实际已看为灰金像素、全不透明且不重叠眼，仍为本鱼工程推断。下一步独立Phase2/3审核后先mode0/2，再批准mode1。

## Phase3 数据和数值裁决

独立Phase1、Phase2分别APPROVED。紧眼层人工细描6039像素，完整上白/金/黑/外白rim，普通鼻白控制点在外；右外rim新增10像素须并入旧清理域，最终source/fallback均7127。独立数据域审查看过overlay与供体后批准进入CPU校准，未跳过视觉。

透明供体nearest延展复刻与实际fallback全RGBA一致；眼区来源扩展0，因此仅本鱼两个old cleaning mask可相同。实测完整pupil/gold各侧唯一、无缺失，其X/Y每源像素物理尺寸均约1/2024。旧fullrim每侧269中心/1147cell样点没有preimage，不把已映射子集bbox当完整原眼尺寸，也不能说新完整rim与旧可见rim一模一样。

使用本鱼原central/full阈值[.00422370582818985,.009503338113427162]，先中心、再独立眼mask所有去重角/边中/中心24505点；原base完整域下界6.22678→7px，base+LOD0..4共同10.86401554→11px。11px两侧样点均唯一、central/degenerate0。原LOD5正侧缺23901、负侧缺3527/重复3942、central7959，全部LOD共同无解。继续保留全六档，未退休、未重建。上述为离散点与三角裁剪诊断，不是全连续时间/实际GPU逐档选择证明。

独立Phase3最终批准11px仅mode0/2局部诊断实现，要求持续保留LOD5 failed gate。修正solver说明中的旧.0055文字为实际.009503338113427162并重跑冻结SHA。没有用无orange代替缺失几何的证据。

## Phase4 第一段：0/2实现与真实GPU

source_ink_sampler_doer新增107 helper/template/profile/freezer，106保持。原材质原眼项精确匹配一次，只在非0模式置0；secondary/mouth/rim原逻辑未泛删，未知路径拒绝。退役贡献在原head返回处独立探针；source/fallback清理与独立restXY眼层另有全路探针。源/材质/配置/实际uniform与顶点顺序严格绑定。

原版baseline从105单鱼审核fixture复制，但将head-source候选donor恢复为当前正式profile。实际模型及所有其他物种profile一致，差别仅单鱼Hall适配；105候选不能冒充原版。新增baseline fixture说明与47张原版GPU。

实际headless8组安装通过，mode1和非法取样反例拒绝；全部surface数组、Skin/骨骼及两身体surface的LOD数量[6,2]前后完全相同。随后真实GPU mode0标准47逐RGBA与独立原版相等；额外48近远/粗细压力mode0与显式baseline-reference逐RGBA相等，两个阶段日志clean。mode2近景两侧圆域完整、无红蓝中央连接，正常吻白在外。实际coarse far出现orange缺域与严重降档，保留为负例，不把这48图一概写成归属通过。

独立Phase4诊断视觉APPROVED，允许以同6039/7127、固定供体、XY1/2024、11px和原gap继续mode1 RGB局部试色。许可仅base..LOD4局部试版，LOD5持续阻断整鱼/正式安装；需最终三基色/退役独立探针、mode0重捕及实际颜色接缝复审。当前未有整鱼接受。

## Phase4 最终：颜色、回归和完成边界

早期0/2代码/配置/回执已归档phase02-freeze，最终0/1/2材料独立冻结。source与opaque分别按已审28×25供体作原生整数镜像RGB副本，各7127像素改变；全alpha及mask外全RGBA不变。独立眼层取原source金黑白RGB，保持原tint/COLOR/光照。原始source、GLB、全部数组及六＋二LOD未改。

最终14批实际GPU共639张图全部成功、日志无ERROR/WARNING。47标准off对独立正式原版RGBA零差，48额外off对新baseline-reference零差。三全路RGB探针独立并集外候选RGBA0变化、alpha0变化；三个retirement-only探针并集也全部包含在全路允许域。正常近景owner无fault；粗压力累计20777个orange像素作为失败保留，不能把final-owner报告当所有LOD通过。实际四次Swim→Turn→Ascend→Dive→Swim共24图核真实blend状态。

主线程实际查看最终侧/顶与标注板；独立material_repair_review查看侧/反侧/顶/前/斜视及真实切换，认可完整金黑白圈、中线断开、普通吻白保留、无明显灰金供体硬缝或眼层滑移。独立Phase4最终APPROVED仅局部试版；又实际headless重跑安装合同通过，但其启动有本机CA证书环境ERROR，未冒称该日志clean。

当前177姿态全部8鳍根通过，490姿态全部8鳍根/膜面通过，原0.5mm collar与0.02mm穿入容差未改。16同姿态身体视图缺失像素全部0。shared body checker只新增严格107分支/dispatcher，绑定当前code/template/model/profile/原shader/include/headprofile、实际7张纹理RGBA、mesh/LOD/rig与mode/projection，3个正例及22拒绝反例通过；未知shader仍拒、覆盖算法/容差/Python wrapper未改。106函数保持，旧负例回归通过，10616视图身体门另重新GPU通过并刷新证据SHA。

Python编译和两仓库diff空白检查通过；完整审查记录`.ai/anvil/reviews/2026-10-21-107-eye-rollout-review.md`，知识`docs/anvil/knowledge/2026-10-21-fish-eye-rollout.md`。Fish `eye-rollout-107/completion.validation.json`绑定最终证据；标注板`review/zander-eye-before-after.png`。原LOD5失败、吻端白环及一般皮肤拖纹、导出包未验证均保留。用户请求的筛查与另一问题鱼试修已完成，正式game未替换、未volume accept、未新增提交/推送。
