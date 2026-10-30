最新蓝鳃R15：R14两眼间断档被用户拒绝；已将眼区保护从整片侧图UV矩形改为实际左右侧眼支持，中央接续恢复。实际同机位中央1008像素改变、两虹膜窗口零改变；1494面/头型/嘴/鱼鳍保持。新源/077/490/072/动作/口裂门实跑通过；头/嘴/皮肤/呈现外观仍pending。默认正面中央对照入口experiments/bluegill-interocular-review-20261031/InterocularReview.gd。草鱼/鲫鱼继续冻结。

最新：草鱼R4、鲫鱼R4用户确认结束冻结；蓝鳃R14材质候选1494面，实际几何/权重/鳍UV未改。新生全头图的正面眼与两侧形体被拒绝，只允许两眼间中央材质ROI；沿唇接原侧图、少量回色到内口缘。当前077/490/072/口裂射线/动作/源冷读实跑通过，头/嘴/皮肤/呈现SOP仍pending。预览入口 experiments/bluegill-lip-review-20261031/BluegillColorReview.gd。证据/清理读蓝鳃mouth-repair-20261031/lip-color-followup/validation-report.json。

最新用户确认：草鱼和鲫鱼当前版本结束、冻结；仅继续蓝鳃沿唇补色与前端下搭修复。鲫鱼R4实际接受和全通过SOP读该鱼manifest/user-acceptance-r4.validation.json；旧R3拒绝保持。

最新鲫鱼进展：头嘴R4候选1440三角，已实际完成077/490/072/动作/冷读；头型、嘴和呈现保持pending而非全绿。可在 `experiments/crucian-head-review-20261031/CrucianHeadReview.gd` 同视角切换本次修正/已拒绝R3。当前输入、负例、对照和清理见鲫鱼 `mouth-repair-20261031/head-followup/validation-report.json`。草鱼用户确认结束冻结，蓝鳃仍待沿唇补色；未替换正式游戏。

2026-10-31最新用户审阅：草鱼当前R4确认结束并冻结；蓝鳃R11沿唇补色/前端下搭被否决；鲫鱼R3前吻鼓宽和头型偏离被否决。先逐条修鲫鱼，再处理蓝鳃。旧技术报告不能覆盖本次否决。

> 当前状态（2026-10-31续做后）：三鱼已完成独立返修候选和实际/专项检查，蓝鳃1494、鲫鱼1454、草鱼1682面，均待用户看效果、未正式安装。当前入口与完整证据读 [三鱼返修交接](FISH-MOUTH-REPAIR-20261031.md)。三个旧拒绝哈希保持拒绝。

以下为续做前检查点与历史记录，不能覆盖上面的当前索引。


> 2026-10-31返修检查点：蓝鳃R8整鱼1494三角，源上下内缘实网格射线与490姿态鳍技术专项通过；正面下巴V形拉伸纹使嘴部外观继续失败。R9扩带又产生补丁，已拒绝。详细记录在 projects/fishing-2d/experiments/bluegill-portable-trial-20261030/mouth-repair-20261031/repair.validation.json；不是正式完成，不推广下一鱼。约169MB重复/可重建缓存已清理，唯一证据和资产保留。
# 鱼类通用工具与DeepSeek审阅：无上下文交接

## 当前：三条嘴部被用户否决（2026-10-31）

用户实际检查列表后否决蓝鳃、鲫鱼、草鱼嘴部横缝、缺少约定下唇线/开口/颌部与左右原画接续、整块抹色。三条manifest已blocked/fix_input，旧嘴和整鱼图审通过撤回，旧账本/报告留历史快照。当前拒绝索引 `docs/anvil/knowledge/2026-10-31-three-mouth-user-rejection.validation.json` 优先于下方全部旧“完成”措辞。罗非鱼R11已确认状态不变。基础检查后先嘴、再全部鳍、再其余；整鱼1500优选/2000硬上限及全部旧要求同时生效，按 `mouth-first-review.md` 逐项实际检查。不能只靠再写SOP或自动填通过解决。当前从蓝鳃嘴部重审，不推进下一鱼。

## 最新：草鱼完整候选（2026-10-31）

草鱼已继续修复补皮和前端投影，当前1832三角/2546导出顶点/18骨，源固化与新进程冷读、完整七鳍490/072、身体077/GPU、头型正负例、真实四动作/过渡、24秒视频及九阶段SOP均通过，51项实际证据。整体外观待用户审阅，正式草鱼未替换。游戏 `experiments/grass-carp-portable-trial-20261030/{manifest.json,final-sop.validation.json,handoff.md}` 为当前状态，下方首轮blocked是历史。

