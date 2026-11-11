# 3D 鱼、水草与布景：知识维护入口

**2026-11-08 静态成品与动作分开接受**：用户明确接受当前大西洋旗鱼 R4、鲸鲨 R8 材质模型以及罗非鱼 C，并要求本地成品改动提交推送、清理实验；游动不满意不否定静态模型。当前共 28 条静态基线，入口 `resources/volume-fish/static-fish-release-20261108.json`、`resources/volume-fish/accepted-fish-inventory-20261108.json`，游戏交接 `plans/reviews/static-fish-release-20261108/HANDOFF.md`。旗鱼/鲸鲨正式源和 GLB 已安装、冷导逐字节相同；当前三鱼正式/缓存/挂钩 91 项通过，旗鱼当前 490/072 通过。鲸鲨完整动作专项及完整生产 SOP 未伪称通过，动作质量另做。只确认这三条已采用本轮新风格；其余 25 条授权材质重烘焙，保持静态几何/UV/骨权，不能把“28 条模型接受”写成“28 条新材质完成”。B/C 清爽像素风格样板、当前源/模型、必要原图、共享资料库和 PDF 保留；旧实验图片/模型/日志退休，不恢复旧实验链。

2026-11-06 双髻鲨 R42 已获用户整鱼成品接受并静态冻结：[正式入口](../resources/volume-fish/final-hammer-pair-20261106.json)。大双髻鲨4524面、无沟双髻鲨3970面，完整8鳍/18骨，正式首读、缓存及垂钓入口直接读取源固化GLB；当前维护看游戏 `plans/reviews/hammer-pair-release-20261106/HANDOFF.md`。尾根端盖法线、共享二维供体接缝方法与逐鱼限制已回写，不恢复旧实验链。

2026-11-05：新11鱼获用户成品接受，共24条成品；安装与参数入口为[十一鱼正式入口](../resources/volume-fish/final-eleven-fish-20261105.json)。用户要求相关旧实验图/模型/密集重放数据退休，仅保留重要文字；[成品保留规则](../resources/skills/fish-volume-production/references/accepted-fish-retention-20261105.md)覆盖旧历史图片保留要求。[完整29页对照PDF](reviews/fish-reference-comparison-20261105.pdf)作为明确要求的交付保留，逐鱼参照角色、差异与未知见[对照文字记录](reviews/fish-reference-comparison-20261105/README.md)。历史删除不代表重新验收，也不修改当前24条成品静态字节。

2026-11-04：路氏双髻鲨已获整鱼成品接受，3994三角面、18骨、完整8鳍；静态形体/UV/像素/蒙皮/骨架冻结，默认后续只改动作。正式参数 [scalloped-hammerhead-final-20261104.json](../resources/volume-fish/scalloped-hammerhead-final-20261104.json)，原逐鱼账本已迁入游戏 `plans/reviews/scalloped-hammerhead-release-20261104/HANDOFF.md`；正式GLB和普通blend可独立冷读，旧两轮实验退役，不能从旧候选继续制作。

2026-11-04：虹鳟、褐鳟、大西洋鲑、海鲈、红皇帝鱼已获整鱼成品接受，静态冻结、默认只改动作。索引为 [五鱼正式入口](../resources/volume-fish/final-five-fish-20261104.json)，游戏交接为 `projects/fishing-2d/plans/reviews/five-fish-release-20261104/HANDOFF.md`。当前源和正式GLB、逐鱼证据迁移表与清理字节均在该交接中；旧实验路径仅作历史来源，不再是运行入口。

2026-11-02 梳理。本文负责导航、规则归属和每轮知识收尾；不保存第二套资产状态。模型是否可交付，仍读当前 manifest、progress、handoff、assets-manifest 和 validation report。

2026-11-03 罗非鱼已由用户整鱼接受并装入正式入口。当前交接为游戏 `plans/reviews/nile-tilapia-release-20261103/HANDOFF.md`，参数为 `resources/volume-fish/nile-tilapia-final-20261103.json`；默认后续只改动作，静态形体/材质/蒙皮/骨架冻结。独立交互入口为 `resources/scripts/volume-fish/open_nile_final.py`。历史实验已精简，不能从旧轮次的“当前/待审”恢复制作。

