# 042：已有 3D 鱼的动作与独立鱼缸

## 已落地的方法

Foundry `volume motion-plan → motion-build → motion-validate` 复用已审核的 GLB，固定模型、物种 profile、审核证据和控制器哈希。技术 handoff 的 `human_review` 仍要求实际引擎视觉审核；它不会自动宣称动作美术合格。

通用控制器位于 `resources/runtime/godot/VolumeFishMotion.gd`，四个 profile 位于 `resources/volume-fish/motion/`。展厅仅消费其产物，每鱼一个控制器与独立鱼缸，一个共享世界/视口。当前动作是游动、转身、上浮、下潜。

基础 AnimationPlayer 使用手动推进。每次先恢复基姿并评估基础动画，再添加局部骨骼弯曲，避免叠加上一帧姿态。骨骼轴需按各自 rest/model/skeleton 基变换确定，不能把银龙鱼的关节数、轴向或相位照搬到其它鱼。转向弯曲幅度和曲率都沿头至尾延迟传播，普通动作切换保持路径连续。重播是用户显式回到起点；上浮/下潜展示循环有平滑回程。

鱼缸按动作范围和保守蒙皮包络设定，不能只检查鱼的中心。实际 Apple M4 GUI 验收覆盖四鱼×四动作、260 项断言。包络每个 60Hz 步检查；实际蒙皮顶点在每周期16个均匀相位、路径/高度四分位、过渡起中终检查。这是离散覆盖，不能称为逐帧全顶点证明。源纹理 nearest、原模型和041鲨鱼眼位保留。

## 物种依据与限制

- [Monterey Bay Aquarium 黑鳍礁鲨](https://www.montereybayaquarium.org/animals-the-ocean/animals-a-to-z/blacktip-reef-shark)：浅水礁区巡游的展示背景；未提供本项目转弯半径或摆尾频率。
- [Smithsonian National Zoo 银龙鱼](https://www.nationalzoo.si.edu/animals/silver-arowana)：长体与连续长背/臀鳍、向水面捕食的形态参考；未提供四动作的定量运动参数。
- [东京海洋生物园带鱼观察](https://www.tokyo-zoo.net/topics/news/kasai/6012_20074_2011-09-23.html)：普通运动主要由长背鳍波动驱动，受到刺激时可水平游动。因此降低原身体摆动叠加，保留独立背鳍动画。本组是主动游动展示，不是头朝上的悬停模拟。

速度、动作周期、弯曲幅度、升降范围和延迟是本游戏的美术校准，不能宣称为实测生物力学。食人鱼也未取得定量动作测量。后续添加鱼需重新审核其轴向、骨骼、鳍和动作范围。

## 成本与证据

042 不重新生成图像、视频或模型：新增生成 API 调用为0。使用已有基础游动动画与实时骨骼/路径动作。正式 handoff：`projects/fishing-2d/plans/volume-motion/042-action-tanks.handoff.json`；原生 GUI 报告：`projects/fishing-2d/output/042-3d-fish-action-qa/validation.json`。完整视觉与入口验收由本轮最终 validation report 记录。
