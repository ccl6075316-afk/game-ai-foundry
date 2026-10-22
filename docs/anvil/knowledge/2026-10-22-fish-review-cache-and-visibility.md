---
type: debug-knowledge
status: SUCCESS
bug_topic: Fish review imported-cache mismatch and background tank rendering
date: 2026-10-22
---

# 启动前导入与分缸可见性

成功范围仅是两个运行问题；112候选的鱼体纹理质量、正面嘴部黑环和下唇线仍未接受。

## 根因

拉取更新后的GLB、新profile与38张surface112贴图后，旧`.godot`缓存仍被runtime直接读取。黑鲷/梭鲈的旧导入数组与新profile不一致，严格眼域/LOD门中止注册；新PNG的ctex缺失，空纹理采样可变成纯白。相同Godot4.7.1仅重新导入后23鱼全部恢复，因此不是必然的跨平台数组不兼容，不应放松哈希门。

独立分缸选鱼只移动相机，仍绘制背景透明缸和其他鱼。巨骨舌鱼近景可达520绘制、p50/p95 39.461/51.559ms。仅隐藏其他缸、保持所有控制器继续运行后降至146绘制、12.775/14.708ms，支持背景渲染是此机位的显著成本。不能据此精确归因新增某张材质。

## 修复与验证

`cli/godot_cmds.py::launch_game_project`在Popen前同步import，检查非零退出和stdout/stderr的ERROR；skip-build仍import。Fish的`open-3d-review.cmd`也先import并阻断错误。独立自建fixture只移走ctex即可重现空采样ffffffff，reimport恢复b4281eff；Godot退出0并不证明没有错误。

`VolumeFishExhibit.gd`只增加缸可见性刷新，在选鱼、总览和近看入口调用。全部鱼时钟、原控制器/材质/模型不变；总览恢复全部，shared_tank始终显示共用缸。未将冻结未选鱼时钟混进同一修复。

新启动测试先在旧版失败，修后CLI全765项通过（2项跳过）。实际GPU展厅回归1314项通过；最终巨骨舌鱼p50/p95 12.573/14.301ms、147绘制。黑鲷9.322/12.774ms，梭鲈9.582/13.119ms。独立debug_review逐阶段批准两个修复。

## 识别与预防

- 新源文件不等于导入缓存已更新。先查实际load与完整日志，再判断profile或美术输出；修启动源头，不删除校验。
- 选鱼/移相机不等于背景内容不渲染。先做同场景可见性单变量A/B，再考虑shader优化。
- 128段搜索的临时二分A/B只显示约0.1ms的force_draw中位差，p95波动，不能把它认定为主要卡顿根因。未部署该shader试验。
- 可见性检查覆盖全部23鱼、暂停选鱼、总览进近看、共游和全部控制器时钟；不能只测初始默认鱼。

## 证据与边界

Fish `experiments/blender-fish/review-regressions-113/runtime/`保存负例、导入、GPU回归与性能报告；嘴部标线与surface隔离在同轮`lip-mapping/`。debug会话见`docs/anvil/debug-sessions/2026-10-22-fish-review-regressions-session.md`。

性能仅覆盖本机Apple M4、已预热的120帧。总览/共游仍绘全场；冷启动、首次shader编译和Windows未作同等性能保证，Windows cmd本机只作静态审查。恢复纹理加载不代表二维供体质量通过；源描边错误环绕正面、口内横条及下唇对应仍须独立返修。人工绿色候选线不等于用户已确认的裁改边界。
