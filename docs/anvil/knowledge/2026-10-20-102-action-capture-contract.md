# 离线采集必须核对实际动作

FoundryFishMotion.set_action只排队，seek会清掉pending。要截指定动作，先assert(set_action(action,true))、step(0.)，再seek(time)。每帧断言snapshot.action与请求一致，并绑定控制器、profile、GLB、采集脚本和截图哈希。不能仅凭输出文件名认定实际动作。

102首次22鱼352帧中264帧误标动作，撤销该批动作标签后重采；修复后0不匹配。只修采集调用，未改控制器。静帧与四动作有限采样都不构成连续时间或切换验证。独立复核见fish项目surface-mouth-audit-102/capture-review.validation.json。
