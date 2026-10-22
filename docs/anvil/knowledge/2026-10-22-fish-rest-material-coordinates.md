---
type: debug-knowledge
status: SUCCESS
bug_topic: Body chart texture swims with GPU skinned coordinates
date: 2026-10-22
---

# 骨骼动画上的静态材质采样

成功范围是19条鱼BodyChart背腹贴图滑转；原图下唇候选已标注，嘴型、黑环与材质美术仍未完成或接受。

## 根因

Godot Compatibility在用户vertex之前完成GPU蒙皮。把VERTEX/NORMAL赋给命名为rest的varying并不能取得未变形属性，静态截面和法线掩码会随身体摆动移动，供体贴图看起来在鱼上滑转。世界/模型整体变换与骨骼变形的坐标空间须分别核对。

## 方法

`resources/runtime/godot/surface-chart-112/RestSurface114.gd`从实际导入ArrayMesh逐surface建立XYZ、normal、原UV的RGBAF最近邻表，无mipmap/sRGB。VERTEX_ID定位加数量、有效位与原UV门，异常显示洋红而不改变alpha。逐surface独立材质避免共享表覆盖。采样恢复静态属性，真正渲染仍使用原蒙皮几何。

`ValidateSurface112`精确重建授权wrapper，逐字节核对实际LUT，冻结helper/template、模型、全surface arrays和LOD摘要；不能只看收据里一个ok。

第一次完整身体门抓到材质duplicate丢弃inactive参数：SourceJaw先设置的false在眼域wrapper中没有uniform声明，duplicate后变null。复制前核对原实际false、复制后恢复false，原口部门保持严格；不要凭receipt静默覆盖上游异常。

## 可证伪验证

固定UV画布仅用于隔离坐标：生产vertex不变，独立oracle取原导入数组；冻结三角集合和cull bounds，使用非均匀供体与最小有效像素门。最终456样本零漂移；只把两条赋值恢复成旧VERTEX/NORMAL即可重现167481变化。固定画布不能替代运行LOD，因此另跑实际几何四动作、三个距离与真实切换；304样本零查表故障。

探针必须证明命中。FrontSkin111彩色像素、SourceJaw0，早期零变化是无效覆盖。最终明确insufficient_probe_coverage，不能叫不漂移；退化UV需要独立3D对应点方法。这两个分支本轮未改。

实际生产最终body23鱼368组无缺块、fin19×177全鳍基、展厅1314回归通过。M4预热帧量级保持113修复后水平，不能保证所有机器或连续时间。

## 复用边界

固定属性方法跨物种可复用，但各鱼仍核对实际surface、UV、数量和模型身份。不能假定都叫Closed_body：piranha、silver_arowana使用profile指定网格名。诊断代码自身的空引用、空命中和LOD剔除必须独立识别。

标线必须显示用户要求的原始供体，不能拿已清洗素材判断被洗掉的嘴部。原PNG以hash冻结，不修改源图；标线是识别候选，不是用户接受或已完成裁改。

证据在Fish `experiments/blender-fish/material-anchor-114/`，状态入口review.validation.json。独立debug_review四阶段批准BodyChart修复，原图/模型/供体/动作控制器未变。

以上是114当时范围；115已按用户确认的原图下唇实际修订两鱼几何与局部保色，当前用户评价为最好版本、口内暂缓。最新适用边界及沉淀入口见[当前原图表面基线](2026-10-22-fish-source-surface-baseline.md)，不以本历史段落的“下唇仍未裁改”覆盖后续成果。
