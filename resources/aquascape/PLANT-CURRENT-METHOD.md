# 原画水草的骨骼微流

适用已生成且审核过的水草叶片网格。先复用原画和资产清单，确认原 workflow 为 done/human_review；仅加骨骼动作不重跑生图。几何和材质是否已最终验收须另记，不能由动态检查替代。

## 约束

根茎、攀附根与叶片基部的 8% 区域固定。每片叶子使用五节真实 glTF 骨骼：一节固定基部、四节弯曲。中间关节平滑过渡，叶尖随弯曲产生滞后感；不能整株平移/旋转，也不能只滚动贴图。

沿原画 UV 的上下方向确定叶长参数，按模型原有源图姿态建立骨架 rest frame、inverse bind 和相邻双骨权重。mesh 的 positions、normals、UV、拓扑以及生成贴图保留原字节。根茎与细根全部绑定固定根骨。附件原点来自该株 profile，而不是另一物种的骨架。

小水榕 `Anubias barteri var. nana` 的厚叶幅度小；爪哇蕨 `Microsorum pteropus` 的长叶幅度稍大。`plant-current-v4.json` 分别提供关节角、侧摆/扭转比例、相位与可接受位移范围。共享十秒水流基频，每叶错开相位并叠加较弱整数倍频，维持自然错动和闭合循环。当前 clip `WaterSway` 以 30 Hz 烘焙 quaternion 动画；Godot 播放原生骨骼/蒙皮，无顶点摆动 shader。

## 检查

`rig_plant_current.py --input <参数> --output <模型目录> --root <Foundry根目录>` 在既有 GLB 上追加骨骼，写 `rig.handoff.json`。

`validate_plant_current.py --input <模型目录> --config <参数> --root <根目录> --output <报告>` 对实际序列化结果验 source bytes、bind pose、权重、81 个完整姿态的所有固定顶点、逐叶叶尖位移与循环端点。Godot 导入后还须读取实际 Skeleton3D/Skin/权重和原生 AnimationPlayer，在多相位采样实际 skin bind 下的固定/叶尖点，再看正面/侧后/灰模和完整循环录像；不能用 CPU 导出成功替代引擎成功。

通用 Godot helper `resources/runtime/godot/aquascape/PlantCurrent.gd` 只负责共同时间、原生 clip 播放与暂停。模型、动作与现场截图/录像哈希进入本次 validation report。验证不会证明全连续时间无叶片互穿，也不会修复原有静态三维姿态的缺陷。

## 延伸范围

海葵需固定附着基盘、给每条触手独立柔性骨骼，不能直接复制阔叶水草权重；软珊瑚或可见珊瑚虫也不能统一当作完全静止。硬珊瑚的骨架可固定。当前只实现两种水草，并未生成海葵或珊瑚资产。
