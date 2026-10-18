# 059i：嘴形调整后必须复核材质边界

用户否定059g的吻部材质衔接。几何圆钝改善不能抵消嘴角贴图破裂；上一轮只看技术和鳍根条件、局部形状仍不足。

根因：`head_projection`按面法线阈值把独立正/侧原画硬切为不同材质，改形后阈值边界移动；原侧图张嘴线和正面闭嘴线未对应，形成断线、接片和嘴纹叠影。

可选`head_projection.continuous_atlas=true`将纵向鱼体头部烘焙成一张连续图集，`blend_end_u`在源图横坐标中控制过渡完成位置。保留原生几何/蒙皮/动作，使用原已审核正侧图nearest取样和空间smoothstep颜色过渡，导出packed PNG、nearest GLB。属于派生纹理，不宣称每个图集像素是未经修改的原画像素。独立CLI校验要求派生文件固定路径、哈希、原画哈希、分辨率和GLB嵌入像素匹配；未声明新图仍被拒绝。此功能暂不支持横向头翼。

059h试验仍带有替换嘴纹donor引入的暗色竖带，未采用。059i提前完成正面取样过渡，移除最后一块mouth donor，侧/正/斜和真实Godot放大图中不再出现明显吻部硬切。diff确认全部5376身体顶点及眼片、鱼鳍、静止骨架不变，四动作32个实际蒙皮样本接触通过。32项CLI测试通过；既存Windows symlink测试因WinError1314无法完成。整鱼仍为实验待审，背腹UV问题未在本轮解决。

profile：`resources/volume-fish/peacock-bass-head-atlas-059i.profile.json`；游戏实验当前handoff：`experiments/blender-fish/models/peacock_bass/059i-head-atlas.handoff.json`。接受状态继续读取handoff与validation report。
