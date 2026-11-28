# 鲨鱼类（软骨鱼）单材质 PBR 升级与制作标准 SOP（v1.0 · 2026-11-28）

> **分类与定位说明**：鲨鱼属于**软骨鱼（Chondrichthyes，预算赛道 `anatomical_group = "shark"`）**，其体表（哑光楯鳞砂纸皮革）、呼吸结构（5 道凹陷鳃裂，无硬骨鱼鳃盖）、鱼鳍（8 片厚实不透明肉鳍）及捕食方式（22 骨大张口摄食 / 鲸鲨 9 形态键主动吸滤）与常规硬骨鱼（`standard_lateral`）截然不同。本 SOP 专门固化全库既有 5 条鲨鱼的 PBR 升级、正式装载以及后续新建软骨鱼（鲨鱼类）的统一执行标准。
>
> **1 号已过审达标样板（已获用户图审认可，可直接正式装载）**：
> - **黑鳍礁鲨 R2（`blacktip_reef_shark`）**：`work/blacktip_reef_shark-pbr-review-20261128/`
>   - `5,878` 三角面（v3 鲨鱼起步档优选 `6,500` / 硬上限 `8,000`）、`1` Mesh / `1` Surface / `1` Draw Call、`1.45 MB` GLB（原版 `5.08 MB`）；
>   - `alphaMode: OPAQUE`、`3 × 1024×1024` 1:1 方图（未压缩含 Mip `16.0 MB` / BC7 `~4.0 MB`）；
>   - 原头皮 38 面内 48 段局部重建双眼，正交俯视与转向双机位超出原头廓均 **`0 px`**，实光高光移动 `47.72 px`；
>   - 22 骨捕食大张口 `32.00°`（263 帧误差 `0`）、上唇挂钩误差 `0.00 mm`、独立冷导 SHA-256 逐字节一致、浅礁展缸实拍 `normal_and_orm = true` / `split_atlas = false` / `is_fin = false`。

---

## 一、全库 5 条鲨鱼台账、面数预算与 Loader 映射

所有面数预算由 `cli/fish_budget.py` 强制校验（`check_triangle_budget(tris, real_length_cm, species=species)`，按展示体长 × `anatomical_group="shark"` 分档）。

| 物种（`species`） | 展示体长 | LOD0 优选 / 硬上限 | 当前官方资产状态（面 / 材质 / 骨 / 形态键） | 贴图目标（1:1 方图 × 3） | 正式运行时 Loader 与 Manifest | 专项互动动作与核心红线 |
|---|---:|---:|---|---|---|---|
| **黑鳍礁鲨**<br>`blacktip_reef_shark` | `150 cm` | **`6,500 / 8,000`** | `3,962` 面 / `3` surf / `22` 骨 / `0` morph（`5.08 MB`）<br>**R2 候选已过审：`5,878` 面 / `1` surf（`1.45 MB`）** | `1024×1024` | `FinalizedElevenFish20261105.gd`<br>`eleven20261105.json`<br>`eleven20261105/blacktip_reef_shark-mouth-anchor.json` | 22 骨捕食（`plans/reviews/blacktip-feeding-20261115/FeedingMotion.gd`，peak `32°`）；**已过审，优先正式装载** |
| **大双髻鲨**<br>`great_hammerhead` | `400 cm` | **`8,500 / 10,000`** | `4,668` 面 / `4` surf / `22` 骨 / `0` morph（`2.27 MB`） | `1024×1024` | `FinalizedHammerPair20261106.gd`（内置 `FISH["great_hammerhead"]` 与 `mouth` 配方） | 22 骨大食物夹持 + 小猎物摄入（`plans/reviews/great-hammerhead-feeding-20261116/FeedingMotion.gd`）；锤头两端眼柄严格 `0 px` 异常凸出，保留上下分面配对鳍衔接 |
| **路氏双髻鲨**<br>`scalloped_hammerhead` | `250 cm` | **`6,500 / 8,000`** | `3,994` 面 / `2` surf / `22` 骨 / `0` morph（`3.01 MB`） | `1024×1024` | `FinalizedScallopedHammerhead.gd`（内置 `MODEL_SHA` 与 `UPPER_LIP` 配方） | 22 骨独立小猎物摄入与大猎物夹持；保留已修平的尾鳍/尾柄接色与外环法线，锤头顶/底/前缘禁止纯侧投拉糊 |
| **无沟双髻鲨**<br>`smooth_hammerhead` | `300 cm` | **`6,500 / 8,000`** | `3,994` 面 / `4` surf / `22` 骨 / `0` morph（`1.17 MB`） | `1024×1024` | `FinalizedHammerPair20261106.gd`（内置 `FISH["smooth_hammerhead"]` 与 `mouth` 配方） | 22 骨独立小猎物摄入与大猎物夹持；合并外皮/眼/口腔/牙齿 4 个 surface 为 1 材质 |
| **鲸鲨**<br>`whale_shark` | `800 cm` | **`12,000 / 15,000`** | `9,990` 面 / `3` surf / `7` 骨 / **`9` morph**（`3.32 MB`） | **`2048×2048`**（全库仅此 1 条巨兽允许 2K 方图） | `FinalizedElevenFish20261105.gd`<br>`static20261108.json`<br>`static20261108/whale_shark-mouth-anchor.json` | 宽口吸滤（`WhaleSharkSuctionMotion.gd`，3 口 × 3.5s）；**严禁任何改拓扑/改顶点序操作，绝对保留全部 9 个吸滤形态键** |

