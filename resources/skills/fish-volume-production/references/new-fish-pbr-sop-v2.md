# 全新海洋生物「一步到位单材质 PBR + 灵动游动」标准生产手册（v2.1 · 2026-11-28 实测定稿）

> **适用范围**：从零开始新建任何**全新鱼类与海洋生物**（硬骨鱼、鲨鱼、海龟、鳐鱼/蝠鲼、章鱼/鱿鱼/甲壳等），**不再走“先做旧像素低模、再二次改造 PBR”的弯路**，直接一次做成**可上线、可贴脸特写、游动灵动、可进 5 万条鱼同屏压测**的正式成品。
>
> **手册体系联动**：
> - **新建物种主手册（本文件）**：[new-fish-pbr-sop-v2.md](new-fish-pbr-sop-v2.md)（v2.1，经公子小丑鱼 v1→v5 全流程从零实测排雷定稿）；
> - **游动运动学权威标准**：[lively-swim-kinematics-standard.md](lively-swim-kinematics-standard.md)（5 大生物力学游动类群、胸鳍 2 轴正交划水+转桨公式、`motion/*.json` 升级值与 `FoundryFishMotion.gd` 衔接）；
> - **既有 28 鱼 PBR + 游动同步升级手册**：硬骨鱼总控见 [README-HANDOFF-GPT-ASTRA-6.2.md](../../../scripts/fish-pbr-pipeline/README-HANDOFF-GPT-ASTRA-6.2.md)（v4），软骨鱼/鲨鱼专项见 [README-SHARK-PBR-SOP-v1.md](../../../scripts/fish-pbr-pipeline/README-SHARK-PBR-SOP-v1.md)（v1.0）；
> - 旧版 [production-sop.md](production-sop.md)（含近邻像素烘焙、旧 2000 面紧预算与历史补丁）仅保留为历史溯源参考。

---

## 一、核心架构原则（先立规矩，再开工）

1. **一步到位单网格单材质（`Draw Call = 1`）**：每个物种最终只交付 **1 个 Mesh + 1 个 Material Surface + 3 张共享 PBR 贴图（`Albedo` + `Normal` + `ORM`）**。
2. **严禁抛弃本地 3D 模型与已验收资产基准**：凡本地资料库存在同种/近缘 3D 参考模型，以及游戏库已有同类验收成品（如嘴部结构、骨架与锚点），**必须先实测加载对齐，绝不允许抛弃本地 3D 数据纯靠手写数学管拍脑袋造鱼**。
3. **静态 100% 归 Blender，动态归 Godot**：形体、嘴、眼球、鳍厚、UV、贴图、骨骼权重、原生灵动 `Swim` 全部固化在可编辑源 `fish.blend`；独立重开 Blender 冷导 GLB 必须与上线 GLB **SHA-256 逐字节一致**。严禁在 Godot 里写静态补色、修形或按顶点序号查表脚本。
4. **面数按「体长 × 形态复杂度」放开 LOD0，靠四级 LOD 扛住 5 万条鱼同屏**：预算由 [cli/fish_budget.py](../../../../cli/fish_budget.py) 强制裁决。
5. **模型与「灵动游动状态」一次到位同步交付**：每条鱼不仅做高质单材质 PBR 静态模型，必须按 [lively-swim-kinematics-standard.md](lively-swim-kinematics-standard.md) 同步做好**原生灵动 `Swim` 动画与对应 `motion/*.json`**。
6. **只有 2 个人工停点，其余全程自动跑通**：
   - **人工检查点 #1（Stage 1 结束）**：定形/定色（确认清爽细像素参考图或 3D 灰模比例）；
   - **人工检查点 #2（Stage 5 结束）**：终审放行（审 6 视图棚拍 + 真实水下展缸 + 实时可交互审查窗口 + 游动实证）。

---

## 二、Stage 0 · 物种立项、三级本地参考加载、形态分轨与生物实证（开工必交）

### 2.1 三级本地参考加载铁律（严禁跳过！缺此步极易出现头型、嘴型、饱满度失真）

