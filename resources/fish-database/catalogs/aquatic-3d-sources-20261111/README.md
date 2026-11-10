# 鱼类与水生动物3D扫描／真实模型：远程资料入口

核查日期：2026-11-11。用途是以后在本地先找到来源，再按具体需要访问远程数据库。本轮只登记网页、目录元数据、数量口径、资料类型和许可条件，**未批量下载模型、贴图、扫描切片或视频**，也未修改游戏资产。

结构化入口是 [platforms.jsonl](platforms.jsonl)，逐平台来源记录在本库 `sources/` 并由 [manifest.json](../../manifest.json) 登记。另保留 FFishAsia [3,055条公开模型元数据](ffish-models.jsonl)和 Digital Life [168条元数据](life-models.jsonl)，总计3,223个远程ID；包含非鱼动物、植物和同种多个版本，不是3,223种鱼。只存标题、学名标签、关键词、许可标签和访问地址等文本。

## 先选什么来源

这里的A/B/C是本地资料路由分类，不是平台官方评级，也不代表全库精度排序：

- **A：整体彩色标本／表面扫描优先。** FFishAsia、FishSim；适合找体形、头宽、鱼鳍位置、颜色及外表面参考。
- **B：CT／解剖优先。** MorphoSource/oVert、ScanAllFish；适合查骨骼、上下颌和内部结构。骨骼或灰度切片不能代替皮肤外形、颜色及活体体厚的核实。
- **C：真实个体资料基础上的人工重建。** Digital Life；适合找较完整的动物形态与部分动画。逐条区分实拍重建、扫描参考和作者补全，不把重建结果直接称为生物实测。

证据级别另记：E0是官方网站/政策/数据页说明，E1是取得并核对公开目录元数据；E2才是实际文件和标本来源核实，E3是有测位、单位及输入哈希的可复核测量。本轮没有把任何新条目提升为E2/E3。平台混合多种内容，实际采用时仍须逐条判断。

