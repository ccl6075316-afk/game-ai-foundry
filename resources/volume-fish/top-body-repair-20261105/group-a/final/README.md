# 2026-11-05 Group A 体宽返修正式参数

维护从游戏仓库 `assets/source/fish/<species>/fish.blend` 与 `game/assets/models/fish/<species>.glb` 冷读，不恢复实验链。各鱼 `source-domain.json` 保存完整 final packed SOURCE_VERTEX → 原解剖 source t/UV、正反皮面与完整侧壁/根域对应；不以变形后法向或色条UV筛选皮面，不以接触结果扩大/缩小根。模型或源变化使本次结果失效，按影响复验。

真鲷用本地 GiltheadBream、黑鲷用 YellowfinSeabream、食人鱼用 RedeyePiranha 的去独立鳍/眼齿身体作艺术横宽参照。它们不是目标种生物实测；近缘/精确种身份限制及文件SHA在逐鱼numeric-evidence。统一吻端到尾柄工程体长，先Wmax/峰位再全身体宽曲线与正俯斜图。保有依据的肩宽；已拒将整段肩峰桥低来追自拟2%目标。499站(.002,.998)不能冒充含端点完整边界；最终没有声称raw全边界2%全通过。

身体少量完整截环支持点来自本鱼原三角重心插值，不迁移参考网格/纹理。真鲷1652、黑鲷1952、食人鱼1988三角面。原完整口腔、上下颌、原生UV像素和真实上下唇共享边逐点独立核对原接受snapshot；肩后拓扑改变使用严格packed_anterior合同，不能伪称全身体indices完全未变。食人鱼仅已审前下巴端盖在原maxX以内局部钝圆，未增加前突/鸟嘴。

支持方法必须读最终有限body，保真正两层和物理closing aliases。LBS(单点,bary混权)不等于posed三角顶点的bary；完整490实际根先于整膜。邻UV节点必须保原边界纵向顺序，不能只挪当前最深sample；食人鱼以all490真实有限probe解短自由过渡，并恢复Dorsal不必要受运输影响的原自由几何，完整roots保持。黑鲷根支持原基线缺陷单列，必要局部miter保中面和skin，欧氏层厚可能改变，不能假称全层距/根coords不变。

专项使用原normal-ray/taper/严格static根接触/尾截面核与真实constant-free负控，并复用Float64 finite-edge self诊断。normal-ray0不代表closing self0。黑最终全self0；真鲷原接受基线本有basal skin/cap自交，本轮按用户仅体宽范围保R10：原pairs左胸21/右胸26/左腹12/右腹15，现13/25/14/15；新增pair均与原坏面共享同一basal patch，没有远端新增区域。胸交点距body外约.106–.368mm、腹内约.159mm，处于原root/collar邻域；normal-volume、完整根、体碰门全部独立通过。此限制保留，不称整鱼self0，也不据此放宽任何专项阈值。

临时图像/视频、dense490网格、negative blends和候选副本不提交。完整实际数值按compact逐鱼JSON保留；原报告SHA只作溯源，退休路径不冒称可重放/再次验过。最终SOP及canonical display/Fishing/hook冷接入由root正式交付入口统一记录。

077开放眼维护保留 `../native_eye_cap_guard.py`、`../validate_native_eye_caps.py` 的严格方法；它们调用原portable闭body/opaque/GPU核，只扩真实开放cap覆盖层，不冒称rigid或closed lens。`piranha/native-cap-support.json` 是当前实际有限body三角/bary/normal offset/有效命名权重数据，不冒充passed077报告。下次从新接受canonical冻结新baseline，旧原模型路径已退休。`../export_fin_with_native_caps.gd` 保存同姿态实际cap/body数组导出方法；实际有限身体的最近距离/边界距离按每帧当前body三角计算，旧490测量不会自动升级为新改动通过。源partition→原normal-volume核的方法是以当前packed源的真实SOURCE_VERTEX/PART_ID/FACE_PART保部件身份，生成一次性ordinary投影并与当前GLB双向核对，再用原normal-ray/taper/接触/尾截面核及真实constant-free负控。历史revision作者/探针入口不保留为生产脚本；下轮按当前source-domain与canonical重新冻结输入。
