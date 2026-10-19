# 082 新鱼整片鳍面穿体调查

- 日期：2026-10-19；Normal mode。
- 任务：除旗鱼外11条鱼3D化；像素游戏目标相机，完整鳍连接与非口腔身体完整性为必检项。
- 证据：`projects/fishing-2d/experiments/blender-fish/082-validation/fins/{crucian,carp}/` 导出490姿态，鳍基报告通过；全鳍面报告失败。鲤鱼胸鳍约0.10mm、腹鳍约0.97mm；鲫鱼胸鳍约0.05mm、腹鳍约0.81mm。
- 冻结限制：根缝0.5mm、自由面穿入容差0.02mm；不放宽。
- 复现：`validate_fin_membrane_clearance.py --plan projects/fishing-2d/plans/changes/082-eleven-fin-clearance.plan.json ... --species carp`。
- 数据流：源图基线/多边形 → `build_fish.py` 中稀疏源面三角剖分 → 每顶点投影与clearance → Solidify → GLB → Godot完整蒙皮 → 原实际身体三角面BVH碰撞检查。
- 初步假设（尚未确证）：稀疏自由面或根带的实体厚度在顶点投影后仍会产生面内穿体；不能由鳍基通过推导整片通过。尚未开始代码修改。
- 对照：已有075/076通过样本；本批身体/动作/表面门23种均通过，仅全鳍面阻断。
- 已委派独立对抗审核与具体最差三角面的调查。Phase1待补证据与审核。

## Phase 1 — 已证实根因，独立审核 APPROVED

`fin_clearance_review` 追踪了原生点、Solidify两侧、源参数和权重：
- 鲫腹鳍Static triangle146跨20.8mm，纯身体权重，顶点埋入0.11–0.14mm，面内0.64949mm。
- 鲤腹鳍sample379 triangle98跨28.6mm，纯身体权重；同三角静止0.46905mm，动态0.97053mm。
- 鲫胸鳍三角112实体内侧0.04597mm，中面在体外0.00840mm；鲤胸鳍三角95实体0.09586mm，中面仅0.01230mm。表明先投影后实心化缺少两侧厚度边际。
- 近期历史：6d58bbd引入现完整基线/clearance实现，本次尚未修改通用建模器。

## Phase 2 — 模式比较与候选约束（待独立审核）

已有076基线细分解决中位鳍弦穿体，但二维盲目密铺曾造成后端投影重合。paired基线是折线，CDT可跨折线形成全根带三角；仅沿基线增加点不足以限制内部弦。

候选A：为root_attachment加入显式opt-in `max_source_edge`，仅用于适用paired鳍。按源图实际aspect度量，对任意顶点t<blend_end的三角，在投影前递归平分超过阈值的边；共享边只增一个中点，1/2/3边split分别生成2/3/4片，共享边相邻三角一并split保证无T结。原轮廓、UV坐标、根带t阈值不变；新的t/权重按原函数重新算，非线性attach重新执行。停止必须所有受影响边短于阈值，迭代/顶点上限失败而非默许。默认无选项时老模型完全不变。median/posterior不自动应用。

候选B必须独立：厚度边际不能由A通过假定解决。先测试A保持厚度、inset、clearance不变。若胸鳍残留，针对成品实体自由面重新校准body clearance（不改根带选区），或明确新增有限厚度预算；绝不放宽检查界限。

Phase3最小实验：使用冻结的鲫/鲤Static和鲤最差sample379检查，不重新生成源图；失败断言是原样本实测穿入超过冻结限制。A试验须分别证明paired局部最大源边长度、完整闭合网格/无退化、UV/外轮廓不改，以及静止与最差动态的全表面结果。B如需要将独立比较中面和实体两侧。完整490姿态是最终交付门，最小实验不替代它。

## Phase 2审核

独立reviewer对模式比较与A/B分开 APPROVED；实验设计 APPROVED，仅设计不等于结果通过。

## Phase 3 — 实验结果（待独立审核）

数值机制实验：`/tmp/fish082-curve-experiment.py`，产物 `output/fish-082/curve-experiment.validation.json`；只读现有blend，不导出候选GLB、不变更生产输入。

