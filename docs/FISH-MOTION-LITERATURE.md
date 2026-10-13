# 045 鱼类运动文献校准

## 直接依据

- Porter et al. (2020), *Volitional Swimming Kinematics of Blacktip Sharks, Carcharhinus limbatus, in the Wild*, DOI: [10.3390/drones4040078](https://doi.org/10.3390/drones4040078). 野外自发巡游均值为 0.75 ± 0.18 BL/s、0.82 ± 0.24 Hz，尾尖峰峰振幅 0.24 ± 0.08 BL；后段屈曲 12.21 ± 3.13°，前段 8.28 ± 1.74°。后段振幅约为前段两倍，支持“前稳、后强”的巡游波。
- Whitlow, Santini & Oufiero (2019), *Convergent evolution of locomotor morphology but not performance in gymnotiform swimmers*, DOI: [10.1111/jeb.13399](https://doi.org/10.1111/jeb.13399). 论文直接将银龙 `Osteoglossum bicirrhosum` 归为亚鲹形 BCF 游泳者，并描述其约后 2/3 身体参与波动、波长向后增加。
- Di Santo et al. (2021), *Convergence of undulatory swimming kinematics across a diversity of fishes*, DOI: [10.1073/pnas.2113206118](https://doi.org/10.1073/pnas.2113206118). 44 个物种的中线实测显示传统游泳型是连续谱；因此本轮用局部实测约束振幅与波分布，而不把类别名称直接换成固定关节角。
- Porter, Roque & Long (2011), *Swimming fundamentals: turning performance of leopard sharks is predicted by body shape and postural reconfiguration*, DOI: [10.1016/j.zool.2011.06.001](https://doi.org/10.1016/j.zool.2011.06.001). 鲨鱼通过改变整身屈曲的大小与时序完成偏航转向，支持将巡游波与临时转弯弯曲分开控制。

## 参数映射

| 物种 | 上一版 | 045 文献校准 | 依据与推断 |
|---|---:|---:|---|
| 鲨鱼程序波尾端航向幅 | 0.55 rad / 31.5° | 0.21 rad / 12.0° | 直接对齐黑鳍鲨后段屈曲均值 12.21°。 |
| 鲨鱼转弯总弯曲 | 0.95 rad | 0.58 rad | 保留明显姿态重构；属于常规展缸转弯的保守推断，不模拟逃逸急转。 |
| 鲨鱼 Turn 半径系数 | 0.45 | 0.65 | 避免把常规转向表现成极限急转。 |
| 银龙程序波尾端航向幅 | 0.78 rad / 44.7° | 0.31 rad / 17.8° | 文献只给游姿分类与活动区间，绝对幅值为保守视觉推断。 |
| 银龙沿身波周期 | 0.85 | 0.67 | 让可见波主要占后约 2/3 身体，避免近一整波造成鳗形观感。 |
| 银龙转弯总弯曲 | 1.00 rad | 0.68 rad | 仍比鲨鱼灵活，但不再形成夸张 C 形。 |
| 银龙 Turn 半径系数 | 0.38 | 0.60 | 与降低后的体弯匹配，保留可读的常规转弯。 |

`body_wave_radians` 是尾端相对头部的程序化航向幅，不等于尾尖横向位移；模型自身基础动画仍以 `base_body_gain` 混合。因此鲨鱼的 12° 映射是动画控制约束，不宣称复现论文个体的完整三维中线轨迹。银龙没有可用的同类关节角实测，已明确标为从同种游姿分类作出的制作推断。
