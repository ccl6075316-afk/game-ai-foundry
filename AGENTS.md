# Game AI Foundry — External Agent One-pager

**2026-10-31 水草追加要求**：美术描述使用“一簇自然生长的某种水草”，以品种的叶形、叶宽、颜色及生长方式区分；不规定叶片数量、固定叶片变体、外张/弯曲角度，不要求侧卷叶、翘叶或展开嫩叶作统一点缀。构建器不得复用一套逐叶角度/特殊叶位模板来制造物种差别，应依据已审核整簇来源确定排列。原有制作记录中的叶片数量只作历史输入，不作新生图要求。当前修正使用同种已存在的正常叶片原画，保留根部连接、低面预算与轻微水流；模型修正须固化在GLB及构建方法，不能只在Godot临时掰叶。技术三角面预算继续生效。

**2026-10-31 批量摆缸面数预算**：当前及以后新增、重建的水草、石头、沉木、人工摆件，均执行 `resources/aquascape/geometry-budgets.json`，按完整摆放实例的三角面合计，包含全部叶片/茎根、双面/封边、子网格及附层。普通石优选400/硬上限600；沉木800/1200；带状草整丛400/600；宽叶草整丛700/1000；复杂人工摆件1200/2000。大主景石须明确分类才可700/1000，不能默默升档。新鱼按用户本轮最新要求优选1500/硬上限2000，覆盖下文旧体长分档，不在本轮改鱼。不得用密集拓扑替代已有材质细节；保留原尺寸画风、轮廓、连接、洞口和动作，必须实际对照。当前 scenery 构建最后经 `optimize_scenery.py --deploy` 和 `validate_scenery_budget.py` 阻断门；不允许绕开预算直接把高面源模型挂入运行目录。大量简单植物动画优先实验低面+shader摆动+实例化，实验通过不冒充用户已验收。

本仓库是给外部 Agent 使用的纯 CLI / Workflow 工具箱。不要假设任何桌面客户端、内置会话或品牌专属运行时。

## 读取顺序

1. 读取 [`resources/skills/gamefactory-toolkit/SKILL.md`](resources/skills/gamefactory-toolkit/SKILL.md)。
2. 运行 `python cli/gamefactory.py workflow --help` 和需要的子命令 `--help`。
3. 按 `context → validate → init → run → status → resume` 调用，全部加 `--json`。
4. 只把 `manifest`、`progress`、`handoff`、`assets-manifest`、`validation report` 当作状态。

鱼类3D新建、返修和批量推广，先读[完整生产SOP](resources/skills/fish-volume-production/references/production-sop.md)：准备材料与生图用途、各部位制作、动作、最终对照和证据按同一流程执行。每次修正回写通用方法、本鱼参数、本次证据；交付前运行 `volume sop-check --review <逐鱼清单> --output <报告> --json`，不能用清单通过替代实际看图或专项验证。清单用 `volume sop-init` 建立，字段与操作见SOP第9节。

**2026-10-31用户明确的检查优先级与约束保留**：基础检查后，第一优先检查嘴，第二优先检查全部鱼鳍，再查其余项。嘴必须实际给出本鱼下唇线、真实开口、上下颌体积、两侧原画补色与跨口缘接续的对应证据；一道横缝、消除黑斑、整块抹色、闭体或SOP机械通过均不能放行。嘴未完成不推进下一鱼、不进入整鱼完成流程。所有旧要求同时生效：整鱼按展示体长分档：≤120cm优选1500/硬上限2000；>120–300cm优选3500/上限4000；>300–600cm优选5500/上限6000；>600cm优选7500/上限8000（2026-10-31用户追加；正好120/300/600cm归前档），计入身体、嘴/口内、全部鳍双侧/封边和附层；修嘴在总预算内重布拓扑，不能堆高密度新嘴或丢掉画风、头型、鳍、身体完整性、蒙皮及正常动作。执行[嘴优先检查卡](resources/skills/fish-volume-production/references/mouth-first-review.md)。

每轮准备完成/正式交付，由Agent主动执行[资产固化与导出收尾](resources/skills/fish-volume-production/references/final-asset-export.md)，不等待用户提醒。应属于模型的静态修正回写可编辑源和最终导出；保存引擎专用资源，正常实时动作保留。在冻结最终验收候选前完成固化，以新进程关闭实验静态构建链直接冷读导出成品并复核。未通过 `sop-check` 的固化/冷读项不能称正式完成；仅有实验预览或进程内缓存不算交付。

## 最小命令

