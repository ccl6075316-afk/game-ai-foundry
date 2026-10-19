# Game AI Foundry — External Agent One-pager

本仓库是给外部 Agent 使用的纯 CLI / Workflow 工具箱。不要假设任何桌面客户端、内置会话或品牌专属运行时。

## 读取顺序

1. 读取 [`resources/skills/gamefactory-toolkit/SKILL.md`](resources/skills/gamefactory-toolkit/SKILL.md)。
2. 运行 `python cli/gamefactory.py workflow --help` 和需要的子命令 `--help`。
3. 按 `context → validate → init → run → status → resume` 调用，全部加 `--json`。
4. 只把 `manifest`、`progress`、`handoff`、`assets-manifest`、`validation report` 当作状态。

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
9. Godot 只实现 Brief / Production Delta 范围。
10. shell、配置写入、删除和网络请求必须显式确认或走白名单。
11. 用户要求“提交”时，同时检查 Foundry 主仓库和 `projects/fishing-2d` 独立 Git 仓库；只提交、推送有保留价值的代码、记录与验收资产。未验收的实验输出先提炼必要证据和结论，再清理无用临时文件。完成前分别确认两仓库 `git status --short` 为空，并报告各自的提交与推送结果。

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