开工前必须按顺序完成以下 3 级本地查证，并写入 `work/<species>-new-pbr-<YYYYMMDD>/species-brief.json`：

1. **一级基准 · 本地 3D 参考模型库（[resources/fish-database/](../../../fish-database/README.md)）**：
   - 库内已沉淀 **325+ 种鱼现成 3D 参考模型 `mesh-exports/*.obj`** 与 408 条竞品预制体资料；
   - 只要存在同种（或同属/同科体型接近物种）`.obj`，**必须直接导入 Blender 量测其真实 3D 截面**：头吻收窄斜率、吻宽/体宽比、口位高低与口裂进深、眼窝曲率与位置、背腹饱满度及全部鳍根附着点。
2. **二级基准 · 项目已验收同类源 `.blend`（直接复用成熟嘴部与绑定工程经验）**：
   - 对照同形态已验收正式 `.blend`（例如：小型圆吻礁鱼/太阳鱼看 `projects/fishing-2d/assets/source/fish/bluegill/fish.blend`；中大型标准侧扁鱼看 `red_seabream` / `black_seabream` / `sea_bass`；掠食鲨鱼看 `blacktip_reef_shark`），核对其**真实切开的中空口腔拓扑、下颌铰链位置、下颌权重渐变区间与上唇挂钩顶点设计**，严禁闭门造车重踩低级坑。
3. **三级基准 · 博物馆形态学与真实游动实证**：
   - 核对 `FishShapes_specimensv1.csv` 标本测量比例（体高/体长、体宽/体长、口宽、眼径）；
   - 遵循根 `AGENTS.md`（2026-11-21）查同种实拍录像或观测分析，记录日常巡航速度（BL/s 与 m/s）、推进方式（BCF / MPF / 翼拍 / 喷水）、能否原地悬停守位及条件，写入 `swim-evidence.md`。

### 2.2 形态分轨（`anatomical_group`）与 5 万鱼 LOD 预算锁定

调用 `cli/fish_budget.py` 锁定本物种预算（`check_triangle_budget(tris, real_length_cm, anatomical_group=group)`）：

| 形态赛道（`anatomical_group`） | 建模基准视图 | LOD0 优选 / 硬上限（大体型随体长升档） | 贴图规格与透明模式 | 运行时 LOD1 / LOD2 / LOD3 目标 | 典型物种 |
|---|---|---:|---|---|---|
| **`standard_lateral`**<br>常规侧扁鱼 | 侧视为主 + 俯视校准体宽 | **`4,000 / 5,000`**（≤120cm）<br>`6,500 / 8,000`（120–300cm） | **`2:1` 图集**（`1024×512` small / `2048×1024` large）<br>`alphaMode: MASK (0.5)` + `doubleSided: true` | `400–600` / `120–160` / **`32–64`** | 鲷、鲈、小丑鱼、蓝吊、金枪鱼、旗鱼、带鱼、鲇鱼等 |
| **`shark`**<br>鲨鱼 / 软骨鱼 | 侧视 + 俯视 + 腹视口颌 | **`6,500 / 8,000`**（起步）<br>`8,500 / 10,000`（>3m）<br>`12,000 / 15,000`（>6m） | **`1:1` 方图**（`1024×1024`；8m 巨兽 `2048×2048`）<br>**`alphaMode: OPAQUE`**（厚肉鳍绝不透光） | `800–1,200` / `250–350` / `64–96` | 黑鳍礁鲨、双髻鲨、豹纹鲨、鲸鲨等 |
| **`dorsal_complex`**<br>俯视主导 / 宽翼 / 龟甲 / 繁鳍 | **3D 体积优先**（俯 + 腹 + 前 + 侧四向） | **`6,500 / 8,000`**（起步）<br>`8,500 / 10,000`（>3m） | **`1:1` 方图**（`1024×1024` / `2048×2048`）<br>`OPAQUE`（薄饰鳍种可用 `MASK 0.5` 但关闭背甲透射） | `1,000–1,600` / `300–500` / `96–140` | 海龟、鳐鱼、蝠鲼、比目鱼、狮子鱼、海马等 |
| **`multi_limb`**<br>多触手 / 多步足海洋生物 | **3D 体积优先**（俯 + 斜 + 前 + 肢体展开） | **`8,500 / 10,000`**（不受小体长限制） | **`1:1` 方图**（`1024×1024` / `2048×2048`）<br>`OPAQUE`（水母半透伞盖另走透明特例） | `1,500–2,400` / `500–800` / `150–220` | 章鱼、鱿鱼、乌贼、龙虾、螃蟹、水母等 |

