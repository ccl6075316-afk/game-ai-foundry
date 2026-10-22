---
type: production-knowledge
status: current_user_preferred_baseline
date: 2026-10-22
module: volume-fish-source-surface-runtime
---

# 原图材质、下唇贴合与稳定展示：当前基线

用户反馈：“目前看 现在已经是 最好的一版了”。当前安装版作为后续比较基线保留；这是一条当前效果偏好，不替用户补造逐鱼解剖或口内接受。用户已明确暂缓口内，后续只关注外部。116阶段只写知识/技能与诊断叠层，没有改模型、贴图、shader或动作配置。123收尾新增两条独立双髻鲨，原23鱼继续保留这一基线；119/122嘴型候选仍单独归档。

## 可以复用的方法

1. **先追踪实际加载链。** 新GLB/profile/PNG落盘不代表引擎已导入。旧缓存曾让黑鲷/梭鲈注册中断，缺ctex采样变白；相同Godot重新导入恢复，不应绕开数组/LOD哈希门。启动入口在真正运行前完成导入并检查日志ERROR，退出0不够。
2. **选鱼可见性与动画时钟分别管。** 只移相机仍会绘制其他透明缸。113的单变量A/B确认绘制成本后只隐藏非当前缸，全部控制器时钟继续，总览/共游恢复可见；不靠冻结其他鱼或删材质提速。
3. **静态材质场用真实静态属性。** 本轮Godot4.7.1 Compatibility的VERTEX/NORMAL已蒙皮；BodyChart的截面/法线场读取它们会滑转。114用当前导入surface的XYZ、normal、原UV独立RGBAF表，VERTEX_ID定位，检查数量、有效位、原UV及全部表字节。仍正常蒙皮渲染，异常显洋红而不裁身体。
4. **原图线、实体边界和UV分别核。** 先在未清洗PNG上标出下唇并由用户确认，再提取实际skin/oral公共边，验证原图支持区、实体投影和UV。端面内部另有供体重参数，115曾相差25–29源像素；不能直接照源图坐标裁模型。当前两鱼全段最大误差约0.42/0.31源像素，而原UV对真实口缘误差小于0.000066像素。
5. **截面运输用局部归一化。** 在保持同X实际外皮包络时，cut的Y/Z先转成当地截面比例，再运到目标截面。混绝对Y/Z曾使向前收缩的吻部鼓包；冻结的目标与限值不能跟着失败候选改动。检查发出的float32有限三角及相邻未改区相交，不只验数学场。
6. **保色mask要有完整边界。** 仅限制嘴的上方会把整个下巴恢复为原图黑轮廓。两鱼当前使用明确上/下/后方的有界保色，真实GPU测试分别验域内、上方、下方与后方非空覆盖及静态表故障；旧mouth projection显式false在material.duplicate丢inactive参数后也要严格保留。
7. **补隐藏纹理有可追踪的二维供体。** 原图二维安全像素块拼接，背腹分别约束，排除鳍、轮廓、眼嘴足迹；保存每个目标像素的原图XY。116重算当前四张背腹图的RGBA，与原PNG供体全相等。它是有来源的美术延续，不是生物实测隐藏背纹。

## 失败经验与边界

- 原口内UV所有三角形面积为0。原UV画布零漂移是空覆盖，不能证明稳定；换成静态XZ的上下腔非退化画布后才有有效诊断。19鱼BodyChart通过不自动涵盖FrontSkin或SourceJaw。
- 小阴影矩形按原生像素周期平铺虽然技术采样通过，却产生规则格栅，实际画面被拒绝，未安装。三次失败历史保留；当前不再改口内，也不让它阻塞外部审阅。
- 端面独立矩形供体可能有色块/边界感，属于外部观察，不能混同口内。用户当前认为整版最好，这一观察不等于必须继续改动的已确认缺陷。
- “背部拼接感”措辞过重。现能标出的主要是俯视左右镜像、局部弧形/菱形纹样节奏；没有清楚证明实际断缝。用户没有感受到问题，故撤出必须返修清单，提供带/不带框的实际截图供判断，不进行自动修补。

## 保留与检查范围

当前115下唇/端面UV与局部保色已安装；完整鳍每鱼490实际候选姿态，经正式导入数组、LOD与全部运行依赖相等桥接，不能说正式又跑了490。正式身体23鱼368视图无缺块，展厅1314检查通过；114另有456画布样本和304真实动作/距离/切换样本。都是离散验证；性能数据只覆盖本机M4预热窗口。

当前基线的23模型与169运行依赖哈希、用户反馈和截图标注读取Fish `experiments/blender-fish/external-display-116/preferred-baseline.validation.json`。历史115 blocked报告保留，不能偷偷改成全部外观通过。

## 可直接找到的实现与证据

- 技能入口：[fish-volume-production](../../../resources/skills/fish-volume-production/SKILL.md)，细节在其 `references/source-surface-repair.md`。
- 静态属性：[RestSurface114.gd](../../../resources/runtime/godot/surface-chart-112/RestSurface114.gd)、[LipMaterial115.gd](../../../resources/runtime/godot/surface-chart-112/LipMaterial115.gd)、[ValidateSurface112.gd](../../../resources/runtime/godot/surface-chart-112/ValidateSurface112.gd)。
- 实体拟合：[measure_lip_binding115.py](../../../resources/scripts/volume-fish/measure_lip_binding115.py)、[validate_source_fit115.py](../../../resources/scripts/volume-fish/validate_source_fit115.py)，按物种profile选网格，不统一假设都叫Closed_body。
- 标注：[annotate_surface_observations.py](../../../resources/scripts/volume-fish/annotate_surface_observations.py)只生成SVG/HTML，嵌入原PNG字节并独立叠加矢量框；输出不参与运行资产。
- 具体调试：[113缓存与可见性](2026-10-22-fish-review-cache-and-visibility.md)、[114静态材质坐标](2026-10-22-fish-rest-material-coordinates.md)、[115失败及保留成果](2026-10-22-fish-source-lip-fit-and-cavity-stop.md)。