本次完整门发现稀疏身体与鳍根蒙皮采样不匹配；按本鱼源根地标/身体权重断点由23环增到38环、重建根投影，未单独移动鳍或改根带/物理限值，当前全部490通过。完整通过后复用相同模型/计划/冻结依赖的490供最终072，避免重复执行。站位配置和当前物种profile在Foundry resources；通用经验/联系表工具同步到本地。最新汇总：`docs/anvil/knowledge/2026-10-31-grass-portable-final.validation.json`。未请求commit/push。

## 最新收敛与第三条实鱼（2026-10-30，优先于下方历史状态）

- 鲫鱼上一轮残鳍/嘴端投影问题已修正，1526三角、2289导出顶点、18骨，当前候选完成源固化/新进程冷读、完整七鳍490/072、身体077/GPU、头型正负例、动作和九阶段SOP。用户整体外观待审，未替换正式鲫鱼。以游戏 `experiments/crucian-portable-trial-20261030/{manifest.json,production-review.json,sop.validation.json,handoff.md}` 为准。旧未完成报告归档为historical，不能再作为最新停点。
- 配准补皮、显式普通源导出、有限前颌颜色图岛、局部截图/空图拦截、七阶段材质候选链、原export triangles适配已归入[本轮经验卡](../resources/skills/fish-volume-production/references/portable-material-lessons-20261030.md)，与本地技能同步。单次材质技术链约10.40秒，不含生图/人工/最终门，无token节省百分比声明。
- 第三条草鱼已实际走过材料准备→归档来源校验→建模→validate→多视渲染/实际图审。新长身体型23环×12径向。首次口腔MANIFOLD四面共边失败，显式EXACT重建通过身体/七鳍闭合与机械八项；正面嘴部原画描边投影仍被图审拒绝，当前blocked/fix_input。只完成首轮试验，未通过完整门、未作正式成品交付。以游戏 `experiments/grass-carp-portable-trial-20261030/{manifest.json,handoff.md,local-review.validation.json}` 为准。
- 当前权威汇总为 `docs/anvil/knowledge/2026-10-30-crucian-grass-portable.validation.json`。旧bluegill-crucian索引保留历史快照。未请求commit/push，本轮不提交。

## 后续实鱼执行状态（2026-10-30，优先于下方早期交接）

用户后来已明确授权：安装本人确认的罗非鱼R11，试做蓝鳃；这条完成后收敛脚本/本地技能，再尝试另一条。**当前已完成这些后续动作，不再适用下方早期“尚未开始/先讨论不选鱼”的停点。**本轮没有请求commit/push。

- 罗非鱼R11已按用户确认正式替换；当前证据读游戏 `experiments/nile-dorsal-route-trial/round11-production-install/manifest.json`。GLTFDocument路径与已审入口一致，480骨架姿态矩阵0差异、四动作GPU逐RGBA相同；旧入口优化轨道的失败与回滚另存。
- 蓝鳃1980面候选完成源固化/冷读、七鳍完整490/072、身体077/GPU、头型负例、动作/多视/水下及九阶段SOP，**用户整体外观仍待审，未装正式蓝鳃**。状态读游戏 `experiments/bluegill-portable-trial-20261030/manifest.json`、`sop.validation.json`、`handoff.md`。
- 经验写回[实鱼收敛卡](../resources/skills/fish-volume-production/references/portable-production-lessons-20261030.md)，对应技能入口与SOP已和本地副本同步。当前60项portable快速测试通过，volume38项通过（1skip）。新工具不用Nile面数/clip/骨名/物种形态常量，但完整身体/490适配仍有明确库存范围。
- 鲫鱼第二次试验已实际完成1526面源/冷导出/实际导入、查看器和四姿态局部鳍膜诊断。提前图审发现身体残鳍、嘴端取色，**未完成整鱼**；状态blocked/fix_input，完整门未跑，正式鲫鱼字节不变。读游戏 `experiments/crucian-portable-trial-20261030/handoff.md`，不要把局部成功提升成整鱼接受。

最新索引为 `docs/anvil/knowledge/2026-10-30-bluegill-crucian-portable.validation.json`。下方保留早期工具/次级审阅史，旧460文件不变声明只适用于当时工具轮，不覆盖后来已授权的本轮修改。

## 当前读取入口

本轮仅把可脚本化的源固化、部位检查、展示与证据流程做成通用工具，并处理次级模型发现的校验问题。**没有开始下一条鱼，没有制作GPU动画，没有修改已验收的罗非鱼成品或旧工具。** 提交前的最终状态由以下记录确认，不能以旧聊天或早期失败报告覆盖它：

