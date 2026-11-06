# 鱼类制作知识索引

2026-11-05已接受24条成品的历史保留与退休，先读[用户授权的成品保留规则](accepted-fish-retention-20261105.md)。当前源与成品、运行依赖、完整对照PDF和有用文字保留，旧实验图片/模型/密集重放数据退休；旧路径不再是可重放验收入口。

2026-11-05双髻鲨独立返修候选：[头颈、有限完整鳍根与尾柄截面经验](hammerhead-finite-cap-lessons-20261105.md)。方法可复用；大双髻鲨/无沟双髻鲨新候选未安装、未获用户接受，不能继承路氏成品状态。

正式游戏挂钩/口缘位置检查见[本鱼口缘recipe与导入权重身份](runtime-mouth-anchor-identity-20261105.md)：ready不等于真实上唇，不能用body-maxX回退；已实证UNORM16导入须比较同编码bin身份。

本文按当前任务找方法；不维护第二份鱼状态清单。先读 [生产 SOP 0—10 节](production-sop.md) 与 [真鲷跨鱼执行表](red-seabream-lowpoly-trial-lessons-20261101.md#跨鱼执行表开工先读)。SOP 后半的日期/编号段落保留历史经验，其完成措辞、旧参数和旧报告不自动适用于当前鱼。

## 当前规则与主线

| 判断 | 维护入口 | 使用边界 |
|---|---|---|
| 参数与方法的本地参考 | [本地鱼资料库](../../../fish-database/README.md)、[SOP 0.5](production-sop.md#05-本地鱼资料库与建模方法选择2026-11-02用户补充) | 可替代重复搜索，缺口再外查；不绑定参考模型建法，不继承形态接受 |
| 来源与 workflow | [工具箱](../../gamefactory-toolkit/SKILL.md)、[新源图排错](new-species-source-review.md)、[现存原画重新审阅入口](../../../../docs/FISH-VOLUME-WORKFLOW.md#existing-pixels-review) | 已接受源可复用；生成参考与风格参考独立核验，缺历史输入须如实记录并走当前审核，不能补造生成记录 |
| 来源用途与固定画布 | [部位质量守卫](component-quality-rules.md)、[侧面投影](side-projection-review.md) | 同开口/姿态/画布比较，不独立拟合局部掩盖误差 |
| 本鱼部位库存 | [物种清单与口内供体](species-inventory-and-oral-donor.md) | 不固定七鳍、八鳍或旧 surface/骨数 |
| 总面预算 | [展示体长及鲨鱼例外](display-length-budget.md) | 11月2日再次确认普通鱼继续按体长分档；真实整鱼最终装配，优选不是下限 |
| 三层回写和清理 | [共通知识收尾卡](../../../../docs/3D-ASSET-KNOWLEDGE.md#每轮修改后的知识收尾卡)、[拒绝与清理](command-rejection-recovery.md) | 通用方法/物种参数/本次证据分别保存；不重放历史删除名单 |

## 按部位选执行卡

| 问题 | 先读 | 需要时继续 |
|---|---|---|
| 头厚、体厚、俯视、头颈衔接 | [宽度依据与审阅](width-evidence-workflow.md) | [原结构横宽试验](transverse-width-trial.md)、[五鱼正式替换教训](five-fish-width-release-lessons-20261101.md) |
| 新建/返修嘴 | [嘴部执行卡](mouth-execution.md)、[嘴优先检查](mouth-first-review.md) | [完整颌部返修](mouth-repair.md)、[原生二维唇色接续](mouth-material-continuity.md) |
| 眼纹归属、浅凸眼、实际支持面 | [眼睛执行卡](eye-volume.md) | [源表面返修](source-surface-repair.md)、游戏 `docs/3d-fish/MOTION-AND-SURFACES.md` |
| 背腹、中央、下巴、补色或贴图滑动 | [部位供体卡](source-zone-review.md)、[源表面返修](source-surface-repair.md) | [材质方法](portable-material-lessons-20261030.md)、[嘴部接续](mouth-material-continuity.md) |
| 逐鱼材质替换、白模多视图生色与原UV重烘焙 | [多视图材质烘焙](whale-shark-multiview-color.md#现有成品逐鱼换材质保留原-uv-的制作方法) | 原画控画风/白模控投影，完整部位归属及真实生成边界；image-only隔离变量，正式替换仍回源冷导出 |
| 鳍原图边界、余边/白边/漏抠 | [原图整鳍分离](fin-source-shape.md)、[精确原像素切鳍](precise-native-fin-cutouts.md) | [鳍精修与有限根带](native-fin-detail-lessons-20261031.md) |
| 鳍型、组织厚度、尾柄/尾根 | [鳍型厚度与尾柄](fin-types-thickness-tail.md) | [有限鳍面接触返修](finite-fin-contact-repair.md)、[鳍壳静态与动态自交](fin-shell-self-intersection.md) |
| 体表根、自由鳍膜、运动控制与身体透明缺块 | [部位质量守卫](component-quality-rules.md) | 游戏 `VALIDATION.md`、`MOTION-AND-SURFACES.md`、`BODY-INTEGRITY.md`；原生/实际引擎均验 |

宽度先按同口径长度与最大横宽/峰位定整体，再核局部 W(t)/Wmax、解剖测位和连续轮廓，直接量冷 GLB 有限网格。2026-11-02 允许体型接近的同属/同科或已审模型作近缘厚度参考，指定样板优先；保存来源 SHA、对应与未知，不冒充同种生物实测。外部扫描可校核结构/测量，不能替代项目原画主体和鳍形后再强贴皮肤。缺资料不再机械要求一律生俯视图。

## 按构建与交付模式选入口

| 模式 | 入口 | 边界 |
|---|---|---|
| 原图控制笼低面新建 B | [控制笼方法](reference-cage-body.md)、[完整重建 SOP](reference-cage-rebuild-sop.md) | 真正按参考逐段塑形，不能拿旧身体减面冒充 B 新建 |
| 配置驱动作者/源/冷导出/实际部位 | [通用工具](portable-finalization-tools.md)、[生产工具经验](portable-production-lessons-20261030.md) | 先看 capabilities 与适配范围，不把工具单测等同整鱼完成 |
| 图集/单 surface 与源固化 | [单材质源固化](single-material-source-finalization.md)、[最终导出](final-asset-export.md)、[cutout水体预检](../../../../docs/FISH-VOLUME-WORKFLOW.md#cutout-water-preflight) | 静态几何/UV/权重/材质进源，保留有向三角/法线/蒙皮和部位身份；冻结前核真实alpha模式及水体合成 |
| 旧 Godot 静态装配的本地迁移 | [次级模型卡](static-merge-secondary-model.md)、SOP 0.2 | 只在用户限定本地迁移范围，不能套新鱼、主动修鳍或正式交付 |
| 完整验收、暂停、续做与正式接入 | [工作流完成门](production-workflow-gates.md)、[最终导出](final-asset-export.md) | `sop-check` 账本、专项、实际图审与用户接受不同；真实游戏入口及导入缓存冷读 |
| 性能盘点 | [实际装配性能审计](performance-audit.md) | 有测量问题才跑，加载/持续游动分开，不为静态材料改动默认重跑矩阵 |

## 物种实例与可迁移范围

以下是方法/负例定位。接受只从对应当前 manifest、handoff、validation 与用户反馈读取；下表不覆盖案例页内的候选演进。

| 实例 | 可复用判断；不继承的部分 |
|---|---|
| [真鲷](red-seabream-lowpoly-trial-lessons-20261101.md) | 二维去鳍底图、实际色相描边、头底非侧鳃、像素密度、头身灰模、缩眼与正式入口；尺寸/接受逐鱼 |
| [黑鲷](black-seabream-production-lessons-20261102.md) | 已定稿近缘样板厚度、左右同光照侧腹覆盖、近根自由面和正式替换；样板接受不转移 |
| [食人鱼](piranha-production-lessons-20261102.md) | 嘴先看源、鳍尖方向、封边 RGB/alpha、实际蒙皮与相机单位；技术全门不自动成为用户接受 |
| [鲤鱼](carp-lowpoly-trial-lessons-20261101.md) | 头底材质从失败补皮到限定生成供体、保留域和接头；局部外观认可不补足未知头型资料 |
| [鲨鱼主线](shark-production-lessons.md) | 项目原画同源、连续实体鳍/异尾、真实口弧和原生冷读；已撤销网上扫描投影驱动的 3986 面路线 |
| [黑鳍礁鲨返修](blacktip-review-lessons-20261101.md) | 有限截面、曲根拓扑分色、派生色声明与深度精度；早期 pending 按鲨鱼主线后续记录定位 |
| [双髻鲨同族](hammerhead-family.md) | 头翼形、物种差异、根带降维；同属不等于同尺寸、同头翼或已接受 |
| [海鲈](sea-bass-lessons-20261031.md)、[大西洋鲑](atlantic-salmon-lessons-20261031.md)、[褐鳟](brown-trout-lessons-20261031.md)、[红皇帝](red-emperor-lessons-20261031.md) | 逐种源线/供体/失败姿态与真实图审，不能从技术通过或案例标题继承状态 |
| [四鱼收敛](four-fish-lessons-20261031.md)、[嘴返修历史](mouth-repair-lessons-20261031.md) | 累积问题与已拒绝补法；新方法优先从部位执行卡进入 |

## 已被替代或必须限制使用的路线

| 旧说法/路线 | 当前处理 |
|---|---|
| 缺同种数据就必须生成俯视图，不能借别鱼 | 11 月 2 日补充允许近缘厚度参考，优先指定样板；保留证据等级和逐鱼审核 |
| 新普通鱼统一1500/2000覆盖旧体长档 | 11月2日用户确认普通鱼继续按体长分档；该旧覆盖条款退役；鲨鱼3000～4000起步，长体型继续升档，当前起步实现3500/4000 |
| 网上扫描投影直接作项目鱼主体/鳍形，再补皮肤迁就 | 鲨鱼主线已明确撤销该推广路线；外部模型只在批准的结构/测量角色使用 |
| 125 非双髻鲨尖突补嘴；一条横线或闭体当嘴完成 | 已撤回，读嘴执行卡；双髻鲨保留嘴线 UV 不代表整鱼接受 |
| R7 单列颜色沿唇弧复制当完整二维像素簇 | 被 R8 二维唇域方法替代；笔触尺度和实际接头逐鱼确认 |
| 鳍根单点/包围盒/保留旧版/177 通过就算全鳍完成 | 完整根与整片自由鳍面分别验，实际全部适用部件和当前候选；离散不保证连续安全 |
| 074 运行时 UV 补皮可作为新静态修正永久交付 | 该案例保留作历史，当前静态修正须回源/GLB并冷读，Godot 保留实时职责 |
| 任意旧报告批量换哈希，或清理后报告路径存在于文本就算可复验 | 原报告不改写；当前依赖重新审核，按归档映射恢复真实输入后验证 |

新增经验优先修订上述对应专题；只有出现新的稳定分支才增文档并接入此索引，避免每轮只在文件尾追加一条“已提交”。

- 2026-11-06 尾部透明封边/尾柄维护：`resources/volume-fish/tail-closure-repair-20261106.json` 与游戏 `plans/reviews/tail-repair-20261106/HANDOFF.md`。保留原鳍基解剖坐标、有限端盖、新增domain后代、严格未改部位继承、单鱼不可变验证输入与EXACT_UV授权域等方法；不恢复退休实验链。
