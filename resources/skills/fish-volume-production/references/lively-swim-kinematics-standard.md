# 灵动鱼类游动运动学标准（Lively Swim Kinematics Standard v1.1 · 2026-11-28 用户实测验收定稿）

> **适用范围**：全部新鱼（`new-fish-pbr-sop-v2.md`）与现有 28 鱼 PBR 升级返修（`README-HANDOFF-GPT-ASTRA-6.2.md`）。  
> **核心目标**：从本次迭代开始，外包/协作 Agent 在升级每条鱼的模型时，**必须同步一次到位升级其 `Swim` 原生动画与对应 `motion/*.json` 游动参数**，告别“躯干发僵、鱼鳍几乎不动”的旧机械感，同时严格遵守各物种真实的生物力学边界（绝不允许把小丑鱼的拍胸鳍套到鲨鱼或金枪鱼身上）。

---

## 1. 诊断：为什么旧版游戏鱼看着偏僵，而新小丑鱼游动更灵动？

对照旧版 `projects/fishing-2d/game/assets/models/fish/motion/width20261101/sea_bass.json` 与 `FoundryFishMotion.gd` 实测，差距来自 4 个具体运动学原因：

| 维度 | 旧版常见参数（偏机械/发僵） | 新版灵动游动标准（生物力学驱动） | 视觉观感变化 |
| :--- | :--- | :--- | :--- |
| **胸鳍运动自由度** | 单轴小幅度摆动（`paired_fin_radians = 0.18` ≈ 10°），像僵硬木片前后抖 | **2 轴正交划水 + 转桨（Rowing + 90° Quadrature Feathering）**：外展推水与侧切收桨相差 90° 相位，左右异步错拍 | 瞬间产生真实的“吃水推力”与流体柔顺感 |
| **中鳍 / 腹鳍随动** | 几乎静止（`median_fin_radians = 0.065` ≈ 3.7°），背鳍/臀鳍像硬塑料板 | **相位滞后二次随动（`0.10–0.16 rad`）**：背鳍前/后叶、臀鳍、腹鳍滞后躯干 `1.0–2.2 rad` 柔顺起伏 | 鱼体转弯、加速与巡游时轮廓充满呼吸与张力 |
| **躯干行波包络** | 振幅偏保守（`body_wave_radians = 0.14`）或各节相位差偏扁平 | **头部稳像 + 尾向二次递增行波**：头骨（`body_00`）极低偏航，能量按 `d^1.4–d^1.8` 逐节传导至尾柄与尾鳍（每节滞后 `0.55–0.75 rad`） | 头部稳重自然，尾波流畅有力，不扭成“麻花” |
| **静息生命感** | 嘴部与鳃盖在 `Swim` 期间完全冻结 | **微幅静息呼吸（`1.5°–2.5°`）**：`jaw_lower`（及可选 `gill_l/r`）缓慢轻柔开合，独立于运行时 `10°–18°` 的主动张嘴/捕食动作 | 特写镜头下立即感觉“是活鱼”，而不是塑料摆件 |

> **学术与实证依据**：本标准参考鱼类游泳生物力学经典分类（Sfakiotakis et al. 1999 *Review of Fish Swimming Modes for Aquatic Locomotion*；Drucker & Lauder 2000–2005 胸鳍三维涡环与正交转桨实测；Webb 1984 推进类群划分），并结合本仓已落地的 `FoundryFishMotion.gd` 与 `FishJawActionMotion.gd` 运行时骨骼叠加契约。

---

## 2. 数学模型（Blender 原生 `Swim` 片段标准）

每条鱼的 `fish.blend` / `.glb` 内置 1 条无缝循环的 **`Swim`** 动画（默认 `60 帧 @ 30fps = 2.0s` 或按物种周期 `1.6s–3.2s`，**帧 1 与帧 61 姿态严格一致**；**仅允许旋转关键帧，禁止缩放与根节点位移**，以兼容 `FoundryFishMotion.gd` 的 `_skin_envelope` 包络校验）。

设归一化周期角 $\theta(t) = 2\pi \cdot \frac{f - 1}{N_{\text{frames}}}$：

### 2.1 脊柱行波（Travelling Spine S-Wave）
对躯干与尾骨链 $i \in \{1, \dots, M\}$（`body_00` 保持稳定 $\approx 0$，防止头部剧烈摇头）：
$$\psi_i(t) = A_i \sin\bigl(\theta(t) - \phi_i\bigr)$$
- 振幅包络 $A_i$ 沿体长向尾端单调递增（$A_i = A_{\text{tail}} \cdot (s_i)^p$，$p \in [1.3, 2.2]$）；
- 相位滞后 $\phi_i = 2\pi \cdot C_{\text{wave}} \cdot s_i$（其中 $C_{\text{wave}} \in [0.65, 1.25]$ 为体内波长数），保证波动**严格从头向尾传播**，绝非整条鱼同相左右摇摆。