> **运行时 LOD 目标（`cli/fish_budget.py` 统一标准）**：`LOD1: 800–1,200` / `LOD2: 250–350` / `LOD3: 64–96`（供 GPU `MultiMesh` 远景合批共享同一套 1:1 PBR 图集）。

---

## 二、死守不松口的 7 条鲨鱼硬门禁

任何一条鲨鱼候选在提交图审或正式装载前，必须全部满足以下 7 条：

| # | 硬门禁项 | 达标标准 |
|---|---|---|
| 1 | **单网格单材质合批** | **`1` Mesh / `1` Surface / `1` Material（`Draw Call = 1`）**，导出必须开启 `export_tangents=True`，所有 accessor 有限无 NaN/Inf |
| 2 | **不透明厚鳍合同** | **`alphaMode: OPAQUE`**（Godot `TRANSPARENCY_DISABLED`），严禁 `MASK` 或 `BLEND`；杜绝厚实鲨鱼鳍水下泛白透光或斜角深度排序错乱 |
| 3 | **1:1 方图 PBR 三图** | 完整包含 `Albedo`（sRGB）+ `Normal`（切线空间 OpenGL `+Y`）+ `ORM`（`R=AO`, `G=Roughness`, `B=Metallic`），全部为 `1024×1024`（鲸鲨 `2048×2048`）方图；整图 `Metallic = 0` |
| 4 | **水下着色器参数合同** | 真实 `res://scenes/current_exhibit.tscn`（`浅礁日光`）实测：`normal_and_orm == true`、`split_atlas == false`、`is_fin == false`（绝不误触薄鳍透射 `fin_sss`） |
| 5 | **面数与轮廓零破坏** | 通过 `cli/fish_budget.py` 预算校验；眼窝局部重建不得导致正交俯视或转向视图超出原头轮廓（**超廓新增像素 = `0 px`**） |
| 6 | **骨架 / 捕食 / 挂钩 / 形态键零退化** | 骨骼数、骨序、逆绑定矩阵、原动画通道逐项一致；22 骨捕食大张口 / 鲸鲨 9 形态键吸滤满幅通过；钓鱼上唇锚点误差 **`< 2.0 mm`**（推荐 `0.00 mm`，且 `jaw_upper = 1.0` 权重一致）；8 片完整厚鳍与口内/牙齿几何零丢失 |
| 7 | **独立冷导逐字节一致** | 全新独立 Blender 5.0.1 进程重开候选/正式 `fish.blend`，以标准选中 + `export_tangents=True` 导出临时 GLB，与交付 GLB **SHA-256 逐字节完全一致** |

---

## 三、黑鳍礁鲨 R1→R2 实测沉淀的 7 条鲨鱼制作铁律（避免一切返工）

1. **严禁外贴“高弧凸眼帽”，必须原头皮局部贴合重建 + 零轮廓外扩验证**
   - 黑鳍礁鲨 R1 在原眼位外贴独立高弧眼帽，正交俯视比原头轮廓多占 `3,853` 像素，形成明显“蛙眼”外凸；R2 改为在原头皮局部面内用 48 段眼缘做连续贴合重建（角膜仅在轮廓包络内浅拱 `1.38–2.13 mm`，眼缘过渡高差 `< 0.0001 mm`），双机位超出原头廓降至 **`0 px`**。
   - **实操优化提示**：若原低模头皮在眼窝中央存在锐利几何折角（如黑鳍礁鲨的 `61.39°` 眉颊水平折线），在确保外轮廓 `0 px` 零外扩的前提下，可对**角膜内区（`r < 0.75`）**的局部法线或高度做温和顺平，消除极近微距下的水平折痕（非强制重做黑鳍 R2，但后续双髻鲨与新鲨鱼推荐默认做到）。