同时在 `species-brief.json` 锁定：**解剖部件清单**（真实鳍/肢数、口位与挂钩点、鳃型、口须/细牙等特殊附件）与**皮肤物理材质配方**（银鳞 / 礁鱼细鳞 / 无鳞黏液 / 金属镜面 / 哑光楯鳞皮革 / 角质龟甲）。

---

## 三、Stage 1 · 视觉定调与参考供体（人工检查点 #1 · 严守清爽细像素基因）

> **画风红线**：新鱼必须与已有 28 条正式鱼同缸和谐！**严禁脱离仓库既有生图逻辑去生成纯写实 CGI/塑料棚拍图**。

1. **生图工具与风格卡绑定**：
   - 调用项目标准外部生图 CLI/API（见 `resources/skills/gamefactory-toolkit/SKILL.md`），不依赖容易触配额的代理内置生图；
   - 所有概念图与多视供体图都必须挂载仓库的 **清爽细像素风格卡**（`resources/volume-fish/styles/clean-pixel-20261108/nile-tilapia-C.png`）作为笔触/色阶/平光基准，并沿用 **“先完整去鳍身体 → 再独立烘鳍”** 流程。
2. **禁止“风格卡反向污染生物特征”**：
   - 只借风格卡的**清爽细像素簇、阶梯色阶与平光漫射**；
   - **严禁把罗非鱼的粗大菱形鳞片抄到光滑礁鱼或无鳞鱼身上**；
   - **严禁给鱼画拟人微笑嘴角、怪异下拉嘴角或过度放大的恐怖谷大眼瞳**——嘴部一律保持本物种真实、中性、自然的闭口/微开鱼嘴，眼径严格对齐本地 3D 参考模型与博物馆比例。
3. **按形态赛道准备供体**：
   - **侧扁硬骨鱼（`standard_lateral`）**：Checkpoint #1 审 1 张**清爽细像素正交侧视 + 吻尾对齐俯视概念图**；侧视图用于外轮廓与无缝身体贴图主供体（被胸鳍遮挡的体表条纹须在 2D 阶段彻底修补干净），俯视图严格用于校准 3D 截面宽度与吻部收窄曲线。
   - **鲨鱼 / 俯视主导 / 多肢体生物（`shark` / `dorsal_complex` / `multi_limb`）**：先结合本地 3D 参考在 Blender 搭出可编辑 3D 灰模定准四向体积、锤头/龟甲/翼展与肢体支点，再从锁定正交相机出图上色。
4. **Checkpoint #1 放行标准**：用户一眼确认“画风与既有鱼群统一、头型眼睛可爱自然、配色花纹满意”，再进入 Stage 2–5 自动化制作。

---

## 四、Stage 2 · Blender 一次性规范建模（经小丑鱼 v1→v5 实战排雷的 7 条硬规范）

在 Blender 5.0.1 中直接建立干净、可编辑的最终拓扑（`fish.blend`）：