### 2.2 胸鳍三轴协同划水 + 90° 转桨 + 侧视轻煽（经黑鲷 v2 用户验收定稿的核心公式）
对左右胸鳍（`Pectoral_left` / `Pectoral_right`），设外展方向 $w = (0, s, 0)$（$s \in \{-1, +1\}$ 指向体侧外方）、鳍骨自身方向 $u = \text{bone\_y\_world}$、**防穿腹严格外展轴** $a_{\text{abduct}} = R^{-1} \cdot \text{norm}(u \times w)$、**转桨轴** $a_{\text{feather}} = (0, 1, 0)_{\text{local}}$（骨局部 Y 轴）、**侧视上下划水轴** $a_{\text{scull}} = R^{-1} \cdot w$，划水倍频 $k \in \{1, 2\}$，左右异步相位差 $\Delta\phi_{LR} \in [0.45, 1.0]\text{ rad}$：
$$\text{abduct}(t) = A_{\min} + A_{\text{sweep}} \cdot \frac{1 + \sin\bigl(k \cdot \theta(t) - \phi_s\bigr)}{2} \quad (\text{严格 }\ge A_{\min} > 0\text{，100\% 防穿腹！})$$
$$\text{feather}(t) = A_{\text{feather}} \cdot \cos\bigl(k \cdot \theta(t) - \phi_s\bigr) \cdot s \quad (\text{滞后 }90^\circ\text{ 的正交转桨/吃水攻角})$$
$$\text{scull}(t) = A_{\text{scull}} \cdot \sin\bigl(k \cdot \theta(t) - \phi_s + 0.45\bigr) \cdot s \quad (\text{侧视/3/4 清晰可读的上下 8 字轻煽})$$
合成顺序保持 `Q = Q(abduct) * Q(feather) * Q(scull)`（与运行时 `native_feather: true` 分解顺序严格一致！）。
- **防穿模硬约束**：外展角全程 $\ge A_{\min} \ge 0.14\text{ rad}$（`~8°–9°`），并在 `motion/*.json` 中用 `fin_motion_constraints.minimum_radians >= 0.12` + `native_feather: true` 双重锁底，俯视与仰腹均零穿腹。
- **侧视可读性教训（黑鲷 v1→v2 用户实测验证！）**：仅做 1 倍频小幅外展（如 `k=1, 8.5°–25°`）在俯视虽明显，但侧面看被透视压缩、显得发“懒”；水族馆慢游的硬骨巡游鱼（如黑鲷/真鲷/海鲈）采用 **`k = 2` 轻快浮力节律（约 1 Hz）+ 外展 `9°–31°` + `±13.5°` 转桨 + `±8°` 侧视上下轻煽** 后，侧面/斜侧/俯视均呈现极佳的真实活力（已获用户实机验收，可参考代码模板 `work/black-seabream-lively-swim-20261128/author/upgrade_seabream_swim.py`）。

### 2.3 中鳍与腹鳍二次随动（Secondary Trailing Lag）
对背鳍（`dorsal_00`、`dorsal_01`）、臀鳍（`anal_00`）、腹鳍（`pelvic_l`、`pelvic_r`）：
$$\alpha_{\text{fin}}(t) = A_{\text{fin}} \cdot \sin\bigl(\theta(t) - \phi_{\text{fin}}\bigr)$$
- $\phi_{\text{fin}}$ 必须**滞后于其附着躯干骨 `0.5–0.9 rad`**，产生真实水阻拖曳感；
- 左右腹鳍可带 `0.4–0.6 rad` 异步相位差，增加轻盈平衡感。

### 2.4 静息呼吸微动（Calm Idle Breathing Pulse）
对带可动下颌的鱼（`jaw_lower`），在 `Swim` 片段内叠加柔和、低幅度的呼吸脉冲：
$$\beta_{\text{jaw}}(t) = A_{\text{breath}} \cdot \frac{1 - \cos(\theta(t))}{2}, \quad A_{\text{breath}} \in [0.025, 0.045]\text{ rad}\ (\approx 1.4^\circ\text{–}2.5^\circ)$$
- **硬要求**：回位必须平稳贴近闭口微缝，绝不能在普通游动中大张嘴；运行时触发的 `MouthOpen`（`10°–18°`）或鲨鱼 `Feeding` 动作在其上干净叠加。

