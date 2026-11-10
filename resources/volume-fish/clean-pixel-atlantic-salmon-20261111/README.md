# 大西洋鲑清爽像素材质：R3已接受并安装

2026-11-11 用户接受当前R3并要求提交推送。维护入口为 release.json，实际正式源为游戏 assets/source/fish/atlantic_salmon/fish.blend，正式模型为 game/assets/models/fish/atlantic_salmon.glb；唯一原供图在源目录 clean-pixel-20261111。游戏 plans/reviews/clean-pixel-atlantic-salmon-20261111/HANDOFF.md 保留本轮方法、参数、数值和限制。28条静态基线，新风格累计10条接受、18条待做。

先完成去鳍身体并实际审嘴/两侧/俯腹/斜视，冻结961589身体纹素，再独立烘8鳍；随后用户反馈偏淡，R3只校准背部243188个RGB纹素，头眼56767纹素、嘴/全部8鳍RGBA与原alpha保持。64个非图像accessor、几何/UV/法线/骨权/骨架/动作不变，1952三角、4026顶点、19骨。具体投影、颜色和保护域参数在 parameters.json；自然暗斑保留，银灰鳍使用本鱼实际前景域。

正式源独立新进程冷导逐字节一致；当前490/072/077、正式/缓存480控制与360切换、四动作像素对照及真实上唇25项通过。SOP runtime通过，未重做的资料/形态/完整视频项仍pending，不宣称完整SOP通过或动作质量接受。

作者脚本为本次实际方法快照，保留历史work相对布局；不得在本目录直接执行或恢复已退休实验模型。后续从当前正式blend维护。正式根域沿用 tail-closure-repair-20261106/atlantic_salmon/complete-root-domains.json，不用材质UV重新定义解剖。清理清单及实际字节见游戏 release-cleanup.json，旧路径/SHA仅作溯源，不表示可重放。
