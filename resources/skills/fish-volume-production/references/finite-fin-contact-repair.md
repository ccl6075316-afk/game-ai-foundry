# 有限鳍面接触返修：源、过渡与实际姿态

适用：已建立且冻结身体、原图鳍轮廓/UV/骨架后，完整鳍根通过但有限鳍面/边在实际姿态穿入身体。不是物种形态、根区、动作或最终SOP的替代验收。

## 方法和边界

1. 用不改限值的 `check_fin_membrane_collision.py` 在当前实际导出找失败顶点、唯一边四分点、重心与60/20/20内点。把 Godot/glTF 顶点按位置、UV、蒙皮映射回可编辑源；不能只查看最差边而漏掉自身穿体的端点。
2. `conform_reference_fin_contacts.py` 只细分失败的有限根面与根/自由面连接边。全根边新点继承既有完整根面所有权；混合边的新点仍是自由面。投向真实闭合身体，插值原UV，取当地身体蒙皮。原始BIN保留，只追加受影响鳍属性。源blend同步重建受影响鳍。
3. 先判断连接构造是否有解。法向所需距离为 `abs(外部间隙-根点有符号距离)`。如果它已超过内部施工边长上限，立即退出。剩余切向余量是 `sqrt(边长上限²-法向距离²)`。`build_feasible_fin_transition.py` 直接求投到实际体表后的可行连接点，不重复细分一个不可能的法向间隙。内部施工尺寸不能替代或放宽根缝/自由面验收限值。
4. 静止投点不能证明大幅身体弯曲后的有限面安全。冻结候选，完整收齐实际姿态的失败包络；包含所有失败顶点、边、面和UV重合点。在实际蒙皮基向量上测外推方向的体表法向增益。`apply_local_fin_envelope.py` 的局部位移须由这一失败包络、增益与明确余量推导，并经审核；不能全鳍盲推、改动作幅度或扩大根区。
5. 新进程读取新GLB，先跑能重现失败的实际姿态，再冻结候选集中跑全部适用门。`verify_fin_source_reexport.py` 对输入保持只读，冷读blend实际再导出，按顶点位置、UV、骨名权重匹配七鳍完整三角面，再检查NORMAL、嵌入材质像素和动画通道。它只证明源可复现，不做外观或动作批准。

## 本鱼参数与复现

尼罗罗非鱼参数在 `resources/volume-fish/nile-tilapia-fin-clearance-20261030.json`，含三个阶段的严格输入模型SHA、施工尺寸、动作测量与局部顶点清单。它是本鱼记录，不能跨物种照搬。

Blender后台调用统一为：

```text
blender -b --python resources/scripts/volume-fish/conform_reference_fin_contacts.py -- --plan <R8的fin.plan.json> --config resources/volume-fish/nile-tilapia-fin-clearance-20261030.json --output <仓库work/output/experiments下的新目录stage1>
blender -b --python resources/scripts/volume-fish/build_feasible_fin_transition.py -- --plan <stage1/fin-gate.plan.json> --config resources/volume-fish/nile-tilapia-fin-clearance-20261030.json --output <新目录stage2>
blender -b --python resources/scripts/volume-fish/apply_local_fin_envelope.py -- --plan <stage2/fin-gate.plan.json> --config resources/volume-fish/nile-tilapia-fin-clearance-20261030.json --output <新目录stage3>
blender -b --python resources/scripts/volume-fish/verify_fin_source_reexport.py -- --model <stage3/fish.glb> --blend <stage3/fish.blend> --output <验证报告.json>
```

计划中的模型路径必须是实际存在的绝对路径；脚本输出路径也解析为绝对路径。脚本拒绝覆盖已有fish.glb/blend。公共依赖从脚本自身所在的Foundry目录解析，不依赖桌面客户端或某个游戏实验目录。

本次基线1476面，有限接触返修1594面，可行过渡1710面；最终局部修正保持1710面。用户优选1500/硬上限2000，因此1710只满足硬上限。`.35mm`过渡边约束曾与`.2587mm`根内嵌加`.15mm`外间隙矛盾；旧失败保留。经用户架构复核采用`.45mm`施工上限；验收仍固定`.5mm`根缝和`.02mm`自由面容差。R8接受嘴部和身体未改。

本轮候选、失败包络、源一致性及实际验收状态读取游戏 `experiments/nile-dorsal-route-trial/round9-fin-clearance/` 的validation/handoff。不要把本方法文档或构造脚本的 `ok=true` 当作整鱼或用户外观验收。

## 静态法线源与正式导出程序

2026-10-30冷读补充检查发现：重建源网格的默认平滑法线与GLB不同，四个返修鳍最初最大分量差达1.87。普通 `normals_split_custom_set` 可改善，但Blender 4.5.3把viewport自定义法线存成`INT16_2D`；近轴分量仍有约0.005–0.007误差。完整尖锐边、重复编码和仅复制GLB顶点行的隔离试验也不能满足历史0.001分量限值。失败报告保留，不能放宽限值或把POS/UV/蒙皮通过写成NORMAL通过。