固定edge=.003native，对已精确定位的原生腹鳍根三角，在3D做诊断用细分并以原inset=.00045投影新增中点：
- 鲫原 −.649490mm → −.119717mm，最大边.001633native，原失败断言为真、细分后在原.5mm根缝内。
- 鲤同静止三角 −.478979mm → −.161600mm，最大边.002913native。它的静止原就在根缝内；不将该结果冒充动态通过。

该实验只确认“长弦→缩短后逐点重投影”机制。不是拟议的源坐标共形细分实现，不证明新GLB拓扑、动态、胸鳍实体或完整490；这些仍是Phase4回归。胸鳍Solidify两侧根因由Phase1独立对照已证实。A测试继续保留现厚度参数，不先混入B。拟先实现opt-in源三角共形细分，配鲫/鲤paired max_source_edge=.003，对实际构建后的失败检查重新运行，B仅在A胸鳍仍失败后单独进行。

## Phase4 A 实现与首次结果 — Strike 1

- opt-in局部共形细分实现于`fin_tessellation.py`，默认无参数直接返回原points/faces，不改历史源面。
- 新不变量测试3项（默认完全一致、共享边/内部边界/总面积/正绕序、非法值阻断）及已有volume_shape/fish测试合计51项通过。首次失败记录为模块尚不存在；测试运行目录错误已改为cli，不算修复试次。
- 鲤082b 正式CLI plan/build/validate通过，paired局部max实际≤.002992，厚度/clearance/inset保持；完整490运行中。
- 鲫082b 原生闭合报告通过，但GLB焊接退化门拦下38片腹鳍三角。不得接受。新的失败证据：不同UV `.5271819,.8031853` / `.5270591,.8031674` 在closest_point投影后位置只差1e-8，形成多对一；这不是源网格共形缺口。
- 回到Phase1审查投影映射和输入侧轮廓/基线；未开始第二次修复。

### 多对一映射复查与诊断候选（尚无第二次生产修复）

独立复算确认鲫塌陷点仍在body侧轮廓内；改基线端点不能消除此原因。拟议radial_section若直接使用原点depth(t)，虽有限网格collapse=0，却被审查**REJECTED**：固定u=.53、v=.806与.8120222672同在root_band，角度完全相同，是连续域的真实多对一。此为修改代码前的数值实验拒绝，不算生产修复试次；不接受该方案。

随后仅在诊断脚本改为固定root_depth构建截面chart，令固定u下角度atan2(z-center,常数depth)严格单调。数据在 `output/fish-082/projection-chart-experiment.validation.json`：全8鳍ray失配/合点/tiny面均0、u偏移0，剩余侧投影反向需要按root/blend分区及3D相交区分。仍待独立gate，不先改生产。

### 验证运行时限

鲤082b的大网格490导出因240s宿主子进程预算超时，已有7.7GB中间样本、未得完整export receipt。该结果是工具超时，不是490模型通过或失败；保留工具错误，不用不完整采样充当门禁。

### 第二次修订候选082c

- fixed-root-depth chart独立Phase2/3 APPROVED：全root法向指标虽有部分反向，但双方边/三角精确交叉实测0；固定u角度回折反例已消除。批准限两鱼实际网格静止中面。
- 增加显式opt-in projection=radial_section；仅允许paired且root_depth>.0001，不适用于posterior。射线与inset保持同source-u截面。无选项原nearest路径保持。
- 两鱼CLI build/validate导出拓扑已通过，鲫082b退化负例在082c消除。
- 原生静止诊断通过：鲫082c所有7片实体鳍，仍用同一全表面检查器、.5/.02mm限制。诊断产物明确kind=NATIVE_REST_ONLY，不能冒充实际Godot/490门。鲤同诊断待结果。
- 尚未修改厚度/clearance或容差；A+投影目前即可改善胸鳍，先不执行B。

## 额外输入根因已实测分离

独立复查确认：红鲷背鳍根边polygon顺序跳过完整baseline，造成39.1mm长rim；草鱼median是inset加实体半厚耗尽物理根缝预算；鲫/鲤腹鳍根边遗漏中间弯点形成非真实自由鳍膜wedge。082e隔离实验保持原投影、无细分/径向参数：修根边后两鱼腹鳍静止通过；草鱼仅median inset=0后背/臀通过；红鲷仅根边顺序修正后背鳍通过。各目标假设均验证，未改的胸鳍保留原失败。

