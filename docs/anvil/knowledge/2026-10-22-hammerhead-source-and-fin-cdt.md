# 两种双髻鲨：源图、独立物种参数和鳍基CDT

121新增 Great `Sphyrna mokarran` 与 Smooth `Sphyrna zygaena`，保留原路氏 `S. lewini`。原120只诊断路氏源图/模型比例，不能称新鱼已做完。三者不是换名、统一增高或复制一个头型。

## 物种约束与来源

- Great：较壮躯干、很高且镰形的第一背鳍；成年锤头前缘接近平直，但有中央浅凹口。FAO2013物种目录图317/印刷273页给头宽23–27%TL。本轮26%TL目标在该范围内，模型最终按完整native X长度再核，不能拿生成图透视像素冒充标本实测。
- Smooth：宽而圆凸的连续前缘，无中央凹口；第一背鳍较适中、尖端更圆，第二背鳍低且有长游离后尖。27.5%TL是制作选择，不冒称找到同种精确均值；CITES鉴别材料只支持小于全长三分之一的区分。
- 显示长度400/300cm是游戏代表尺寸；隐藏横宽、头厚和未见鳍面仍是制作推断。路氏2023标本的31%尾鳍背缘长不能跨种套为这两鱼比例，也不能和bbox对角混量。

来源：[Florida Museum Great](https://www.floridamuseum.ufl.edu/discover-fish/species-profiles/great-hammerhead/)、[Smooth](https://www.floridamuseum.ufl.edu/discover-fish/species-profiles/smooth-hammerhead/)、[FAO2013](https://www.fao.org/4/i3178e/i3178e.pdf)、[CITES鉴别材料](https://cites.org/sites/default/files/shark-ndf/ID_%20hammerhead%20sharks_2023.pdf)。资料只作形态约束，没有下载作游戏贴图。

## 生图与状态的实际边界

用户明确授权把现有锤头风格参考、两种提示词及后续派生参考送到当前Foundry配置的apilio/gpt-image-2。首次自动审核拒绝后取得的是这次明确数据/目的地授权，不能写成以后任意外发的通用许可。

独立projects下冻结Brief，依次context/validate/init/run/status。把新Brief放进已有fishing项目深层会被解析到父production，须修输入路径，不能绕开错误继续。view枚举为bottom_up。短超时宿主detach子进程被中止后，读取同一失败manifest再resume；不再开一轮run。

编辑源图不能把将被resume清理的自身raw路径当reference-image；先留不可变引用。换引用路径时重生成pipeline计划，单改Brief不保证旧命令已变。Great一次修改把中央凹口画成外凸喙，Smooth第一侧图是双眼斜视，都经实际视觉否决重做；提示词写了并不等于图已符合。

派生底图错误画成上下投影均V形尾，Great俯视有非正交背鳍轮廓。本轮仅接受这些图的明确局部皮肤供体，不接受其全图解剖；实际尾和鳍几何来自正确侧图、头横向来自物种约束。接受记录必须写区域和排除项，不能冒称所有三视都正确。

## 两类实际鳍失败，分别修

第一/二轮正式构建保留准确profile、验证失败与独立复现：

1. source alpha半平面裁剪可能产生多个部分，却被一个顶点链以共线基线反复桥接，成为弱简单多边形。CDT边界顶点degree4、face fan不连通，Solidify后出现四面共边。不是闭合门误报。修输入为经过真实源tip的单一连续自由弧，再以完整作者A/B和有限隐藏collar闭合；不得直接删掉基线尾段过门。内部鳍基到alpha边的距离不是生物误差；首次任意8px预警被新证据否决，改记实际stitch并看原图，而非放宽物理门。
2. 原builder把基线细分点当长边附近的无约束自由点，f32插值形成近共线微楔；原Smooth D1三点t仅约1e-8，投影和挤厚后重复顶点。边界确实与baseline吻合时，把细分点插入唯一边界链及face loop，删除原长边约束；内部基线仍按原语义。不要只加深度救这种舍入小楔。
3. 修过输入后，两鱼D2另有真实二维根带面近乎压成曲线（相邻t约.0175/.0211），不是同一个D1微楔。只给两D2显式有限root_band_depth，保留原完整.025选区；其余鳍无此字段。缺省inset返回旧值。法向内缩会含X分量，不能说X逐值保持或全域严格满秩。

载入原生blend回放投影前必须显式REST：Object.ray_cast会受到已保存Swim姿态影响，实测命中差约.29/.37mm。默认与有限深度负/正例先在实际REST身体上验证闭合、无round7重复顶点，再整建。二维CDT通过不等于投影/挤厚/导出通过。

实际第三次GLB通过官方检查。按原生全长和显示scale，计入半厚度的D2最深预算Great .424145mm、Smooth .422017mm，均低于原0.5mm根缝；这只作工程上界，不能替代177完整鳍根、490全鳍面或GPU身体和视觉门。物理限制0.5mm/0.02mm、完整选择没有放宽。

## 复用入口与状态

通用构建器 `build_fish.py/fin_source_geometry`、`cli/volume_shape.py`；源平面预检 `preflight_fin_polygons.py`。物种数据为 `resources/volume-fish/{great,smooth}-hammerhead-121.profile.json`，动作数据另存同目录motion-121。`author_hammer_pair121.py`的坐标只适用这两幅源图，不是跨鱼参数模板。

Fish `experiments/blender-fish/hammer-pair-121/`保留源图与工作流、失败快照、独立诊断及最终状态；以其completion validation和模型接受记录为准。该知识不是最终交付收据，不将未跑的鳍/身体/引擎门写成通过。

## 完整鳍面揭示的第三类失败

Great第三版所有根带采样点通过，但高body gain下左右胸鳍约15mm长三角边跨过凸身体，边内点穿入.520/.606mm，超过原.5mm根缝；最近鳍顶点仍相距约3.8mm。端点预算和只加密检查样本不能修实际长弦。第四版仅将该鱼成对Pectoral的实体baseline_spacing设为.0005 native（约2.02mm），重新CDT/投影/导出；完整.025根带、骨骼、动作、鳍厚与所有物理阈值保持。490全鳍复验通过，后续正式25鱼门另见交付收据。

这个字段控制真实网格边界细分，不是检查器插值密度。默认路径保留旧.004/.001语义，不给另一条已通过的Smooth或全部旧鱼套同一密度；旧模型未重建，不能声称所有旧profile重建字节相同。
