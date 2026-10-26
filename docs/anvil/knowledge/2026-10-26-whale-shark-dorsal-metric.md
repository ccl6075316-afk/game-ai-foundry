---
type: debug-knowledge
status: SUCCESS-scoped-metric
bug_topic: transported fish reference coordinates reused as physical surface distance
date: 2026-10-26
---

# 鲸鲨形体运输后的背纹距离表

## 根因

159使用158身体资源。形体调整保留了旧材质reference坐标，以维持嘴眼鳃等特征归属；153背纹弧长LUT也随之保留，却仍被当成当前实际体表距离。155个64点环可恢复，后背当前/旧横向比例0.823–1.302。独立实际三角面截交1643点表明旧距离最大误差22.53%。

## 单一修正与验证

`remeasure_transported_arc.py`以当前实际环YZ累计距离，保留reference theta索引；采用GPU纹素中心采样，不改原图、shader算法和特征域。`bind_surface_distance_metric.gd`只换skin153_arc，并逐项验证其它纹理字节、uniform、几何/UV/权重/LOD不变。当前独立距离误差最大0.21622%通过原1%限值，原负例失败，143个现有volume单测通过。四阶段独立对抗审查通过，仅针对这项数值修复。

## 识别与预防

reference是图案归属坐标，不必等于当前几何位置；物理距离场不能仅因reference未变而复用。形体改变后检查依赖，保留两套概念。新距离可能改变点列相位，仍须看中心线、肩部混合区和实际斜视。正确弧长不保证二维展开无剪切，不证明美术已认可。

工具适用于可恢复、单值角度排序的规则横截环；不是分叉/非星形/纵向整体改形的通用解。六位小数去重具有native单位精度约束，换物种/尺度必须重验。active_max_x之外的LUT节点仍可能通过插值影响边界：本鱼有效区到.30，X改形从.3128开始，留有间隔。距离测试使用实际三角截交和分段角度插值，不是连续曲面解析证明。

## 美术与交付边界

另存艺术渐缩候选：原154完整像素场/白中线/齐列保留，尾/肩缩点，整张1152px图沿纵向重复，不是小块拼贴。它不属于单变量度量修复批准，也不是用户接受。对照和实际输入在 `work/whale-shark-spots/review.validation.json`、`review.html`；参数在 `resources/volume-fish/whale-shark-dorsal-20261026.json`。

主游戏绑定未替换。159当前完整鳍根/全鳍面、身体GPU、动作与最终SOP仍待完成；本轮只交局部材质审阅候选。不要把数值通过或原RGB保留当整鱼验收。

后续结论：用户拒绝该平铺渐缩候选，认可范围转为原生背图映射的背部；物理度量修复仍是独立成立的技术结果。侧图/视频辅助模型与本轮提交收尾见 `2026-10-26-whale-shark-video-model.md`，不能把本条状态读成当前整鱼外观接受。
