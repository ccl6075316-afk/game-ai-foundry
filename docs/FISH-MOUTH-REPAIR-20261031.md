最新蓝鳃R15：R14两眼间断档被用户拒绝；已将眼区保护从整片侧图UV矩形改为实际左右侧眼支持，中央接续恢复。实际同机位中央1008像素改变、两虹膜窗口零改变；1494面/头型/嘴/鱼鳍保持。新源/077/490/072/动作/口裂门实跑通过；头/嘴/皮肤/呈现外观仍pending。默认正面中央对照入口experiments/bluegill-interocular-review-20261031/InterocularReview.gd。草鱼/鲫鱼继续冻结。

最新：草鱼R4、鲫鱼R4用户确认结束冻结；蓝鳃R14材质候选1494面，实际几何/权重/鳍UV未改。新生全头图的正面眼与两侧形体被拒绝，只允许两眼间中央材质ROI；沿唇接原侧图、少量回色到内口缘。当前077/490/072/口裂射线/动作/源冷读实跑通过，头/嘴/皮肤/呈现SOP仍pending。预览入口 experiments/bluegill-lip-review-20261031/BluegillColorReview.gd。证据/清理读蓝鳃mouth-repair-20261031/lip-color-followup/validation-report.json。

最新用户确认：草鱼和鲫鱼当前版本结束、冻结；仅继续蓝鳃沿唇补色与前端下搭修复。鲫鱼R4实际接受和全通过SOP读该鱼manifest/user-acceptance-r4.validation.json；旧R3拒绝保持。

最新鲫鱼进展：头嘴R4候选1440三角，已实际完成077/490/072/动作/冷读；头型、嘴和呈现保持pending而非全绿。可在 `experiments/crucian-head-review-20261031/CrucianHeadReview.gd` 同视角切换本次修正/已拒绝R3。当前输入、负例、对照和清理见鲫鱼 `mouth-repair-20261031/head-followup/validation-report.json`。草鱼用户确认结束冻结，蓝鳃仍待沿唇补色；未替换正式游戏。

2026-10-31最新用户审阅：草鱼当前R4确认结束并冻结；蓝鳃R11沿唇补色/前端下搭被否决；鲫鱼R3前吻鼓宽和头型偏离被否决。先逐条修鲫鱼，再处理蓝鳃。旧技术报告不能覆盖本次否决。

# 2026-10-31 三鱼嘴部返修候选

三条旧拒绝版本保持拒绝；本轮是三个新哈希的返修候选。执行者已实际查看本鱼原画、灰模/材质多视、独立鱼鳍、纯身体、动作/切换阶段和水下画面，并完成源固化、新进程冷读和同候选专项及SOP。**用户尚未接受，未安装到正式游戏。** 不以清单或技术通过替用户判断。

| 鱼 | 旧拒绝面数 | 新整鱼三角面 | 身体含口内 / 全部鳍 | 导出顶点 | 候选哈希前缀 |
|---|---:|---:|---:|---:|---|
| 蓝鳃太阳鱼 R11 | 1980 | 1494 | 664 / 830 | 1683 | `8fab2250f40f` |
| 鲫鱼 R3 | 1526 | 1454 | 1042 / 412 | 2488 | `678486caac39` |
| 草鱼 R4 | 1832 | 1682 | 1330 / 352 | 2422 | `50b0b30d8932` |

优选约1500、硬上限2000与画风、头型、眼、完整身体、鳍基/膜、蒙皮及动作同时有效。草鱼保留原动态支撑截面，未为1500目标破坏鳍连接。没有追加独立高密度嘴。已确认罗非鱼R11仅作对照，模型SHA仍为 `2ec51a58e8d273910f22cf5414cb4969e92b00827131e829d942ecb15f96e28a`。

## 当前窗口和操作

已打开Godot窗口“嘴部返修 · 三条鱼待看效果”，入口：

`projects/fishing-2d/experiments/new-fish-mouth-review-20261031/MouthReviewList.gd`

实际目录为 `viewer/catalog.json`，界面只冷读完整GLB及正常动作，不重建静态鱼。左侧切鱼；左拖旋转、右拖平移、滚轮/按钮缩放；嘴部近景会暂停并放大，正/侧/俯视保留当前距离，复位视角回整鱼。罗非鱼在列表末尾供对照。实际GPU烟测含列表点击、移动、旋转、平移、缩放、嘴部按钮、四鱼正/斜近景、选择与模型一致和空画面负例，共127项，通过记录在 `viewer/smoke-r6/viewer.validation.json`。烟测不是鱼外观接受。

