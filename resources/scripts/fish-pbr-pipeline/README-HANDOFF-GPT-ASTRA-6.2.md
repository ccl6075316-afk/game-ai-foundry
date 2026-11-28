# 通用单材质 PBR 鱼类升级流水线与正式装载验收 SOP — 外部 Agent（GPT Astra 6.2）手册（v4）

> **顶层架构目标**：服务「珠海长隆级大型海底世界（**300+ 鱼种常驻、50,000 条鱼同屏压测上限**）」——通过 **“单网格单材质（`Draw Call = 1`）+ 轻量共享 PBR 图集（`2–4 MB` BC7/种）+ 前排 LOD0 真骨骼精雕 + 中远景 GPU `MultiMesh` LOD1/2/3”**，同时做到**贴脸特写映画级细节**与**5 万条鱼浪 60 FPS**。
>
> **已达标基准（硬骨鱼 + 软骨鱼两大主赛道均已跑通 1 号样板！）**：
> - **硬骨鱼样板**：
>   - **真鲷（`red_seabream`）**：已正式安装入库（`2,810` 面、`1` Draw Call、`3.85 MB` GLB、`16.0 MB` 未压缩 / `4.0 MB` BC7 显存）。
>   - **黑鲷（`black_seabream` R2）**：已完成本地正式装载与 5 项实机验收（`2,852` 面、`1` Draw Call、`1.44 MB` GLB、`8.0 MB` 未压缩 / `2.0 MB` BC7 显存）。
>   - **海鲈（`sea_bass` R2）**：已完成本地正式装载与 5 项实机验收（`2,858` 面、`2,042` GPU 顶点、`1` Draw Call、`1.43 MB` GLB、`8.0 MB` 未压缩 / `2.0 MB` BC7 显存）。
> - **软骨鱼（鲨鱼）1 号样板**：
>   - **黑鳍礁鲨（`blacktip_reef_shark` R2）**：已通过用户图审与全部 9 项技术/水下门禁，**可正式装载并放开推进其余鲨鱼**（`5,878` 面、`1` Draw Call、`1.45 MB` GLB、`3 × 1024×1024` 1:1 `OPAQUE` 方图、`0 px` 眼廓外扩、22 骨捕食 32° 零偏差；独立完整标准见 **[鲨鱼类单材质 PBR SOP v1.0](README-SHARK-PBR-SOP-v1.md)**）。

---

## 一、现行达标规则与硬性技术合同（2026-11-28 · 5 万条鱼同屏标准）

所有正式预算已代码固化在 `cli/fish_budget.py`（按 **展示体长档 × 形态复杂度 `anatomical_group`** 取高值）及 `resources/skills/fish-volume-production/references/display-length-budget.md`。**如果是从零制作全新物种（而非升级已有 28 条旧鱼），请直接改读主 SOP：`resources/skills/fish-volume-production/references/new-fish-pbr-sop-v2.md`。**

### 1.1 LOD0 面数放开档位（体长 × 形态复杂度）与 5 万条鱼 LOD 分层目标

**核心原则**：5 万条鱼同屏由 GPU `MultiMesh` 的 LOD1/2/3 保底（总面数稳在 ~400 万面以内），**源模型 LOD0 绝不再为了抠几百面去毁坏眼球、鳃盖、嘴唇、鳍根或俯视/多肢体生物的立体轮廓**！优选不是下限，已有少面合格模型不为凑数加面。

| 形态分类（`anatomical_group`） | 起步 LOD0 优选 / 硬上限 | 大体型升档（>300cm / >600cm） | 运行时自动 LOD1 / LOD2 / LOD3 目标 | 典型物种 |
|---|---:|---|---|---|
| **`standard_lateral`**（常规侧扁鱼） | **4,000 / 5,000**（≤120cm）<br>**6,500 / 8,000**（120–300cm） | `8,500 / 10,000`；`12,000 / 15,000` | `400–600` / `120–160` / **`32–64`** | 鲷、鲈、鲤、鳟、沙丁鱼、金枪鱼、旗鱼、带鱼等 |
| **`shark`**（鲨鱼 / 软骨鱼） | **6,500 / 8,000** | `8,500 / 10,000`；`12,000 / 15,000` | `800–1,200` / `250–350` / `64–96` | 黑鳍礁鲨、各双髻鲨、鲸鲨（8 m 适用 `12,000 / 15,000`） |
| **`dorsal_complex`**（俯视主导 / 宽翼 / 龟甲 / 繁鳍） | **6,500 / 8,000** | `8,500 / 10,000`；`12,000 / 15,000` | `1,000–1,600` / `300–500` / `96–140` | 海龟（蠵龟）、鳐鱼、蝠鲼、比目鱼、狮子鱼、海马 |
| **`multi_limb`**（多触手 / 多步足软体与甲壳） | **8,500 / 10,000**（不受小体长限制） | >600cm 升 `12,000 / 15,000` | `1,500–2,400` / `500–800` / `150–220` | 章鱼、鱿鱼、乌贼、水母、龙虾、螃蟹 |

