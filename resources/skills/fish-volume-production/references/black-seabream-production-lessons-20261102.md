# 黑鲷：近缘厚度参考与左右材质覆盖

适用：同种横宽资料不足、用户指定已满意样板；左右侧腹材质覆盖不一致；完整鳍根已通过而近根自由面仍穿体。当前黑鲷已获用户外观确认，正式状态只读游戏`experiments/black-seabream-lowpoly-sop-20261102/manifest.json`和`release-20261102`。接受绑定GLB `670071c6725f5fc3c99597c7129375f1eff3490c5464c06781b2607a16db6022`，不转授其他鱼。

## 可复用的决定与代码

1. **厚度参考先恢复成品。** 用户允许同种资料不足时参考体型相近的同属/同科鱼，指定样板优先。查实际已接受GLB与SHA，按尾基、肩/鳃盖、眼、嘴角、吻端逐项对应，以完整可见长度归一化后量实际有限截面；不要直接复制厘米值或把近缘比例叫同种实测。用`audit_transverse_width.section`量实际面，用既有`prepare_transverse_width_from_config.py → author_transverse_width_trial.py`冻结并写入横向场。普通未合并源也可按同一场变形，当前完整执行例见本鱼`thickness-symmetry-20261102/prepare_width.py`及`author_width.py`。本例额外包含确诊鳍余量，不能原样用于下一鱼。
2. **左右覆盖先排除光照。** 在实际有限体表取镜像点，投到对侧三角面，重心UV按nearest采嵌入RGBA；并看同光照左右/腹视。原背腹供体直接用有正负号的横坐标，会把两侧送到不同明暗和纹样区。`native_body_skin_transport.native_roof_coordinates`新增可选`transverse_mapping="bilateral_inward"`，图表构建器新增`bilateral_color_coordinates=true`。默认旧行为保留；只在本鱼要求对称覆盖且供体已审后启用，保留原侧眼/鳃/完整唇域和二维像素密度。本例456对取样平均RGB差19.64→1.60；三角图块最近像素相位不等于缺一整侧腹部。执行例`check_bilateral.py`和`bilateral-r3.validation.json`。
3. **切鳍按实际组织边界。** 深蓝、炭灰和浅边都要识别归属，不能只删纯黑。`portable/native_source_edge.py`在明确窄走廊内用组织对比度和连续路径追边，`prepare_native_fin_domains.py`按可选`native_edge_paths`只编辑alpha、断言RGB不变。PNG须合成到有色背景，避免把alpha0底层RGB误看成残留。默认不启用新追边器。
4. **根点通过不证明整面。** 当前失败是曲根之间自由面的长弦穿体。`author_annotated_fin_cages.py`支持有界`additional_source_seeds_px`，断言声明点实际进入源鳍域；按自己的完整根线补少量控制行，不改变自由轮廓、原RGB、根域或阈值。原有支持不足时只抬自由片可能反折；先验真实相对法线厚度，再验整鳍490。反复自适应加密不能替代定位，也不能突破整鱼预算。
5. **非线性场检查实际有限法线。** 连续雅可比法线在粗三角上可能反向；实际点积失败的角点改用该有限面法线，其余光滑法线保留。不得改winding或放宽077。本例身体3面触发，当前1904三角不变。收薄还可能引出动态微穿插，按一轮收齐、局部修正、冻结、完整检查执行，旧物理报告失效。
6. **接受后走正式入口。** 复用`FinalizedWidthBatch20261101.gd`的源成品加载/检查和独立动作参数；不新增黑鲷专属builder。退役前核清共享JSON中的本鱼行、专属导入/材质/动作路径、独占资源与Git恢复点。`capture_installed_source_owned.gd`核真实`VolumeFishExhibit._add_fish`首次/缓存数组、像素、PBR、LOD、动作与切换；override槽里同一嵌入材质可正确，不应误判为补丁。

## 本鱼参数与失败边界

35cm是游戏`reported_whole_fish`展示口径，TL/SL/FL未知。真鲷是用户指定的近缘造型参考；最大体宽/体长约.131895，35站有限截面近似误差最大约.609mm，非生物标准。1904三角、18骨、7完整鳍，只说明本鱼。

原8px根域及0.02mm自由面容差保持。源根线7测位和12/24px支持行、先前1.5mm自由余量、本轮追加胸鳍.65mm和臀鳍腹侧.06mm均是确诊后的本鱼参数，不设为默认。当前模型/配置变化后须重跑鳍根/全鳍面、身体/动作和冷读；490不证明连续时间。

## 恢复与复用入口

游戏`release-20261102/user-acceptance.json`绑定用户确认，`installation.validation.json`记录正式接入，`installed-review/installed-cold.validation.json`记录实际入口，`final-sop.validation.json`为完整逐鱼证据。独立实验历史通过不追认为用户接受。当前编辑源、模型与准确路径从该目录最终manifest恢复；来源/生成用途/限制在`production-facts.json`。清理先提炼失败最坏姿态、参数、实际源/模型SHA、当前视频和复现方法，再删缓存；清单与恢复点随交付保留。
