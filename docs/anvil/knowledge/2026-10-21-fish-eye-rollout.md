---
type: debug-knowledge
status: verified-local-eye-trial
bug_topic: 梭鲈旧眼清理与独立眼层推广
date: 2026-10-21
---

# 107：推广眼睛方法前先辨认不同来源

## 已证实的根因

23个对象筛查包括21条当前游戏鱼的210张新GPU图，以及真鲷/黑鲷已有实证。新增明确试修对象只有梭鲈；没有把全部头顶拖纹重列成眼睛问题。鲤鱼鼻部黑金小圈、鲑鳟天然斑点和俯视可见的正常侧眼应保护；真鲷深梯条已有描边来源证据；银龙独立眼几何需不同方法，带鱼需专用镜头。

梭鲈GPU白圈争议像素反查到原眼上白圈，旧keep=1所以未清；中央暗区另来自旧补色供体。普通吻白控制点来源在眼外且保持。源图文件编码哈希与解码像素哈希不能混为一谈；实际082接受PNG与当前GLB源完全相同，Godot导入baseRGBA快照则单独严格核验。

## 可复用的方法

1. 每鱼先看当前侧/反侧/顶/前/斜视与无光照，记录源、配置和材质真实参数；不能只信旧截图或按暗色分类。
2. 原眼纹清理域、独立眼层域、旧runtime cleanup产生的染色足迹是三个概念。前二者可在源图圈定，第三者须从实际shader执行路径单独取证。退役旧分支后，也可能恢复源mask外正常皮肤。
3. 拆眼层只退役原眼项，不统一关闭承担嘴/rim/其他特征的head helper；匹配必须唯一，未知装配拒绝。关闭模式仍执行原路径并对独立原版逐RGBA证明身份。
4. 由本鱼完整pupil/gold实测双轴像素尺度。外围原映射有缺失时如实报告，不把可映射子集说成完整原圈。紧眼层与清理mask分别人工审；新增rim超旧mask时显式合并并重冻。
5. 原source与opaque fallback分别生成原生邻近供体RGB副本，所有alpha与域外RGBA保留。fallback nearest来源必须实际复现后才决定能否用同mask。
6. 新眼层在rest空间定位，原RGB/alpha/mask/侧别权重混入原光照颜色，保持nearest、tint和COLOR。用全路三基色以及退役旧分支独立三基色探针限定影响，再检查候选域外变化；不以after差异定义允许区。
7. 保留全部LOD并逐档检查。黑鲷106批准退休坏LOD的例外不能跨鱼复制。梭鲈最粗档失败仍原样保留，局部视觉可保留不等于允许正式安装。
8. 身体检查识别动态shader须绑定真实安装codeSHA、helper/template/config/model、实际纹理RGBA及不透明合同，不能伪造资源路径或放行未知shader。共享检查器改变后回归已有支持鱼。

## 本次参数和完成边界

梭鲈6039眼层、7127旧清理、[1780,335,1808,360)灰金供体、像素XY=1/2024、11像素下移及原gap只适用于本轮冻结输入。全六档LOD保留；base至LOD4离散域校准通过，LOD5仍失败并有真实粗压力负例。

最终47标准和48额外mode0逐RGBA身份、三基色允许域外/alpha零差、24真实切换、177鳍根、490全鳍根/膜面和16身体覆盖通过。独立视觉/代码审查批准局部眼睛试版；吻端白环与一般皮肤拖纹未解决，整鱼未接受，未替换正式game。导出包未验证。

实现位于Foundry `resources/runtime/godot/eye-ownership-107/`，物种profile与冻结CLI分别在`resources/volume-fish/eye-zander-107.json`和`resources/scripts/volume-fish/freeze_eye_features_107.py`。阶段证据在Fish `experiments/blender-fish/eye-rollout-107/`，失败域不能因最终局部颜色可看而改为通过。