---

## 3. 五大鱼类运动类群实证参数表（按物种查表执行）

> **铁律**：禁止全鱼套用同一套参数！制作每条鱼前，必须先按 `swim-evidence.md` 归入下表对应的运动类群，再取对应区间参数。

| 运动类群 | 代表物种 | 周期 `Swim` | 脊柱波 `body_01 → tail_01` (rad) | 胸鳍倍频 `k` & `sweep / feather` (rad) | 胸鳍左右相位差 | 中鳍 / 腹鳍随动 (rad) | 对应 `motion/*.json` 推荐升级值 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. 礁区胸鳍划水型 (Labriform / MPF)** | **公子小丑鱼**、蓝鳃太阳鱼、蝴蝶鱼、河豚类 | `1.8–2.2s` | `0.04 → 0.28–0.32`（`C=0.80`） | **`k = 2`**，`sweep 0.30–0.38` / **`feather 0.16–0.22`** | `0.75–1.05 rad`（轻快交替划水） | 背/臀 `0.10–0.15`，腹 `0.08–0.12` | `body_wave_radians: 0.18–0.22`, `paired_fin_radians: 0.34–0.40`, `median_fin_radians: 0.12–0.15` |
| **2. 亚鲹科通用巡游型 (Subcarangiform · 黑鲷 v2 用户验收标杆)** | **黑鲷✅、真鲷、海鲈、大黄鱼、鲤鱼、草鱼、鲫鱼、虹鳟、褐鳟、大西洋鲑、梭鲈、罗非鱼、孔雀鲈、食人鱼、红皇帝鱼** | `2.0s` | 头稳 `0.7°`，`body_01 0.9° → 尾柄 12.2° → 尾鳍 16.5°`（`C≈0.85`） | **`k = 2`（水族馆浮力节律 ~1 Hz）**：外展 `9°–31°`（`0.16–0.54 rad`）/ **转桨 `±13.5°`（`±0.24 rad`）** / **侧视轻煽 `±8.0°`（`±0.14 rad`）** | `0.70–0.85 rad` | 背 `10.5°` / 臀 `11.5°`（`0.18–0.20 rad`），腹外展 `8°–20°` + `±6.5°` 转桨；下颌呼吸 `2.4°` | `body_wave_radians: 0.18–0.22`, `paired_fin_radians: 0.34–0.42`（配 `native_feather: true`）, `median_fin_radians: 0.14–0.18`, `native_jaw_breath: true` |
| **3. 金枪鱼高速巡航型 (Thunniform)** | **太平洋蓝鳍金枪鱼、大西洋旗鱼、鲯鳅** | `1.5–1.9s` | 前半身极稳 `0.01 → 0.04`，后 1/3 尾柄骤增 `0.24–0.30`（`p ≈ 2.2`） | **`k = 1`**，`sweep 0.08–0.14` / `feather 0.04–0.07`（高速水翼微配平） | `0.20–0.35 rad` | 仅尾叉与第二背/臀鳍微幅 `0.04–0.07` | `body_wave_radians: 0.16–0.19`, `paired_fin_radians: 0.12–0.16`, `median_fin_radians: 0.06–0.08` |
| **4. 鳗形/长体全身波浪型 (Anguilliform / Long-body)** | **带鱼、银龙鱼、巨骨舌鱼、非洲鲇鱼** | `2.2–2.8s` | 全身多节连续大行波 `0.05 → 0.34–0.42`（`C=1.05–1.30`） | **`k = 1`**，`sweep 0.22–0.30` / `feather 0.12–0.16`（带鱼无腹鳍、胸鳍轻摆） | `0.50–0.80 rad` | 长背/长臀鳍随脊柱逐段波浪 `0.12–0.18` | `body_wave_radians: 0.24–0.30`, `body_wave_cycles: 1.05–1.25`, `paired_fin_radians: 0.24–0.30`, `median_fin_radians: 0.14–0.18` |
| **5. 软骨鲨鱼滑翔巡游型 (Carangiform-Shark)** | **黑鳍礁鲨、大双髻鲨、路氏双髻鲨、无沟双髻鲨、鲸鲨** | `2.6–3.4s`（鲸鲨更缓 `3.8–4.5s`） | 沉稳宽幅尾部推波 `0.02 → 0.22–0.28`（头部保持轻微左右平衡摆 `0.03–0.05`） | **刚性水翼！绝不拍打！** 仅极微弱纵倾配平 `sweep 0.03–0.05` / `feather 0.02–0.03` | `0.0 rad`（对称稳定水翼） | 背鳍几乎刚直 `0.02–0.04`，尾鳍随尾柄延迟屈曲 | `body_wave_radians: 0.18–0.22`, `paired_fin_radians: 0.05–0.08`, `median_fin_radians: 0.04–0.06` |

