# 两件大型活珊瑚

2026-11-24 用户确认两件预览并要求提交。游戏 `758b4bcc` 注册了原样发布的两件 GLB。当前目录共 102 件，32 件可选覆藻。

| 造景 | 默认最长尺寸 | 三角面 | 组合用途 |
|---|---:|---:|---|
| 大型活麋角珊瑚 | 2.70 米 | 954 | 加勒比浅礁，以层叠板枝作为礁台主景 |
| 大型活团块珊瑚 | 2.15 米 | 854 | 印太暖礁，以连成一体的团块承接中景 |

麋角珊瑚以加勒比 `Acropora palmata` 的浅水尺度和板枝群体形态为依据。团块珊瑚采用印太的滨珊瑚团块生长型。 [NOAA Fisheries](https://www.fisheries.noaa.gov/species/elkhorn-coral) · [澳大利亚博物馆 Lizard Island Field Guide](https://lifg.australian.museum/Group.html?groupId=f1c5pokN)

沿用 [六面意向方法](../ORTHOGRAPHIC-METHOD.md)。宽枝和团块先落实为连续实体，再用六面原画最近邻取色。生长底面归零，整件闭合，使用一个不透明表面及一张 2048 × 2048 图集。两件按米级刚性造景沿用 `large_rock` 的 700 三角优选 / 1000 硬上限，数值与候选期使用的代理档位一致。珊瑚为静态造景模型，活体观感来自形态和材质。六面来源、可编辑源、体积参数和 GLB 哈希见 [发布清单](release.json)。

扩充组连同六件礁块共 52 件通过标准预算和几何检查。两件归一化顶点分布均与原目录不同。用 Blender 5.0.1 重建两件 GLB，字节与发布版本一致。另冷开正式 Blender 源核对位置、UV、法线和内嵌图集。 [重建入口](rebuild.py) · [预算报告](budget.validation.json) · [Blender 校验](blender.validation.json)

Godot 4.7.1 冷读正式目录，在实际 15 × 8 × 5.1 米缸包络中验到 102 件摆放、接地及临时存档变换回读。两件各按默认尺寸附在各自暖礁组合的真实岩面，前方留出 1.30 米通道。32 个覆藻开关也通过回读。 [摆放报告](placement.validation.json) · [组合报告](composition.validation.json) · [加勒比麋角珊瑚](evidence/caribbean-elkhorn.webp) · [印太团块珊瑚](evidence/indo-pacific-massive.webp) · [覆藻报告](algae.validation.json)

可在原生审查窗搜索两件中文名，查看正式材质和灰模。 [Mac 入口](../surface-repair-20261124/review/open-review.command) · [Windows 入口](../surface-repair-20261124/review/open-review.cmd)