1. **逐面打好部位属性（`foundry_logical_part_id`）**：合并为单网格前，为每个面写入整数属性 `foundry_logical_part_id` 与 Mesh 自定义属性 `foundry_geometry_parts_json`（区分 `body_skin`、`oral_cavity`、`eye` 及每一片独立 `fin` / `limb` / `shell`），杜绝靠骨权猜部位漏面。
2. **法线绕序严格朝外（硬断言！）**：生成网格后**必须用脚本断言背脊/体侧三角叉积法线严格朝外（如 `dorsal_normal.z > 0`），口腔内壁法线严格指向空腔内部**——严禁靠 `doubleSided: true` 掩盖内翻法线（否则光照与法线贴图全部反转！）。
3. **嘴部真切开中空口腔，且 100% 严锁原画头廓（小丑鱼 v1→v5 最核心教训！）**：
   - **必须从真实口角位置把头部拓扑劈开为两片完全独立的外壳**：**上颌壳（`jaw_w = 0.0`）**与**独立下颌壳（`jaw_w = 0.55 → 1.00`）**，仅在左右口角处汇合；
   - **严禁为了做嘴向外撑大脑袋/加宽吻部/鼓出双下巴！** 上下颌全部前吻断面必须 **100% 锁定在原画侧视与俯视真实外廓以内**（下颌宽度略内收 `3%–5%`），做到**只向内切、绝不向外膨胀**；
   - **闭口前缘上下均匀闭合（零正中弧形黑缺口！）**：最前端唇缘闭口时从嘴角到正中保持均匀紧凑的细唇缝（约 `1.4–1.8 mm`），**严禁在唇正中额外上下反向拱开导致正视出现一个椭圆/弧形黑洞**；
   - **沿完整口缘闭环向内挤出 3 圈深邃中空口腔**（内卷唇厚 → 宽阔口腔室 → 深喉封闭底），内唇严密藏于外唇内侧（闭口不露红边），上腭固定于 `body_00`、下舌底随 `jaw_lower` 旋转；`jaw_lower` 铰链置于口角后下方（对照 `bluegill` / `red_seabream`），确保张嘴 `14°–20°` 时整个下颌连同中空口腔真实敞开，严禁封闭圆管吻端硬捏假洞；
   - 鲨鱼/食人鱼等带牙物种把牙齿做成实体附着几何；可钓鱼物种记录精确实体上唇顶点索引 `foundry_upper_lip_vertex_index`。
4. **克制、自然贴服的高段数 3D 眼球**：
   - 硬骨鱼双眼每圈 **32–48 段**，底缘拟合实测头侧眼窝曲面并赋予解析平滑椭球法线；**弧高比严控 `dome_h / radius ≈ 0.22–0.28`** 并轻微内嵌眼窝，正视/俯视柔和自然、绝不凸泡眼；
   - 鲨鱼类严格按 [README-SHARK-PBR-SOP-v1.md](../../../scripts/fish-pbr-pipeline/README-SHARK-PBR-SOP-v1.md) 在原头皮面内贴合重建，正交俯视与转向超廓新增像素均为 **`0 px`**。
5. **完整有根鳍 / 宽翼 / 多肢体**：鱼鳍从根部平滑嵌入体表（杜绝悬空漏缝），向自由缘渐薄；鲨鱼厚肉鳍、海龟鳍肢、蝠鲼宽翼做实心封闭体；多触手/翼翅弯曲段预留均匀环线。
6. **平滑连续体表，杜绝脏断面**：严禁相距 `< 0.001` 的重合极近双断面法线打架（海鲈教训）；鳃盖/5 鳃裂浅起伏柔和无自交。
7. **面数核验**：导出前立刻跑 `cli/fish_budget.py` 确认通过。

---

## 五、Stage 3 · 单材质 UV 规划与一次性 PBR 三图烘焙

### 5.1 UV 排布硬合同（严格匹配游戏 `FishUnderwaterLit.gdshader`）

- **`standard_lateral`（硬骨薄鳍鱼 · `2:1` 图集）**：
  - **左半 `UV.x ∈ [0.0, 0.5)`**：
    - 鱼身两侧排成**连续无断层单岛**（严禁按固定竖线 `x = const` 劈开鳃盖！需要头部高密度时用平滑单调非线性 `u(x)` 拉伸）；
    - **防腹底黑线铁律（拓扑安全域 UV）**：躯干环形 UV 按拓扑环序号分半映射并严格留在安全域内（如左半 `v ∈ [0.58, 0.94]`、右半 `v ∈ [0.22, 0.58]`，背脊 `0.58` 无缝连续、腹底干净落于 `0.94 / 0.22` 并向外 Padding），**严禁对 `atan2` 角度做 `+span` 跨缝补值导致 `v > 1.0` 回绕采到贴图底黑边**；
    - 口腔独立小岛放安全角落；
    - **双眼固定放在左下角湿润高光区**：Blender `u < 0.09, v < 0.18`（Godot `UV.x < 0.09, UV.y > 0.82`），配 `ORM.G < 0.36`，触发水下湿润角膜高光。
  - **右半 `UV.x ∈ [0.5, 1.0]`**：打包全部薄鳍岛（互留 `>= 2%` 边距），自动触发水下薄鳍透射（`fin_sss`）。