2. **程序化高解析瞳孔/虹膜 + 彻底去假灯斑 + 移动主光实测**
   - 严禁把原画像素眼里的静态白色高光点烤进 Albedo（否则水下灯光转动时眼神发死）。
   - 参考黑鳍 R2：从原画眼区提取稳健的瞳孔深色、虹膜中位色与眼缘过渡色，在眼部独立图块内绘制圆滑无锯齿的瞳孔/虹膜与细微放射虹膜纤维，外圈与原头皮色及 ORM 无缝融合；角膜核心给 **`ORM.G = 0.20–0.24`**，并在 `current_exhibit.tscn` 中固定镜头单独移动主灯，实测高光中心随光位明显平滑偏移。

3. **无鳃盖 → 5 道凹陷鳃裂；无鱼鳞 → 哑光楯鳞皮革感**
   - **严禁套用硬骨鱼的单片凸起鳃盖或鳞片网格法线！**
   - 皮肤与 8 片厚鳍保持哑光皮革质感：**`Roughness = 0.62–0.80`**，**`Metallic = 0.0`**；采用 3D 物理坐标连续各向同性微粒噪声跨接缝烘焙楯鳞肌理，体侧主干法线 RMS 倾角控制在 **`~1.5°–2.0°`**（P95 `~3.0°`），既有微粒立体感又绝不显塑料反光。
   - 颈侧严格按本物种原画位置标定 **5 道柔和弧形凹陷鳃裂**（叠加法线凹槽 + 轻度 AO 暗槽）。

4. **多材质合批（外皮 + 眼 + 口腔 + 牙齿 / 鼻孔）的分区物理参数合同**
   - 将原 `2–4` 个材质槽全部合并到同一张 `1:1` 方图的空闲安全区（2× 超采样烘焙 + `distance_transform_edt` 最近岛 Padding + 跨岛接缝梯度归零 `guard` + `2×2` 盒滤波降采并重归一化法线），确保绝无岛边渗色或亮暗线：
     - **体表与 8 片厚鳍**：`Roughness 0.62–0.80`、`Metallic 0.0`
     - **双眼角膜核心**：`Roughness 0.20–0.24`、`Metallic 0.0`（注意压在 `< 0.28` 以便水下着色器自动识别为眼部！）
     - **深暗口腔内壁**：`Roughness 0.84–0.86`、`Metallic 0.0`
     - **实体牙齿**：`Roughness 0.34–0.38`、`Metallic 0.0`（硬质微亮，且 `> 0.28` 不误触眼部高光）
     - **鼻孔暗腔（如有独立槽）**：`Roughness 0.80–0.85`、`Metallic 0.0`

5. **解剖保护区必须使用宽幅平滑渐变（避免俯视硬截断线）**
   - 吻尖、上下唇缘、眼眶外围、5 道鳃裂与 8 片鳍根必须排除高频颗粒噪点；
   - **防坑提示**：吻部/背脊微粒衰减过渡带尽量拉宽并避开低模头背稀疏横环的精确 `x` 坐标（例如避免把窄渐变恰好压在稀疏环折线上），防止正交俯视强光下出现横向明暗带。

6. **3 条双髻鲨（大 / 路氏 / 无沟）专属规范**
   - **锤头（Cephalofoil）禁纯侧投**：保留已接受源资产的分组/上下分面 UV 布局（或按顶面/底面/前缘独立分岛 + EDT Padding），严禁把锤头顶底压进纯左右侧投影导致花纹糊成条纹；
   - **锤头末端双眼**：双髻鲨双眼位于头翼左右最外端，眼部重建更必须严守正交俯视 **`0 px` 异常外凸** 与眼缘顺滑融合，且严格绑定到对应头部骨骼；
   - **保留双分支捕食**：合并多 surface 时绝对不破坏 `22` 骨权重、口内/牙齿几何以及各自已验收的小猎物摄入 + 大猎物夹持回放。