F输入计划：完整基线成为真实多边形根边；每鱼使用自身曲根，不套别人坐标；inset=0使根带中面在体表，实体半厚最大约.25mm，保持原.5mm根缝及.02mm自由面门。082f 11份profile结构检查全基线段都是实际polygon相邻边。没有A/C新参数；若全部通过，则移除非必要通用代码变动，仅保留输入/工程记录。

## F 方案独立审核与最终生产入口

- 独立review逐鱼查看11源图及曲根局部、对照11份F差异：APPROVED，允许正式验证。
- 虹鳟继承082a先前对尾根端点的校准（.381/.629→.39/.62），此为已通过初始拓扑门的原修复，不是新F暗改。
- 生产前恢复HEAD正式CLI、build_fish.py与验证wrapper；移除本任务A/C实验模块和测试（保留`output/fish-082/experimental-code/`代码快照）。最终F不依赖新增通用代码。
- C实验全490导出已完成，但根/全表面检查尚未完成；在F输入方案已批准后主动停止C两验证及其Blender子进程，保留导出，明确不接受C且不将其当490通过。A/C用于诊断，最终生产走原维护实现。
- F正式CLI plan/build/validate→原生静止诊断正在进行；后续按新模型完整freeze、实际导入490、全23模型body/motion/material与视觉重新检查。

## F 拦截与G前的数值试验 — Strike 2后先查证

- F草鱼/大黄鱼CLI闭合及REST通过；其余9条拦于median根边4次使用（非流形）。paired/Caudal拓扑没有失败。零inset将部分Solidify根面放到精确体表线，产生焊接合边。
- 独立/tmp只读重建25片median，inset0逐片复现F坏边数；仅正inset=.0002后25/25闭合/无退化，最深根顶点约.430mm。继续同样试验inset=.0001后25/25闭合/无退化，最深约.340mm，物理余量更合适。新生产修复前已经有负例与因果对照。
- native REST helper原只导出根顶点，缺少与正式Godot exporter一致的每根边7个内点。Black/Rainbow两个F胸鳍点实际上在完整root边上，≤.5mm仍被该诊断近似误判自由面；正式490检查器和exporter不受影响。独立增free_clearance实验不改善，故不改模型。现补齐诊断根边，原诊断不作为验收依据。
- 草鱼082f actual Godot490完整鳍基/全鳍面均通过；仍保留F，不为统一参数重建已通过者。G拟只对另9鱼median设.0001，其他保持F。

## G 最终输入实验批准

独立审核最终G APPROVED：Grass/Yellow保留F；其余9鱼仅median inset=.0001、paired/Caudal=0，所有free_clearance仍.002。独立完整root边诊断证明Black59条/Rainbow51条root边补足后两胸通过；先前单pose helper的漏边是诊断误报，不是正式检查器bug；不加入无因果改善的.004。首次修补该/tmp helper有括号语法错误，未产出报告，已修正；正式生产CLI与检查器没有此修改。独立数值结果已足以冻结G，正式CLI/REST/490仍待。

## G 完整结果与停止点 — Strike 3

原维护实现最终F/G全部闭合和原生静止通过；正式实际GLB490姿态：9鱼全鳍基/全鳍面通过，黑鲷左胸18姿态最深.023142mm、真鲷左7姿态.028363mm/右10姿态.041642mm仍失败。23鱼身体完整性、动作与表面归属通过。9鱼实际多视/四动作视觉审核后已执行volume accept，真鲷和黑鲷未接受。实际按钮切鱼和36动作检查通过（配置DOTNET_ROOT后重跑无引擎错误；第一次缺.NET路径的运行不作为通过依据）。

独立review精确UV核对：Black最坏点t=.0599676<原.065，离散root选区遗漏跨界三角内的连续根域，不能直接扩大豁免。Red两最坏点t=.0770599确为自由面；中面在外但实体内侧穿体。具体原姿态、三角、源UV与两侧量测已复制到游戏plans/reviews/082-residuals/。原failed报告不改。

按A/F/G保守计三轮，停止两鱼模型/参数/检查器修复。独立review支持计数；C中止和工具超时不计。请求人审核具体两项架构及最小实验，详见architecture-review.md；不得借拆分根因重置计数。通用实验代码已恢复HEAD，未交付失败候选为推荐实现。