- **`shark` / `dorsal_complex` / `multi_limb`（非薄鳍生物 · `1:1` 方图 + `OPAQUE`）**：
  - 统一用 `1024×1024`（8m 巨兽 `2048×2048`）+ `OPAQUE`，自动关闭薄鳍透射；双髻锤头、龟甲、宽翼、触手按解剖俯/腹/侧自然分岛，严禁纯侧投拉糊。

### 5.2 PBR 烘焙（`Albedo` + `Normal` + `ORM`）7 条质量铁律

1. **常规侧扁鱼回归「纯侧投无缝铺满整身」，严禁拼贴导致上下分层（小丑鱼 v3 核心教训！）**：
   - 去鳍侧视供体在制备阶段先向内腐蚀 `3–4 px` 去描边抗锯齿灰边再 EDT 外扩 Padding，且**仅局部微补 2D 画死的那条窄黑嘴缝**（不破坏周围任何肤色）；
   - 烘焙 `Albedo` 时，从背脊到侧腹再到腹底**统一无缝投射干净侧视图**——**严禁把色温/亮度不同的顶视图块、人工腹底提亮块、内缩截断带或平涂合成吻部色块硬叠到鱼身上**，从根源消灭一切上下分层线与脸颊竖缝！
2. **2× 超采样烘焙 + 28 轮 EDT 最近岛 Padding**：在 2 倍分辨率画布完成烘焙后，先将全部岛外空白填满最近岛颜色与 3D 位置，再 2×2 盒滤波降采样并重归一化法线。
3. **高对比花纹鱼必加「色块边缘法线抑制」**：存在纯白/纯黑/高饱和条纹突变的物种（小丑鱼、蓝吊、神仙鱼等），必须用亮度梯度遮罩（`not_stripe_edge`）抑制花纹交界法线，严禁在条纹边刻出虚假凹槽。
4. **接缝梯度抑制（`guard`）**：求高度图法线梯度前，用 3D 位置跳变 + `foundry_logical_part_id` 跳变检出全部岛边像素并做高斯归零衰减，杜绝接缝亮暗线。
5. **解剖保护遮罩**：高频微鳞/皮肤浮雕仅作用于体侧/背甲主体，**上下唇、下巴底缘、吻尖、眼下脸颊、各鳍根部、口腔内壁**必须用 smoothstep 完全排除。
6. **眼球去假高光**：抹除原画瞳孔里写死的静态白灯斑，眼周做肤色过渡，给湿润低糙度（`ORM.G ≈ 0.18–0.30, Metallic = 0`），让水下真灯光实时产生移动高光。
7. **按皮质给准物理参数**：银鳞硬骨（`Rough 0.40–0.65, Metal 0.05–0.14`）、珊瑚礁细鳞（`Rough 0.46–0.62, Metal 0.02–0.05`）、无鳞黏液（`Rough 0.36–0.50, Metal 0`）、镜面金属鱼（`Rough 0.28–0.42, Metal 0.25–0.45`）、鲨鱼哑光楯鳞（`Rough 0.62–0.80, Metal 0` + 5 凹陷鳃裂）、口腔内壁统一暗润哑光（`Rough 0.80–0.86, Metal 0`）。

---

## 六、Stage 4 · 骨架、灵动游动标准与确定性冷导出

1. **规范骨架与权重**：
   - 常规鱼 `18–22` 骨（含独立 `jaw_lower` 与背/胸/腹/臀/尾鳍骨）；鲨鱼 `22` 骨；海龟/蝠鲼/章鱼按真实肢体/翼翅/腕足分节；鲸鲨吸滤用 Shape Keys；
   - 3D 眼球按眼眶环皮肤权重**刚性统一绑定**；全部顶点限 `Top-4` 骨权并归一化。
