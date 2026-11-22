# C 版游客与三鱼展缸试摆

成年女性采用用户确认的 C 版头身比和五官布局，可编辑源为 `woman.blend`，贴图为 `face-layout.png`。成年男性、小孩和老人共用 C 版的五官位置。短发轮廓、肩宽、四肢比例、衣装和站姿通过各自模型区分。老人采用银发、浅紫开衫和细框眼镜。每人使用一张图集和一个材质。

男游客的平眉半睁眼看向一侧，小孩抬眼张嘴惊叹，老人隔着镜框眯眼露齿笑。三人的独立五官原画在 `expressions/`，眉、眼、鼻、嘴分别按 C 版的脸部位置贴入图集。`expressions.jpg` 是四个游戏模型的并排近照。

在游戏仓库运行 `open-tank-design.cmd visitors` 打开只读试摆。界面可以在展缸旁的自然朝向和近距离正面之间切换。四个固定站位在 `game/scenes/visitor_family_display.tscn`，试摆入口读取 `game/examples/hall-handoff-20261120.json` 的三鱼矩形展缸。日常人群的移动与动画接入属于后续工作。

四份同名 Blender 源均内嵌贴图。`paint.py` 从保留的原画生成男游客、小孩和老人的图集，Blender 后台脚本 `build.py` 从四份源导出游戏模型到 `projects/fishing-2d/game/assets/visitors-c/`。`models.json` 记录源模型统计，`check_hall.gd` 在实际游戏工程运行，`hall-check.json` 记录三鱼、四人、玻璃间距和两个镜头的后台验证。`exhibit.jpg` 使用游戏中的站位、鱼的位置、相机方向与展缸尺寸，在 Blender 中近似还原展缸材质和照明。
