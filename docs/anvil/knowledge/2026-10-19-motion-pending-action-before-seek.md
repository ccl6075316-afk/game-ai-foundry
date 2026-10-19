---
type: debug-knowledge
status: SUCCESS
bug_topic: Queued fish action cleared by seek
date: 2026-10-19
---

# 排队动作后用step消费请求，再定位

083隔离交互预览从Turn重新开启行为时仍停留Turn。真实smoke稳定在恢复Swim断言失败；根因是wrapper先set_action(Swim,true)再seek(0)。控制器seek清空pending action/restart，因此请求丢失；初始已是Swim时掩盖了问题。

只把wrapper初始化的seek0换step0。公开step先消费restart、把_action设为Swim，再内部seek0，不推进时间，不修改控制器。原smoke10鱼/16s结束/重播/Turn→重新开启全部通过，独立Phase4批准。检查绑定的模型、controller、motion及shader均未修改。

未来测试从不同当前动作返回，而不只测试初始默认态。区别排队请求、消费请求与定位当前动作；按公开API时序调用，不能为修调用方而改变seek语义。

相关：resources/runtime/godot/FriendlyFishExhibit.gd；docs/anvil/debug-sessions/2026-10-19-083-friendly-toggle-session.md；projects/fishing-2d/plans/reviews/083-friendly/083-ui-review.validation.json。该UI成功不构成黑鲷几何接受。