2. **强制按「灵动游动运动学标准」制作（完整公式与验证见 [lively-swim-kinematics-standard.md](lively-swim-kinematics-standard.md)）**：
   - **告别旧版“躯干发僵、胸鳍单轴微抖、背臀鳍像硬塑料板”的机械感**！每条鱼的 Blender 原生 `Swim`（60 帧 @ 30fps 无缝循环、仅旋转通道）与 `motion/*.json` 必须按本物种所属 **5 大生物力学类群**一次做到位：

| 运动类群 | 代表物种 | 脊柱行波 `body_01→tail_01` | 胸鳍 2 轴正交划水 + 90° 转桨 | 中鳍 / 腹鳍滞后随动 | `motion/*.json` 升级参考 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1. 礁区划水型 (`Labriform`)** | 小丑鱼、蓝鳃、蝴蝶鱼 | `0.04→0.30 rad` | **2 倍频** `sweep 0.30–0.38` / `feather 0.16–0.22`（左右异步 `0.85 rad`） | `0.08–0.15 rad` | `paired 0.34–0.40`, `median 0.12–0.15` |
| **2. 通用巡游型 (`Subcarangiform` · 黑鲷 v2 标杆)** | 鲷、鲈、鲤、草、鲫、鳟、鲑、大黄鱼等 | 头 `0.7°` → 尾柄 `12.2°` → 尾鳍 `16.5°` | **2 倍频** 外展 `9°–31°` + 转桨 `±13.5°` + 侧视轻煽 `±8°`（异步 `0.80 rad`） | 背/臀 `10.5°–11.5°`，腹 `8°–20°` | `paired 0.34–0.42`（`native_feather: true`）, `median 0.14–0.18` |
| **3. 远洋高速型 (`Thunniform`)** | 蓝鳍金枪鱼、旗鱼、鲯鳅 | 前半身极稳，后 1/3 骤增 `0.24–0.30` | 水翼微配平 `sweep 0.08–0.14` / `feather 0.04–0.07` | `0.04–0.07 rad` | `paired 0.12–0.16`, `median 0.06–0.08` |
| **4. 长体波浪型 (`Anguilliform`)** | 带鱼、银龙鱼、巨骨舌鱼、鲇鱼 | 全身多节大波 `0.05→0.38`（`C=1.15`） | `sweep 0.22–0.30` / `feather 0.12–0.16` | 长背/臀鳍逐段 `0.12–0.18` | `body_wave 0.24–0.30`, `median 0.14–0.18` |
| **5. 刚性水翼鲨 (`Carangiform-Shark`)** | 黑鳍礁鲨、双髻鲨、鲸鲨 | 沉稳尾推 `0.02→0.26`（周期 `2.6–4.2s`） | **刚性水翼绝不拍翅！** 仅极微弱对称配平 `0.03–0.05` | 背鳍近刚直 `0.02–0.04` | `paired 0.05–0.08`, `median 0.04–0.06` |

   - **微幅静息呼吸**：带可动下颌的鱼在 `Swim` 内叠加 `1.5°–2.5°` 缓慢呼吸微动（不干扰运行时 `10°–20°` 主动张嘴/捕食）；
   - **主动互动动作**：必带 1 个真实可动的张嘴 / 捕食 / 吸滤动作，并在 Godot 中用 `(global_rest.basis.inverse() * Vector3(0, 0, 1)).normalized()` 实测验证下颌本地旋转轴方向严格向下张嘴。
3. **Blender 5 确定性导出合同**：
   - 薄鳍鱼材质节点为 `Albedo.Alpha → Math(GREATER_THAN, 0.5) → Principled.Alpha`（导出 `MASK 0.5`，禁 `BLEND`）；鲨鱼/不透明种直接不连 Alpha（导出 `OPAQUE`）；
   - 开启 `export_tangents=True`；保存 `fish.blend` 后用**全新独立 Blender 进程**冷导一次，验证与候选 GLB **SHA-256 逐字节一致**。

