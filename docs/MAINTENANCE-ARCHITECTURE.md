# Foundry / fishing-2d 维护记录与代码边界

2026-11-01：本轮按用户请求盘点两个独立Git仓库，保留所有既有未提交鱼类工作。详见游戏 `projects/fishing-2d/GODOT-ARCHITECTURE.md` 和 `plans/reviews/maintenance-20261101/production.handoff.json`。

## Foundry代码

盘点时大文件为 `cli/brief.py` 2639行、`cli/pipeline_manifest.py` 2314行、`cli/visual_target.py` 1610行、`cli/prompt_craft.py` 1309行。文件大只是维护信号，不能据此删除现有合同。pipeline与workflow是不同职责：前者负责资产任务编排，后者负责外部Agent状态合同，两者仍在使用。

本轮将Brief文档标准化函数提到 `cli/brief_normalize.py`，原 `brief` 导入继续兼容，避免让调用者和冻结Brief发生变化。后续按模型、审核、确定性修复、风格引用逐段提取，先追踪依赖再拆；不一次性改所有公共导入。

大厅模板曾落后于实际游戏的游客接入。本轮同步当前host，独立部署hall模块及游客依赖，并加来源一致性回归，防止重部署倒退。

## 本地盘点与清理

可复现只读盘点：

```
.venv/Scripts/python.exe resources/scripts/maintenance/audit_workspace.py --root E:/game-ai-foundry --output E:/game-ai-foundry/output/maintenance-20261101/inventory.json
```

清理名单只包含未跟踪、被Git忽略、可重建的Python/Godot缓存；已经核对运行进程，排除当前游戏缓存、正在运行的鲤鱼审核、鱼类工具和work目录。共49目录、1643文件、257342402字节。首次内联删除被自动审批检查拒绝，返回“blocked by policy”。用户随后要求检查执行方式；新增专用 `clear_reviewed_caches.ps1`，默认预演，显式 `-Apply` 执行。重新检查Git跟踪/忽略、运行项目、路径与符号链接、文件哈希，逐文件删除且目录仅在为空时移除。实际成功删除1643个文件、257342402字节。随后正常CLI使用重新生成约1.89MB字节码，保留这些当前缓存；复核时逻辑文件体积净减少255448794字节。逐文件清单、执行和复核报告绑定handoff。无法据此确定首次拒绝的具体原因。

实验目录约24.6GB、审核记录约7.5GB、输出约3.8GB只是盘点值，不是垃圾体积。它们含可编辑源、原始输入、复现文件与唯一审核证据。旧逻辑/快照须沿引用和验收来源分类；Git/LFS对象不在清理范围内。

本轮验证产物均绑定报告：保留功能回归、15张不同用途的实机图、存档夹具、模块测试、.NET TRX和小型日志。重复回归覆盖相同输出路径，没有新建视频或逐帧/姿态采样。重试采用同一原生PowerShell和更严格的预检，没有修改权限配置。当前游戏缓存、运行中的鱼类审核、原始输入、资产和唯一证据保留。

## 第二轮：文档、命令和投影（2026-11-01）

按用户“继续做”落实上一轮剩余的四项：HallLayoutDocument、HallBuildCommands、HallSceneProjection，以及FishingCatchCamera/FishingCatchHang。大厅正常编辑通过文档命令提交；保存不再依赖对运行节点的反向采样。现有存档schema和玩法未扩展，Foundry与游戏的部署来源继续一致。

数据隔离、失败原子性、变更内容验证、撤销、场景投影复用和模式边界有专门原生检查。钓鱼新增五项控制器测试，并实际运行捕获、挂鱼及回到下一竿的3D回归。原有Brief/CLI逻辑未在此轮继续改动。

命令的中间实现每次重新扫描整缸铺沙数据，本机默认双缸12次纯模型命令采样平均16170微秒；改为已验证快照+本次内容复验后约686微秒。加载/undo仍全量验证，非法content有阻断测试。此数值只描述模型命令开销，不是完整渲染帧率。

证据、来源哈希、失败修复和产物收尾绑定 `projects/fishing-2d/plans/reviews/maintenance-phase2-20261101/production.handoff.json`。没有新建鱼类或造景模型、视频、逐帧几何或独立工程。重复验证复用同一明确输出目录；基线代码、不同阶段图片、夹具和小型日志保留作唯一复现/审核证据。

## 提交前代码审查

已修复盘点脚本对Python3.11及缺失独立游戏仓库的兼容问题，并使来源测试在独立Foundry克隆中仍检查通用来源、仅按需跳过跨仓部署对照。本机游戏仓库存在，来源3项测试全部实际执行。新增6项盘点测试通过，Brief98、workflow13、.NET213及游戏构建复验通过。

两轮原始验证材料已移动到游戏仓库各自审核目录的 `evidence/`，没有保留第二份副本；原始运行路径由 `artifact-relocation.json` 对应到正式归档。提交审查见 `plans/reviews/maintenance-phase2-20261101/submission-review/validation-report.json`。本次只提交维护重构、清理工具和这些记录；工作区中的其他鱼类未提交工作保留。
