# 造景六面材质与实体返修

2026-11-24，用户确认本次实机预览并要求提交。修正全目录审查发现的 30 件大面积铺色拉伸，加上 1 件半球脑纹硬珊瑚的实体沟纹。游戏提交为 `6a4f0d5a`，按原登记的路径替换 31 个 GLB。目录仍为 100 件，32 件可选覆藻。两件大型活珊瑚处于本地候选阶段。

## 打开原生审查窗

使用当前的 Foundry 与 `projects/fishing-2d` 游戏检出，并拉取 Git LFS。Mac 打开 [open-review.command](review/open-review.command)，Windows 打开 [open-review.cmd](review/open-review.cmd)。游戏资源先在后台导入。Mac 窗口在主屏可用区域居中，保留前台焦点。Windows 启动器按现行 Godot Mono 路径编写，本轮实机在 macOS 验证。

可以筛选 31 件修版和 32 件覆藻对象，固定角度看原材质与覆藻，并独立拖动覆盖面积和浓淡。六个正交视角和灰模适用于全目录。审查滑杆是本窗口的预览参数，游戏内仍使用现有的「藻覆盖」开关。用 `--before` 启动时，从上一个游戏提交校验并缓存 31 件旧模型，可并排比较新旧材质和灰模。

## 方法与源

以六面材质板确定识别特征和主要凸凹位置，按旧件占地、底面和腔体约束在网格上塑造石层、坑槽、木根和珊瑚沟纹。25 件经过实体编辑，6 件保存原 POSITION/NORMAL 数据并从六面重新投影上色。阶台灰岩、青灰叠层石和剥皮老木段另外对齐顶视占地轮廓。每件使用一个不透明表面和一个最近邻图集，完整实例面数按原类别记账。主要参数、图集六面来源、原始 PNG SHA、可编辑 Blender、已发布模型 SHA 及取样结果都在 [release.json](release.json)。

[重建脚本](rebuild.py)读取已归档六面板和上一版 GLB，可在游戏目录外生成候选。已重建全部 31 件并验证 GLB 与发布字节一致。先通过 [prepare_baseline.py](review/prepare_baseline.py)准备旧件，再执行 `rebuild.py --baseline <旧件目录> --output <临时目录> --blender <Blender 5 可执行文件>`。维护时以当前 [Blender 源](source/)为准。用 [verify_blender.py](verify_blender.py)冷开可对照每个角点的位置、UV、法线和内嵌图集。

## 实机交付证据

- 31 件完整实例在原类别硬上限内，网格闭合，保持各自原网格的连通分量与欧拉特征。六件带穿口的物件各通过原通道核心的 81 条离散射线。旧件入口、底面与顶壁的适用采样也保持通过。射线只覆盖取样过的通道，不代表任意鱼体的导航。
- 31 件正式导入资源从独立 Godot 进程抓取 248 张材质角度及 248 张灰模角度，与已看候选同视角对照。另实看审查窗的新版/旧版、灰模和双方同角度的覆藻强度、面积。审查窗核对 20 件旧水草的已有水流或骨骼播放绑定。 [代表实拍](evidence/review-highlights.webp) · [逐件实拍 1](evidence/fixed-01.webp) · [2](evidence/fixed-02.webp) · [3](evidence/fixed-03.webp) · [4](evidence/fixed-04.webp) · [覆藻滑杆实拍](evidence/algae-variation.webp) · [正式导入对照数据](native-captures.validation.json)
- 31 件可编辑源冷开核对，位置、UV 和内嵌图集与发布 GLB 对齐，Blender 存储的角点法线分量最大差 0.00291。 [冷开报告](blender.validation.json)
- 在实际 15 × 8 × 5.1 米缸包络中验证全部 100 件摆放、接地与临时存档读取的变换一致性。32 个覆藻选项逐件验证同网格、同底色、单遍渲染及保存回读。 [摆放回读](placement.validation.json) · [覆藻回读](algae.validation.json)

保留当前正式模型、可编辑源、其唯一六面原画和少量审查证据。清理本批重复预览 GLB、旧抓帧和已转存的生成目录，共 934.2 MiB。 [清理清单](cleanup.validation.json)旧版 GLB 由游戏 Git/LFS 恢复。两件待审大型活珊瑚保留在本地。