> **A 类常规硬骨鱼批量推进队列（每批 3–4 条并联）**：
> - 第 1 批（全在 `width20261101`）：`red_emperor`、`rainbow_trout`、`brown_trout`、`atlantic_salmon`
> - 第 2 批（全在 `width20261101`）：`crucian`、`grass_carp`、`bluegill`、`nile_tilapia`
> - 第 3 批（含特殊附件重点盯）：`carp`（4口须）、`piranha`（4细牙）、`peacock_bass`（实体上颌褶）、`zander`

### 1.2 死守不松口的 5 条性能与渲染硬门禁

| 指标 | 硬门禁标准 | 说明 |
|---|---|---|
| **网格 / 材质数** | **`1` Mesh / `1` Surface（`Draw Call = 1`）** | 严禁拆成 2–4 个材质槽，确保 5 万条鱼 `MultiMesh` 单批次合批 |
| **透明与深度模式** | **硬骨薄鳍鱼**：`alphaMode: MASK`，`alphaCutoff: 0.5`，`doubleSided: true`<br>**鲨鱼（厚肉质不透明鳍）**：`alphaMode: OPAQUE`（严禁切 `BLEND`） | 保留硬件深度写入，杜绝斜角“后鳍挡前鳍” |
| **PBR 贴图组合与显存** | **3 张图**：`Albedo` + `Normal`（切线空间）+ `ORM`（R=AO, G=Roughness, B=Metallic）<br>• 中小鱼：`1024×512`（未压缩 `8 MB` / BC7 **`2 MB`**）<br>• 大型硬骨鱼：`2048×1024` Albedo + `1024×512` Normal/ORM（未压缩 `16 MB` / BC7 **`4 MB`**）<br>• 鲨鱼类：**`1:1` 方图**（`1024×1024` 未压缩 `12 MB` / BC7 **`3 MB`**；8 m 鲸鲨可给 `2048×2048` 仅 1 份） | 全精度（2×）重烘并做最近岛 Padding 后再 2×2 盒滤波降采样 + 切线法线重归一化；LOD0/1/2/3 全部共享同一套贴图（零额外显存） |
| **水下着色器 UV 合同** | `FishUnderwaterLit.gdshader` 对 **2:1 图集** 自动启用 `has_split_atlas_uv`：<br>• 左半 `UV.x < 0.5` = 鱼身 / 眼 / 口腔（鳞片丝缎反光）<br>• 右半 `UV.x >= 0.5` = 薄鳍（自动触发 `fin_sss` 薄鳍透射）<br>• 眼部高光角：Godot `UV.x < 0.09 && UV.y > 0.82`（Blender 左下角 `u < 0.09, v < 0.18`）且 `ORM.G < 0.36` 自动触发湿润角膜高光 | **鲨鱼强制走 `1:1` 方图 + `OPAQUE`**，自动关闭 `has_split_atlas_uv` 与薄鳍透射，防止厚肉质鲨鱼鳍在水下被照成透明薄膜 |
| **骨架 / 动作 / 锚点 / 冷导** | 保留全部原骨骼、骨序、逆绑定矩阵、原动画通道及形态键（鲸鲨）；下颌张合满幅；上唇挂钩点误差 `< 2 mm`；独立重开 Blender 冷导 GLB 与候选 GLB **SHA-256 逐字节一致** | 通过 `verify_fish_pbr_gate.gd --dump-mouth-recipe` 自动导出精确 UNORM16 配方 |

