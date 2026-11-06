# 当前尾鳍返修的保留合同

仅用于 `task_type=repair`、`affected_anatomical_parts=["Caudal"]`。逐鱼 `*-contract.json` 绑定当前正式源/GLB、开工已接受资产快照和独立材质分区快照。旧资产SHA须在实际用户接受入口中存在；快照在正式替换前读取，补充材质绑定从Git HEAD/LFS旧GLB读取并先核相同SHA。快照不是从候选反填的旧记录。

`cli/volume_repair_preservation.py` 从当前GLB全部真实分区求出保护域，不接受操作者自报省略。非尾定向三角的POSITION、NORMAL、UV、有效命名蒙皮、实际材质绑定与材质/采样语义、原生clip、骨架及节点变换须相符。未审额外绘制流/morph被拒绝。`head/mouth/eyes/skin` 才能使用 `accepted_exact_preserved`；其余阶段仍引用当前真实门和图审。新建/重建不可继承。

大黄鱼/梭鲈仅允许已明确授权、独立从未变源权重逐点预测出的Blender5序列化结果，不使用一般权重容差。记录精确原/现源与GLB SHA、全部非尾源组签名及每分区预测定向签名。罗非鱼1ULP UV改变曾导致6角nearest颜色改变，故被拒绝并恢复非尾精确UV流；没有UV容差例外。

大黄鱼/罗非鱼两个明确尾组织tile使用逐鱼锁定的mask、尺寸、结果RGBA SHA。mask外原像素与全部实际非尾nearest三角取样域须保持；禁止全图alpha填充。共享纹理的未支持UV包裹/边界在合同中失败，不能悄悄忽略。

`caudal_repair_current_volume` 包装器只组合真实受影响尾部的四法线对向射线、渐薄、有限尾截面和独立源→实际GLB双向位置证据，以及同一当前模型的完整鳍490根/膜和派生072。实际模型全部鳍库存与490逐姿态库存强验，原物理阈值不变。真鲷/食人鱼/鲤鱼原组合报告额外绝对.5mm接触项仍为false；包装器不把它改成通过，完整接触使用当前原1mm外隙/6mm埋入门。

正式逐鱼SOP及原字节数值报告在独立游戏仓库 `plans/reviews/tail-repair-20261106/<species>`；内部历史实验路径仅供溯源，不是现行可运行依赖。原画、现行源/GLB、当前完整根域及本目录合同是保留输入。不恢复退休作者链或旧媒体。
