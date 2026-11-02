---
name: aquascape-production
description: Build or repair source-art-based 3D aquatic plants, rocks, driftwood, ornaments and substrates in Game AI Foundry; maintain whole-instance budgets, rooted motion and native-engine review. Use for aquascape production and its SOP maintenance, excluding fish and unrelated game features.
---

# 原画驱动的 3D 水草与布景

定位实际 Foundry 根目录和目标游戏，读根 `AGENTS.md`、[工具箱合同](../gamefactory-toolkit/SKILL.md)及[造景生产 SOP](references/production-sop.md)。本 skill 是仓库维护源；具体执行路径相对 Foundry 根目录，不依赖本机安装位置或特定桌面客户端。

## 选择本次分支

| 本次工作 | 读取入口 |
|---|---|
| 新草/修叶、根茎与整簇布局 | SOP 第 2—3 节；`resources/aquascape/normal-leaf-sources.json` 和本种来源/布局配置 |
| 石头、沉木和三向结构 | [正交视图方法](../../aquascape/ORTHOGRAPHIC-METHOD.md)；SOP 第 4 节 |
| 罐、桥、管、洞屋等带空腔物件 | SOP 第 4 节；游戏 `docs/AQUASCAPE-DECOR-V1.md`；`resources/aquascape/decor-10-v1.json` |
| 骨骼水流 | [原生骨骼微流](../../aquascape/PLANT-CURRENT-METHOD.md)；SOP 第 5 节 |
| 大量草的 shader/实例化和性能 | SOP 第 5—6 节；游戏 `docs/AQUASCAPE-CATALOG-V5.md` 的 V10 实时摆动修复及 V11 |
| 底床与碎石 | SOP 第 4 节；游戏 `docs/AQUASCAPE-SUBSTRATES-V2.md`、`docs/AQUASCAPE-SAND-TRIAL-V1.md` |
| 旧实验复现、扩充目录、跨机器恢复 | SOP 第 1、7—8 节的版本/工具边界，不直接重跑旧整批生产器 |

## 关键判断

- 新原画用 Foundry workflow，复用原画核验原来源、实际资产审核和 SHA；`done/human_review` 是进入图审的条件，不等于图已经接受。图像失败先修输入，`validate before matting`。
- 描述“一簇自然生长的某种水草”，只规定品种叶形/叶宽/颜色/生长方式，不固定叶片数、逐叶角数组、特殊翘叶或统一嫩叶。已审核整簇决定布局，独立叶片图不能证明整簇三维排列。
- 保留原尺寸像素纹理和 nearest；白边、透明边、单面翻转、无源隐藏面各自判断，不用整块涂色或密集拓扑替代材质。静态叶形/姿态/绑定修正固化到 GLB 和构建方法，Godot 保留实时水流与材质绑定。
- [完整实例预算](../../aquascape/geometry-budgets.json)包含全丛叶片/根茎、两面/封边和附层，不能分叶计算、静默升档或强行凑优选面数。历史高面路径末端经 `optimize_scenery.py --deploy`；V11 直接低面构建，经 `validate_scenery_budget.py` 阻断再部署。不得让高面中间源绕过门进入当前目录。
- 骨骼与 shader 分开记录。按本种固定根、绑定/作者锚点、位移和循环验证；实际 MultiMesh 的叶片须实时变化，暂停逐像素一致、恢复继续摆动。时钟、水面或单 Mesh 特写变化不能证明实例化草在动；注意实例 COLOR 白色数据的依赖。
- 石木须有连续体积和正确分叉；人工摆件另验真实洞口、内壁/底面，贴图上的黑洞不能代替几何洞。三视跨度接近和网格闭合不能代替结构对应与实际看图。
- 新进程冷读最终模型、实际 shader/导入资源与当前目录，检查正/侧/背/俯/斜/灰模、水中运动及需要的摆放保存回读。离散采样与独立千丛性能实验不证明连续无互穿或完整鱼缸性能。

## 收尾

按 SOP 第 7 节完成通用方法、本对象配置、本次证据三层回写，失败/暂停同样更新原 handoff。不要将旧批次叶片数、Windows 路径、shader 参数或 `accepted_for_commit` 变成通用标准。造景尚无 `volume sop-check` 等价总门；逐个检查实际预算、几何/根/循环/洞口、图审和冷读，不虚构新命令。

每轮先保存唯一来源、当前资产、必要负例和代表证据，再清理精确列出的可再生临时产物，记录剩余体积。用户要求提交时检查 Foundry 和独立 `projects/fishing-2d` 仓库，完成 commit + push；接受状态仍按原报告与用户反馈。
