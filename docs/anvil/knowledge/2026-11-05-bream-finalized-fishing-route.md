---
type: debug-knowledge
status: SUCCESS
bug_topic: Finalized bream fishing routing after history retirement
date: 2026-11-05
---

# 成品鲷鱼的钓鱼入口必须使用当前成品合同

## 根因

真鲷、黑鲷已经用完整自带动画的packed GLB取代旧实验装配，展示缸使用当前width finalizer直接读取GLB，钓鱼入口却仍走旧导入PackedScene、退休review controller和body mesh名称猜选。退休旧资源后，真实钓鱼configure先因缓存场景引用final171/final172的old-native-animation.res失败；即使重导缓存，随后控制器路径和Anal_mesh口锚归属仍不正确。不能恢复旧资源或用null守卫掩盖整个合同缺失。

## 修法

只对width表明确提供`mouth_recipe_required`及哈希绑定上唇recipe的行启用成品钓鱼路径。本轮只加入真鲷、黑鲷：复用已有width finalizer的SHA守卫、direct GLTF loader、motion profile/controller及原嵌入材质，按原review scale归一，再使用钓鱼类既有native position/UV/named skin/socket身份核验。其他22鱼入口行为保持原样，没有静态builder、旧资源恢复或绕过守卫。

上唇点必须来自实际skin/oral roof共有边，先冻结body/mouth归属，再在真实上唇域内定位，不从整鱼maxX或nearest head选点。黑鲷没有现成中央上唇顶点：当前绑定实际侧端，保留其非零横向偏移；中央对应边的插值证据另存，不把侧点写成中央点，也不为钓钩改变嘴形。

## 验证与限制

修前真实canonical Godot进程：piranha成功，两鲷configure/ready失败。用同一未修改GLB组装既有成品合同，独立两次新进程均22项通过。一次实现试验因helper原用tab而追加spaces发生解析错误，已立即回滚；直接check-only精确定位后，只改新增块缩进，在隔离项目先验证。Godot check-only可能exit0同时输出Parse Error，必须检查完整日志。

隔离真实actor正例通过；错误model SHA、错误recipe SHA、修改UV并更新recipe hash、非body vertex四负例均拒绝该鱼，另两控制鱼保持成功。随后正式入口新进程34检查通过，包括四动作、真实蒙皮上唇、钓钩放置、scale、单rig/player、静态数组不变。全24对照只有两鲷false→true，其余22结果相同；11个范围外既有旧入口失败如实保留，未声称全项目测试全绿。每阶段独立adversarial review通过，无commit/push。

本验证只绑定当时canonical旧模型字节，不能授予后来身体返修GLB通过。安装新源/模型后必须更新身份表和recipe，重新实际冷验。完整debug session及收据索引：`docs/anvil/debug-sessions/2026-11-05-repaired-bream-fishing-session.md` 与游戏 `experiments/top-body-repair-20261105/root-review/`。

## 预防与入口

新成品替换检查必须同时覆盖展示缸、FishingVolumeFish.configure和真实mouth_world/place_hook，不能只核展示缸和静态SHA。packed mesh名不是解剖部位，不依赖生成器偶然留下的Anal_mesh名称判嘴。先在隔离项目验证脚本解析、正例和身份拒绝，再更新当前runtime；文件缩进风格保持本文件原样。

相关实现：游戏`game/scripts/screens/FishingVolumeFish.gd`、`game/scripts/aquarium/FinalizedWidthBatch20261101.gd`、width20261101 manifest及两份mouth-anchor。静态语义提取与新导出重绑工具分别为Foundry `extract_packed_upper_lip_recipe.py`、`rebind_repaired_upper_lip.py`。这些工具只提供候选绑定，真实上唇、源身份和新进程钓鱼检查仍由操作者完成。

本轮收尾：完成调试的fishing-route-game/staged-runtime隔离夹具已按清单退休，仅保留实际输入SHA、正负例结论及生产实现；不是可重放旧模型证据。该调试时的canonical为身体返修前版本，后续新模型实际入口读fish-shape-repair-20261105正式记录。
