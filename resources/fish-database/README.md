# 鱼类资料数据库

Foundry 的鱼类资料入口。集中保存物种资料、照片/扫描、第三方游戏模型、几何测量、来源与核验记录，供鱼类制作查证与比较。以版本化 JSON/JSONL 和原始文件保存，普通 CLI 即可读取，不依赖桌面客户端或在线数据库。

## 入口

- [`manifest.json`](manifest.json)：资料来源、目录及记录入口。
- [`handoff.md`](handoff.md)：本轮结果、待解问题及恢复方法。
- [`validation-report.json`](validation-report.json)：本次入库与完整性检查。
- [`catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.html`](catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.html)：**当前模型取得情况，325/325 个基础鱼名、646/646 条预制体与变体已取得**，可搜索、打开网格及来源记录。
- [`catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.csv`](catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.csv)：逐鱼取得情况和首选网格导出路径。
- [`catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.jsonl`](catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.jsonl)：结构化的逐鱼资源对应。
- [`catalogs/fishing-master-xiaomi-20260814/fish-catalog.html`](catalogs/fishing-master-xiaomi-20260814/fish-catalog.html)：初次 APK 调查的历史鱼名清单，可用性描述只代表当时的包内调查。
- [`catalogs/fishing-master-xiaomi-20260814/fish-catalog.csv`](catalogs/fishing-master-xiaomi-20260814/fish-catalog.csv)：初始中文检索提示、英文资源名、变体和来源路径，保留原始整理字节。
- [`catalogs/fishing-master-xiaomi-20260814/entries.jsonl`](catalogs/fishing-master-xiaomi-20260814/entries.jsonl)：可直接检索和复用的结构化目录。
- [`catalogs/fishing-master-cdn-cnformal1-20261102/resource-bundles.jsonl`](catalogs/fishing-master-cdn-cnformal1-20261102/resource-bundles.jsonl)：官方 CDN 清单中的 734 条 `b_fish_` 资源包记录，包含变体、非鱼动物和道具，不能当作鱼种数。
- [`references/fishing-master-cdn-rainbowtrout-rest-mesh.json`](references/fishing-master-cdn-rainbowtrout-rest-mesh.json)：已成功补下载并读取的虹鳟模型样本。
- [`evidence/fishing-master-cdn-cnformal1-20261102/method.md`](evidence/fishing-master-cdn-cnformal1-20261102/method.md)：远程资源的发现、下载与核验方法。
- [`evidence/fishing-master-cdn-cnformal1-20261102/rig-animation-report.json`](evidence/fishing-master-cdn-cnformal1-20261102/rig-animation-report.json)：UV、实际顶点权重、骨骼绑定、动画状态与片段的后续核查，含鲫鱼实例。
- [`evidence/fishing-master-xiaomi-20260814/aquarium-motion-report.json`](evidence/fishing-master-xiaomi-20260814/aquarium-motion-report.json)：水族箱官方功能证据，以及 AquariumController、FishFlock 鱼群、路径、速度、范围、分离/碰撞/逃离接口的定位结果。

- [`evidence/fishing-master-xiaomi-20260814/motion-reconstruction/README.md`](evidence/fishing-master-xiaomi-20260814/motion-reconstruction/README.md)：**水族箱鱼群算法还原与采用建议**；巡游、聚群、转向、点预测避障、优先级逃离，含可读公式、逐函数地址及395组原生执行对照。

## 存放规则

| 目录 | 内容 | 版本管理 |
|---|---|---|
| `sources/<来源ID>/source.json` | 来源、作者/发行者、版本、URL、时间及未知事项 | 普通 Git 文本 |
| `catalogs/<来源ID>/` | 名称、索引引用、中文检索提示和派生浏览表 | 普通 Git 文本 |
| `references/` | 实际模型/扫描/照片的用途、部位对应与验证事实 | 普通 Git 文本 |
| `measurements/` | 有来源哈希、长度口径及测位定义的测量记录；取得数据后才建立 | 普通 Git 文本 |
| `artifacts/` | APK、资源包、模型、图片、视频、PDF等保留的原始输入和唯一证据 | Git LFS |
| `evidence/<来源ID>/` | 调查报告、提取记录、原始文本索引与迁移映射 | 普通 Git 文本 |
| `schemas/` | 来源、参考物与测量记录的数据约定 | 普通 Git 文本 |

