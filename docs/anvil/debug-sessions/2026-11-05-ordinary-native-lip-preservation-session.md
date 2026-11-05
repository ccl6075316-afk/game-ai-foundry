# 普通多网格鱼原生完整口域保留验证适配

## 入口

- 时间：2026-11-05T19:52:13.684660+08:00
- 初始模式：Degraded；尚待实际失败报告。当前静态判断置信度：High。
- 授权范围：本轮九鱼必要SOP验收工具适配，不变更模型门槛、不虚构重新绘制完整semantic chart、不更改用户接受状态。
- 问题：mouth完整原生口域的preserved分支只支持packed geometry_parts，不能表达普通多primitive鱼确实保留的完整口域。孔雀完整body/oral未改；大黄/梭鲈肩部已另行合法重绘UV，只能声明完整口腔和保守前颅域保持，不声明whole body chart unchanged。
- 现有调用链：volume_sop.check_native_lip_report → volume_packed_acceptance.check_preserved_chart → _arrays只读取meshes[0].primitives[0] → extras.geometry_parts必须两part body_skin/mouth。
- 初读历史：e3dfed4/6ea64ab/6839727/30566b1；旧packed适配目的及门保持。
- 独立审阅复用当前三名执行agent中的group-b，遵守用户只用三个agent的要求，不增第四个worker。

## Phase 1（待真实复现与独立审阅）

静态可确认普通模型缺geometry_parts，即使保持全部实际口域也不能进入packed布局比较。不能据此直接实现或放行；等当前普通报告与canonical baseline实证，重现实际拒绝，再锁定失败。

## 不变的边界

全oral域、实际完整上下口缘及两侧皮肤邻面必须覆盖；原native UV、每个保护面的真实像素/material/嵌入图对应须可核；几何宽度变化和肩部新atlas不冒称原版全body不变。真实source/model/source-image SHA绑定，任意小白名单/伪ok/过期输入须被拒。当前packed默认分支行为不变。

### Phase 1实际复现完成（Normal）

B组完整提取脚本与孔雀candidate-r4的ordinary-chart-{baseline,current}.json、ordinary-native-chart-preservation.validation.json已到位。Root独立调用未改check_native_lip_report，重现invalid_preserved_native_lip_chart；原两个实际body/oral primitive的UV、triangle indices、材质、嵌图与named skin全相同，当前完整shared rim77边（upper36/lower39/commissure2），不是缺嘴证据。before报告在root-review/ordinary-chart-before.validation.json。

根因锁定为保存域与存储布局被硬编码耦合：_arrays只取第一个mesh/primitive，随后强制extras.geometry_parts的两packed角色，因而普通GLB在真实材料保留时也必拒。另A组当前packed body肩部支持面分裂而完整oral及保守前颅域全保留，旧适配要求整个body indices完全不变也无法表达mouth门真正需要的完整前域保留；不能伪造原全body保持或当前自造accepted baseline。

本轮只适配真实前域的保存证据；重绘semantic chart路径、旧packed whole-body默认路径和其他嘴/形体/鳍门不变。待Phase1独立审阅。

### Phase1独立审阅

B组APPROVED Q1–Q5。特别纠正：旧_arrays普通输入先读到Anal，而非Closed_body；缺失geometry_parts只是之后的布局假设失败。未批准实现。

## Phase2模式对照（待独立审阅）

完整阅读现有check_preserved_chart及其PackedAcceptanceTests正/负例；完整阅读semantic checker及six_cyprinid_lip_evidence.py、six_carp_bluegill_lip_evidence.py两种真实作者/后续保存证据生成器。原语义路径证明实际原画donor texel→作者嵌图，再证明后续当前body/mouth arrays和core/fade RGBA保持；原packed保存路径证明完整两part UV/indices/embedded PNG/material保持，并绑定已接受baseline。它们均不要求为了后续纯形变重新涂色。

差异逐项：单mesh单primitive/连续part行区间→Closed_body多primitive；同一PNG/material→每primitive引用及可能新增肩atlas；原全body index不变→肩部拓扑合法split但完整oral与前域原faces保持；连续packed source IDs→普通导出split/reorder rows；完整body保存声明→明确partial前域保存且肩部另证。原source-image/model SHA、原native UV、嵌图/材质与完整实际上下口缘均须保留。