```bash
.\gamefactory.cmd workflow context --brief <brief> --json
.\gamefactory.cmd workflow validate --brief <brief> --json
.\gamefactory.cmd workflow init --brief <brief> --json
.\gamefactory.cmd workflow run --manifest <manifest> --stage assets --detach --json
.\gamefactory.cmd workflow status --manifest <manifest> [--job-id <job_id>] --json
.\gamefactory.cmd workflow resume --manifest <manifest> --task-id <task_id> --json
```

首次若无 `.venv`：`py -3 cli/gamefactory.py setup ensure-python --json`，之后不要用裸 `python`（Windows Store stub）。

## 行动规则

1. `ok=false` 或 `next_action=fix_input` 时读取 `failures[].kind/code/message`，先修输入，不继续执行。
2. `status=blocked` 按 `next_action` 处理；`status=failed` 才用 `resume`；`status=paused` 用 `resume`；`pending` 且 `next_action=run` 时再 `run`；`status=running` / `next_action=poll` 时只查同一 job/manifest，禁止再开一轮 `run`。
3. 只有 `status=done` 且 `next_action=human_review` 才进入 assets review、Godot、test。
4. `validate before matting`；图像失败先修 prompt/Brief。
5. 长任务：短超时宿主默认 `workflow run --detach` + `workflow status --job-id`；长超时可用同步阻塞。动画拆帧默认 **24**（3–4s 视频；`duration×6` 可上调；Brief `sprite_frames` 可覆盖）。
6. 动画原始帧、idle 独立 `*_nobg.png`；视频帧用 `video matte-frames --engine ai`；`split-frames` 默认 `optimize_loop`。
   已有动画的角色续做动作，必须从已验收动画的稳定动态帧取参考，避开静转动过渡段；转身首尾帧分别匹配切入与回接动画。只有运行时也使用左右镜像时，尾帧才可由目标游动帧镜像得到，不能复用不匹配的旧转身尾帧。详见 `docs/AI-HANDOFF.md`「连续动作的首尾帧规则」。
7. **导入保清晰**：静帧/动画导入不压到 `display_size`；游戏内大小用 `real_length_cm` / runtime scale。
   鱼类转向的生成、相位衔接、曝光、深度边界及验收按 [`docs/FISH-TURN-WORKFLOW.md`](docs/FISH-TURN-WORKFLOW.md)；复用方法，每条鱼独立确定参数，不照搬银龙鱼帧号和时长。
   **3D 鱼先统一源图画风**：新鱼先走 Foundry 生图，引用已有像素鱼作风格参考；源图生成完成且资产审核接受后，才走 `volume plan → build → validate → render`，完成视觉审核后 `volume accept --handoff <handoff> --note <实际审核说明> --json`（均 `--json`）。已有已接受源图可经同一来源/审核门复用。通用建模器和物种 profile 保存在 Foundry `resources`，不得只留在某个游戏实验目录。原尺寸像素贴图用 nearest 采样；源图/风格参考/三视及引擎对比的视觉审核不能由机械检查代替。详见 [`docs/FISH-VOLUME-WORKFLOW.md`](docs/FISH-VOLUME-WORKFLOW.md)。
   **鱼类部位不确定或无法验收先查证**：对位置、形状、连接、测位或动作判断不清，或用户指出形态不符时，按 `projects/fishing-2d/docs/3d-fish/ANATOMY-RESEARCH.md` 查询部位术语和目标物种资料，转成制作约束与有效验证后再修该部位；查不到保留未知，不以机械通过或连续猜测代替。可复用方法与物种参数分别沉淀，不把找到术语等同已有实现或跨鱼种验收。
