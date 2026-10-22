# 像素钓鱼场景：3D 水、竿和鱼的接入记录

来源：fishing-2d 的 114 → 115 → 124 迭代，2026-10-23。技术检查完成，用户视觉验收仍待确认；不代表复用鱼模型的新一轮外观批准。

## 可复用方法

- 远景与船保留 2D；水、鱼、外放鱼线在同一个 3D 世界中，才能共享深度遮挡。前景竿另用相同相机的透明视口。低分辨率视口以 nearest 整数放大，避免像素宽度不均。
- 海面大形使用方向性 Gerstner 波，细节法线、反射和泡沫分开控制。CPU 与 shader 共用时间、波参数；查询实际水高时反解水平位移，不能直接把参数平面的坐标当世界坐标。
- 深度纹理用于鱼身附近接触泡沫和水下衰减；Compatibility 的 NDC 深度换算必须单独处理。透明物体不一定写深度，不要把屏幕读取当作完整折射或流体模拟。
- 鱼跨越实际波面时在世界坐标发射水滴；速度影响强度，水滴落回同一波面后结束。涟漪应稀疏并淡出，密集白环会像标靶。
- 线的终点使用实际骨骼蒙皮点，鱼动画、姿态和镜头更新后再求连接。机械连接测试不证明鱼种解剖位置正确：下位口等物种仍需专门嘴部锚点和视觉检查。
- 鱼竿抬高、居中后再调整受力弧线；UV 程序材质可采用原像素图的黑金配色与阶梯高光。nearest 本身不能把写实软木纹理变成像素画风。
- 导环支架应沿自身局部轴缩放；旋转后直接按世界轴缩放会出现尖刺。线轴放线转动由实际放线速度驱动，不能只监听收线按钮。
- 起鱼时保留鱼的初始相机深度，再连续移向近景，避免从远处瞬间跳到镜头前。

## 复用鱼模型的验收

复用现有 GLB 和动作控制器，不修改共享模型以解决场景表现问题。保留模型原有接受状态。记录模型、动作配置、控制器和验证脚本哈希。

完整鳍基检查使用 `resources/scripts/volume-fish/validate_fin_completion.py`。默认 exporter 固定加载通用控制器；当 plan 的 `controller_script` 指向物种专用控制器时，必须显式传入 `--exporter resources/scripts/volume-fish/export_runtime_fin_roots112.gd`。124 的首次全量检查因此中止：19 种正确控制器报告保留，其余六种用正确 exporter 重跑，再逐项校验哈希后汇总。不可将控制器不匹配解释成鱼模型通过，也不能放宽阈值跳过。

身体完整性另跑 `validate_body_integrity.py`。技术通过只覆盖所采样姿态；不能替代每鱼灰模、贴图和嘴部解剖审核。

## 证据与清理

游戏仓库保留 `plans/reviews/124-fishing-water-volume/validation-report.json`、完整 plan、接触/身体检查报告、最终少量 GPU 截图及测试结果。逐姿态 `sample-*.json`、失败草稿和重复截图可在报告落盘后清理；清理清单记录数量、大小与哈希摘要。保留的报告仍是历史检查证据，删除原始采样后须重跑才能复算。

## 参考

- [GPU Gems：实时水模拟](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)
- [Godot 屏幕读取与深度纹理](https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html)
- [像素水 shader 参考](https://github.com/taillight-games/godot-4-pixelated-water-shader)
- [Stylized water 分层方法](https://halisavakis.com/my-take-on-shaders-stylized-water-shader/)

124 使用自己的 shader 实现，未复制参考项目的 shader 资产。