三个生产构造工具现都调用 `restore_fin_source_normals.py`：在可编辑源保存近似viewport自定义法线，同时保存精确的`_FOUNDRY_NORMAL_GLTF` FLOAT_VECTOR/CORNER静态法线。它与源几何/UV/蒙皮/材质名、对象变换、父级逆变换、骨架静止绑定的签名和法线数据签名绑定。任何非既有ARMATURE的modifier（如减面或细分）会直接阻断。修改源网格或法线后，旧签名失效，必须重新制作和复验。

正式可复现导出使用 `export_source_with_frozen_normals.py`。它读取源float属性与签名，不读取参考GLB法线；由Blender把精确角点数据与同一顶点一并导出，然后只把相关primitive的NORMAL绑定到该已导出的属性流。POSITION、UV、蒙皮、索引、嵌入图像、动画和导出BIN不改。普通Blender File Export可能仍采用viewport量化法线，不能当本源的正式复现程序。

```text
blender -b --python resources/scripts/volume-fish/export_source_with_frozen_normals.py -- --blend <fish.blend> --output <新的fish.glb> --report <导出报告.json>
blender -b --python resources/scripts/volume-fish/verify_fin_source_reexport.py -- --model <冻结参考fish.glb> --blend <fish.blend> --output <冷读完整对照.json>
```

只读验证器实际冷读源并调用以上正式导出程序，再比较参考资产。GLB对照三角面只允许三个循环顶点移位，禁止倒序对应，避免把背面剔除差异藏在任意排列中；反转单片鳍面的负例已被阻断。几何/UV/权重使用明确1e-6绝对分量比较；NORMAL历史0.001限值保持，并同时报告1e-6结果。当前本鱼七鳍NORMAL分量误差为0，全部嵌入图像字节和动画时间/输出分量精确一致。故意改源顶点或float法线的负例会在写出前阻断。新源SHA及最终状态仍以本轮报告为准，不由此文档代替验收。

只读验证器只接受明确的model/blend/output参数，拒绝已有导出作为输入，也拒绝输出与输入别名；只清理本次自己创建的临时导出，不能删除调用方证据或参考模型。诊断测量工具可在哈希证明对应时读取已有导出，但不会删除它，也不允许输出覆盖输入。


## 2026-10-30：单材质正式源与逻辑部件

采用单材质实验后，不让Godot进场临时拼UV/补色：保留已验Blender骨架/原生动作，在新源建立同一skinned mesh，几何岛仍分开，普通UV/共享atlas/材质都写入源。`build_packed_fish_source.py`以冻结单primitive为一次作者输入，`export_packed_fish_source.py`普通冷导出只读源，不读目标GLB。精确NORMAL与UV分别存在source FLOAT角点属性；UVMap负责Blender可见编辑，精确glTF UV避免双重翻V舍入，几何/属性签名同时绑定。源始终要求active与active_render都是实际材质读取的UVMap。

Blender新增CustomData层会使已持有的RNA层句柄失效。必须先建完所有层，再按名字重新获取并写值，逐loop核对原始NORMAL/UV后才签名。首轮错误句柄导致法线被UV值覆盖、exactUV全零，严格检查已阻断；不能靠法线/UV容差掩盖。Blender默认法线codec可能产生同源顶点的额外导出row；只能在最终绑定POS/NORMAL/UV/JOINTS/WEIGHTS完全相同且SOURCE_VERTEX身份相同时压紧。不同源顶点绝不互焊；清理未引用streams会改变BIN，明确报告，不冒称只改JSON。

单面组内用source POINT逻辑part/sourcevertex属性与FACE partID保留可编辑归属；导出extras.geometry_parts由实际导出ID/indices重新核对，全部三角恰覆盖一次。身体外皮和口腔仍分别标记，身体专项按二者并集；七鳍各自保存来源，不能因合材质扩大根区。材质guard验证UseNodes、四节点atlas/UVMap/BSDF/output显式Color/Alpha链、节点mute、projection、图像alpha/colorspace/packed bytes、源MASK契约。正式导出按源契约映射MASK/.5、nearest无mip、rough1/metal0/spec0，不复制目标材质JSON。

`verify_packed_fish_parity.py`比较完整1710有向三角与五组属性、RGBA逐像素、材质采样语义、原named node rest/parent/skin.skeleton、IBMs和54原生轨道。改变root rest位置/父链必须被负例拒绝，不能只看IBMs和动画。源guards另以实际Blender内存修改测试几何/法线/UV/part/节点开关/贴图解释/UV层/路径别名，均在写出前阻断。当前本鱼参数在nile-tilapia-single-material-finalization-20261030.json，实际source-finalization及失败/guard证据在游戏round11-single-material-finalization。该源固化证明不替代Godot冷读/完整鳍/身体/外观及SOP审核，最终状态由本轮实际报告给出。