最终技术结果：55项快速测试通过、独立调试四阶段全部通过；最终执行器真实保存源及新进程冷导出通过，11顶点/9三角/3骨/2clip全部语义与IBM误差0；冻结代码的一次实际导入和16组身体GPU覆盖通过、透明负例4278像素。主执行者已实际查看新覆盖对照图。原460文件哈希不变。这里完成的是通用工具，完整新鱼形态/490/077及用户视觉验收仍按各鱼SOP执行。

1. [当前实现与验证索引](anvil/knowledge/2026-10-30-fish-portable-tools.validation.json)：当前代码、有效证明、范围与限制。
2. [通用工具操作SOP](../resources/skills/fish-volume-production/references/portable-finalization-tools.md)：配置和命令，不需重读全部历史实验。
3. [次级审阅调试记录](anvil/debug-sessions/2026-10-30-portable-secondary-review-session.md)及[独立分阶段复核](../.ai/anvil/reviews/2026-10-30-portable-secondary-debug-review.md)：具体缺口、修复前反例、处置和最终门。
4. `work/fish-portable-tools/manifest.json`及其引用的最终报告：本轮执行断点/当前任务状态。

新会话先读仓库AGENTS和toolkit/鱼类技能的必要入口，再按上述四项续做。用户要求本轮收尾、清垃圾、commit+push并使工作区干净；之后先讨论，不自动选鱼或继续制作。

## 本轮做了什么

- 新工具在`resources/scripts/volume-fish/portable/`，保持旧罗非鱼R11绑定脚本和资产原字节；没有把旧通过报告改成新模型通过。
- `prepare_spec.py`读取显式部位表，自动生成输入SHA和实际计数；不再手抄1710/18/54或假定七片鳍。
- `run_source.py`串起预检→Blender源作者→新进程冷导出→完整语义对照→最终spec/model/manifest。默认dry-run，执行须`--execute`；不支持输入提前拒绝，失败停下留日志。
- `parts.py/PackedFishParts.gd`按任意显式库存做完整互斥覆盖，实际Godot按属性/骨名权重/有向三角多重集匹配，不依赖导入顶点顺序。
- `validate_body_gpu.py`做两个原生姿态×八视的身体透明覆盖及透明负例；它不是完整077或全控制器/连续时间保证。
- `view.py/FishAssetViewer.gd`冷读、bbox构图、拖动/缩放/平移、原生/可选控制器；镜头由配置提供。`evidence.py`整理声明截图/哈希/nearest拼图，视觉审核仍pending。

当前限制：一个rig、单位源变换和已支持的单surface MASK/nearest/PBR合同；新解剖、颜色供体、鳍根/整鳍膜/490和完整077仍需本鱼约束与实际审核。不要为“通用化”删除guard、放宽物理容差、照搬罗非鱼形态或把各鱼都强制成七鳍。特殊shader/rig/结构先明确缺口。

## 次级模型实测与必须保留的用户约定

用户持续允许PI/次级模型处理本工程必要内容；本轮又明确允许向DeepSeek发送`fish_asset_spec.py/build_source.py/source_snapshot.py/verify_parity.py/glb_io.py`五文件作只读审阅。密钥只从环境/本机配置读取，不能写进代码、提示词、报告或Git。

用户明确要求**不要人为设置生成token预算**：默认不传`max_tokens/max_completion_tokens`，使用供应方默认容量；不把服务自身容量称为无限。这个约定不取消Godot/Blender等执行程序的失败控制/执行超时。详细规则已写入[次级模型执行卡](../resources/skills/fish-volume-production/references/static-merge-secondary-model.md)。

DeepSeek Flash/high实际三次：

| 调用 | 生成设置 | 结果 | API总tokens |
|---|---|---|---:|
| 1 | 人工max_tokens8192 | 全部用于推理，length，无结论 | 20225 |
| 2 | 人工max_tokens24576 | 全部用于推理，length，无结论 | 36609 |
| 3 | 不传人为生成上限 | stop，获得7项发现 | 42967 |

三次API耗时合计约400.97秒，总99,801tokens；其中prompt36,099（cache hit23,798/miss12,301），completion63,702。供应方未返回实际费用，不估算；这些不是Codex计量，不能写成Codex节省百分比。思考内容没有保留，只有最终审阅和用量。根目录`work/fish-portable-tools/deepseek-source-review*.validation.json`保存逐次事实。

