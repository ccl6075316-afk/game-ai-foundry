# 082k2 新画风源图尾根拓扑阻断

Normal mode。任务为用户授权的单真鲷源画风试验，非原082胸鳍架构第四轮。正式082h游戏资源不变。

证据：新source已完成Foundry generation/matte且由Agent接受作独立3D试验；models/red_seabream/082k2.handoff.json正式build被GLB门报Degenerate fish triangle；native closed_mesh=true不能替代该门。

- Attempt1 082k2：Caudal110点按alpha追踪，后端面根区投影后两片退化。两Solidify侧在同源UV(.19,.611)都落同一个3D点，第三点源UV(.19,.608663)。
- Attempt2 082k2a：假设零inset壳重合，仅设Caudal inset=.0001。原两片仍退化，只发生x平移，假设不成立。style reference同时纠正为实际鲨鱼anchor（原错误沿用了旧红鲷的style path）。未继续盲改。

当前Phase1/2/3独立review进行中：怀疑追踪器把靠根的自由轮廓冗余点与baseline端点围成了二维根三角，posterior投影将整片根面压到中位竖线；Solidify法线无法生成厚度。需检查原native/source_t与实际面，先验证因果再执行第三次候选。

只读输入实验：保留baseline/root_band=.065以及原厚度/动作/容差，分别去掉距baseline的t<=.066/.085/.10/.12的外边冗余点，候选108/107/106/103点，源tail alpha覆盖99.9575/99.8489/99.8943/99.8518%。该实验不是模型通过；目前未构建这些候选。

报告：output/fish-082k2/tail-junction-input-experiment.validation.json。禁止以模型保留检查、缩鳍/锁鳍、扩大根豁免或忽略退化替代当前阻断。第三次如果失败则停止并按anvil:debug做架构复核。

Phase1/2/3 independent reviewer APPROVED: original endpoint neighborhood all root (max_t .002973), projected area 2.906e-14. Removing only two redundant outer points yields max_t .116160, area1.671267e-6. Same Solidify negative/positive: zero area2→0, duplicate1→0, bad edges2→0, min area7.179278e-8; endpoint separation0→.00055. Proceed third official candidate082k2b; preserve all root definitions and inset0.

Phase4 APPROVED（尾拓扑限定scope）：正式082k2b build/validate/render通过；独立GLB复核960尾三角、min area7.1792789e-8、Euler2，零面积/重复/坏边/边界边/绕序冲突均0。原2退化面消除。其余geometry/skin/animation/source保持；口部26行UV有最大1.788e-7末位漂移（.000346源像素），如实记录不称全字节一致。报告projects/fishing-2d/plans/reviews/082k2b-tail-topology.validation.json。知识沉淀docs/anvil/knowledge/2026-10-19-tail-projection-degenerate-wedges.md。

整鱼独立验收边界：177姿态鳍根通过，身体16视角GPU覆盖通过，四动作240帧记录；490全部鳍根通过，但右胸鳍11姿态自由面穿入，worst −.04057598mm，超过冻结.02mm；其他鳍通过。本尾拓扑修复成功不等于整鱼接受。未执行volume accept，未替换082h正式资产；原胸鳍架构三次失败后的停止规则仍有效，本轮不再猜测修胸鳍。