7. **鲸鲨（8 m 滤食巨兽）专属规范：零拓扑改动铁律**
   - 鲸鲨现有 `9,990` 面已完全满足 `12,000 / 15,000` 预算，且宽口口缘、两侧口角、鼻缘和前喉依赖 **9 个原生 Shape Keys** 驱动吸滤动画（`WhaleSharkSuctionMotion.gd`）。
   - **红线**：**严禁增删任何面、严禁焊点改顶点数、严禁破坏顶点顺序！** 只做零拓扑改动的 `3 surface → 1 surface` 单材质合并（将眼、鼻孔 UV 映射到 `2048×2048` 1:1 方图安全空区），烘焙哑光灰蓝楯鳞 + 象牙白斑平滑过渡法线与 ORM（斑点边界加色块梯度抑制，避免白斑边缘刻出假凹槽），实机核验 3 口吸滤动画（631 采样零误差）与上唇挂钩。

8. **鲨鱼类游动状态同步升级红线（衔接 [lively-swim-kinematics-standard.md](../../skills/fish-volume-production/references/lively-swim-kinematics-standard.md)）**
   - 升级每条鲨鱼模型时，按灵动游动标准的 **第 5 类群（`Carangiform-Shark` 刚性水翼滑翔型）** 同步核验并优化 `Swim` 与 `motion/*.json`：
     - **沉稳尾向行波**：周期 `2.6–3.4s`（鲸鲨 `3.8–4.5s`），柔和头部平衡摆 `0.03–0.05 rad`，尾柄至尾鳍平滑宽幅推波 `0.22–0.28 rad`（`body_wave_radians: 0.18–0.22`）；
     - **胸鳍为刚性水翼，绝不拍打！** 仅允许极微弱对称纵倾配平（`sweep 0.03–0.05 / feather 0.02–0.03`，`paired_fin_radians: 0.05–0.08`），背鳍近刚直（`0.02–0.04`），严禁把硬骨鱼的大幅胸鳍划水套到鲨鱼身上！

---

## 四、正式装载前的 2 项一次性引擎侧适配（所有鲨鱼复用）

在正式装载 1 号样板 **黑鳍礁鲨 R2** 时，同步完成以下 2 处极小、精准的引擎适配（绝不破坏任何未升级旧鱼）：

### 4.1 `FishUnderwaterLit.gdshader` 补充 1 行鲨鱼水下眼部识别
当前 `projects/fishing-2d/game/scripts/aquarium/FishUnderwaterLit.gdshader` 第 153 行仅对 `has_split_atlas_uv`（2:1 硬骨鱼图集）自动开启 `pixel_is_eye`。因为鲨鱼走 `1:1` 方图（`has_split_atlas_uv == false`、`is_fin == false`），且本 SOP 严格保证**只有角膜核心 `ORM.G < 0.28`**（牙齿 `0.34–0.38`，皮肤 `0.62–0.80`，口腔 `0.84–0.86`），在 155 行紧随其后补 1 个分支即可让全库 5 条鲨鱼水下角膜同步解锁湿润低糙度（`0.216`）、`SPECULAR = 0.54`、顶光角膜反光与焦散屏蔽：

```glsl
if (has_split_atlas_uv && !pixel_is_fin && UV.x < 0.09 && UV.y > 0.82 && orm.g < 0.36) {
	pixel_is_eye = true;
} else if (!has_split_atlas_uv && !pixel_is_fin && orm.g < 0.28) {
	pixel_is_eye = true;
}
```
> 影响面核验：常规硬骨鱼走 `has_split_atlas_uv == true`，不受影响；旧版无 ORM 的鱼不进 `if (has_orm_tex)`，不受影响；造景不走此 shader。

### 4.2 三个鲨鱼正式 Loader 精准接入 `"pbr_material": true` 分支
参照 `FinalizedWidthBatch20261101.gd` 的实现，分别为以下 3 个 Loader 增加精准的 PBR 物种分支（**只对已标记 `"pbr_material": true` 的物种放行 `surface_count == 1` + 线性过滤 + Normal/ORM 断言，严禁放松未升级物种的旧断言**）：
1. **`FinalizedElevenFish20261105.gd`**（负责 `blacktip_reef_shark` 与 `whale_shark`）：
   - 当 `bool(row.get("pbr_material", false))` 为 `true` 时：
     - 断言 `surfaces == 1`、`material.normal_enabled and material.normal_texture != null`、`material.roughness_texture != null or material.metallic_texture != null`、`material.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED`；
     - **跳过 `_bind_nearest(meshes)`**（保留 GLB 原生线性过滤与 PBR 贴图，不再强设 `TEXTURE_FILTER_NEAREST`）。
   - 更新 `eleven20261105.json`（黑鳍礁鲨）或 `static20261108.json`（鲸鲨）对应条目的 `model_sha256`、`triangles`、`surface_count: 1`、`"pbr_material": true` 及新 `mouth_recipe.sha256`。