成功报告提出的四类问题已用小样复现：优化Python剥除assert导致假通过、primitive实际材质绑定漏检、非法负/未归一权重被忽略、校验后的文件/配置变化可污染报告哈希。修复按独立调试阶段门执行；当前结论看最终索引，不能只看DeepSeek说“changes_required”或中间阶段ok。

另三项不盲改：同RGBA的PNG容器重编码属于允许差异并单独报告；源作者阶段不是最终接受、`run_source`已有强制rest/IBM最终门；空manual expected不取消哈希绑定的基线与候选对照。不得因此收紧像素/几何合同或增加每鱼无效工作。

## 验证与复现策略

本轮用合成小样验证不同骨/面/部位/clip数量，不通过制作下一条鱼来调试工具。旧实现阶段有42项快速测试、6项部位测试及14次真实headless正负例；审阅修正会增加专门回归，最终准确计数和当前source SHA看验证索引。

真实Blender案例为11顶点/9三角/3骨/2clip和7顶点/5三角/2骨/1clip；保存源、原rig/rest/动作、新进程冷导出和全语义对照均有报告。GPU身体验证16对0缺像素，透明负例4278像素；更新解析器后使用新版本的最终证明，不重写旧报告输入哈希。当前源及校验器变化只做相关小回归，不重跑罗非鱼490或36项性能矩阵。

常用检查从Foundry根执行：

```bash
.venv/bin/python -m unittest discover -s resources/scripts/volume-fish/portable/tests -p 'test_*.py'
.venv/bin/python -m unittest discover -s resources/scripts/volume-fish -p test_portable_fish_parts.py
```

Blender合成复现：`portable/tests/run_blender_smoke.py --blender <实际工具> --output <全新允许目录> --json`。源生成和独立导出/对照的完整命令见SOP。不要覆盖已冻结的证明目录；修复前六份代码已按精确SHA保存在`work/fish-portable-tools/deepseek-repro/reviewed-source/`，有版本映射收据。

本机已确认工具，不要重复全盘寻找或安装：

- Python：Foundry `.venv/bin/python`。
- Blender4.5.3：`/Users/czl/.gamefactory/toolchain/blender/Blender.app/Contents/MacOS/Blender`。
- Godot4.7.1 mono：`/Users/czl/.gamefactory/toolchain/godot/Godot_mono.app/Contents/MacOS/Godot`。
- `DOTNET_ROOT=/Users/czl/.gamefactory/toolchain/dotnet`。

换机器先用仓库doctor/配置定位实际工具；上述Mac路径是已知本机事实，不是跨机器常量。只有确认未安装才处理工具缺失。

## 关于后续动画：本轮只讨论，没有实施

普通骨骼动画烘焙通常可只新增Action/clip，不改身体拓扑、UV、权重、骨名、骨架rest，也不必新增骨骼。若写回同一blend/GLB文件，文件SHA仍可能变化，需要按实际影响绑定新证据；文件变化不等于重建几何。

真正转GPU播放还需运行时方案：骨骼动画纹理/矩阵及着色器，或VAT顶点/法线纹理及稳定顶点索引。后者与拓扑/导入顺序更强绑定。当前Godot控制器还逐骨计算身体转弯和鳍摆动；单加Blender Action不会自动把这些计算搬到GPU。未来先确定要烘焙基础波形、如何保留动态转弯/幅度/速度，再实现；不得在本轮提交里顺带改。

## Git、保留与下一步

Foundry分支`codex/pure-workflow-toolkit`，本轮前HEAD=`2f884af`；游戏独立仓库分支`main`，已推送基线=`ce39f8ca`。本轮新通用代码/小样证据属于Foundry；游戏资源无新改动时不制造空提交。最新交付提交就是包含本交接的Git提交，实际SHA用`git log -1`或本次对话最终提交回执确认，避免本文件自引用提交hash。

收尾保留通用代码/SOP、当前合成原始输入与源/导出、唯一截图、修复前负例及紧凑验证/清理报告；删除重复尝试、测试缓存、已可重建且不再引用的模型/日志。不能用`git clean -fd`或整删work实现“清空”。`work/fish-portable-tools`保留的是有明确引用的小型证据包，临时垃圾须按清单删除；证据文件由Git属性保留原字节。

提交必须Foundry commit+push，游戏检查并在有改动时commit+push，否则确认远端同步；结束分别确认`git status --short`为空、HEAD与origin对应分支无ahead/behind。Git推送若游戏旧SSH代理失败，可单次使用`git -c core.sshCommand=/usr/bin/ssh push origin main`，不改持久网络配置。

完成后等待用户讨论或明确下一鱼。不得自动重新审核已完成罗非鱼、重做嘴、批量鱼推广、开新生成任务或GPU动画迁移。