## 按任务进入

| 任务 | Skill | 执行 SOP | 参数与知识 |
|---|---|---|---|
| 3D 鱼新建、重建、返修、逐鱼推广 | [fish-volume-production](../resources/skills/fish-volume-production/SKILL.md) | [鱼类生产 SOP，0—10 节](../resources/skills/fish-volume-production/references/production-sop.md) | [按问题检索](../resources/skills/fish-volume-production/references/knowledge-index.md)；[游戏解剖知识库](../projects/fishing-2d/docs/3d-fish/README.md)；`resources/volume-fish/` |
| 3D 水草、石木、人工摆件、底床 | [aquascape-production](../resources/skills/aquascape-production/SKILL.md) | [造景生产 SOP](../resources/skills/aquascape-production/references/production-sop.md) | `resources/aquascape/`；[当前目录与 V2—V11 经验](../projects/fishing-2d/docs/AQUASCAPE-CATALOG-V5.md) |
| 原画生成、复用与作业恢复 | [gamefactory-toolkit](../resources/skills/gamefactory-toolkit/SKILL.md) | `context → validate → init → run → status → resume`，业务命令加 `--json` | [CLI 与状态合同](AI-HANDOFF.md)；`--help` 只读核对真实参数 |

本仓库是外部 Agent 的 CLI 工具箱，不要求特定桌面客户端。仓库 skill 是维护源；本机安装位置只作链接或同步副本。缺本机安装不妨碍从本仓库入口读取，不得假称已经安装。

## 每类资料只负责一件事

| 层 | 放什么 | 不放什么 |
|---|---|---|
| `SKILL.md` | 触发范围、必读 SOP、按问题选参考、关键完成条件 | 长篇实验流水、复制一整套物种数值 |
| SOP | 材料→制作→验证→源固化→实际入口→知识与产物收尾 | 把历史候选的新编号当推荐顺序 |
| 专题知识 | 条件、方法、依赖、负例、替代关系和验证能力边界 | 脱离输入 SHA 的“全部通过” |
| 物种/物件配置 | 本对象的来源、测位/布局、供体、根区、动作与预算分类 | 把另一个对象的尺寸或接受结论转成默认值 |
| handoff / validation | 本次实际输入输出、SHA、图审、通过/失败/待查、用户接受范围、复现及清理 | 另建与原账本不同步的状态表 |

## 现在采用的口径