2. **`FinalizedHammerPair20261106.gd`**（负责 `great_hammerhead` 与 `smooth_hammerhead`）：
   - 对对应物种条目支持 `"pbr_material": true`、`surfaces: 1`、线性过滤 + Normal/ORM 校验，并更新精确 `model_sha256`、`triangles` 与 `mouth` 配方（保留原 `length_m` 与 `motion_path` / `motion_sha256`）。
3. **`FinalizedScallopedHammerhead.gd`**（负责 `scalloped_hammerhead`）：
   - 升级路氏双髻鲨时同步更新 `MODEL_SHA`、`UPPER_LIP`、单 surface PBR（`OPAQUE` + Normal + ORM + 线性过滤）断言与 `triangles`。

---

## 五、候选审查交付物与正式装载 6 步验收 SOP

### 5.1 候选交付物（未获用户图审通过前，严禁覆盖 `projects/fishing-2d` 正式文件）
每条新升级的鲨鱼在 `work/<species>-pbr-review-<YYYYMMDD>/` 输出：
- `fish.blend` + `<species>.glb`（独立冷导 SHA-256 逐字节一致）+ `author/` 可复现脚本
- `comparison.jpg`（棚拍原版 vs 新版 整鱼 + 头部/捕食近景）
- `head-top-comparison.jpg`（正交俯视头廓与眼窝对照）
- `underwater-comparison.jpg` + `underwater-eye-comparison.jpg` + `underwater/`（真实 `current_exhibit.tscn` 浅礁日光同机位对比 + `validation.json`）
- `qa/`（4 基础视图 + 俯视头图 + `gate_report.json` + `anchor.json` + `eye-outline.validation.json` + `eye-light-response.jpg` + `feeding-overlay.validation.json` + `texture.validation.json`）
- `open-review.command` + `review.gd` + `source.validation.json` + `review.validation.json` + `HANDOFF.md`

### 5.2 正式装载 6 步验收（用户拍板通过后执行）
与硬骨鱼 v4 主手册第六节完全一致，但逐项走鲨鱼专属口径：
1. **正式源与模型落位 + 独立冷导逐字节复验**：覆盖 `assets/source/fish/<species>/fish.blend`、`game/assets/models/fish/<species>.glb` 及对应 `*-mouth-anchor.json`（或内嵌配方），用独立 Blender 5.0.1 进程重导已安装 `.blend` 确认 SHA-256 逐字节一致；
2. **Manifest / Loader 绑定 + 水下眼部着色器检查**：完成 4.1 与 4.2；
3. **正式路径技术门禁 + 预算复跑**：对已安装 GLB 跑 `cli/fish_budget.py` 与鲨鱼 Godot 门禁（`alpha_mode == OPAQUE`、`draw_calls == 1`、`three_square_1024_maps` 或鲸鲨 `2048`、`upper_lip_err_mm < 2.0`）；
4. **真实游戏 5 项运行时实机检验**（不经临时替换，直接走 `FishInstanceFactory` 正式入口）：
   - ① 首次冷加载 `create_display(species)` 断言全过、单材质 PBR 完整；
   - ② 二次缓存命中 `FishAppearanceCache` 材质/法线/ORM 零洗白；
   - ③ 真实钓鱼 `create_fishing(species)` + 上唇挂钩多帧游动/捕食贴合零漂移；
   - ④ 四动作 480 帧有限 + 专属捕食/吸滤动作完整复验（黑鳍/双髻鲨 22 骨捕食、鲸鲨 3 口吸滤）；
   - ⑤ 正式入口进入 `current_exhibit.tscn` 实拍确认 `normal_and_orm == true`、`split_atlas == false`、`is_fin == false`（含水下眼部效果确认图）；
5. **LOD 兼容与 `fish-lod.res` 检查**：核验 `FishMeshLod.gd` 更新（或干净回退并如实记录 `lod_status`）；
6. **验收归档与提交边界**：在 `projects/fishing-2d/plans/reviews/<batch-name>/` 落盘精简 `install.validation.json`、`runtime.validation.json` 与 `HANDOFF.md`；不带入 `work/` 临时文件；**未获明确授权前不 push，授权推送时保证 `PATH` 含 `/Users/czl/.local/bin:/opt/homebrew/bin:/usr/local/bin` 以正常上传百度 LFS**。

