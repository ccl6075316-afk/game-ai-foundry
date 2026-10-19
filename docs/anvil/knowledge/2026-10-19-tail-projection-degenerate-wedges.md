---
type: debug-knowledge
status: SUCCESS
bug_topic: Caudal root projection collapses dense outline wedges
date: 2026-10-19
---

# 尾根投影后退化：先检查面邻域，再检查壳厚

## 根因

082k2真鲷新源图的尾鳍alpha轮廓在完整baseline两端附近保留了两枚冗余点。CDT把下端点组成一个全部处于root_band=.065以内的三角邻域（max source_t=.002973）。posterior attachment投影将它压向同一根线，面面积仅2.906e-14；Solidify无有效法线，端点两个壳顶点完全重合，导出后两三角退化。native closed_mesh=true未阻断；正式CLI GLB焊接拓扑门正确拒绝。

## 修复与反例

082k2a只改inset0→.0001，退化原样出现；平移根线不能恢复面法线。082k2b恢复inset0，只删除两枚近根外缘冗余点，baseline端点、root_band、blend_end、厚度及容差不变；归一化最大源距也未变。只读同算法对照先复现负例，再证明最小修订：零面积2→0、重复坐标1→0、坏边2→0、最小实体面积7.179e-8、端点壳分离0→.00055。源tail alpha保留99.9575%，43像素局部根轮廓差异有记录。

第三候选正式volume build及validate通过。独立实际GLB复核尾鳍960三角、Euler=2、边界/坏边/绕序冲突/零面积/重复位置均0。该结论只对尾拓扑，不等于整鱼视觉、鳍基或鳍面通过。

## 识别与预防

原始2D轮廓不退化不证明投影后的3D面合法。出现degenerate triangle时对照其源UV、foundry_fin_source_t、投影前后面积和Solidify壳间距。源alpha的每个像素阶梯不必作为几何关键点；简化必须保留真实自由边、完整baseline并量化轮廓偏差。不要扩大根豁免、修改容差、删失败面或把零面积面当闭合通过。不同鱼须独立查明，不能通用删点或把.066筛点实验当新的root_band。

## 位置与证据

- resources/scripts/volume-fish/build_fish.py：CDT、root projection、mesh/Solidify。
- cli/volume_fish.py：GLB welded triangle/edge gate。
- resources/volume-fish/red_seabream-082k2b.profile.json：本物种最小输入修订。
- output/fish-082k2/build-b.json、validate-b.json：正式CLI结果。
- projects/fishing-2d/plans/reviews/082k2b-tail-topology.validation.json：独立GLB复核。
- docs/anvil/debug-sessions/2026-10-19-082k2-tail-junction-session.md：完整过程。