依赖：glb_io严格当前GLB读取/accessors，PIL RGBA与嵌图原字节哈希；原accepted release模型SHA与source-art SHA；快照JSON自身哈希。新检查必须重读当前GLB，不信actual_current_chart/ok布尔或edge计数；从完整baseline几何导出保护face域并覆盖所有oral及全部真实shared rim的皮肤邻面。实际source/current顶点映射须单射且逐UV/角色/受保护face拓扑与材质像素可核，源口域不从用户任意少量face列表推导。

拟保持单一变更：在现preserved入口对显式layout调用单独严格保存域适配；未声明新layout的旧packed路径、semantic作者路径、其他嘴检查及490/077完全不变。新的ordinary complete-body先以孔雀实际案例作正例；带肩变化的普通/packed anterior域使用同一完整oral+源保护域规则，不谎称全body保持。

### Phase2独立审阅

B组Q1–Q4 APPROVED。普通与packed肩拓扑变化所需的保护域/身份映射由源作者维护；不能把完整前域声明变成任意face白名单。未批准实现或新容差。

## Phase3假说与最小检验（待独立审阅）

假说：在当前原UV/全部body与oral indices/原材料与嵌PNG完全相等的普通孔雀中，拒绝来自固定packed存储假设；若图表本身缺失/旧hash/嘴缘不完整，独立原数组/77完整shared rim与当前SHA核应揭出，不会得到现有全等结果。已两次由不同agent及root直接调用同一入口、同一真实report重现误拒；before独立报告绑定未改checker SHA。旧packed完整正例与改UV负例测试同时运行作控制，确认不能以简单放宽generic ok解决。

最小改动假说只需新增显式保存域布局读取器；输入当前GLB与接受baseline snapshot都实际重核，原UV/index/material/image不变的ordinary案例应从拒绝变通过；变UV/丢oral/rim邻面/漏保护域/改图/错source或model SHA都仍拒。partial anterior正例只允许保护域外肩部变化，保护域由完整baseline口腔/源轴域/完整rim拓扑推导，不采信任意face列表；换名wholebody必须因真实全body差异被拒。旧两条路径测试及全CLI suite行为保持。

失败用例早于实现：group-b/extract_ordinary_chart_preservation.py末端实际未改SOP调用、group-b ordinary-chart-sop-reproduction.validation.json、root独立ordinary-chart-before.validation.json，均是相同ok preservation在入口被拒；不是先写fix再造失败。实现后仍以同一真实输入复跑及原生GLB合成正/负例覆盖。

### Phase3独立审阅

B组Q1–Q5 APPROVED。补同一原packed fixture仅删geometry_parts的单变量隔离：原正例通过、删布局元数据后拒绝，UV/indices/PNG/material/baseline均未改。

## Phase4实现与验证（待独立审阅）

仅新显式layout派发到volume_native_chart_preservation；旧packed默认与semantic路径原样。新核重读实际全部body/oral primitive，解析真实嵌PNG、RGBA与sampler，release SHA校验接受baseline，自动全oral+完整shared rim皮肤邻域+源前域，有向face/单射row/UV/材料图像全核。没有重画嘴、改鳍阈值或通行白名单。

真实孔雀wholebody与完整anterior两正例通过；实际改UV、改嵌图RGB、删oral face/role（都诚实更新新GLB SHA）、错source/model、漏保护map、伪wholebody、伪rim计数及未接受baseline，共12case按预期；临时测试二进制删除24,976,171字节。原packed和SOP相关完整37测试通过。before重现存在于实现前，待B组P4独立Q1–Q6审阅。无失败fix strike。

### Phase4独立审阅与收尾

B组Q1–Q6全部APPROVED，独立再跑37测试通过。新分支只验证原生材料图保存；位置/rig/动作仍由原专项核，不冒称形态接受。紧凑12case+37test与四阶段审阅存resources/volume-fish/fish-shape-repair-20261105/native-chart-validation.json；临时二进制24,976,171字节已删除。Peacock实际current全9stage/67证据SOP通过并按用户明确条件接受完成。无失败fix strike。