所有库内文件引用相对于本目录，使用 `/` 分隔。来源 ID 标识一次明确的资料版本；不同版本另建来源，不覆盖旧文件。稳定逻辑记录 ID 不冒充生物学物种 ID。原始文件保留实际字节并记录 SHA256，推导文件绑定输入哈希与处理方法。`catalogs` 中的 CSV/HTML 是浏览材料；索引事实及来源路径以 `entries.jsonl` 和对应证据为准。

## 使用边界

2026-11-02用户补充：后续建模优先使用本地库，可替代重复联网搜索，作为参数与方法选择的稳定参考。先核对实际文件、来源、物种/部位和适用范围；库内不足、冲突或无法判断的部位再外查。完整规则见[生产SOP第0.5节](../skills/fish-volume-production/references/production-sop.md#05-本地鱼资料库与建模方法选择2026-11-02用户补充)。不要求照着对应模型建模；拓扑、UV、骨架及制作路线按当前项目独立选择。模型中可观察的结构或实现可供参考，未核实的作者制作过程不作已知方法。

1. 区分生物实测、实物扫描、照片推断、游戏美术模型和用户已定稿参考。外部游戏模型默认只是造型参考，不能写成目标物种的实测或用户接受。
2. 目录有名称、资源包可获得、网格可读、物种核准和形态可用是不同证据。仅出现文件名不能证明模型完整；同名前缀资源包也可能只有材质或贴图。
3. 别名、泛称、稀有/精英/怪物皮肤、L 编号与不同生物物种分别处理。未核对时保留原英文名、中文提示与未知，不用目录数量宣称物种数量。
4. 测宽先定义 TL/SL/吻端到尾鳍基等长度口径，排除鳍，检查静息姿态、骨骼和节点缩放；先比 `Wmax/L` 和最宽位置，再比贯穿头身的 `W(t)/Wmax`。口宽、眼前宽、鳃盖宽须分别定位；不能用包围盒代替身体截面。
5. 同种优先；同种资料不足可使用体型接近的同属/同科资料或已审模型，但须记录参考物种、文件 SHA、对应部位、长度归一化和未知。用户指定的已定稿样板优先。
6. 研究资料入库不自动改变任何游戏资产。实际制作仍执行本仓库鱼类生产 SOP、嘴优先、完整鳍、身体、动作、预算及冷导出验证。
7. 保留来源许可、权利人及已知使用范围；未知就记录未知。外部游戏资源入库仅按本次造型研究用途记录，不默认取得再分发或生产资产使用许可。

## 新资料入库

为来源建立 `source.json`，登记版本和来源链接；原始文件放入 `artifacts/<来源ID>/`，在 `assets-manifest.json` 中登记实际大小和 SHA256。游戏内名称未映射到真实物种前，保持 `scientific_name: null`。将实物/模型参考写入 `references/`，只有取得可复核测量后才按 `schemas/measurement.schema.json` 添加测量记录。

### 首轮制作参考试用：尼罗罗非鱼

已用正式R11低模与库内 `NileTilapia` 做本地检索、原包变换核对、身体/鳍/眼分区、贴图与灰模多视、有限三角截面对照。[试用报告与图片](../../output/fish-database-nile-trial-20261102/report.html)保留原模型SHA、工程长度口径及限制；[静态身体宽度记录](measurements/niletilapia-game-model-body-width-bind-20261102.json)可供后续查阅。参考的身体组另含两只108面眼球，量体厚时已排除；它的头吻更宽圆、身体更厚，但不因此判定已定稿模型错误或自动改形。库内物种身份、生物精度与实时动作仍未核准。

`manifest.json`、`handoff.md` 和 `validation-report.json` 记录本轮入库状态与限制。重复或未采用的实验文件在 `work/` 下处理；核对保留证据及引用后清理，不把下载缓存永久纳入资料库。

`artifacts/**` 由根目录 `.gitattributes` 统一交给 LFS；JSON、JSONL、CSV、HTML、Markdown 等索引与说明保留普通 Git 文本。LFS 的使用不代替来源、完整性或形态核验。

当前《欢乐钓鱼大师》APK 已完整下载并通过全部 ZIP 条目校验；325 个基础鱼名来自其预制体索引，尚未逐一核准真实物种。官方 cnformal1 快照已补齐这些名称的 646 条预制体及变体和完整声明依赖：661 个包约 823 MB，均通过大小与 MD5 校验；593 个网格对象读取成功，按导出字节去重保留 588 个 OBJ，1858 个引用贴图对象全部解码成功。644 条预制体的蒙皮骨骼引用可解析，另 2 条使用没有蒙皮骨骼绑定的 MeshRenderer；未进行实际动作播放审核。

后续核查确认 593 个网格均有 UV0，591 个含蒙皮权重的网格可独立解出规范化权重和有效骨骼索引，另 2 个没有蒙皮权重。目标预制体引用的 605 个动画控制器及其片段引用均可解析。当前 OBJ 保留几何、UV 和法线，骨骼/权重/动画仍在原始资源包中；尚未导出可直接播放动画的完整 GLB，实际动作触发与骨骼/速度联动尚未追完；程序级核心运动另见下方还原报告。

水族箱已获官方公告与 APK 内模块的双重确认。后续已从本版 APK 的 ARM64 原生代码还原 FishFlock 核心运动，定位15个类型/70个方法，并与原始指令做330组内核及65组完整求解对照，全部通过。路径/群中心、聚群/同向/分离、指数转向、点预测箱/球避障和优先级逃离已入库，附我们现有鱼群实验的采用建议；保留实现缺陷和证据。Lua业务编排、线上逐鱼配置、线程时序、骨骼与实际运动联动和实机效果仍未知，不把合成执行验证当作实机或规模基准。

服务器样本日期早于该 APK，来源分开保存，不声称版本相同或是最新在线资源全集。完整取得的是上述 325 个基础鱼名的索引范围；远程清单中其他道具、非鱼动物和无关资源未一并下载。《钓鱼发烧友》目前只有官方产品来源记录，APK、完整鱼种表和模型仍未取得。当前新增一条经过身体/鳍/眼划分及工程长度归一化的尼罗罗非鱼静态游戏模型宽度记录，不是生物实测，也不代表其余模型已量测。

2026-11-03另补[双髻鲨头翼截面证据](evidence/hammerhead-local-sections-20261103/sections.json)：原包默认姿态、等比变换及55/70/85%半展截站的实际有限厚度。具体种仍未核准，只作科级游戏造型参考；未建立该鱼完整去鳍身体宽度曲线，也不套用身体宽度measurement schema。首轮实际应用、原画轮廓保留与眼部负例见路氏双髻鲨原实验HANDOFF。

同日用户指出首轮只审外翼峰值漏掉内侧：现补[完整双髻鲨头部截面](evidence/hammerhead-local-sections-20261103/full-head-sections.json)，左右各23横向×17前后测位。中央后界为宽头后颈宽最小处的工程分界（吻后0.108整长），外翼取有限切片真实相连前段；明确不是生物标志。默认张口中央腹侧不得直接当近闭嘴目标，极外端有限拓扑误差要另报；初轮R4已因内侧过厚被用户拒绝，库中入档不等于形态接受。

2026-11-03头/体参考范围补记：HammerheadShark具体种仍未核准（用户疑似大双髻鲨）；用户允许其大致头型/比例及平顺内侧连接继续作近缘造型参考，路氏躯干体高另查同种。头翼展须先排除两个独立64面眼体，最窄颈对应仅为工程指标。实际R11来源/归一/部位/未知见该reference新增head_reference_scope_20261103；不把幼鱼体高或科级库躯干当250cm路氏成体标准，也不转移外观接受。

2026-11-04补[双髻鲨逐鳍截面](evidence/hammerhead-fin-sections-20261104/sections.json)及实际网格测位定义/线框图：按各鳍局部根梢坐标测有限弦法向厚度与`t/c`，明确左右配对、四个展向测位和腹鳍近根与身体重叠的无效站；库具体种及生物厚度未知，仅供独立游戏造型参考，不是组织实测或外观接受。

2026-11-05 [鲸鲨外部资料](evidence/whale-shark-20261105/sources.json)：iNaturalist 实拍、DigitalLife 个体 Mosi 的多相机重建（官方 GLB 已入库，逐索引核实 157312 个三角面）及已下载的一份独立艺术 GLB。区分真实个体与艺术模型。