---

## 七、Stage 5 · 自动化门禁 + 6 视图实机自检 + 水下双图审（人工检查点 #2）

在 `work/<species>-new-pbr-<YYYYMMDD>/` 跑完全部自动校验（未过审前绝不改动正式游戏库）：

1. **技术门禁**：`cli/fish_budget.py` 通过；`verify_fish_pbr_gate.gd` 通过（`draw_calls == 1`、`alphaMode` 正确、显存达标、480 帧有限、张嘴满幅、适用时上唇误差 `< 2 mm`）；独立冷导 SHA-256 逐字节一致。
2. **提交前执行者必须逐张目视自检 6 件套（严禁有盲区直接扔给用户！）**（macOS CLI 调 Godot 4.7 Mono 须设 `DOTNET_ROOT=/Users/czl/.gamefactory/toolchain/dotnet` + `--rendering-method gl_compatibility`；拍水下图挂到 `exhibit.contents` 并用 `global_position` 与 `exhibit.viewport` 抓图）：
   - `qa/` 棚拍 **6 视图**：
     - `01_swim_3q.png`（3/4 游姿：核对清爽细像素画风、**无上下分层**、头身比例与原画一致）
     - `02_turn_top.png`（俯视：**严检头吻绝未被撑大**、眼凸度克制、胸鳍不穿腹）
     - `03_jaw_open_vs_closed.png`（闭口 0° vs 张口满幅同机位对比：严检闭口均匀无缺口、张口真实露中空深腔）
     - `04_rear_fins_depth.png`（后斜鳍遮挡深度正确）
     - `05_front_head.png`（**正前头视**：严检双眼舒适不凸眼、**闭口唇缝均匀无正中弧形缺口**、无嘴下黑线）
     - `06_ventral_belly.png`（**正腹仰视**：严检嘴下方与腹底正中 **100% 零黑线**）
   - `underwater/` 真实 `res://scenes/current_exhibit.tscn` 实拍整鱼 + 头部近景 + **与正式 PBR 鱼（如真鲷/黑鲷）同框画风一致性对照**（核对 `normal_and_orm == true`）；
   - `open_live_preview.gd` / `open-review.command`（Godot 交互旋转审查窗口，遵守 macOS 居中无抢焦规则，带 1–6 机位与 `M` 键实测张嘴）；
   - `swim-evidence.md` + `review.validation.json` + `HANDOFF.md`。

---

## 八、Stage 6 · 正式装载、游戏 5 项实机验收与 5 万鱼 LOD 落地