---

## 二、黑鲷 + 海鲈 + 公子小丑鱼实测沉淀的 8 条近景、本地基准与游动制作铁律（避免任何返工！）

每一条都是真实踩坑验证出来的硬经验，后续每条鱼升级与新鱼制作必须默认全部执行：

1. **严禁靠骨权“猜”鳍面——优先读取源 `.blend` 的 `foundry_logical_part_id`**
   - 正式源 `.blend` 普遍带 `mesh['foundry_geometry_parts_json']` 与面属性 `foundry_logical_part_id`。黑鲷 R1 靠骨权漏掉 208 个胸鳍根面导致发黑锯齿；改为逐面按部位标记保留全部原身体/口腔/鱼鳍后彻底根除。
2. **严禁对 3D 眼球做粗暴减面，必须高段数圆弧 + 解析法线 + 去假高光**
   - 双眼使用每圈 **32–48 段**顺滑圆弧，按实际侧头曲面拟合眼窝底面并赋予**解析平滑法线**，眼周做肤色柔和过渡；参考海鲈 R2，**主动抹淡原画瞳孔里写死的静态白灯斑**，让高光交由水下真灯光实时生成。
3. **严禁按固定竖线 `x = const` 拆头/身 UV 岛劈开鳃盖，并排查原源近距双断面法线打架**（海鲈 R1→R2 新铁律！）
   - 海鲈 R1 为了给头部提密度，按竖线 `x = 0.229` 硬拆了 `head` 和 `flank` 两个 UV 岛，导致弧形鳃盖被劈出一条笔直竖缝；同时发现原源在鳃盖处存在两圈相隔 `0.00022`、法线打架的旧断面。
   - **正确做法**：侧面优先排成**连续单岛（共享边 UV 差 = 0）**，用平滑单调拉伸兼顾头部与体侧密度（若非拆不可，接缝必须严格藏在弧形鳃裂缝内部）；烘焙前先检查白模在鳃盖/胸鳍前缘是否有极近双断面法线跳变并顺平。
4. **高频微鳞浮雕必须加“解剖保护遮罩”，严禁扫到嘴周/眼下/鳍根/口腔**
   - 体侧鳞区从原画亮度提取局部微对比叠进 Albedo、Normal 与 Roughness；
   - **上下唇缘、下巴底缘、吻尖、眼眶正下方脸颊、各鳍根部、口腔内壁**必须用 smoothstep 遮罩完全排除高频锐化，杜绝麻点与锯齿唇。
5. **新 UV 重烘必做“EDT 最近岛边缘 Padding + 跨岛边界梯度抑制”**
   - 逐像素栅格化后先用 `distance_transform_edt` 填充岛外空白；求法线梯度前用 3D 位置跳变 + 部位跳变检测接缝像素并对邻域衰减归零，杜绝任何 UV 岛边界亮暗线。
6. **必须用真实水下展缸（`current_exhibit.tscn`）量化复核暗侧鳞片层次，不能只看灰底棚拍**
   - 必须把候选置入真实 `res://scenes/current_exhibit.tscn`（`浅礁日光` 或 `黑潮深海`），核对 `FishUnderwaterOptics` 绑定 `normal_and_orm = true`、`split_atlas` 正确，并确保**水下暗侧的侧腹鳞片起伏与银光质感清晰可读**（参考海鲈 R2：暗侧去低频后的亮度标准差由 `6.10` 提升至 `7.09`）。
