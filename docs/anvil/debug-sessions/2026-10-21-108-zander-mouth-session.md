# 108 梭鲈嘴部材质与实体边界调查

日期：2026-10-21。模式：Normal（已有 107 实际 Godot 截图、运行收据和网格导出）。

## 用户反馈与范围

用户指出梭鲈下嘴唇没有贴合材质，前端还伸出一块，并询问剩余未修项目。调查当前 107 眼睛局部试版的嘴部；眼睛试修不代表嘴部已验收。保留 106、107 证据及正式游戏，另建 108 诊断/候选。

## 证据清单

- 原图：`projects/fish-082-zander/output/char_zander_082_nobg.png`，2024×742，SHA256 `fd2d0c154c140aca906201fcd7c7f80e043221827f4c97a14b714e24fa825b67`。
- 当前 GLB：`projects/fish-107-zander-eye/game/assets/models/fish/zander.glb`，SHA256 `c1b10d96c7aa83e41129df16170d7302f4c4335b226785c5f5bd562b6e0aef`。
- 物种配置：`resources/volume-fish/zander-082g.profile.json`。
- 107 固定机位截图：Fish `experiments/blender-fish/eye-rollout-107/color/zander/head-side.png`。
- 107 实际网格：同目录 `zander-mesh-rest.json`。
- 约束：原画实际唇线约束实体口缘；上唇、口裂、下颌底、上下最前端分开检查；不得用移动 UV、全身重取色或加厚嘴唇掩盖边界错误。

## Phase 1 — 根因已定位，独立审查 APPROVED

已确认 `oral_jaws.lower_projection=0`、`upper_retraction=0`。不能将前伸归因于这两个参数。模型为闭合身体外皮和深色口内壁，须检查实际开口切割位置与源图唇线，而非假设有独立下颌。

证据：Fish `experiments/blender-fish/mouth-alignment-108/source-mouth-alignment.validation.json` 与 `same-source-canvas.png`；诊断脚本 `resources/scripts/volume-fish/audit_mouth_source_alignment_108.py`。

实际 GLB 的两个 surface 有 397 条匹配的共享口/皮肤边。源图不透明上下嘴尖均 x=2019；实际上尖 x=1999.868119，下尖 x=2015.903984，故下尖相对上尖前出16.035865px，但下尖没有超出源图。上尖短19.131881px，下尖短3.096016px。原 profile 最后两截面上缘迅速下降，与向 front 以外线性延伸的 cutter roof 相交，代码预测 x=1999.883110，与实际差0.014991px，解释了上吻被提前切掉的因果链。下颌底同列也偏浅17–25px（例如1960列25.34px），不仅是嘴尖误差。

该 profile 来源17891c3，oral builder/volume_mouth来源6d58bbd。107不改GLB，眼域也没有覆盖嘴端，因此不是107新引入的下颌加长或眼材质污染。实际口缘、源画唇线、取样UV分别有偏差；颜色遮盖无法恢复缺失的体积。

独立审查：`material_repair_review` APPROVED，仅批准以上根因。完整手工上下唇目标及横宽尚未确定，未批准修订实现。后续不能只缩短下尖、用原body/鳍门豁免嘴型，也不能抹掉所有暗线/口内材质。

## 保护与已知未完成

107 是眼睛局部试版，非整鱼验收。梭鲈吻端白环、头部拖纹、最粗 LOD5 仍登记未完成。其他鱼的材质/嘴型/膜面问题须逐项保留，不将“未发现同类眼纹串接”写成全鱼通过。

修复尝试：0。尚未改模型、材质或 107 参数。

### 物种资料核对

