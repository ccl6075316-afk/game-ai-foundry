# Architecture Plan: 巨骨舌鱼头部正侧贴图归属

## Evidence and Scope

v14 前视重影眼睛的像素射线落在 `Closed_body`，位置约 u=0.92，表面法线 `(0.63, ±0.77, 0.07)`；正面覆盖限值 0.65 排除了这些面。侧视同一原生源图的眼睛应保留。v12 把正面图覆盖到侧腹，侧视眼鳃变形；v13 加宽头部后变形加剧。本阶段只重做头部纹理归属，不改鱼身上下轮廓、骨骼、其他物种或游戏交互。

## Module Boundaries

### Profile validation (`cli/volume_fish.py`, `resources/scripts/volume-fish/build_fish.py`)

- **Responsibility:** 校验可选的头部底图捐赠区域和朝向范围。
- **Inputs:** `head_projection.underlay_donor` 的 `source_rect`、`offset`、`front_normal_min`、`side_normal_range`。
- **Outputs:** 有限、在原图边界内的冻结 profile；无新状态文件。
- **Invariants:** 未配置该字段的鱼保持原行为；不得接受越界 UV、非有限值或未知字段。

### Blender builder (`resources/scripts/volume-fish/build_fish.py`)

- **Responsibility:** 仅在指定原生侧图眼区、且面朝前斜侧的底层身体面，将 UV 移到同一张已接受侧图中的邻近无眼皮肤；纯侧面保留原眼。正面叠层仍使用已接受正图。
- **Inputs:** 已冻结的双源 handoff、profile 和源图。
- **Outputs:** 闭合、蒙皮、nearest、可导出的 `.blend`/`.glb`；验证报告记录被处理的面数。
- **Invariants:** 不修改源 PNG，不向游戏加入视角相关着色器；面级 UV 岛整体平移，避免一面内跨过被移除的眼图案。

### Arapaima profile and review

- **Responsibility:** 只为巨骨舌鱼标定源图眼区、捐赠偏移与正侧交界；以 v12 几何为基础。
- **Inputs:** 已接受侧/正原画、同机位 v11–v14 三视。
- **Outputs:** 新版本 profile/handoff 和四张审核图。
- **Invariants:** `style_visual_review=pending` 直到三视与 Godot 实景均无重眼、眼鳃拉伸和明显接缝。若圆桶外轮廓仍违背用户关注点，候选不进入游戏。

## Interface Definitions

`underlay_donor` 只在 `head_projection` 下有效：

```json
{
  "source_rect": [0.901, 0.445, 0.945, 0.565],
  "offset": [-0.055, 0.0],
  "front_normal_min": 0.5,
  "side_normal_range": [0.65, 0.9]
}
```

`source_rect` 是侧面原画归一化 `[左,上,右,下]`；`offset` 是同图捐赠像素位置的归一化位移；两个法线条件都按鱼头方向和左右绝对值解释。构建器只给与该矩形相交且满足法线条件的前斜侧身体多边形换 UV，其他面保持原生 UV。此字段不给未带正面原画的 profile 使用。

## Log Specification

延续现有 `validation.json`，在 `metrics` 增加确定性的 `underlay_donor_faces` 计数；无额外日志文件、请求或随机数。CLI 失败沿用 `failures[].code/kind/message`。

## RTK Filter Presets

此机器没有 `rtk`；使用 `python cli/gamefactory.py volume ... --json`、`python -m unittest cli.test_volume_fish`、`git diff --check`，限制输出到失败摘要和必要的构建指标。

## Critical Patterns Check

已读 `docs/solutions/patterns/critical-patterns.md`；其中历史 ACP/JSON-RPC 条目与 Blender 网格路径无关。本设计不新增会话、配置或网络依赖。

## Simplicity Audit

只加一个可选 profile 区块及一段面级 UV 归属逻辑；不引入通用材质图节点系统，也不改其他鱼。删除底图归属逻辑会重现 v14 正面双眼；删除正面叠层会丢失接受的正面原画。因此没有可删掉的半套实现。

## Gate Condition

- [ ] 同一前视相机确认 `Closed_body` 的双眼像素归属被移出，而纯侧视眼仍在。
- [ ] 四张 Blender 审核图和侧/正原画对照无双眼、鳃纹拉伸、明显接缝或口部失真。
- [ ] Godot 展厅正面、侧面、斜视及动作中仍可信；未通过则不 `accept`、不替换旧 GLB。
- [ ] 机械验证、既有 CLI 单元测试、差异检查通过；代码审查通过。

## Design Revision After v15 Review

v15 的眼区底图 UV 捐赠被视觉审核否决：同一斜侧面在正视和侧视都可见，移除底图眼睛也会移除侧视眼睛。其代码已撤回，v15 仅保留诊断产物，不作为正式模型。

新的最小结构是可选的**弧形前脸薄壳**，而不是修改底层侧图。`head_projection.face_shell` 在已接受正面 PNG 的指定矩形与鱼头几何之间建立一个闭合、蒙皮的浅凸面：正面遮住侧图眼区，侧面投影变薄，原侧图保留。现有 `head_projection` 面覆盖方式作为未启用 face_shell 的兼容路径。薄壳参数只描述横向宽度、上下范围、前端 x 位置、两侧后退量和正面源图矩形；所有值由 profile 冻结且受 CLI 与 Blender 双重校验。材质仍是 nearest、非金属、原尺寸已接受正图，不生成或改写 PNG。

新的失败门槛：正面必须保有两只清晰眼睛和嘴线、没有侧图重眼；侧面必须保有原图眼鳃，不能出现突出的平板边缘；斜视不能出现悬浮贴片或露白。任一不满足则保持 `style_visual_review=pending`，不复制进游戏。

## Visual Gate Results and Next Design Boundary

v16 的独立前脸薄壳虽通过闭合网格及贴图机械检查，侧面仍露出矩形边缘，斜视出现黑条；已撤回代码。v17 不加构建器代码，只用已有 `body_uv_patches` 和 `eyes.surface_patch` 拆出侧眼；前视仍是圆桶轮廓且眼上有碎纹，侧视重眼。两版均未验收、未进入游戏。

后续实现不能再依靠一张投影面片或对原生侧图眼区做局部 UV 位移。下一次设计应将**头肩外轮廓**与**双图纹理归属**作为各自可验证的输入：先按用户最在意的视角确定额头、眼、吻、下颌和肩部的三维边界，再把正、侧图分别展开到同一连续头表面的明确区域；正面源图中的后躯透视部分不可直接作为头部贴图。开始构建前需画出对应关系，审核通过后才增加通用 builder 能力。