7. **模型与「灵动游动状态」必须一次到位同步升级（硬性新要求 · 2026-11-28）**
   - 用户明确指示：**后续升级每条鱼时，不再只改静态模型/材质，必须同步修复并升级该鱼的游动状态**！
   - 开工前必须精读 **[灵动鱼类游动运动学标准（lively-swim-kinematics-standard.md）](../../skills/fish-volume-production/references/lively-swim-kinematics-standard.md)**，严格按物种归属的 **5 大运动类群**（Labriform 礁区划水 / Subcarangiform 通用巡游 / Thunniform 高速远洋 / Anguilliform 长体波浪 / Carangiform-Shark 刚性水翼鲨鱼）一次做到位：
     1. **重编 `fish.blend` / `.glb` 原生 `Swim` 循环动画**：头部稳像 + 尾向递增行波脊柱 S-Wave + **胸鳍 2 轴正交划水与 90° 转桨（`sweep + feather`，左右异步；鲨鱼保持刚性水翼绝不拍翅！）** + 背/臀/腹鳍相位滞后随动 + `1.5°–2.5°` 柔和静息呼吸（仅旋转通道、首尾帧无缝闭合）；
     2. **同步在候选审查与正式安装 Step 2 调优 `motion/*.json` 灵动参数**：告别旧版偏僵的 `paired_fin_radians: 0.18 / median_fin_radians: 0.065`，按类群查表提升至实证灵动值，同时保持 `fin_motion_constraints.minimum_radians >= 0.12`（杜绝胸鳍穿腹）与 `FoundryFishMotion.gd` 包络/480帧验证 100% 通过！
     3. 若修改了 `motion/*.json`，须在 `manifest.json` 同步更新 `motion_sha256` 并重跑完整 5 项实机验收。
8. **严禁抛弃本地 3D 模型数据与已验收口腔/外廓基准（新鱼与存量返修同适用）**
   - 既有 28 鱼升级必须直接沿用正式源 `.blend` 已验收的形体、中空口腔与上下颌权重，只提质感、眼部、单材质合批与灵动游动，**严禁推倒重搓低质简模**；
   - 全新物种制作必须先加载 `resources/fish-database/` 内 325+ 种本地 3D `.obj` 参考模型并对照已验收同类正式 `.blend`（如 `bluegill`/`black_seabream`/`blacktip_reef_shark`）校准头吻、嘴型与截面饱满度，切嘴绝不撑大原头廓、闭口前缘均匀无正中缺口、侧扁鱼纯侧投无缝铺满禁上下分层（完整细则见 **[new-fish-pbr-sop-v2.md](../../skills/fish-volume-production/references/new-fish-pbr-sop-v2.md)** v2.1）。

---

## 三、全库 28 条鱼的材质分类（含非鳞鱼与鲨鱼）

| 类别 | 物种（共 28 种） | 改造策略 |
|---|---|---|
| **A. 典型硬骨鳞片鱼（15 种）** | 真鲷✅、黑鲷✅(本地已装)、海鲈✅(本地已装)、红皇帝鱼、鲫鱼、鲤鱼、草鱼、蓝鳃、罗非鱼、虹鳟、褐鳟、大西洋鲑、梭鲈、孔雀鲈、红腹食人鱼 | 直接复用黑鲷 R2 / 海鲈 R2 流程（`2:1` 图集 + `MASK 0.5` + 连续单侧 UV + 48 段眼球 + 鳃盖浅起伏）。特例保护：鲤鱼 4 口须、食人鱼 4 细牙、孔雀鲈实体上颌褶。 |
| **B. 特化硬骨鱼（8 种）** | 大黄鱼、鲯鳅(`3 mesh/4 surf`)、蓝鳍金枪鱼(`24 鳍`)、大西洋旗鱼、巨骨舌鱼、银龙鱼、非洲鲇鱼(`无鳞滑皮+长须`)、带鱼(`67 骨+镜面金属+无张嘴`) | 全部可做，但按皮质切 PBR 参数：鲇鱼关闭鳞片法线改湿润黏液皮（`Roughness 0.38–0.52, Metallic 0`）+ 保长须；带鱼拉高金属度（`Metallic 0.25–0.45`）且无张嘴测试；鲯鳅合并 3 mesh 严保骨权与上唇锚点。 |
| **C. 掠食性鲨鱼（4 种 · 软骨鱼）** | **黑鳍礁鲨 R2**✅(图审通过待装，`5878面/1 surf/22骨`)、**大双髻鲨**(`4668面/4 surf/22骨`)、**路氏双髻鲨**(`3994面/2 surf/22骨`)、**无沟双髻鲨**(`3994面/4 surf/22骨`) | **已放开批量推进！** 严格执行独立标准 **[README-SHARK-PBR-SOP-v1.md](README-SHARK-PBR-SOP-v1.md)**（LOD0 预算 `6,500/8,000`，大双髻鲨 4 m 为 `8,500/10,000`，`1:1` 方图 + `OPAQUE` + `0 px` 眼廓外扩）。 |
| **D. 滤食巨兽（1 种 · 软骨鱼）** | **鲸鲨**(`9990面/3 surf/7骨 + 9 吸滤 Shape Keys`) | **已放开按 SOP 推进！** 执行 **[README-SHARK-PBR-SOP-v1.md](README-SHARK-PBR-SOP-v1.md)** 第 3.7 节：LOD0 预算 `12,000/15,000`，**严禁改拓扑与顶点序**（保护全部 9 个吸滤形态键），仅做零拓扑改动的 `OPAQUE` 单材质合并 + `2048×2048` 楯鳞白斑重烘。 |