| 来源 | 主页与数据库 | 已核实的规模口径 | 能找什么 | 商用与改造条件 |
|---|---|---|---|---|
| FFishAsia / floraZia，A/E1 | [模型目录](https://sketchfab.com/ffishAsia-and-floraZia/models)、[标本数据库](https://ffish.asia/)、[公开目录API](https://api.sketchfab.com/v3/models?user=ffishAsia-and-floraZia&sort_by=-publishedAt) | 主页摘要3,050，API逐页3,055个唯一ID，差异未核实；鱼类747条、333个二名学名标签；643条可下载鱼类标CC0，308个二名标签 | 鱼、龟、章鱼、鱿鱼/墨鱼、蟹、虾、海星等；全目录还含植物和昆虫 | 按条目。CC0可商业修改；CC BY需署名及说明修改；含NC、仅学术或保留全部权利的条目不作为直接商用候选。SA另有同许可义务 |
| MorphoSource / oVert，B/E0 | [MorphoSource](https://www.morphosource.org/)、[佛罗里达博物馆鱼类入口](https://www.floridamuseum.ufl.edu/fish/digitized-specimens/)、[oVert](https://www.floridamuseum.ufl.edu/overt/) | 全平台当前鱼种/模型总数未核实。UF官方报告约3,400次鱼扫描、1,400多种；不是全平台当前可下载数量 | 鱼类CT、头骨、上下颌、骨骼、海龟等；鱿鱼/章鱼/水母合适条目本轮未核实 | 同时检查版权许可、Permits commercial use、下载协议及附加协议。UF资料商业使用及衍生物需书面批准/商业合同 |
| ScanAllFish / ScanAllFishes，B/E1 | [项目主页](https://www.adamsummers.org/scanallfish)、[OSF数据库](https://osf.io/ecmz4/)、[鱼类索引](https://osf.io/ecmz4/wiki/Fishes/) | 2017年官方报告已扫描2,500多种；当前公开可下载总数未知。本轮OSF198个直接子目录不能当作198种 | 普通鱼、鲨鱼、双髻鲨、鳐鱼等CT与部分STL | 主页有面向任何用途开放的说明；OSF主节点未列具体许可，wiki有科研教育说明，未取得全库商业衍生授权结论。查具体文件条款或权利人明确说明 |
| Digital Life，C/E1 | [项目与政策](https://digitallife3d.org/3d-model)、[模型目录](https://sketchfab.com/DigitalLife3D/models)、[公开目录API](https://api.sketchfab.com/v3/models?user=DigitalLife3D&sort_by=-publishedAt) | 168个模型；鱼类41条，按名称合并约22种；海龟约6种，鲸豚类约7种。名称组不是分类审核结果 | 鲨鱼、蝠鲼、鲟鱼、鲈鱼、海龟、鲸豚、螳螂虾、深海等足类、巨型住囊虫 | 161条CC BY-NC、3条CC BY、4条许可未列；官网默认非营利使用，商业用途联系项目/大学/合作方。平背海龟53A、53B是CC BY例外，按具体条目核对 |
| FishSim V2，A/E0 | [DOI](https://doi.org/10.18710/OY9QWA)、[DataverseNO数据页](https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/OY9QWA) | 160条整鱼研究数据，154个带纹理外表面模型，约5种白肉鱼；不是154种。V2发布2026-09-10，README更新2026-09-16 | 大西洋鳕、黑线鳕、pollock、tusk、ling，外表面/尺寸及摩擦弹性数据 | 数据页CC0，可商业修改，学术规范建议引用数据集。未下载约1.5GB包；Batsfjord批次需按逐标本长度重定标 |

统计来源：[FFishAsia官方方法介绍](https://www.kyushu-u.ac.jp/en/researches/view/240/)、[UF扫描规模](https://www.floridamuseum.ufl.edu/exhibits/online/inner-beauty/)、[FHL 2017官方报告第1页](https://fhl.uw.edu/wp-content/uploads/sites/17/2017/12/IntTidings2017_final.pdf)。FFishAsia/Digital Life的目录统计方法、输入哈希与限制见[核查报告](../../evidence/aquatic-3d-sources-20261111/validation-report.json)。旧报告的年份不因本轮访问而更新。

## 龟、水母、鱿鱼、章鱼去哪里找

| 类别 | FFishAsia已核实覆盖 | Digital Life已核实覆盖 |
|---|---|---|
| 龟类／乌龟／海龟 | 约5个二名学名标签，另有杂交个体；海龟本轮核到蠵龟Caretta caretta，其余包括日本石龟、草龟、红耳龟、中华鳖。约18条CC0元数据，含杂交版本 | 海龟约6种：蠵龟、玳瑁、绿海龟、肯氏龟、平背海龟、棱皮龟，另有淡水彩龟；多数NC |
| 章鱼／八爪鱼 | 普通章鱼Octopus vulgaris、短蛸O. ocellatus、长蛸O. minor、北太平洋巨型章鱼Enteroctopus dofleini，共4个学名标签/7条，均标CC0 | 本次目录未找到 |
| 鱿鱼／乌贼／墨鱼 | 剑尖枪乌贼Uroteuthis edulis、日本飞乌贼Todarodes pacificus、莱氏拟乌贼Sepioteuthis lessoniana、耳乌贼Euprymna morsei、金乌贼Sepia esculenta、拟目乌贼Sepia lycidas；6个标签/9条，其中7条CC0 | 本次目录未找到 |
| 水母／jellyfish | 本次目录名称/分类标签未找到；日语キクラゲ是木耳，不能算水母 | 本次目录未找到；巨型住囊虫不是水母 |
| 其他水生动物 | 蟹类约78个学名标签、虾类约6个、海星约3个；海水/淡水混合，不能全部叫海洋物种 | 鲸、海豚、鼠海豚、螳螂虾、深海Booralana等足类、Bathochordaeus住囊虫等 |

入口实例：[FFishAsia鲤鱼](https://sketchfab.com/3d-models/c93d3091110a4ae2aed67a2063e84b03)、[蠵龟](https://sketchfab.com/3d-models/162c2c1391424d91b6c770614bd8f7ff)、[长蛸](https://sketchfab.com/3d-models/acf183a0a0214b58b86b6ad2eeb2eefb)、[剑尖枪乌贼](https://sketchfab.com/3d-models/ff42bc83f0ac4a459199ed15e83975d2)、[Digital Life平背海龟53A](https://sketchfab.com/3d-models/442372b7f02b4730882d41d959726156)。本轮没有下载、开模或视觉审核这些新条目的网格。

## 在本地检索

在Foundry根目录执行，命令只读本地JSONL，不联网、不触发模型下载：

```powershell
.\.venv\Scripts\python.exe resources/scripts/fish-database/search_remote.py "章鱼" --kind model --license cc0 --json
.\.venv\Scripts\python.exe resources/scripts/fish-database/search_remote.py "海龟" --kind model --json
.\.venv\Scripts\python.exe resources/scripts/fish-database/search_remote.py "Cyprinus carpio" --kind model --json
.\.venv\Scripts\python.exe resources/scripts/fish-database/search_remote.py "CT" --kind source --json
.\.venv\Scripts\python.exe resources/scripts/fish-database/search_remote.py --kind source --json
rg -n "水母|仅学术|商业合同" resources/fish-database/catalogs/aquatic-3d-sources-20261111/platforms.jsonl
```

可加 `--source ffishasia` 或 `--source digitallife3d`；`--limit`只限制返回数量，`matched_count`仍给出全部匹配数。`--license cc0`筛选的是目录许可标签，不代替实际下载时的权利核对。中文关键词用于发现线索，学名标签及中文别名均未升级为物种身份核准。

水母等未找到类别记在平台记录的 `known_gaps`/说明中。搜索工具不把否定覆盖说明当作“有该动物”的正向命中；查询水母资料缺口请看本表或用上面的 `rg`。未找到不证明远程永远没有，也不外推到其他作者或整个平台。

## 作为真实数据参考后自己建模

1. 观察真实标本的体形、头宽、鳍位、骨骼关系，取得少量客观比例，再独立设计几何、UV、贴图、骨架和动作，通常属于事实参考及独立创作。客观事实不会仅因资料标了NC就自动成为作者专属表达。[CC关于事实与数据库的说明](https://creativecommons.org/faq/#which-components-of-databases-are-protected-by-copyright)
2. 沿原模型表面吸附/重拓扑、提取密集截面重建外壳、投射或烘焙原贴图/法线，仍涉及原资产/数据的复用，不能仅凭“网格重新建过”称为不受原授权约束。复制艺术家自行补全的造型或纹样也要区分独创表达。
3. 版权许可之外，下载时接受的科研限定、数据使用合同、适用地区数据库权利等仍须分别核对。UF政策明确涉及测量及衍生物，并要求商业使用书面批准；不能把“只作参考”当作对所有合同的统一豁免。[UF政策](https://www.floridamuseum.ufl.edu/digital-lab/digital-data-policies/morphosource-digital-data-policy/)、[MorphoSource协议](https://duke.atlassian.net/wiki/spaces/MD/pages/35422351/Standard%2BUse%2BAgreement)
4. CC0可复制、修改和商业使用；CC BY要求署名、许可链接和修改说明；SA还涉及同许可；NC不允许受许可约束的商业复用；未知/仅学术/保留全部权利不能直接当商用素材。[CC0](https://creativecommons.org/publicdomain/zero/1.0/)、[CC BY](https://creativecommons.org/licenses/by/4.0/)、[CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/)、[CC BY-NC](https://creativecommons.org/licenses/by-nc/4.0/)
5. 对本项目优先找明确CC0的真实标本资料，结合同种照片/论文独立制作；保存来源URL、标本号、许可版本、发育阶段、姿态、测位/单位和实际使用方式。艺术重建、幼体及保存变形的标本不能直接当成年活体标准；后续取得实际文件再登记SHA并逐部位审核。

本记录是检索和采用前核对依据，不是对所有条目、地区及使用方式的统一法律许可，也不是鱼类生产SOP/用户形态验收。

## 更新与保留范围

公开目录经Sketchfab Data API v3的只读列表取得，按 `sort_by=-publishedAt` 稳定分页，按UID去重；没有调用模型下载接口。保留精简字段，不保留完整作者描述、缩略图或下载档案。学名按分类行/名称规则提取，二名标签归并不代表已做异名审核；sp./cf.等未定种不能强塞为确定物种。Digital Life约22种鱼是名称组人工合并，不用仅有的二名标签数量代替。

统计是2026-11-11快照，入口、许可和数量可能变化。更新时另建日期版本并登记manifest；只有核对了实际文件、来源与条款才能更新采用结论。临时完整目录元数据和一次性写入/检查脚本在精简目录及报告核对后删除，未生成任何新模型或大媒体缓存。