用户点头放行后，直接执行 [README-HANDOFF-GPT-ASTRA-6.2.md 第六节「正式装载与发布验收 SOP」](../../../scripts/fish-pbr-pipeline/README-HANDOFF-GPT-ASTRA-6.2.md#六正式装载与发布验收-sop用户拍板通过后执行)：
1. 正式落位 `fish.blend` / `<species>.glb` / `*-mouth-anchor.json` + 正式路径独立冷导 SHA-256 复验；
2. 注册物种 profile、灵动 `motion/*.json`、`manifest.json`（标 `"pbr_material": true`）与运行时 Loader 绑定；
3. 跑真实游戏 **5 项实机检验**（冷加载、缓存命中、钓鱼上唇挂钩、展厅四动作+张嘴/捕食、正式 `current_exhibit.tscn` 水下光学）；
4. **5 万条鱼同屏 LOD 就绪**：检查 `FishMeshLod.gd` 兼容性并登记 `LOD1 / LOD2 / LOD3`（共享同一套 PBR 贴图）；
5. 落正式验收报告至 `projects/fishing-2d/plans/reviews/`，获用户授权后按 `git-lfs` + `bdpan` 规范提交推送。

---

## 九、可直接复制给外部 Agent（GPT Astra 6.2）的两套标准任务指令

### 指令 A · 从零新建全新物种（单材质 PBR + 本地参考校准 + 灵动游动一次到位）
```text
请严格按照 `resources/skills/fish-volume-production/references/new-fish-pbr-sop-v2.md`（v2.1 实测定稿版）、`resources/skills/fish-volume-production/references/lively-swim-kinematics-standard.md` 与 `cli/fish_budget.py`，从零制作全新物种 `<species>`（中文名：<中文名>，展示体长：<XX> cm，形态赛道：`standard_lateral` / `shark` / `dorsal_complex` / `multi_limb`）。

硬性要求：
1. Stage 0 严禁抛弃本地模型资料！必须先加载 `resources/fish-database/` 内同种或近缘 3D `.obj` 参考模型 + 对照已验收同类正式 `.blend`（如 `bluegill`/`black_seabream`/`blacktip_reef_shark`）校准头吻、嘴型与饱满度，并写游动实证卡。
2. Stage 1 调用项目标准外部生图 API 并挂载清爽细像素风格卡（`nile-tilapia-C.png`），严禁纯写实 CGI、严禁拟人笑嘴/恐怖大眼，在 Checkpoint #1 停下来发我定调确认。
3. 确认后一口气跑通 Stage 2–Stage 5：外向法线断言 + 严锁原画头廓（绝不撑大头部）的真口角切开中空口腔（闭口均匀无正中缺口、张口真实露深腔）+ 自然克制 3D 眼球 + 侧扁鱼纯侧投无缝铺满（禁拼顶图致上下分层）+ 拓扑安全域 UV（禁腹底黑线）+ 按 `lively-swim-kinematics-standard.md` 做齐 2 轴正交胸鳍划水/行波脊柱/滞后中鳍的灵动 `Swim` 与 `motion/*.json` + 独立冷导 SHA-256 一致 + 6 视图自检（含正前/仰腹/闭口vs张口）+ 真实 `current_exhibit.tscn` 水下同框。
4. 候选放进 `work/<species>-new-pbr-<YYYYMMDD>/`（通过 Checkpoint #2 前不改动 `projects/fishing-2d` 正式文件），发我审查包终审。
```

### 指令 B · 既有鱼类「模型升级 + 全库灵动游动系统复核与同步修复」指令
```text
请精读 `resources/skills/fish-volume-production/references/lively-swim-kinematics-standard.md`、`resources/scripts/fish-pbr-pipeline/README-HANDOFF-GPT-ASTRA-6.2.md`（v4）与 `resources/scripts/fish-pbr-pipeline/README-SHARK-PBR-SOP-v1.md`，把当前项目的鱼类游动系统整体复核并升级：

1. **先查实际运行入口与最终写骨层**。黑鲷样板使用 `FoundryFishMotion.gd` 的显式双轴胸鳍约束，并接通展缸行为及张嘴控制。复用前核对本鱼的旋转顺序、局部鳍轴、外展下限、原生呼吸及物种覆盖。把匹配的 `motion/*.json` 和签名写入候选，用真实展缸同轨迹录像和逐姿态游离鳍面碰撞检查验收。[28 鱼运行基线与黑鲷实测](../../../volume-fish/black-seabream-swim-20261128/HANDOFF.md)
2. **全库游动参数与原生 `Swim` 按 5 大生物力学类群一次性升级**：
   - 后续每一批 PBR 升级（硬骨鱼 A/B 类与双髻鲨/鲸鲨）不再只升级静态模型，必须同步按 `lively-swim-kinematics-standard.md` 重编原生灵动 `Swim`（脊柱行波 + 硬骨鱼胸鳍 2 轴正交划水与异步相位 + 中/腹鳍滞后随动 + 微幅呼吸；**鲨鱼严守刚性水翼绝不拍翅**）并同步更新对应 `motion/*.json`（告别旧版偏僵的 `paired_fin_radians: 0.18 / median_fin_radians: 0.065`）；
   - 对已做完 PBR 的 `red_seabream` / `black_seabream` / `sea_bass` / `blacktip_reef_shark` 同步排期补刷灵动游动并复跑 5 项实机验收。
3. **继续保留本地 3D 参考与既有模型几何基准**：所有升级均以既有正式 `.blend` 与 `resources/fish-database/` 本地模型数据为几何基线，严禁抛弃本地模型基准。
```