---

## 四、鲨鱼类（软骨鱼）单材质 PBR 专项规范（完整执行见独立 SOP）

> **权威入口**：黑鳍礁鲨 R2 已跑通完整实证并获用户放行。全部 5 条鲨鱼的台账、Loader 适配、7 条制作铁律（含 `0 px` 眼廓外扩、去假灯斑、移动主光测试、双髻鲨锤头与鲸鲨 9 形态键零拓扑保护）、水下着色器 1 行眼部识别补丁及放开推进队列，均已完整固化在独立手册 **[README-SHARK-PBR-SOP-v1.md](README-SHARK-PBR-SOP-v1.md)**，开工前必须直接精读该文档！

核心摘要（6 条不可违反）：
1. **无鳃盖 → 5 道凹陷鳃裂；无鱼鳞 → 哑光楯鳞皮革感**：皮肤与厚鳍保持 `Roughness 0.62–0.80, Metallic 0.0` + 3D 物理坐标微粒法线（RMS ~1.65°），严禁套用鱼鳞法线或硬骨鱼鳃盖。
2. **眼窝原头皮局部贴合重建 + 零轮廓外扩**：严禁外贴高弧“凸眼帽”；48 段眼缘平滑接回原皮，正交俯视与转向双机位超出原头轮廓均为 **`0 px`**，程序化圆滑瞳孔/虹膜并彻底抹除静态白灯斑（角膜 `ORM.G = 0.20–0.24`）。
3. **厚肉质不透明鳍 → `1:1` 方图（`1024×1024`，鲸鲨 `2048×2048`）+ `alphaMode: OPAQUE`**：确保 `FishUnderwaterOptics` 自动置 `has_split_atlas_uv = false` 与 `is_fin = false`，彻底修掉旧版 `MASK` 鲨鱼水下泛白透光问题。
4. **多材质合批严保 22 骨捕食 / 鲸鲨 9 形态键**：口腔 `Roughness 0.85`、牙齿 `0.35`、角膜 `0.20–0.24`；严禁破坏 22 骨捕食权重、牙齿几何与上唇挂钩点；鲸鲨绝对零拓扑改动。
5. **水下着色器眼部识别补丁**：在正式装载黑鳍礁鲨 R2 时，按 `README-SHARK-PBR-SOP-v1.md` 第 4.1 节给 `FishUnderwaterLit.gdshader` 补 1 行 `!has_split_atlas_uv && !pixel_is_fin && orm.g < 0.28` 分支，让 1:1 鲨鱼角膜也触发水下湿润高光与焦散屏蔽。
6. **正式 Loader 精准分支**：`FinalizedElevenFish20261105.gd`、`FinalizedHammerPair20261106.gd`、`FinalizedScallopedHammerhead.gd` 按 `"pbr_material": true` 精准放行已升级鲨鱼，不得放松未升级物种的旧断言。

---

## 五、候选审查交付物清单（供用户图审拍板）

每条新鱼在工作目录 `work/<species>-pbr-review-<YYYYMMDD>/` 中交付候选（**未获用户图审通过前严禁直接覆盖正式游戏目录**）：
- `fish.blend` + `<species>.glb`（独立冷导 SHA-256 逐字节一致）
- `comparison.jpg`（原版 vs 新版 棚拍整鱼 + 头部近景四宫格）
- `underwater-comparison.jpg` + `underwater/`（真实 `current_exhibit.tscn` 浅礁日光同机位原版 vs 新版 整鱼 + 左右头部近景 + `validation.json`）
- `qa/`（4 视图 `01_swim_3q.png`、`02_turn_top.png`、`03_jaw_closeup.png`、`04_rear_fins_depth.png` + `gate_report.json` + `anchor.json`）
- `open-review.command` + `review.gd`（可旋转交互对比窗口）+ `review.validation.json` + `HANDOFF.md`

