# 通用单材质 PBR 鱼类升级流水线 — 外部 Agent（GPT Astra 6.2）操作交接手册

> **设计目标**：服务「珠海长隆级大型海底世界（未来 300+ 鱼种、超多鱼同屏群游）」——**严格锁死单网格 + 单材质（`Draw Call = 1`）**，显存较旧版直降 **90%–97%**，同时提供水下焦散与鱼群集体转向银鳞反光。
>
> **基准已落地物种**：**真鲷（`red_seabream`）** 已通过本流水线正式合入 `projects/fishing-2d`（`2,810` 面、`2,685` GPU 顶点、`1` Draw Call、`3.85 MB` GLB、`16.0 MB` 未压缩 / `4.0 MB` BC7 显存、`8/8` 硬门禁 + 展厅张嘴 + 钓鱼上唇挂钩实测全通过）。

---

## 一、硬性技术合同（任何物种均不得违反）

| 指标 | 硬门禁标准 | 说明 |
|---|---|---|
| **网格 / 材质数** | **`1` Mesh / `1` Surface（`Draw Call = 1`）** | 严禁拆成 2–3 个材质槽，保底超多鱼群绘制次数 |
| **透明与深度模式** | **`alphaMode: MASK`，`alphaCutoff: 0.5`，`doubleSided: true`** | 必须保留硬件深度写入，杜绝斜角“后鳍挡前鳍” |
| **PBR 贴图组合** | **3 张图**：`Albedo` + `Normal`（切线空间）+ `ORM`（R=AO, G=Roughness, B=Metallic） | Normal/ORM 均由全精度图 2×2 超采样降分辨率并做切线法线重归一化 |
| **体型分级显存** | **`--tier large`**：`2048×1024` Albedo + `1024×512` Normal/ORM（未压缩 `16 MB` / 硬件压缩 **`4 MB`**）<br>**`--tier small`**：`1024×512` Albedo + `1024×512` Normal/ORM（未压缩 `8 MB` / 硬件压缩 **`2 MB`**） | 主力大鱼（>1 m / 招牌种）用 `large`，常规中小群游鱼用 `small`（法线保持 `1024×512` 确保鳞片凹凸锐利）；300 种鱼全常驻仅 `~700 MB`（开 VRAM 压缩） |
| **骨架 / 动作 / 钓鱼锚点** | 保留全部原骨骼与 `Swim` 轨道；`jaw_lower` 张嘴满幅；上唇挂钩点误差 `< 2 mm` | 通过 `verify_fish_pbr_gate.gd --dump-mouth-recipe` 自动导出精确 UNORM16 配方 |

---

## 二、工具清单与两种执行模式

核心文件位于 `resources/scripts/fish-pbr-pipeline/`：
- `upgrade_fish_pbr.py` — Blender 5 通用升级脚本（**外部 Agent 禁止自行改写核心算法**）
- `verify_fish_pbr_gate.gd` — Godot 4.7 硬门禁校验 + 4 视角标准截图 + 自动导出 `*-mouth-anchor.json`
- `configs/red_seabream.json` — 真鲷精雕参数模板

### 模式 A：`--mode fast_pbr`（推荐默认，覆盖 90% 常规物种，零物种配置！）
* **适用**：中小群游鱼、批量快速把全馆 27 条鱼升级成单材质轻量化 PBR（已用 `black_seabream` 实测 8/8 通过：`1.27 MB` GLB、`4.0 MB` 未压缩 / `1.0 MB` BC7 显存、`0.00 mm` 上唇误差、连续双侧 UV 无面片折痕）。
* **原理**：不动原拓扑/原嘴型/原蒙皮权重，自动把碎片化旧身体 UV 重烘为连续双侧 UV、自动识别所有鱼鳍并无损打包进右半图集、写入空间法线锥平滑拆分页法线（消除旧散面在 PBR 下的钻石切面感）、生成像素锁定 Normal/ORM 并导出单材质 `MASK(0.5)` GLB。

```bash
# 1. Blender 5 转换（以 black_seabream 为例，中小群游鱼选 --tier small，大型招牌鱼选 --tier large）
/Users/czl/.gamefactory/toolchain/blender5/Blender.app/Contents/MacOS/Blender \
  -b projects/fishing-2d/assets/source/fish/<species>/fish.blend \
  --python resources/scripts/fish-pbr-pipeline/upgrade_fish_pbr.py -- \
  --species <species> --mode fast_pbr --tier small \
  --out-glb /tmp/pbr_out/<species>/<species>.glb \
  --out-blend /tmp/pbr_out/<species>/fish.blend

# 2. Godot 4.7 硬门禁 + 4 张验收图 + 自动导出精确钓鱼上唇配方（large 传 --max-vram-mb 16.5，small 传 8.5）
/Users/czl/.gamefactory/toolchain/godot/Godot_mono.app/Contents/MacOS/Godot \
  --path projects/fishing-2d/game \
  --script resources/scripts/fish-pbr-pipeline/verify_fish_pbr_gate.gd -- \
  --species <species> \
  --glb /tmp/pbr_out/<species>/<species>.glb \
  --out /tmp/pbr_out/<species>/qa \
  --max-vram-mb 8.5 \
  --dump-mouth-recipe /tmp/pbr_out/<species>/<species>-mouth-anchor.json
```