8. 图片后处理使用 `--input` / `--output`。
   **每条3D鱼交付前必须验鳍根**：新建、微调、换材质、重新导出或改动作后，都检查全部适用鱼鳍的完整鳍基，覆盖静止、原生循环、Godot四动作与切换。用同姿态实际蒙皮身体表面的有符号距离，不能用“与旧版一样”“包围盒内”或单个埋入点代替。执行 `resources/scripts/volume-fish/validate_fin_completion.py` 阻断检查，模型/配置改变后旧报告失效；缺鱼鳍、空选区、悬空或过度埋入不得声明完成。根区须按物种源图/资料定义，不能照抄其他鱼的选点。仍需灰模/贴图多视与原图对照，离散采样不证明全连续时间。详见项目 `docs/3d-fish/VALIDATION.md` 的072门。
   **本地 Godot 静态脚本合并临时例外（用户于2026-10-27指定）**：仅将当前实际显示的静态部件从 Godot 装配脚本回写可编辑源和 GLB、且尚未作为正式鱼资产交付时，允许先完成“本地迁移检查点”：核对旧实际装配与新冷读导出的部件、几何/UV/蒙皮、材质绑定和代表姿态画面，记录输入哈希、差异与已知缺陷。此检查点暂不重复跑完整鳍根/整鳍面177/490姿态，也不为此补齐历史逐鱼账本；受重导出影响的旧报告标为失效/待复验，不写通过。发现新增鳍穿体或装配不等价须先修相关问题。后续两次计划中的鳍大修完成并冻结正式候选时，再执行全部适用鳍专项、实际视觉审核和 `volume sop-check`；本例外不适用于新鱼、主动修鳍形/厚度/拓扑/骨骼、批量推广或正式交付。细则见生产SOP第0.2节。
   **静态模型修改逐鱼隔离**：Godot 中的实验性造型脚本仅可作用于明确指定的一条鱼和实验入口；未经该鱼旧装配对照、源 blend/GLB 固化及新进程冷读，不得加入通用进场链或推广至其他鱼。后续优化前，静态形状、UV、蒙皮及应属模型的贴图应落在可编辑源和导出资产；Godot 保留正常实时动画、行为及引擎材质绑定。每条鱼独立确定参数并记录结果，不复用上一鱼的外观验收结论。
9. Godot 只实现 Brief / Production Delta 范围。
10. shell、配置写入、删除和网络请求必须显式确认或走白名单。
   实验命令的临时目录、日志和重定向输出必须放在当前仓库明确指定的 `work/`、`output/` 或实验目录内；执行前核对解析后的绝对路径，不得把产物写到 `E:\` 等盘符根目录。实验结束后按已核验的保留清单清理临时产物和空目录，保留被 manifest、handoff、validation report 引用的证据。
   **每轮实验/验证结束必须做产物收尾，不能等到提交时才清理。**先核对运行状态及输入/输出引用，把有用结论、失败原因、参数、来源哈希、代表性图片/视频和复现方法写入既有 handoff、validation report 或项目正式记录；再按明确清单删除未采用候选、重复截图/录像、逐帧图片、稠密采样、临时模型/工程、日志和可重建缓存。验收所需的原始输入、当前资产及唯一证据不得因体积大而直接删除；不确定用途的文件先查引用与归档，不能把实验报告或技术通过当成用户验收。清理后核对实际剩余体积、清单目标及 Git/LFS 状态，并在本轮交付中说明保留与删除的范围，避免本地累积数十或数百 GB 的残留。
11. 用户要求“提交”即 **commit + push**，不能只 commit；同时检查 Foundry 主仓库和 `projects/fishing-2d` 独立 Git 仓库。只提交、推送有保留价值的代码、记录与验收资产。未验收的实验输出先提炼必要证据和结论，再清理无用临时文件。完成前分别确认两仓库 `git status --short` 为空，并报告各自的提交与推送结果。

## 文档

| 需要 | 文档 |
|---|---|
| 外部 Agent 协议 | [`resources/skills/gamefactory-toolkit/SKILL.md`](resources/skills/gamefactory-toolkit/SKILL.md) |
| CLI 与字段 | [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) |
| 工具链与配置 | [`docs/TOOLS.md`](docs/TOOLS.md) |
| 施工与验收 | [`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md) |
| 迭代 Delta | [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md) |
| Pipeline 阶段 | [`resources/skills/orchestrator/pipeline-schedule.md`](resources/skills/orchestrator/pipeline-schedule.md) |

077鱼类验收补充：用户明确身体除正常口腔外不接受镂空。每鱼交付须通过 `validate_body_integrity.py`，检查闭合身体、逐surface不透明供体及GPU同姿态覆盖；不能以网格闭合代替透明缺块检查。详见项目 `docs/3d-fish/BODY-INTEGRITY.md`。

083鱼类验收补充：身体纺锤形不意味着吻端应收成针尖。新鱼/头部修改须以同种吻型资料和正、俯、斜视灰模独立验证口裂、眼前宽度与唇缘；不要为贴图方便改错头型。已有鳍/身体门和旧profile approved不得替代此门。冻结物种横向包络时运行 `check_head_form.py` 并检查旧尖头负例，详见目标游戏 `HEAD-TRANSVERSE.md`。

125用户拒绝记录：嘴前端的平切面需要与上下唇自然弧面过渡，不能靠在原端面前追加尖突来伪造圆滑，更不能做成鸟嘴；不得为材质取色缩小眼前颅部。125非双髻鲨嘴部改动已按用户要求全部撤回，失败参数和运行时补丁不再作为模板。三种双髻鲨仅保留嘴线UV修复，不代表用户验收通过。详见目标游戏 `docs/3d-fish/ANTERIOR-125.md`。