---

## 六、正式装载与发布验收 SOP（用户拍板通过后执行！）

> 适用对象：**已通过视觉与水下审查的成品候选**（当前立即可执行：**黑鲷 R2 `black_seabream`**、**海鲈 R2 `sea_bass`**）。严格按以下 6 步逐项落实并输出验收报告，缺一不可：

### Step 1：正式源与模型落位 + 独立冷导逐字节复验
1. 覆盖以下 3 个正式文件：
   - 源工程：`projects/fishing-2d/assets/source/fish/<species>/fish.blend`
   - 运行时模型：`projects/fishing-2d/game/assets/models/fish/<species>.glb`
   - 钓鱼上唇配方：`projects/fishing-2d/game/assets/models/fish/motion/width20261101/<species>-mouth-anchor.json`（或对应批次 manifest 声明路径，确认内部 `model_sha256` 与已安装 GLB 完全一致）
2. **独立冷导校验**：用全新独立 Blender 5.0.1 后台进程读取**已安装的** `projects/fishing-2d/assets/source/fish/<species>/fish.blend`，导出临时 GLB（`export_tangents=True`），验证其 SHA-256 与已安装 `<species>.glb` **逐字节完全相同**。

### Step 2：清单（`manifest.json`）与运行时 Loader 精准绑定
1. **对 `width20261101` 批次（含真鲷、黑鲷、海鲈等 12 条常规硬骨鱼）**：
   - 更新 `projects/fishing-2d/game/assets/models/fish/motion/width20261101/manifest.json` 对应物种条目：
     - `model_sha256` → 新 GLB SHA-256
     - `triangles` → 新导出精确三角数（如黑鲷 `2852`、海鲈 `2858`）
     - `"pbr_material": true`（触发 `FinalizedWidthBatch20261101.gd` 的 PBR 法线/ORM 校验，跳过旧 `TEXTURE_FILTER_NEAREST` 断言）
     - `mouth_recipe.sha256` → 新 `*-mouth-anchor.json` SHA-256
     - 若按铁律 7 同步升级了 `motion/*.json` 的灵动游动参数，须同步刷新对应 `motion_sha256` 并确认 `FoundryFishMotion.gd` 包络与 480 帧全通过；保持 `motion_runtime` 与 `runtime_dependencies` 完整。
2. **对非 `width20261101` 批次（如 `FinalizedElevenFish20261105.gd`、`FinalizedHammerPair20261106.gd`、`FinalizedScallopedHammerhead.gd` — 后续鲨鱼/特化鱼入库时）**：
   - 在对应 loader 中按 `FinalizedWidthBatch20261101.gd` 的方式精准增加 `"pbr_material": true` 分支（允许单材质 `surface_count = 1` + 保留线性过滤与 Normal/ORM），**不得放松未升级物种的旧 SHA/材质断言**。

### Step 3：对正式安装路径复跑 8 项技术门禁 + 面数预算检查
1. 跑 `cli/fish_budget.py` 校验 `check_triangle_budget(triangles, real_length_cm, species=species)` 返回 `ok: true`；
2. 对**已安装的** `projects/fishing-2d/game/assets/models/fish/<species>.glb` 直接运行 `verify_fish_pbr_gate.gd`，确认 `FISH_PBR_GATE_JSON` 中 **`"ok": true`**（8/8 全过、`draw_calls == 1`、`upper_lip_err_mm < 2.0`、`vram_uncompressed_mip_mb <= 8.5 / 16.5`）。