**鱼类资料复用**：后续建模先查[本地鱼资料库](../resources/fish-database/README.md)，可用已取得且可复核的资料替代重复联网搜索，为参数与方法选择提供稳定参考；缺口或冲突再外查。执行细则见[鱼SOP第0.5节](../resources/skills/fish-volume-production/references/production-sop.md#05-本地鱼资料库与建模方法选择2026-11-02用户补充)。建模路线按当前原画、目标和预算独立选择，不要求复制库内对应模型的拓扑、UV或骨架；来源类型、逐鱼审核及验收继续分别记录。

**2026-11-11远程扫描资料索引**：[鱼类与水生动物3D来源表](../resources/fish-database/catalogs/aquatic-3d-sources-20261111/README.md)登记5个平台的主页/数据库/API、资料类型与证据级别、规模口径、龟/章鱼/鱿鱼等覆盖和商用/独立建模条件，并提供3,223条可离线检索的公开目录元数据。只是来源发现，没有批量下载或验证新模型；水母未找到的范围、未知物种及许可限制继续保留。

**鱼**：先基础检查、再嘴、再全部鳍、最后其余。嘴须有真实开口、下唇线、上下颌体积及左右/跨口缘补色；鳍根和完整自由鳍面分别检查；身体除正常口腔外不允许透明缺块。局部先审稳定再冻结，完整门、源固化、冷读和实际入口不能由提交或操作者审核代替。

预算已由用户在2026-11-02再次明确：[普通鱼继续按展示体长分档，鲨鱼保留例外](../resources/skills/fish-volume-production/references/display-length-budget.md)，与 `cli/fish_budget.py` 一致。旧“新鱼统一1500/2000覆盖体长档”条款退役；造景JSON的fish行只对应普通≤120cm档，不能覆盖更长普通鱼或鲨鱼。鲨鱼最低起步范围为3000～4000（当前实现3500/4000），>300cm使用5500/6000，>600cm使用7500/8000，体长更长继续增加，4000不是全鲨鱼统一封顶。已有合格低面资产不凑数增面，本轮不改预算算法或任何资产。厚度不足可按 11 月 2 日用户补充采用近缘资料/已审模型，指定定稿样板优先，标明物种、实际来源 SHA、部位对应、归一化和未知，不冒充同种实测或继承接受。项目原画约束主体和鳍形，外部模型用于结构/测量校核，不能直接挪扫描轮廓再强贴项目皮肤。

**草**：艺术输入为“一簇自然生长的某种水草”，按叶形、叶宽、颜色及生长方式区分；不强制叶片数、统一角数组或特殊翘叶。整簇来源决定布局，单叶图只提供部件；静态修改落在 GLB 和构建方法。骨骼与 shader 是不同运行分支，固定根、循环、真实叶片运动、暂停/恢复分别验证。

**景**：按[完整实例预算](../resources/aquascape/geometry-budgets.json)统计全部两面/封边/附层；洞口、内壁、底面与连续枝根须保留。历史高模须经优化部署和预算阻断；V11 从预算内直接构建，经同一验证器阻断后部署。三向原画是有相机/对应限制的艺术参考，不能称扫描级重建。

## 本次盘点发现与处理

| 发现 | 本轮处理 |
|---|---|
| 鱼 skill 同时承担路由、16 条长部位守卫和历史进展 | 缩短入口；完整守卫移到专题，全部旧参考由知识索引可达，不删除负例 |
| 鱼 SOP 旧“缺同种必须生俯视”与近缘补充冲突 | 在当前执行段替换绝对限制，明确近缘/生成图均不算生物实测 |
| 新普通鱼1500/2000旧覆盖条款与体长分档实现冲突 | 已询问并获用户明确：普通鱼继续按体长分档、鲨鱼保留例外；各入口同步，算法和资产不变 |
| 水草/布景无统一 skill，经验分布在 V2—V11 | 新建造景 skill 和 SOP，按草、石木、洞口摆件、底床和运行分支路由 |
| V5 总览开头只提 V10/V9，实际已追加 V11 | 总览前置当前组合与权威报告入口，历史章节保留 |
| V9 的 MultiMesh 一度不动，旧性能数字易误用 | SOP 保留实际叶片像素、白色实例 COLOR、暂停/恢复负例；不引用旧结果证明当前动画性能 |
| 历史脚本含 Windows Python 路径和固定批次目录 | 标出可移植/需适配边界，不运行历史生产器覆盖扩充后的目录 |
| 本机 `~/.codex/skills` 盘点时没有这两项生产技能 | 当前仓库文件作为唯一维护源；本机链接结果见本轮 validation report |
| 清理后旧报告有已归档绝对路径 | 从归档索引恢复必要输入，不能把 LFS 指针、缺文件或旧路径当当前可执行证据 |

当前规模的定位证据为 V11 `production.handoff.json`：20 种草、30 件静态造景，共 50 件；该数字不包含鱼、底床或独立碎石实例。用户“看着还可以、提交”绑定当前预览的 `accepted_for_commit`，不扩大为整缸性能或连续碰撞接受。这里不重验 50 件资产，不新授予接受。

## 每轮修改后的知识收尾卡

在原 handoff / validation report 补以下内容；已有字段可直接复用，不建立第二套必填 schema。鱼的九组证据继续以 `volume sop-init / sop-check` 为准，造景目前没有同等汇总检查器。

1. **范围与基线**：对象 ID、实际源/模型/配置/运行依赖 SHA，本轮改了什么，保留了什么，哪些旧报告失效。
2. **方法与替代**：触发问题、采用方法、必要依赖及局限；失败原因、最小负例和替代入口。无新方法时记“沿用某卡，参数变化见配置”，不再新建经验文档。
3. **三层回写**：通用判断进入对应 SOP/专题；本对象值进入 profile/布局配置；本轮图审、参数、SHA、失败/待查及接受范围留在原证据。新专题必须从 skill 或索引可达。
4. **实际证据**：同机位原图/旧/新对照，实际多视和代表动作；技术通过、操作者视觉判断、用户接受分开，引用当前输入的报告。暂停也及时写明下一步。
5. **交付与清理**：静态修改源固化、冷读和实际入口；归档恢复映射；精确保留/删除清单与剩余体积。唯一原始输入和验收证据不得按体积直接删。
6. **提交范围**：核对两个独立仓库，避免混入其他现场。用户要求提交时执行 commit + push，并分别确认结果；提交本身不提升接受等级。

短记录示例：

```text
对象/修改范围：
当前输入与输出 SHA / 旧报告失效范围：
采用方法链接 / 配置位置：
失败方案 → 替代 / 未知：
实际图审与专项报告 / 用户接受的范围：
源固化与冷读 / 正式入口或仍为候选：
知识回写：通用 / 本对象 / 本次证据：
保留、归档恢复、删除与剩余体积 / 下轮起点：
```

这张卡用于本轮结束时自检，不把所有旧资产追补成全绿，也不要求每次写新的总结文章。确认方法已经回到可发现的维护入口，再进行用户授权的提交。

## 本轮验证记录

2026-11-06旗鱼资料库双视/头嘴与有限鳍根返修：方法见[实际方法记录](../resources/skills/fish-volume-production/references/library-aligned-head-finite-roots-20261106.md)与[眼位/眼片执行卡](../resources/skills/fish-volume-production/references/eye-volume.md)，参数与当前源见[旗鱼候选索引](../resources/volume-fish/atlantic-sailfish-library-aligned-20261106.json)。当前眼位修正后3982面，眼片106/身体GPU/冷导出通过；原3968面完整490根/鳍面按实际身体与9鳍全属性/rig/runtime精确保留证明沿用，没有重写旧报告或声称新跑490。仍为外观待审候选，完整SOP与游戏安装未完成，不能当成成品冻结入口。

[知识梳理 validation report](validation/2026-11-02-3d-asset-knowledge.json)记录技能格式、维护入口链接、参考覆盖、本机同步和改动范围；不充当鱼、草或布景的模型验收报告。

## 2026-11-04 六鱼成品入口

真鲷、黑鲷、鲫鱼、草鱼、鲤鱼、蓝鳃太阳鱼均已安装、获用户整鱼接受并冻结。当前 [六鱼索引](../resources/volume-fish/final-six-fish-20261104.json) 与 [游戏收尾卡](../projects/fishing-2d/plans/reviews/six-fish-release-20261104/HANDOFF.md) 包含逐鱼参数、实际当前验证和精确清理收据；旧六鱼资料库实验路径已退役。默认后续只改动作，静态重新开启须有用户明确要求。

### 2026-11-10 虹鳟清爽像素材质发布

[当前发布](../resources/volume-fish/clean-pixel-rainbow-trout-20261110/release.json)与[游戏交接](../projects/fishing-2d/plans/reviews/clean-pixel-rainbow-trout-20261110/HANDOFF.md)绑定用户已接受R2。先身体后8鳍，中央额部供体排除侧眼、口部外壁不等同口腔；方法见多视材质卡。新风格8条接受、20条待做，当前静态再冻结；动作质量和未重复完整SOP项另计。

2026-11-11孔雀鲈R5接受与嘴部意图：[当前发布](../resources/volume-fish/clean-pixel-peacock-bass-20261111/release.json)、[方法及未来开合意图](../resources/volume-fish/clean-pixel-peacock-bass-20261111/README.md)。实体颌褶与真实口腔分别识别；1892三角、18骨，原0–18°控制保留。自动呼吸与合理闭口仅记未来意图，本次静态成品接受，新风格17/28。