- [Pérez-Bote / MNCN-CSIC 同种描述及原照](https://www.vertebradosibericos.org/peces/identificacion/sanlucid.html)：长颌、锥齿及犬齿的文字证据。实际以隐藏浏览器查看 Figure 1 的 400×300 全鱼侧照；口部太小，不能从它量化唇厚或前伸量。
- [查尔斯大学动物收藏口部标本照片](https://commons.wikimedia.org/wiki/File:Osteichthyes_-_Sander_lucioperca_(mouth,_teeth_detail).jpg)：MAKY.OREL，2019-05-31，CC0。实际隐藏浏览器查看完整上下颌，支持连续实体下颌及唇缘/齿列/口内分区；它是人为张口的干制标本，不能当微张口的游戏原画比例模板。
- `maxillary extends beyond eye` 描述后方颌骨的范围，不能用于证明下嘴尖应前伸多少。
- 先前 web 图片请求失败；随后浏览器确实显示并查看照片，不将搜索摘要等同看过图。照片仅供结构判断，未下载或作为游戏纹理。
- 具体游戏上下唇、下颌底和嘴尖继续以已接受源图为约束；横宽仍属制作推断。

## Phase 2 — 方案选择（独审 APPROVED，仅CPU测试）

目标数据：Fish `mouth-alignment-108/source-target-proposal.validation.json`。前端2005/2010/2015/2019列的 alpha 空隙区分上下唇；前端像素中心与 cell 边界分开记录。上、下端分别约束，完整下巴用原画外轮廓。后部两条黑线未确证，不把两条都切开；后段口缘先保持原几何并保留未知。

比较：

1. 直接套091/093分段截面映射：不选。093已有high/rim次序错误被epsilon夹住、identity仍移动及灰模圈纹的失败证据。
2. 原生ellipse/body重建后splice：暂不选。改bottom section也移动侧面和眼区；还需实现变间隙口缘，范围更大。
3. 选择直接紧支撑的光滑XY位移场，Z保持；不使用截面/rim归一化除法。以实际口缘/外壳的稀疏控制点对到冻结源目标。上下surface的同坐标点用相同函数。RBF必须按最终乘支撑窗后的残差求解，不能先拟合再乘窗后宣称命中。

眼睛采用保守全Z棱柱保护：原源画布XY [1800,1920]×[315,445]，并冻结实际incident面/法线共享顶点；由该集合实际最大X加余量确定front X场起点。后下巴场只在实际旧lower floor以下启用，保留后口缘，不猜后黑线。解析遮罩保证完整保护域及后部零场，不能以稀疏pin点替代。

仅口区skinUV允许按已冻结源坐标显式同步；不改源PNG或oral1常色，不全身重投。identity模式POS/NORMAL/UV都必须不动；候选法线与实际灰模另核，Jacobian正确本身不代表灰模通过。

原Godot `.glb.import` 的 `meshes/generate_lods=true`。修改GLB后不能声称只因base索引保留就保留全部旧LOD表；新实际表须重新导出、冻结、逐级核查和绑定。旧439面LOD5失败仍保留，不从报告中删掉，也不自动承认新LOD已修好。

冻结方案见 Fish `mouth-alignment-108/phase2-local-field-proposal.md`、`eye-protection-proposal.validation.json`。实际保护skin659/oral231顶点，front支撑起点1922.194880px。`material_repair_review`按Phase2 Q1–Q4全数APPROVED，仅允许冻结参数后的CPU可行性/反例试验；不授权写模型、UV或runtime。求解冲突、病态、折叠、自交及保护域变化均须明确失败。

末列tip的401.5/430.5为源像素区间代表点，不是生物学测点。一个旧端点不得同时指定代表点与406唇界的矛盾目标；Phase3首次冻结前须按实际控制点角色明确选择，显示cap/唇缘实际误差，不把像素游戏要求升级为完全复刻某个垂直像素cell平面的硬标准。

## Phase 3 — 首次最小验证与结果

- 零场/identity完整字节保持。
- 原模型及仅缩短下尖的假修必须继续失败于上尖/下巴约束。
- 去掉眼保护或支撑窗的场必须被保护域/后部差异门拒绝。
- 实际三角翻转、退化、自交、上下唇穿插分别检查；故意坏场应被拒绝。
- 只移几何不更新UV的候选应继续失败于真实口缘到源唇取样对应。
- 确认可行后再批准Phase4模型候选，并重新跑实际多视、动作、鳍根/全鳍面及身体完整性；107的旧报告不为108背书。

### 首次CPU结果：假设被否证，独审REJECTED

`probe_mouth_field_108.py`、Fish `mouth-alignment-108/cpu-phase3/`。首次一次冻结15控制点、64px Wendland核及全部窗，未调参、未写模型/UV/runtime。尽管控制残差约1.5e-13px，最小采样Jacobian -4.735883，实际同面选择基线交叉0对、候选已检范围交叉266对，三角图明显褶叠；部分前口隙仍被侵入。保护域659/231顶点、Z及后部保持，不能抵消几何失败。

另外X矩阵条件数4.269e20，脚本却以lstsq继续，违反已冻结的“奇异/病态即拒绝”；后口缘5.723e-8px也不是exact0。该次探针的总ok未纳入这两个门，应作为诊断实现不足记录，不能因其他失败恰好拦住就称这两个门正确。后续场只可作为越过预检拒绝后的负例，低残差不能反向批准它。

`material_repair_review`明确REJECTED，不得Phase4。原参数/失败证据归档，不继续调核半径或窗。没有安装修复，Phase4尝试数仍0。

## 返回Phase2 — 第二方法仅先验证Stage1

自由XY场没有保证体积/次序，控制点命中不能避免中间折叠。改比较具有连续正Jacobian构造的单变量步骤，不继承RBF参数。

Stage1提案：先以`V=Y-slit_center(X)`剪切，按只依赖V的凸权重组合两个分支的单调X映射`f_b(X)=X+Delta_b*g_b(X)`，再逆剪切。`g_b`在1988及之前严格0、到各旧分支尖端为1，Delta上/下均正。固定V时导数是两个正导数的凸组合，剪切/逆剪切det均1。后部未知口缘<=1988、完整眼区解析恒等；实际前端跨V三角/离散自交仍要另查。Stage1只证明tip reach和此变形可行性，不称下巴、口隙或UV已修。完整下巴与前唇的Stage2另经严格实际分支包络/有序目标分析后再审。

### Phase2b APPROVED；Phase3b REJECTED（未改资产）

冻结方案与实际V分布：Fish `mouth-alignment-108/phase2-stage1-monotone-proposal.md`、`stage1-branch-distribution.validation.json`。独审批准后执行 `probe_mouth_slit_stage1_108.py`，定位工具 `localize_mouth_stage1_108.py`。结果在 `cpu-stage1/`。

两尖X均2019.5；identity、眼659/231的POS/NORMAL/UV、640后口缘、共边、Z精确保持；采样及连续Jac最小1，解析/差分误差2.98e-9，skin base无新增反向或退化。但oral base出现2个细三角相对运输normal反向，以及2对从基线0变来的真实交叉，另有9个未解共面候选；旧LOD也失败。

独审用报告old/new坐标复算了两对严格段/三角内部相交，REJECTED，不准按旧拓扑施工或进入Stage2。交叉位于约source(1991.8,411.66)，最近顶点距离0.0165源像素只是定位尺度，不作为豁免容差。该结果反驳的是直接移动原有限三角的路径，不否定连续单调证明。没有第二个已安装修复，Phase4尝试仍0。

### 返回Phase2c：口内局部离散连接方案

只读比较局部edge flip与oral roof/floor的XZ约束重三角化；拟保留Stage1场、外皮、完整既有边界、坐标/属性及后桥，仅替换有限口内连接。待检查active patch的边界简单性、点云单值、与保留片/skin的逐边共形和CDT是否需新增点后，再独审授权CPU。当前不调用CDT、不写模型/UV/runtime，不降低既有失败门。

上述为方案提出时的状态，后续独审已 APPROVED 单次 upper97 CPU CDT；lower140 连接及 Stage1 参数不变。三角形只重连现有68个几何点，37条边界冻结，返回坐标弃用，仅按一对一 origins 回接原点。原同位组的 J/W/UV 一致，NORMAL 不一致，不能把几何点合并误写成全部渲染属性一致。新活动面允许独立 flat normal 属性顶点，未保留面原属性不得改变。

### Phase3c CPU 结果：独审 APPROVED，仅独立几何候选

正式包：Fish `mouth-alignment-108/cpu-upper-cdt/phase3c-package.validation.json`。后台 Blender4.5.3 首次有效 CDT 输出68点97面，所有点使用，无新增、合并或边界拆分；全部37条patch边和397条skin接口精确保留。二维面积差约 −3.79e-19 rest²，无正面积重叠。

交叉检查器另修复了 `js>i` 会遗漏“静态低索引 × 活动高索引”对的问题，并保留共享顶点pair。相同新checker：原版交叉0，Stage1旧连接交叉6，新连接交叉0，共面正面积重叠0。旧Phase3b的2对报告保持历史原样，不追认为完整计数。此checker范围仍是离散静止三角与有限数值阈值，不证明连续动作无碰撞。

独审发现另有两片新面只有连接改变、顶点本身在恒等区，原选区漏查。独审保守选入全部 upper68 点后仍交叉0；随后永久修复 validator，冻结同一 CDT 输出重跑得到9353对/1005片活动面、所有新97片均已选入，交叉0、共面正面积重叠0。37条有向边也与旧片逐条相同。旧9295对/1000片报告与脚本归档为选区不完整，不追认为全片检查；没有再次运行 CDT 或改变参数。

`material_repair_review` 已 APPROVED 此base几何：允许独立 Stage1+upper97 CDT GLB 与灰模，未批准正式替换或 Stage2。`mahi_phase_review` 复核补检固化、各输入哈希并实际复跑 validator，APPROVED 闭环，见 `.ai/anvil/reviews/2026-10-21-108-zander-mouth-review.md`。`yellow_mouth_trial` 作为doer制作独立几何候选；raw/actual口内1189片几何唯一映射已确认，实际索引次序不同、定向均反向，不能用Godot面号直接改raw面。

下巴及前唇Y尚未修，UV尚未改。实际新导入LOD仍未知，旧6/2表只作历史敏感性证据，不能代替新LOD检查。新眼绑定、身体/鳍/动作及材质门仍待后续，不以早期灰模候选代替整嘴或整鱼接受。完整上下颌源图Y包络仅准备独立方案，尚未获准Stage2施工。

### 隔离Stage1灰模候选已输出，完整嘴型仍未通过

Fish `geometry-candidate-stage1/zander.glb` SHA256 `002c34131da631de768cf938413c4d7047c894ad57c58f66ae763607c0edc2b8`。原BIN前缀、其他primitive、材料、图片、rig、动画保持；原raw口内kept1092片同序，新97片追加291个flat-normal属性顶点、仍仅使用68个原几何点。保护skin659/oral231的POS/NORMAL/UV精确保持。重复GLB已验证同SHA删除，report-only序列化故障记录在implementation-log。

实际写出float32 GLB再检：交叉0、共面正面积重叠0，397条skin/oral接口同位且定向相反，组合边次数非2为0、非流形0。上下尖X均约2019.500015（float32误差）。上尖Y401.2964，下capY422.1553..436.1553，尚未修到源下cap425..436。

Root实际查看同机位侧/斜灰模：reach改善，但上尖局部折角明显，且下巴/UV缺陷仍在。这是已预先限定范围的分步候选，不是可接受的完整嘴修复。不得只凭交叉/闭合通过宣称完成，也不将此灰模强装正式游戏。下一步完整额头/下巴/前唇Y方案须消除该局部喙状外形，并接受新的独审与视觉检查。

## Phase2d / Phase3d：完整Y与UV提案，有限网格仍失败

首次仅CPU轮廓提案补上额头/完整下巴，但窄过渡产生额头小峰和下巴肩；保留 `cpu-y-uv-proposal/`，没有施工。只读旧/源表显示：强迫1940立即贴源会反向，而从保护外原top接1960源锚可保持单调；chin从1780原实际接1870.5源锚有同号端导。固定更长Hermite接合，经独审 APPROVED 一次CPU，不扫窗口。

`cpu-y-uv-monotone/`：Hermite端值误差0、一阶连续误差≤4.44e-16，端切线与旧轮廓精确匹配；眼659/231、baseline640后口缘、相对Stage1的704未知后口缘点及397接口保护通过。strict branch排除了原144片straddle，不把下支混成上包络。最小采样dY/dY为0.785714，但这不是全域单射证明。

实际原有限面仍有28对交叉、skin6/oral3反向，集中前口缘sourceX约1999–2005，故独审 REJECTED；未写Stage2 GLB/UV/normal/runtime。源UV采样alpha0由416减至275不等于颜色通过；真实opaque回退均alpha255，不可据此叫body洞，但部分暗供体仍会污染外皮。暗fallback与几何问题分别保留。

## Phase2e：共形局部细分，一次有界CPU已批准

只读证据 `refinement-readonly.validation.json`：固定Stage1-X slab[1988,2010]选761片（skin567/oral194），实际bbox1984.0006..2019.4926；覆盖28对中的全部24片失败面。最大原域XY边23.396px，F(原边中点)相对变形后直边中点偏4.263px，支持有限近似问题，但不证明所有失败均出于离散。涉及65条原397 parent边、36个未知后唇点、125片共形邻居，无眼域冲突。

冻结提案 `phase2e-conforming-refinement-proposal.md`：1px指原Stage1域XY最长边；F中点误差只作诊断。新点按原Stage1三角bary生成后再求固定F，不在已变形直边取中点。全部共享边统一edge-ID+dyadic参数缓存，397 parent边改查完整反向child链。JW按骨ID聚合、超过4拒绝；hard normal/UV分组不混。未知后唇原点/属性与新边插点的恒等语义分别记录。

独审 APPROVED 一次CPU；深度每个原face谱系最多8，全部closure child累计上限50000，范围只在761+必要125邻居，超限立即失败且不调场/源锚/窗或自动扩大。所有新拓扑面、局部对周边几何、baseline640及eye保护必须查。无论CPU是否通过，既有UV透明/暗回退风险都不自动解决，仍不授权资产施工。

## 用户新增交付要求

2026-10-21用户明确：结束以后沉淀知识/技能和本次问题，清理实验垃圾，commit push Foundry与Fish直到两个工作树为空。已授权执行106/107重复截图清理：先归档完整runtime、素材与可移机重建包，保留关键正负例/原报告/108依赖，再提炼已删图SHA清单；没有改旧失败为通过。最终提交前仍需完成本轮审查、保留明确未完成项，并分别确认双仓push和`git status --short`为空。

## Phase3e失败；Phase2f/3f局部graph重连通过

有界细分在原face谱系深度8先耗尽，1px尺度尚未完成，也未进入其后的失败面追加细分；停止网格的237交叉/85反向或退化不能与旧28比较而断言解析场变差。完整保留 `cpu-conforming-refinement/` 的冻结与停止原因，没有调预算重跑。

只读证明前吻四片可构成destination XY的Z=f(X,Y)图域。lower两个微小UV分组冲突因此不合并，选择更小的左右upper两片重连；lower495片、跨Z15片、exact-Xconstant cap46片保持。旧upper投影重叠是待修离散负例，不要求它先无重叠才允许重连；新graph明确改变有限面插值，不声称原连续表面全部保留。

Phase2f独审批准左右各一次固定CDT。Phase3f `cpu-upper-skin-cdt/`：68/70原点、103/106面，全部原点使用，无新增/合并，63有向边界原样；完整397接口闭合。保守float32选区166174对、交叉0、共面正面积0、全base零退化。负normalcos11处保留为微分运输失配诊断；有向图域面积与真实交叉才判断拓扑，不靠更换法线掩盖。独审复验通过，允许独立完整Y几何候选。

## Phase4完整嘴型候选：视觉REJECTED，Strike1

`geometry-candidate-y/zander.glb` SHA256 `227b7a1671bae5f8010924046014a0ad1d712bd7ab806168c97bd4ecc1b0b071`。实际写出float32再检19235对/2122片活动面，全部209新skin+97新oral纳入，交叉/重叠/退化0、397接口反向闭合。计数不同于CPU报告，因为实际raw比较不把double→float32纯舍入全当变形。

法线合同经独审明确修订：按原smooth/hard/UV组、实际f32面面积加权，只改incident于几何/连接改变的口域；后唇受影响者可导出normal变化，逐ID记录，不追认旧normal-exact门。眼与口外仍exact；所有后唇POS/UV/JW保护不放宽。

Root与独审实际查看四视灰模，确认下巴纵向凹折、前唇盾片/下钩，**视觉拒绝**。机械通过不能代替形态接受。本轮完整修复Strike1；此前明确分步Stage1不算完整嘴修复。未启用UV修补、未装Godot/正式游戏，不用材质遮盖。

## 返回Phase1：保护与source语义错误

- 以实际冻结值纠正先前口述：旧保护maxY约453.9519，当前计算anchor约455.95，不是456.95。X1920.5旧B458.2187、实际anchor455.7721，只剩2.4466px却展开21.7813px；中层dY/dY17.69、X1921处dY/dX30.49。2px眼保护退场造成三维高应变，二维外轮廓单调不排除此凹折。
- 按真实6039像素完整眼层、11px位移与实际shader侧别门，clip三角后逐source pixel-cell相交，base直接支持246顶点，normal incident一环338。旧659包含413多余点，不能因此直接缩为246：base+已通过LOD0–4实际支持union为304点，含18个旧659外点，粗级延伸到更大区域。LOD5原失败另列；不将全局maxY当全部X的下巴anchor。新合同须保存真实支持与同位属性，候选新LOD仍须fresh检查。
- `material-lip-semantic-readonly/`经独审确认：2005金白唇带到406，407..412仍opaque暗带；alpha边413不等于实体亮唇界407，2010同类差5px。将alpha保留域直接做实体外皮，是盾片的重要建模假设错误；不进而断言暗带全属口内。已手标区段可作材质约束，1998–99连接、2015/19暗端继续unknown。尚未授权新场/缩保护/模型/UV。

### 真实眼部支持合同与第二次方案准备

独审核对完整眼层支持后，批准以下合同方向用于拟案：base246真实眼层支持点的完整原三角、corner groups、POSITION/NORMAL/UV/JW和lookup须精确保留；旧base+LOD0–4的304点支持union是历史依赖证据，不要求全部粗级端点成为新模型永久形状钉点。若新模型退休全部旧LOD，则新实际LOD必须逐项重新计算完整6039眼层支持并检查侧别、唯一性、来源和动态画面；复用任意旧LOD则仍须保护或重验其依赖。旧LOD5失败保留，不能用退休其他表的方法掩盖它。该批准不等于新field、模型或LOD通过。

只读事实：actual V=0跨面skin144/oral7，最前X分别1894.460/1894.464；1922..1988无跨面。旧rim也并非精确等于每个X的全局包络：upper后段Y−R最低约−5.27e−5px，lower后段Y−L最高1.45434px。故移除错误bbox锚点后也不能沿用旧640/704后口缘全EXACT声明，须在新方案明确释放范围、逐ID披露并审查。

106/107已完成独立文件保留与代码提交审查，导入设置以`.import.txt`和精准恢复映射归档，实际恢复逐字节核对通过；没有把该核对说成新GPU/LOD验证。已提交推送Foundry `01c0194`、Fish `30a7059`。108仍独立待修，后续提交不得借这两个提交的通过范围扩大接受声明。

## Attempt2：固定新场，CPU与后补诊断均未接受

方案经独审后只执行一次CPU：移除全局眼框锚，rear lower以实际L→B展开；统一U/R/L/B有序Y图，原完整眼408三角/246点精确保留。源金白唇边被定义为Rt目标，旧暗端仍未知。结果 `attempt2-cpu/completion.validation.json`：已知X2000.5目标407，实际有限面408.305309，误差1.305309>预冻1源像素，立即停止；397接口反向闭合、眼部和后缘小于0.25px等先行门通过。未补写为pass，globalcross在首轮停止时未运行。

独审另批同一场的只读补证及RAM灰模，不保存新GLB/候选。原下巴凹折位置的峰值dY/dY由约17.7降至约4.8；但根本不证明形态通过。侧/斜上唇仍折，正面仍有中缝。实际Camera3D投影显示默认1280×720窗口的鱼viewport为1280×378：1.305源像素在normal镜头约0.12–0.15屏幕像素，closest正面约2.028；720高resize上限诊断closest正面3.863。不能笼统称像素游戏看不见；头部近看仍重要。

只读全几何补检 `attempt2-connectivity-readonly/` 纳入全部24130实际面：26处真正三维穿插、0共面正面积、0退化，397接口仍闭合。旧F2的左右upper CDT连接各7片投影反向；各两个内部点落到新边界外约0.00077/0.04254源像素，不以微小为由挪回或扩大epsilon。错误对角线5919→369是F2专用新连接，其邻面关联11处真实穿插。oral97的XZ图仍合法。坐标改变后，旧CDT验收不能沿用；有些内点已在边界外，也不能直接把同点集重新CDT。

`lip-alias-readonly/`另记录一个独立形态风险：Rt强制413平台→407平台，5像素内峰斜率−1.8，约旧R的4.81倍；端部二阶导由0跳到±1.44。C1不等于曲率连续，可能把材质像素台阶实体化；它不是已证明的唯一根因。原图的色簇/1998–99过渡和暗端不确定性，不自动授权改成3px容差或第三条曲线。

## 固定场、恢复原skin的单变量CPU

独审批准的 `phase2-original-skin-proposal.md` 和冻结包只撤销F2专用209片重连，恢复原22941片skin连接，保留Stage1所需oral97及同一attempt2点坐标、属性、场/目标/容差。实际raw indices、原属性、11672/3142原序f32点及oral97哈希均冻结。

`original-skin-cpu/completion.validation.json`仍因X2000.5实际408.099225、误差1.099225>1停止，不能追认通过；其余已知源节点误差不超过1，眼408/246、后缘、397闭合及零退化先行门通过。独审已另准同一原连接的只读全局交叉、四视RAM灰模与失败边曲率归因，以判断撤销错误对角线是否解决主要缺陷。尚未授权新顶点、split、第三场、GLB、UV或正式运行时。

新RAM factory须处理旧normal helper的零新增面边界：`[-0:]`会误选全身，nnew=0时只禁用这一新增面尾段标记；旧冻结脚本不改，仍按实际面和原seam组派生，眼及口外保留合同不变。这是范围实现纠正，不是用法线藏几何折角。

## 原skin后补结果与2026-10-22物种资料

`original-skin-readonly/`全局24345对/全部24130面后补仍有16处真正三维穿插，0共面正面积重叠、0退化。穿插集中在X1998.57–2002.52、Y407.16–409.01，包含skin/skin及skin/oral；撤销旧209片CDT使26降到16，但否定了“只是旧CDT连法”与“只剩一点源图采样误差”两种充分解释。397接口反向闭合、全边incident2仍不能替代无穿插。原失败边11581→370在X2000.5处的变形后直线为408.099225，而原域内点先求固定非线性场为406.972435，曲率残差1.126790像素。没有插点。

Root实际查看`original-skin-ram-grey/original-skin-comparison-CPU-FAILED.jpg`：恢复原连接仍有前唇台阶、正面中缝和斜视折口，维持视觉拒绝。没有保存新模型或用UV掩盖。

新资料为Javier Blasco-Zumeta的[043 Sander lucioperca图册](https://monteriza.aranzadi.eus/wp-content/uploads/peces/043.sander-lucioperca.pdf)，印刷页3；PDF SHA256 `fa8adae912c4d2604e1a16f4ee59a8a43dd5c5ba997d1609b7736d79c7ce6c55`。Root、doer与独审实际查看解剖页。侧面张口、正面接近闭口/大张口及背腹头照支持连续斜唇、横向圆拱和实体下颌的定性方向，但握持、透视与开闭不同，不能量成准确横宽、唇厚、闭合差或源图Y。牙齿也不能变成实体外皮盾片。仅归档URL、哈希、页码和观察记录，不复制完整版权PDF/照片进仓库。

独审Phase1批准前瞻区分“材质亮暗色边”和“实体唇缘在已确认唇材质区域内且连续斜行”：413/407平台不包含端导数=0的信息。旧零导平台是额外工程假设，短陡目标与有限边近似的共作用仍需检验，照片不是单因果证明。任何新方案必须先冻结逐X可确认带界/未知段、物理嘴尖和微张状态、曲率规则，再量实际有限边是否在带内；不能统一改成±3px、追认旧1px失败，或放宽眼/闭合/交叉硬门。当前仅开展源带只读调查，尚无第三场执行授权。

106/107另外178项已归档临时文件于2026-10-22按精确白名单删除，逻辑67,311,388字节，逐项确认不存在；审计在Fish106/107 `cleanup-audit/`。107candidate与108活动输入保留，后续仍需完成收尾审查和双仓提交。

### 连续唇形提案前的只读约束

`phase1-continuous-lip-readonly/`确认16处穿插涉及的10片原skin与6片oral97均有原边跨陡变X段；原skin失败边11581→370也在穿插中，原Stage1+oral97写出模型则为0cross。旧R在大部前吻约−.374，但末端约0.01px拟合导数显著变化，不能泛称恒斜率；旧collapsed U=R=401.296404，新top401.5，直接恢复旧R会产生末段负厚度。

`source-lip-band-readonly/`人工逐列查看原生画布：1985≤X<1998奶金簇Y[407,413]，2000≤X<2010亮金簇Y[402,407]，2010≤X<2012同高度但变暗、把握较低。1998–99及后暗端不扩认为已知。独审仅批准它们成为下一工程允许域的证据，不能视为已批准切割路径或生物唇界。

`phase2-continuous-lip-proposal.md`拟只替换Rt，恢复原skin、保留oral97与其余场。单条五次以下多项式固定两端值/导，余两自由度唯一最小化弯曲；不以穿插数或看图反复调参。固定join1972来自首已知13px段等长后延，明确新增13.5px旧后缘释放是工程推断，须独审批准；全材质cell区间、内缩余量、实际PL落带、单collapsed角色和完整三维门分别定义。当前提案包f066e2ca…，尚未求解/执行场或生成模型。若获批后任何硬门失败即该次完整尝试失败，不自动换join、次数、CDT或容差。

### 完整修复尝试2：唯一曲线不可行，停止

独审批准前述固定方案、1972 join/13.5px后缘前瞻释放和high/medium分别标注的带约束；所有旧失败不追认。首次生产求解前冻结三份实现与数值方法，`continuous-lip-cpu/execution-freeze.validation.json` SHA `6676a9f83490f5f908401c43b2d89eeafb62152d09e05b7c5b15ed031a2290a3`。12项合成数学反例控制通过，不能当候选几何通过。

唯一生产求解的第一次精确有理二维QP即不可行，未得到新Rt、未进入exchange，**未执行新场、f32几何/眼/后缘/接口/交叉/灰模门**。按事前策略计完整修复尝试2失败，没有换join、degree、端导、带或余量重试。此前名为`attempt2-cpu`的旧冻结场与原skin对照仍是历史分阶段调查，不回溯重新计数。

失败后只读Farkas证书以三条冻结约束 Rt(1985)≤412.5、Rt(1998)≥407.5、Rt(2000)≤406.5，在该固定四端条件/deg≤5两自由度空间里非负有理加权。A/B系数精确抵消为0而右端约−0.1993619122，证明该空间可行域为空，甚至不需非回钩约束。它不证明全部连续唇线或源材质本身互相矛盾，也不是更换优化器或提高精度可解。报告与证书待独审复算，尚无第三次修复许可。

### 完整尝试3：固定C2空间，CPU通过待视觉

独审已精确复算上述Farkas证书，确认Strike2。`context.validation.json`与`context-errata.validation.json`区分旧报告通用package字段的基线含义、固定top/chin/lower参数与真正新授权包；“次数”仅指同空间的优化迭代次数，不含degree改变。历史12控制缺完整输入/执行器，只保留为历史证据，不称可重跑套件。

第三提案包`f8030d89…`经独审，唯一变化为固定knots `[1972,1985,1998,2000,2012,2019.5]` 的C2 clamped cubic空间。四内点Y自由，仍唯一最小弯曲；精确4×4 SPD与各段Bezier导控制非正定义保守有限域。其余场、源high/medium带、内缩、原skin/oral及全部门不改，不声称新空间必可行。实现冻结SHA `52a14f2739e4bd6d3e08632704c5c40e14a494072f11fb01e648728d022dc14e`，21个控制保留具体输入/执行器/命令，开发中的一处fixture预期算术更正单列，未改生产合同。

一次生产求解/CPU报告 `continuous-spline-cpu/completion.validation.json` SHA `bf90691c0ea89775b806f869b55cd60ba2aaabba0f80f3d195cab48281d11cc6`：19去重限制、1056active子集得到精确SPD/KKT唯一最小；全部24130实际f32面、24762对为0cross/0overlap/0deg；397反向接口与全边incident2/方向成对通过。完整眼408三角/246点、后缘X≤1972最大0.228546px、全部high/medium实际PL唇带与旧lower1px通过。新释放为104个端点样本、52个唯一skinID，最大位移1.6875305px，仍为未知工程区。

尚不能据此接受自然形态：最大actual dY/dY约12.427在近collapsed点3030，最大三角切向stretch21.709、最小0.18356；参考有理区间证明与IEEE执行/连续蒙皮证明分别声明，端点无Jacobian承诺。CPU待独审，未渲染新灰模/资产、未做UV/Godot/身体/鳍/新LOD。若此完整尝试后续视觉或硬门失败，按已批准策略计Strike3并停止第四轮，进入架构复审与沉淀清理。

## 终末：完整尝试3视觉失败，停止修复并归档

CPU通过后只生成RAM灰模与只读截面/旧镜头数学投影，没有保存第三版GLB或替换游戏资产。侧面上唇对齐改善，但正面下颌呈较长杯形凸体，斜视下缘仍有硬折。根因调查显示X1920/1950的口内底面不变，外侧中央壳深约10.79/10.28变成32.51/35.04源像素；继承的下颌展厚未约束好横向体积。不是数学针状尖脊，也不能全部归因于新Rt。旧镜头的整体位移不是缺陷尺寸或新模型GPU画面。

独立最终报告 `mouth-alignment-108/visual-review-final.validation.json` SHA `ac1db51f6713e63536721c8d91ad1e362506fa6d0125840848b0f73a58dfcfdb` 绑定26项证据和固定审查片段：CPU通过，形体拒绝，**Strike3 STOP**。按Anvil:debug三次失败规则，不继续第四轮同架构修复。第三次未保存新GLB；UV、运行时、实际新LOD、身体不透明和全鳍/动作等新交付门未执行，正式模型未替换。此前Stage1/fullY实验GLB仍保留为历史证据。后续若重开，应先重新设计完整下颌横截面/内外壳约束，不将本轮C2解作为可接受模板。

通用知识已沉淀到 `docs/anvil/knowledge/2026-10-22-zander-mouth-source-fit.md`，制作技能与mouth-repair参考同步补充。回家查看入口为Fish `docs/3d-fish/SESSION-106-108-20261021.md`，含鱼种和位置标注。历史失败、数值通过与视觉拒绝分别保留；106/107的局部眼睛改进不等于整鱼通过。

本轮脚本是冻结证据的历史重放工具，不是生产CLI。重放需按各execution-freeze/manifest恢复源图、GLB、运行时覆盖及导入设置；RAM诊断依赖前序冻结输入、Blender和部分工具的numpy/scipy。已归档完整输入的21项C2控制可重跑；12项早期控制只有历史结果，不称可重跑套件。六个临时工程的活动文件恢复按 `final-cleanup-plan/restore-active-fixture.py`，输出必须为不存在的工程根目录，不能附加`/game`；恢复文件不等于已做引擎导入或GPU验收。最终删除必须使用终末快照精确白名单、先确认保留源已提交，再执行并记录回执。

### 清理已执行

必要来源先以Foundry `3571d2a`（含`ad2cc71`）及Fish `4da26b2`提交推送。终末包经独审后，实际HEAD/LFS/全树/进程预检通过，按manifest `b0aeaf33281d96d5a340727890124cd115cd131a29dde78799af019c892ab494`执行64项精确清理，370文件、75,502,025逻辑字节。root逐项复核全部不存在，回执和核对位于Fish108 `final-cleanup-plan/terminal-execution/`。六个实验工程已删但243个活动输入有恢复映射；三个版权资料只保留来源记录，不能离线还原。用户原Godot54404与共享工具链未动；嘴型仍拒绝，未运行新的验收门。