## 文件与证据

下表根目录均从仓库根解析。每条根目录下 `candidate-版本/source-run/source/fish.blend` 是自足可编辑源，`candidate-版本/source-run/fish.glb` 是当前导出；`delivery-版本/review` 保存实际多视、对照图、动作视频和专项原始记录。

| 鱼 | 根目录 | 版本与正式清单 |
|---|---|---|
| 蓝鳃 | `projects/fishing-2d/experiments/bluegill-portable-trial-20261030/mouth-repair-20261031` | `r11`；`production-review-r11.json`、`sop-r11.validation.json` |
| 鲫鱼 | `projects/fishing-2d/experiments/crucian-portable-trial-20261030/mouth-repair-20261031` | `r3`；`production-review-r3.json`、`sop-r3.validation.json` |
| 草鱼 | `projects/fishing-2d/experiments/grass-carp-portable-trial-20261030/mouth-repair-20261031` | `r4`；`production-review-r4.json`、`sop-r4.validation.json` |

每鱼实际报告包括：七处真实开口BVH/旧嘴负例、源与冷导出语义一致、逐surface不透明/GPU身体077、头型/尖头负例、实际动作、490姿态完整鳍根/全膜及072复用审计。全部绑定各自当前模型；旧报告不能移给新候选。保留的数值/离散采样不是连续时间或生物精密测量证明。

总索引：`docs/anvil/knowledge/2026-10-31-three-mouth-repair.validation.json`。各鱼父目录 `manifest.json` 指向当前返修；历史 `production-review.json` 和拒绝侧文件保留旧哈希，不追认旧版。

## 生图模式、保存图与提示词

本轮及前轮辅助颜色图使用 **built_in_imagegen_edit（内置生图）**，每条只负责自己的前下颌颜色，原图保留，已复制到项目中。各鱼上述根目录下：

- 最终保存的辅助图：`front-aux/generated.png`。
- 完整最终请求/提示词：`front-imagegen-request.json`。
- 真实来源和受限颜色用途接受：`front-aux/assets-manifest.json`。

没有给既有外部生成图伪造Foundry生图job；源颜色接受是本轮操作者审核。辅助图嘴型漂移、失败几何配准不参与模型或生物测量；几何由本鱼原图边界和实际身体确定。隐藏颜色/横宽及混杂像素簇的解释仍是艺术制作。各鱼色图/提示词的完整路径与SHA在总索引逐项列出。

## 经验、参数和失败方案

通用方法与失败边界：`resources/skills/fish-volume-production/references/mouth-repair-lessons-20261031.md`。通用源制作脚本、实际开口验证及有限口腔/帽面实现均保存在Foundry `resources/scripts/volume-fish`。

各鱼已冻结的源边界和前端颜色配方另存于 `resources/volume-fish/*-mouth-source-boundaries-20261031.json`、`*-mouth-front-chart-20261031.json`。这是源制作配方，不把带过程注记的profile当作标准 `volume build` 的已接受新物种profile。复现最终成品优先用已保存的普通源与源固化spec；它不依赖运行时造型、补色或历史author脚本。精确历史author版本另存 `authoring-script.snapshot.py` 和对应provenance报告，代码迭代后仍可追溯。

草鱼删共线环的1442面候选被490拒绝，恢复原支撑环的1682面候选才通过；失败的根/膜结果和最差原始姿态保留。旧端面前追加尖突、窄唇带无限扩大、平色矩形补前吻、额头补丁、重复V纹等均不能成为模板。下一条鱼仍独立标注、选参数和实际看图。

## 本轮清理

保留全部原始来源、当前资产/可编辑源、源配方、当前完整静帧、三段24秒实际动作视频、专项全量数值结果及最差/静止原始姿态、必要失败代表图。按SHA逐文件清理重复历史截图、已压片的冗余帧和可重建稠密采样；被清的原始缓存不再假称仍在磁盘，历史export/frame清单的重放须重建缓存。

最后一次批量清理196.46MiB，加各轮已记录清理，本链路累计约755MiB。最后核对三个返修目录约248.17 / 170.93 / 142.99MiB，合计约562MiB。精确清单、删除SHA与剩余字节见 `docs/anvil/knowledge/2026-10-31-mouth-repair-final-cleanup.validation.json` 及各轮cleanup报告。未提交或推送；保留了两仓库既有未提交工作。
