#101 大黄鱼下巴局部暗色试修

从099恢复；100整片背腹重采样已被用户拒绝。本试作只在身体surface0的下巴底边和小范围前下颌外皮处理暗色，正常身体、背腹、眼、鳃、口腔沿用099。

参数冻结在parameters.json；没有改源图、GLB、UV、权重、骨骼、动作或鳍根plan数字。FishHeadSource.gd和head-source.json仍为099原文件。两个shader文件以099为底，只增加局部遮罩和诊断开关。

1. 下边界参考099实际身体截面；与口部的距离参考真实下唇segment，不用旧侧图口线高度替代真实三维唇缘。
2. 只挑该区内暗色，从同列上下24个源像素内寻找邻近不透明浅色供体；找不到就保留原色，不远取其他身体/眼/鳍，不填一大片白色。
3. 保留唇缘、口内与正常灰色层次；本试作不声明所有暗色均该去掉。隐藏前端皮肤供体仍是艺术延续推断。
4. 相同实际游戏场景/机位/姿态分别渲染原099、新shader关闭/启用和允许修补mask。validate_local_material_preservation.py检查九视，关闭时须与099像素完全相等；启用后范围外须零变化，不裁切配准、不膨胀mask、不放宽容差。
5.100整片背部取色画面作为反例；同一遮罩下应因范围外改变失败。范围/颜色正确与否仍需用户看对照，机械门不做视觉批准。

证据：fish仓库experiments/blender-fish/yellow-chin-ink-101/completion.validation.json。尚未替换正式资产，未执行volume accept。原本背腹的暗纹在本轮没有处理；后续另行定位，不套用100全曲面重采样。

## 本轮后台运行

GPU截图、录像使用macOS open -g -j -n，不调用窗口置前。普通检查Godot --headless、Blender -b。resources/scripts/godot_background.py供需要同步等待的验证wrapper使用；它要求显式实际Godot路径，并设置FOUNDRY_MANUAL_RENDER=1。LaunchServices不转发引擎退出码，wrapper仍必须核日志和新鲜receipt。

capture_body_coverage.gd的后台手动渲染在新姿态第一视图前提交一次骨骼状态，随后同姿态比较actual/reference。初次无预热时，4条未改鱼的maximum_amplitude/view0出现少量伪轮廓缺失；保留失败报告，改采样时序后全部336视图零缺失。没有改变模型/容差/比较选区。
