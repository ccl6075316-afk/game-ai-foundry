# 施工体系

> 目标：从冻结 Brief 得到可编译、可验收的 Godot 工程，且每次施工都可恢复、可回溯。

## 1. 四条支柱

### 1.1 Spec 先于 Code

`brief.json` 是玩家体验与范围契约；`production.json` 是可施工蓝图。两者都不能靠会话记忆替代。

```bash
python gamefactory.py brief freeze --input <draft> -o <brief> --json
python gamefactory.py production derive --brief <brief> -o <production> --json
python gamefactory.py production validate --production <production> --brief <brief> --json
```

### 1.2 Production 蓝图

Production 至少包含：

- `scenes[]`：场景树、入口、主流程。
- `systems[]`：脚本职责、信号、状态与规则。
- `input_map[]`：控制映射，对齐 Brief `controls`。
- `godot_tasks[]`：依赖、实现范围、每项 `verify[]`。
- `validation.acceptance_criteria`：功能与视觉验收。
- `validation.regression_checks`：旧行为回归。

### 1.3 确定性施工链

```text
production → scaffold/assemble → progress → godot task → validate → test
```

```bash
python gamefactory.py godot scaffold --production <production> --project <project> --validate
python gamefactory.py project progress init --production <production> --brief <brief>
python gamefactory.py project handoff create --title "<title>" --summary "<summary>" --task-id <task_id> --brief <brief> --json
python gamefactory.py godot validate --project <project>
```

### 1.4 分层验收

| 层 | 门禁 | 证据 |
|---|---|---|
| L0 静态/构建 | `godot validate` | import、C# build、main scene |
| L1 单元 | `test unit` | 系统规则与纯逻辑 |
| L2 功能 | `test plan` + `test play` | 输入模拟、截图、胜负与核心循环 |
| L3 视觉 | visual target + screenshot | 画面符合 Brief |
| L4 回归 | `test regression` | Change 后旧行为仍通过 |

## 2. 范围控制

施工实现的唯一范围是：

```text
冻结 Brief + 已应用 Production Delta + 当前 handoff
```

- 不增加 Brief 未声明的场景、系统或玩法。
- 不通过修改测试期望掩盖实现错误。
- 不把未来规划提前写进当前 slice。
- 不因资产失败绕过验证直接组装。
- 复杂游戏按 slice 施工；当前 slice 完成并验收后再扩范围。

## 3. 权威状态

| 文件 | 施工用途 |
|---|---|
| `production.json` | 蓝图、任务依赖、验收 |
| `progress.json` | 任务状态、validation phase、回归快照 |
| `handoff` | 单次施工输入、范围、完成条件 |
| `manifest` | 资产 DAG 与输出状态 |
| `assets-manifest` | 资产交付与 review |
| `validation report` | 构建、功能、视觉、回归证据 |

新会话必须先读取这些文件；不能凭自述判断完成。

## 4. 标准施工循环

```bash
# 1. 发现
python gamefactory.py workflow context --brief <brief> --json
python gamefactory.py workflow status --manifest <manifest> --json
python gamefactory.py project progress show --progress <progress> --json

# 2. 选择任务
python gamefactory.py project handoff list --json
python gamefactory.py project handoff show <handoff_id> --json

# 3. 实现限定范围
# 读取 production、handoff、progress 后修改 <project>

# 4. 验证
python gamefactory.py godot validate --project <project>
python gamefactory.py test unit --project <project>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>

# 5. 记录
python gamefactory.py project progress task --progress <progress> --task <task_id> --status done
python gamefactory.py project handoff status <handoff_id> --set done
```

状态更新必须以实际验证结果为依据。

## 5. 资产到 Godot

1. Workflow 跑完 assets stage。
2. `assets review list` 检查交付路径与 `review.status`。
3. 接受、替换或定点重生成问题资产。
4. `godot assemble` 导入已审查资产。
5. `godot validate` 构建并启动主场景。
6. 资产不合法时回到 Pipeline，不手改 manifest 冒充完成。

关键媒体规则：

- `validate before matting`。
- 动画使用原始 still；idle 使用独立 `*_nobg.png`。
- 视频帧用 `video matte-frames --engine ai`。
- 图片后处理使用 `--input` / `--output`。

## 6. Change 后的施工

```bash
python gamefactory.py production delta --change-id <change_id> --intent "<intent>" -o <delta>
python gamefactory.py production apply-delta --delta <delta> --production <production> --dry-run --json
python gamefactory.py production apply-delta --delta <delta> --production <production> --progress <progress> --json
python gamefactory.py project progress sync --production <production> --progress <progress>
```

随后只施工 Delta 新增/修改的 `godot_tasks[]`，并重跑受影响测试与 `test regression`。

## 7. 失败处理

| 失败 | 修复方向 |
|---|---|
| production 校验失败 | Brief/Delta 不一致；重新 derive 或修 Delta |
| asset failed | 读取 manifest task result，修 prompt/输入后 resume |
| asset review rejected | replace/regenerate，不继续 assemble |
| Godot build failed | 修 Production 声明的工程问题 |
| unit/play failed | 对照 acceptance criteria，修实现或提出 Change Request |
| regression failed | 恢复已接受行为，不能降低旧验收 |

## 8. 不可协商规则

1. 冻结 Brief 是设计事实源。
2. Production 是施工事实源。
3. Progress / handoff 是续作事实源。
4. Validation report 是验收事实源。
5. Godot 实现不越 Brief / Delta 范围。
6. 未通过验证的任务不能标为 done。

相关文档：[`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)、[`AI-HANDOFF.md`](AI-HANDOFF.md)、[`GODOT-GAME-ARCHITECTURE.md`](GODOT-GAME-ARCHITECTURE.md)。
