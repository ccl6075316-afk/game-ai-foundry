# 命令拒绝与实验清理：按需处理

仅在命令被拒绝、清理失败，或准备执行实验产物清理时读取。不扩展 AGENTS.md 的常驻正文，不把聊天中的“换个命令”当成无条件重试规则。

## 已验证的本仓库入口

先查 `resources/scripts/maintenance/clear_reviewed_caches.ps1`，不要每轮重新拼长内联删除命令。它默认预演，显式 `-Apply` 才删除；校验工作区绝对路径、符号链接/目录联接、文件哈希、Git 跟踪/忽略状态及运行中的工程，逐文件用 `Remove-Item -LiteralPath` 删除，仅移除空目录。

**适用范围是已审核、被 Git 忽略且未跟踪的 `.godot`、`__pycache__`、`.pytest_cache` 缓存。** 当前游戏导入缓存受保护，活动工程跳过。它不是任意实验目录清理器，不能把鱼鳍490姿态JSON、动作帧、源blend、原始参考或正式资产改名放进其白名单。其他产物须另行核对引用、保留清单和适用的执行器，不直接扩大现有脚本的白名单。

从仓库根目录执行；`-Plan` 指向本轮新审核且位于仓库 `output/` 下的清单，不能原样重跑历史执行名单：

```powershell
& ./resources/scripts/maintenance/clear_reviewed_caches.ps1 -Plan ./output/<本轮目录>/cleanup-plan.json -WorkspaceRoot E:/game-ai-foundry
# 查看预演结果，确认本轮授权、保留项与输入仍一致后，才使用执行模式：
& ./resources/scripts/maintenance/clear_reviewed_caches.ps1 -Plan ./output/<本轮目录>/cleanup-plan.json -WorkspaceRoot E:/game-ai-foundry -Apply
```

清单包含 `workspace`、`directories` 和 `files`（每项 `path`、`sha256`、`bytes`），字段以实际脚本为准。预演也会在清单旁写 `cleanup-preflight.json`；执行写 `cleanup-execution.json`。事后检查实际删除数、跳过原因、保留项和两仓库 Git/LFS 状态，不能仅凭退出码或预演成功宣称已清理。

## 拒绝后怎样判断

1. **先确定是否执行过。** 保存工具返回的原文、实际命令/脚本与输入清单引用；读取任务/进程/执行报告，防止部分执行后重复提交。不要把工具启动前拒绝、shell语法错误、脚本预检失败和运行中失败混成一种问题。
2. **修有依据的问题。** 路径、引号、参数、输入格式或工具能力确有错误时，修正该错误并重新预演。新操作优先用已审阅的仓库脚本与短参数调用；复杂操作先落可审阅脚本，避免多层shell、字符串拼命令、宽泛递归删除。记录具体改善了什么，不能只记“换命令就能过”。
3. **审批拒绝不等于语法错误，也不等于整个目标永久不可做。** 若返回的是自动审批/安全拒绝，遵守所述权限与行为限制；可以先只读查证、重新审阅清单，判断是否存在允许范围内、实质更安全的方案，并明确新增的校验和适用边界。若只给 `blocked by policy`，原因记为未知，不自行断定误报或声称某种写法必定解决。不得仅用同义命令、换解释器、编码、拆分、提权或降低校验来绕过同一拒绝。
4. **保留可复用结论。** 在既有 handoff/validation report 写清失败类别、修正依据、工具/清单哈希、预演和实际执行结果。适用且授权的处理仍被拒绝时，记录未完成范围和保留体积；不要反复盲试，也不要把一次拒绝推广成今后所有清理都不能做。

## 本地成功案例与适用限制

**鱼类交付姿态/帧缓存已有独立入口**：`resources/scripts/maintenance/clear_reviewed_fish_delivery_cache.ps1 -Plan <output中的审核清单>` 默认预演，`-Apply` 才执行。它不扩展普通缓存脚本白名单；只接受已完成交付下的 `fin490/<物种>/sample-NNN.json` 与 `review/frames/frame-NNNN.jpg`。清单须由当前 `prune_delivery_cache.plan()` 重新计算，绑定当前交付/模型/专项报告、已验证归档与保留的极值/代表相位。执行器拒绝归档保留项、已跟踪文件、未忽略文件、越界路径、目录联接和活动工程，不递归删目录。

2026-11-01用户再次要求处理后，该入口实际删除3653文件、950986575字节；237个保留姿态/帧重新验哈希通过。记录见游戏 `plans/reviews/five-fish-width-detail-20261031/cleanup-20261101/`。此前拒绝记录仍保留，不能改写成当时已通过。

本次可复用的调用问题：Windows Git `check-ignore --stdin` 不接受本次测试中的驱动器绝对路径，使用仓库相对路径；PowerShell文本管道的CRLF会使该Git把CR当路径字符，显式传LF后才正确识别。批量查询同时异步读取stdout/stderr，避免大清单写stdin与输出管道互等；不要为绕开误判取消Git检查。3653目标的完整预演约8秒。新缓存目录的忽略规则也须限定实际可重建路径，不能用全实验目录忽略来掩盖待提交源资产。

2026-11-01 维护记录 `docs/MAINTENANCE-ARCHITECTURE.md`“本地盘点与清理”：首次内联删除返回 `blocked by policy`；用户随后要求检查执行方式，新增上述专用脚本与更严格预检后，实际删除1643文件、257342402字节，未修改权限配置。证据见游戏 `plans/reviews/maintenance-20261101/evidence/cleanup-execution.json`、`cleanup-verification.json`，历史路径迁移见该轮 `artifact-relocation.json`。

这些案例证明各自特定范围的清理入口曾实际成功；**首次审批拒绝的具体原因仍未知**，不能推广为“只要把被拒命令装进脚本就可执行”，也不能混用不同产物的白名单。