---

## 六、鲨鱼类放开推进队列（可直接复制给外部 Agent GPT Astra 6.2）

> **推进节奏**：先正式装载已过审的黑鳍礁鲨 R2 并补齐 1 行水下眼部着色器与 Loader 分支，再依次放开推进 3 条双髻鲨与鲸鲨。

```text
请先完整阅读新定稿的鲨鱼专项标准手册 `resources/scripts/fish-pbr-pipeline/README-SHARK-PBR-SOP-v1.md`（以及总手册 `resources/scripts/fish-pbr-pipeline/README-HANDOFF-GPT-ASTRA-6.2.md` v4、`cli/fish_budget.py`）。

黑鳍礁鲨 R2（`work/blacktip_reef_shark-pbr-review-20261128/`）已获用户图审通过！现在按以下顺序放开推进鲨鱼类（软骨鱼）单材质 PBR 升级：

### 阶段一：正式装载并验收「黑鳍礁鲨 R2（`blacktip_reef_shark`）」+ 一次性补齐水下眼部识别
1. 在 `projects/fishing-2d/game/scripts/aquarium/FishUnderwaterLit.gdshader` 第 155 行按 SOP 第 4.1 节补齐 1 行 1:1 鲨鱼方图眼部自动识别（`!has_split_atlas_uv && !pixel_is_fin && orm.g < 0.28` → `pixel_is_eye = true`），并确认不影响任何既有硬骨鱼。
2. 在 `projects/fishing-2d/game/scripts/aquarium/FinalizedElevenFish20261105.gd` 按 SOP 第 4.2 节精准增加 `"pbr_material": true` 分支（保留线性过滤与单材质 OPAQUE + Normal/ORM 校验，不放松未升级物种的旧断言）。
3. 严格按 SOP 第 5.2 节 6 步将 `work/blacktip_reef_shark-pbr-review-20261128/` 正式装入 `projects/fishing-2d`（含 `eleven20261105.json` 与 `blacktip_reef_shark-mouth-anchor.json` 更新、已安装 `.blend` 独立冷导逐字节一致、真实游戏 5 项运行时实机检验含 22 骨捕食与 `current_exhibit.tscn` 水下新眼部实拍、`fish-lod.res` 核验），验收报告落到 `projects/fishing-2d/plans/reviews/pbr-install-blacktip-reef-shark-20261128/`。

### 阶段二：按鲨鱼 SOP v1 放开制作剩余 4 条鲨鱼候选（逐批交付图审，未过审前不覆盖正式目录）
1. **双髻鲨批次**（3 条，可先出 **大双髻鲨 `great_hammerhead`**，再并联 **路氏双髻鲨 `scalloped_hammerhead`** + **无沟双髻鲨 `smooth_hammerhead`**，分别输出到 `work/<species>-pbr-review-20261128/`）：
   - 严格遵循 SOP 第二、三节（`Draw Call = 1`、`OPAQUE`、`1024×1024` 1:1 方图、哑光楯鳞皮革 `Roughness 0.62–0.80 / Metallic 0`、5 道凹陷鳃裂、眼角膜 `0.20–0.24` 去假灯斑）；
   - 锤头顶/底/前缘保留原分岛 UV 严禁侧投拉糊；锤头两端眼柄严格满足正交俯视 `0 px` 异常凸出，并在角膜内区温和顺平底层低模折角；
   - 完整保留各自 22 骨小猎物摄入与大猎物夹持捕食动作及上唇挂钩点。
2. **鲸鲨收尾（`whale_shark`，8 m 滤食巨兽）**（输出到 `work/whale_shark-pbr-review-20261128/`）：
   - **绝对零拓扑改动、零顶点序变动**（完整保护全部 9 个吸滤形态键与 `WhaleSharkSuctionMotion.gd` 3 口吸滤动作）；
   - 仅做 `3 surface → 1 surface` 单材质合批 + `2048×2048` 1:1 方图 `OPAQUE` PBR 三图烘焙（哑光灰蓝楯鳞 + 白斑边缘法线抑制防假凹槽 + 深棕眼 `0.20–0.24` 与鼻孔独立图块）。

完成后先汇报阶段一正式安装验收结果与阶段二候选图审材料；**先不要 push，等用户确认后统一提交推送。**
```