### Step 4：真实游戏 5 项运行时实机检验（Godot 4.7 针对已安装资产实跑）
编写/运行一次正式安装验证脚本，在 `projects/fishing-2d/game` 下**不通过临时替换、直接走正式游戏入口**逐项实测并留存 JSON 报告：
1. **首次冷加载（Cold Display Load）**：`FishInstanceFactory.create_display(species)` 成功，`FinalizedWidthBatch20261101.apply()` 断言全部通过，无报错，材质为单表面 PBR（`normal_texture != null`、`roughness_texture != null`）。
2. **二次缓存命中（Warm Cache Hit）**：经 `FishAppearanceCache` 第二次实例化同物种，验证缓存命中、材质/法线/ORM 完整保留不洗白、无内存/节点异常。
3. **真实钓鱼实例与上唇挂钩（Fishing + Upper-Lip Hook）**：`FishInstanceFactory.create_fishing(species)` + `FishingVolumeFish.bind_upper_lip()` 实测绑定成功，上唇挂钩顶点世界位置在多帧游动与张嘴下均准确贴合实际实体上唇、无漂移。
4. **展厅四动作 + 正式张嘴回放**：验证 `Swim` / 转向 / 上浮 / 下潜 480 帧全部有限无穿模，正式展厅张嘴按钮动作（`black_seabream` 0–10°、`sea_bass` 0–14°）起口、全开与回位顺滑。
5. **真实 `current_exhibit.tscn` 水下光学校验**：直接从正式游戏入口加载该鱼进入 `current_exhibit.tscn`，核对 `FishUnderwaterOptics` 绑定 `normal_and_orm == true`、`split_atlas == true`（鲨鱼为 `false`），保存 1 张正式安装后水下确认图并目视确认与审查通过版零偏差。

### Step 5：LOD 兼容与 `fish-lod.res` 检查
- 检查 `FishMeshLod.gd` 加载该物种时的行为：
  - 若尚未针对新 PBR 拓扑重烘该物种的 `fish-lod.res` 条目，确认它能干净回退到完整 LOD0 网格（仅有一条预期的 `GLB changed` warning，无崩溃、无索引错乱、无破面）；
  - 若具备既有 LOD 烘焙脚本，则同步为新安装 GLB 生成 `LOD1/LOD2`（及后续 `MultiMesh` 用 `LOD3`）并更新 `fish-lod.res` 且抽检 LOD 切换无裂缝。验收报告中必须如实注明 `lod_status`（`"updated"` 或 `"clean_fallback_pending_batch_lod"`）。

### Step 6：仓库卫生、提交边界与 LFS 规范
- 严禁把 `work/` 审查目录、临时 PNG/脚本或未授权修改带入 `projects/fishing-2d` 工作区；
- 在 `projects/fishing-2d/plans/reviews/<batch-name>/` 下落一份精简的 `install.validation.json` 与 `HANDOFF.md` 记录正式安装哈希与全部测试结果；
- **提交与推送纪律**：跑完以上全部验收前不得提交；获用户明确授权提交推送时，确保非交互 shell 下 `PATH` 包含 `/Users/czl/.local/bin:/opt/homebrew/bin:/usr/local/bin`（保证 `git-lfs` 与 `bdpan` 正常上传百度 LFS 对象），推送后核对远端 SHA 与 LFS 对象数。

---

## 七、大规模开工总指令（2026-11-28 标杆已全部定稿，可直接复制给 GPT Astra 6.2！）

> **前置标杆已全部经用户实机验收完毕**：
> - **单材质 PBR 标杆**：硬骨鱼（真鲷 / 黑鲷 R2 / 海鲈 R2） + 鲨鱼（黑鳍礁鲨 R2 + 双髻鲨/鲸鲨 SOP v1.0）；
> - **灵动游动标杆（v1.1 用户验收定稿）**：[lively-swim-kinematics-standard.md](../../skills/fish-volume-production/references/lively-swim-kinematics-standard.md)（已按用户刚实机验收的**黑鲷 v2** 校准：硬骨鱼 2 倍频 `~1 Hz` 浮力胸鳍外展 `9°–31°` + `±13.5°` 90° 转桨 + `±8°` 侧视轻煽 + 尾鳍 `16.5°` + 背臀 `10.5°–11.5°` + 呼吸 `2.4°`，配合 `FoundryFishMotion.gd` 的 `native_feather: true` & `native_jaw_breath: true`；**鲨鱼严守刚性水翼绝不拍翅！** 可直接参考 `work/black-seabream-lively-swim-20261128/author/upgrade_seabream_swim.py`）；
> - **新建物种全流程手册（v2.1）**：[new-fish-pbr-sop-v2.md](../../skills/fish-volume-production/references/new-fish-pbr-sop-v2.md)（严守本地 3D 模型参考库、纯侧投禁上下分层、严锁原画头廓切中空口腔、闭口零正中缺口）；
> - 11 月 28 日已复跑全部 28 条正式鱼的四动作包络，运行时双轴约束（`native_feather: true`）与呼吸平滑衔接（`native_jaw_breath: true`）已跑通；后续每批在 PBR 候选中一并交原生循环、对应运动配置和同种观测，鲨鱼保留各自捕食或吸滤契约。[五类清点及黑鲷验收记录](../../volume-fish/black-seabream-swim-20261128/HANDOFF.md)

