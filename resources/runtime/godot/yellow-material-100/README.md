# 大黄鱼100：已被用户拒绝的背腹取色试作

**视觉失败：用户指出正常身体纹理也发生了坏的变化。不得继续作为推荐材质或安装到正式游戏。** 整片曲面重新取色会改变正常鳞片/明暗/像素分布；后续从099恢复，只允许明确局部黑边范围的修补。

保持099 GLB和侧图，按全身体表截面在未见的背/腹继续金色和银白源皮肤。仅用于本条大黄鱼的材质试作，不是通用鱼类配色模板。嘴型、鳍根、骨骼与动作不变。

- `freeze_body_cap_chart.py`按当前Closed_body surface0冻结完整截面；参数和模型SHA在parameters.json。可重生成body-cap-yellow-croaker.json，结果逐字段相等。
- 历史隔离试验曾把chart写到100实验工程head-source.json的yellow_croaker.body_cap_chart；Helper校验模型SHA并传入uniform。
- FishBodyOpaque把已有原图去鳍纹计算抽成clean_skin_color，使原UV与新背腹供体共用修复。诊断unlit默认false，不影响普通游戏曝光。
- FishHeadSource只对大黄鱼应用试作。供体保持原图nearest像素，不以单色填满或添加细碎噪声。背腹和头前端未知外观标为艺术推断。
- 正式素材未替换；用户已明确拒绝该视觉结果。独立实验和真实游戏窗口：projects/fish-100-yellow-material/game。证据读取fish仓库experiments/blender-fish/yellow-material-100/completion.validation.json。

大黄鱼源图2014×727：侧图边缘及最近不透明扩展的黑绿暗色曾形成背腹环带。旧头部局部修复未覆盖完整下巴。另需同时检查原图眼圈、鱼鳍和鳃线是否被重投影到中央曲面；材质归属技术通过不能代替隐藏鳍/正俯仰视视觉核对。
