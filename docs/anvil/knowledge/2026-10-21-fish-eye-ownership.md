---
type: debug-knowledge
status: verified-local-eye-trial
bug_topic: 黑鲷侧图眼纹跨头顶连接
date: 2026-10-21
---

# 106：把鱼眼作为独立特征投影

## 根因

侧图的眼纹被整个头部皮肤取样复用，侧面看似正确，头顶却把左右眼圈连接起来。旧103只擦中间窄带；旧源眼椭圆还漏了下方眼圈。原画眼位是否在生物意义上错误没有证据，本轮不改原画。

仅扩大3D椭球也不成立：实际蒙皮画面的射线追踪证明，可见上金圈已经进入原定中央禁眼带。保留全部旧投影与清空中央眼纹存在冲突。必须分开皮肤取样与眼睛本体，不能用逐档猜radius代替定位。

另发现实际Godot最粗LOD5（402三角）丢失上半头和瞳孔区域。基础网格、原图哈希和近景正确均不能证明运行时LOD正确。该坏表示被明确退休，不能记成通过。

## 当前试修方法

1. 冻结完整源眼圈与旧眼纹清理区，两个mask分别定义。旧清理区修订为12752源像素；独立眼层9819像素，包含金圈、瞳孔、白反光和外黑圈，排除右侧天然黑点。颜色连通/凸包只是本次人工选区的辅助，不是通用鱼眼分类规则。
2. 追踪不透明皮肤供体的nearest来源。本鱼旧眼区没有被延展到透明背景，source/fallback可以共用清理域；其他鱼必须重新检查。
3. 从实际导入顶点顺序冻结rest XYZ查表，vertex按VERTEX_ID取值，fragment在原静态空间投影。独立眼层使用rest XY，身体UV、骨骼和动画保留。GPU参考UV不匹配或越界须明确失败，不能把空命中当通过。
4. 根据当前源瞳孔与实际表面反求锚点，检查左右、像素单元边界与全部可用LOD。当前物理像素尺寸为`.9/1986`原生单位，向下22个物理像素；这是本鱼工程参数，不是物种实测，也不是跨鱼种默认值。瞳孔尺寸约为旧版100%，外黑圈约小6–7%，不得宣称眼睛大小完全未变。
5. 旧眼域只补邻近原生皮肤RGB，原alpha保持；新眼层从未改动的source取原RGB，按source alpha × eye mask × owner混入原ALBEDO，保留原色彩转换、tint/COLOR与光照。身体不写ALPHA或discard。
6. 只移除Closed_body surface0中已证实坏掉的LOD5。原GLB、全部surface数组、base和LOD0–4索引、其他surface/鱼鳍LOD、Skin和骨骼绑定保留。退休是运行时表示集合的修复，不是跳过坏LOD后声称原模型全部通过。

## 必须保留的验证

- mode0对独立原始场景逐RGBA比较。近远/LOD压力另与“只修LOD、没有眼层”的参考比较，不能将LOD造成的几何变化混成改色结果。
- 用独立RGB三基色探针先冻结实际影响区并集，再验证候选域外零变化；不能用after差异反推允许域。
- 检查完整两侧眼圈、正/俯/斜视、静态与四动作及真实切换。当前控制器`restart=true`会seek并归steady；测试切换须使用`set_action(target,false)`，核实真实transition状态。
- 近景、旧粗LOD负例和修复后的粗压力图一起保留。三角数量或字典少一个LOD不能代替实际画面。
- 动态生成shader没有固定resource_path，身体覆盖检查应以安装时绑定的generated-code SHA、helper/template/config/model及实际不透明shader合同验身份，禁止伪造旧路径或对任意未知shader放行。

## 本次范围和局限

最终独立Phase4代码门和局部视觉审核均通过，允许保留展示106眼睛试修。最终冻结后47图身份/域外像素保留、48图LOD-only参考身份、85图有效归属诊断、24图真实切换通过；原身体门重新运行16视图无缺块。该状态限定本地眼睛试验，不能传播为整鱼接受。

仅黑鲷独立试版，未替换正式游戏、未调用volume accept。最终验收状态见Fish仓库`experiments/blender-fish/eye-separation-106/`的当前报告。新眼形与皮肤补色仍属制作判断；其他鱼的眼数、侧别、特征分布和LOD须独立确定，不把本鱼左右投影参数套到所有鱼。

原模型全鳍面门仍失败：490姿态中左胸鳍35姿态轻微穿体，最深约0.024176mm，超过原冻结0.02mm界限。177姿态完整鳍根门通过不代表全鳍面通过。保留失败，不为像素风事后放宽容差，也不把眼睛试修写成整鱼接受。

## 相关实现

- `resources/runtime/godot/eye-ownership-106/`：实际眼层、LOD退休、诊断与合同检查。
- `resources/scripts/volume-fish/freeze_eye_features.py`：源RGB副本、原生mirror取样与严格保留证据。
- `resources/volume-fish/eye-black-seabream-106.json`：本鱼参数；当前有效参数在projection/repair，centers/radii/fade_q属于早期失败诊断的历史数据。
- `docs/anvil/debug-sessions/2026-10-21-106-eye-ownership-session.md`：被否定的假设、射线证据与分阶段独立审核。