### 批量推进队列（每批 3–4 条并联，PBR 模型 + 灵动游动 v1.1 一次到位！）
- **已装好 PBR 的先行鱼补刷灵动游动 v1.1**：`red_seabream`、`black_seabream`、`sea_bass`（及 5 条鲨鱼按第 5 类群刚性水翼复核）；
- **A 类常规鳞片硬骨鱼批量队列**：
  - 第 1 批（全在 `width20261101`）：`red_emperor`、`rainbow_trout`、`brown_trout`、`atlantic_salmon`
  - 第 2 批（全在 `width20261101`）：`crucian`、`grass_carp`、`bluegill`（第 1 类群礁区划水型）、`nile_tilapia`
  - 第 3 批（含特殊附件重点盯）：`carp`（4口须）、`piranha`（4细牙）、`peacock_bass`（实体上颌褶）、`zander`
- **B 类特化硬骨鱼队列**（按各自皮质 + 运动类群）：
  - `yellow_croaker`（第 2 类群）、`mahi_mahi` / `pacific_bluefin_tuna` / `atlantic_sailfish`（第 3 类群远洋高速型）、`hairtail` / `silver_arowana` / `arapaima` / `african_catfish`（第 4 类群长体波浪型）
- **鲨鱼类（软骨鱼）**：遵循 **[README-SHARK-PBR-SOP-v1.md](README-SHARK-PBR-SOP-v1.md)** 与第 5 类群刚性水翼规范。

### 可直接复制的「大规模开动」执行指令
```text
全部标杆与手册均已由用户实机验收定稿，请立即进入大规模批量推进！严格遵循以下 4 份定稿文档：
- 硬骨鱼总控与正式装载：`resources/scripts/fish-pbr-pipeline/README-HANDOFF-GPT-ASTRA-6.2.md`
- 游动运动学标准（v1.1，已按用户实机验收的黑鲷 v2 校准）：`resources/skills/fish-volume-production/references/lively-swim-kinematics-standard.md`（参考实现见 `work/black-seabream-lively-swim-20261128/author/upgrade_seabream_swim.py` 与 `resources/volume-fish/black-seabream-swim-20261128/HANDOFF.md`）
- 鲨鱼专项 SOP：`resources/scripts/fish-pbr-pipeline/README-SHARK-PBR-SOP-v1.md`
- 全新物种从零 SOP（v2.1）：`resources/skills/fish-volume-production/references/new-fish-pbr-sop-v2.md`

执行纪律：
1. **模型 PBR 升级与灵动游动 v1.1 同步一次到位**：每批 3–4 条并联推进（先将已装 PBR 的 `red_seabream` / `black_seabream` / `sea_bass` 对齐到用户刚验收的黑鲷 v2 灵动标杆并复核 5 条鲨鱼刚性水翼，随后按 A 类第 1→2→3 批与 B 类顺推）。每条鱼同时完成单材质 PBR 升级 + 按 5 大生物力学类群重编 `Swim`（硬骨鱼采用 2 倍频外展 9°–31° + ±13.5° 90° 转桨 + ±8° 侧视轻煽标杆，配 `native_feather: true` & `native_jaw_breath: true`；鲨鱼严守刚性水翼绝不拍翅！）+ 同步更新 `motion/*.json`、同种游动实证与真实 `current_exhibit.tscn` 水下检验。
2. **严禁抛弃既有已验收源 `.blend` 拓扑/口腔与 `resources/fish-database/` 本地 3D 模型基准**；所有候选均先在 `work/` 出齐棚拍+水下对照与冷导 SHA-256 报告发我批次确认，再走第六节 6 步正式装载与 5 项实机验收。
3. 未获用户授权前不擅自 push 远端；每完成 1 批立即发精简批次汇总与审查入口。
```