> **扩展类群提示（未来新增非标准体型）**：
> - **蝠鲼/鳐类（Rajiform / Mobuliform）**：推进动力完全在宽大胸鳍的**前后行波翼拍（Wing-beat wave）**，躯干与鞭尾仅被动微随。
> - **海龟类（Subaqueous Flight）**：前肢做 8 字形升力扑翼（`sweep + pitch + roll` 三轴协同），后肢充当方向舵。
> - **头足类/多触手（章鱼/鱿鱼）**：外套膜脉动收缩 + 触手多段相位滞后波浪拖曳。

---

## 4. 与游戏运行时 `FoundryFishMotion.gd` 的衔接规范

1. **Blender / GLB 侧（必做，所有 Agent 每次交付必含）**：
   - `Swim` 片段必须直接内置完整的 **脊柱行波 + 2 轴胸鳍正交划水/转桨 + 滞后中/腹鳍随动 + 微幅静息呼吸**；
   - 这样在任何独立预览器、棚拍 QA 与直接播放 `AnimationPlayer.play("Swim")` 的场景（如大型生态展缸）里，**开箱即呈现完整的灵动游动效果**！
2. **游戏 `motion/*.json` 侧（正式安装与存量升级时同步更新）**：
   - 在 `projects/fishing-2d/game/assets/models/fish/motion/width20261101/<species>.json` 中，按上表第 8 列同步调优 `body_wave_radians`、`body_wave_cycles`、`paired_fin_radians`、`median_fin_radians`（同时保持 `fin_motion_constraints` 的 `minimum_radians >= 0.12` 与 `envelope_radius_m` 包络验证 100% 通过）。
   - 黑鲷样板已验证显式启用的双轴约束。在对应胸鳍约束设置 `native_feather: true`，以骨局部 Y 为鳍轴，按“外展 × 轴向转桨”编排原生旋转。运行时先从原生四元数分解转桨，再限制外展，最后依原顺序合成。启用时外展下限至少 0.12 rad。旧动画沿用旧约束。候选的 `native_jaw_breath: true` 让张嘴按钮从当前呼吸姿态过渡到已验峰值；真实展缸里须检查物种行为层最后一次写入的姿态。鲨鱼按刚性水翼逐种验，不复制黑鲷配置。[黑鲷样板、门禁和全库基线](../../../volume-fish/black-seabream-swim-20261128/HANDOFF.md)
3. **不破坏现有交互动作契约**：
   - `jaw_lower`（或旧骨架 `LowerJaw`）的本地旋转轴必须经 Godot 实测验证**向下张嘴**（参考公式：`(global_rest.basis.inverse() * Vector3(0, 0, 1)).normalized()`）；
   - 严禁改变 `upper_lip` 上唇挂载点与现有 `FishJawActionMotion.gd` 所需的骨名契约。

---

## 5. Stage 5 游动灵动度验收门禁（硬核验）

每条鱼在提交前，必须在 Godot 实机（棚拍 + 真实 `current_exhibit.tscn`）确认以下 5 项，否则打回返修：
1. **无缝循环**：`Swim` 首尾帧零跳变，且仅含旋转通道（`FoundryFishMotion.gd` 校验通过）。
2. **胸鳍活度与防穿模**：俯视（`02_turn_top.png`）与仰腹（`06_ventral_belly.png`）在胸鳍最大内收/外展相位均**零穿模进侧腹**；硬骨鱼可见清晰划水+转桨姿态变化，鲨鱼则保持刚性水翼稳定滑翔。
3. **中鳍跟随**：背鳍/臀鳍/尾鳍在游泳相位呈现流畅的滞后弯曲，无“硬木板直挺挺”感，也无断裂脱根。
4. **头部稳像**：`body_00` 无剧烈左右甩头（偏航 `<= 0.04 rad`），眼睛与嘴部自然稳重。
5. **主动张嘴与呼吸分明**：巡游静息呼吸克制（`1.5°–2.5°`），触发 `M` / 展厅张嘴按钮时下颌干净向下展开（`10°–18°`），无圆孔嘴、无上翻穿模。