### 模式 B：`--mode sculpt_pbr --config <species.json>`（仅用于重点主角鱼：立体眼球 + 鳃盖精雕）
* **适用**：需要立体 3D 凸起眼球与鳃盖/头吻局部精雕的重点鱼（参考真鲷 `configs/red_seabream.json`）。
* **操作方式**：复制 `configs/red_seabream.json` 为 `configs/<species>.json`，只测填目标鱼的 `eye.center_right`、`eye.radius`、`body_bounds_xz`、`upper_lip_anchor`、`fin_src_uv_boxes`、`operculum`（鲨鱼类设 `operculum.enabled = false`），然后跑与模式 A 完全相同的命令（把 `--mode fast_pbr` 换成 `--mode sculpt_pbr --config resources/scripts/fish-pbr-pipeline/configs/<species>.json`）。

---

## 三、已由脚本兜底的 5 个致命坑（切勿人工绕过）

1. **Blender 5 `MASK` 导出坑**：Blender 5 必须把 `Albedo.Alpha` 经 `ShaderNodeMath(GREATER_THAN, 0.5)` 连入 `Principled BSDF.Alpha` 才会导出 `alphaMode="MASK"`；直接连 Alpha 会导出成 `BLEND`，导致斜角**后鳍挡前鳍**。
2. **3D 眼球急转弯漂移坑**：眼球不可写死绑 `body_00`，必须按眼眶环真实骨权刚性绑定（`upgrade_fish_pbr.py` 已自动采样）。
3. **口腔串色与唇沿锯齿坑**：严禁细分跨过嘴缘，必须直接读取原 `fish.blend` 专用口腔 UV 带（`u > 0.955, v < 0.025`）。
4. **旧散面 PBR 钻石切面坑**：旧鱼体多为碎片 UV + 散面，必须经连续双侧 UV 重烘 + 空间法线锥平滑法线才可上 PBR 高光。
5. **运行时 PBR 材质洗白坑**：`FinalizedWidthBatch20261101.gd` 已支持在 `manifest.json` 对应物种上设置 `"pbr_material": true`；`FishInstanceFactory.gd` 也已自动保留含 Normal/ORM 贴图的 PBR 材质。

---

## 四、单鱼正式入库验收清单（必须全部为真才能覆盖正式文件）

1. `verify_fish_pbr_gate.gd` 输出 `FISH_PBR_GATE_JSON` 中 **`"ok": true`**（所有子项均为 `true`）。
2. 人工 / 视觉逐张查看 `qa/` 下 4 张实机渲染图，确认无异常：
   - `01_swim_3q.png`：体表平滑无钻石切面、鳞片/鳍条清晰、无色渗；
   - `02_turn_top.png`：俯视转向脊柱顺滑、双眼紧贴眼眶、背鳍居中不裂；
   - `03_jaw_closeup.png`：张嘴口腔内壁干净无白块、上下唇沿无污点；
   - `04_rear_fins_depth.png`：后斜角前侧腹鳍/胸鳍严格遮挡远侧鳍，无前后倒挂。
3. **独立冷导一致性校验**：从生成的 `fish.blend` 重新冷导出 GLB，确认与 `out-glb` 的 `shasum -a 256` **逐字节一致**。
4. 正式替换 `projects/fishing-2d/game/assets/models/fish/<species>.glb`、`projects/fishing-2d/assets/source/fish/<species>/fish.blend` 与自动导出的 `*-mouth-anchor.json`，更新对应 `manifest.json`（`model_sha256`、`triangles`、`"pbr_material": true`、`mouth_recipe.sha256`）。
5. 跑真实游戏 `FishInstanceFactory.create_display()` / `create_fishing()` / `FishingVolumeFish.bind_upper_lip()` 与展厅张嘴测试确认全过。

---

## 五、可直接复制给 GPT Astra 6.2 的任务指令模板

```text
请严格按照 `resources/scripts/fish-pbr-pipeline/README-HANDOFF-GPT-ASTRA-6.2.md` 的流程，将物种 `<species>` 升级为单网格单材质 PBR 资产（Draw Call = 1）。

硬性要求：
1. 不要修改 `resources/scripts/fish-pbr-pipeline/upgrade_fish_pbr.py` 的核心算法；常规鱼直接使用 `--mode fast_pbr`（中小群游鱼 `--tier small`，大于 1 米招牌鱼 `--tier large`）。
2. 先在 `/tmp/pbr_out/<species>/` 输出候选 GLB 和 blend，并运行 `verify_fish_pbr_gate.gd`（附带 `--dump-mouth-recipe`）。
3. 必须检查 `FISH_PBR_GATE_JSON` 的 `"ok": true`，并亲自读取查看 `qa/01_swim_3q.png`、`02_turn_top.png`、`03_jaw_closeup.png`、`04_rear_fins_depth.png` 确认无切面、无嘴角白块、无后鳍挡前鳍。
4. 通过独立冷导 SHA-256 逐字节校验后，再展示 4 张验收图与门禁报告让我确认是否正式替换游戏文件。
```
