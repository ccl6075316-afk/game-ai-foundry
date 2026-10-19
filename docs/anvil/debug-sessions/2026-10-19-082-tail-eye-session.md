# 082 用户反馈：大黄鱼尾鳍、真鲷眼睛

- 当前阶段：Phase1，只读定位与验收纠正；尚未实施视觉修复。不是胸鳍第四轮修复。
- 证据：用户指出尾鳍/眼睛；实际GPU截图、正式profile/native、旧游戏源图与本次接受源图。Normal mode（实际引擎验证记录可用）。
- 大黄鱼：旧参考叉形→r2源图尖菱形发生在生成阶段；当前Caudal polygon另有裁掉下叶/肩部，不得把mesh称为忠实复现。独立复算u<.10自由尾区24917不透明源像素中3047落在polygon外，12.23%。此前目视接受应撤回，历史报告留档。尾形设计优先级已请求用户澄清；不擅自将两种混用。
- 真鲷：实际正面出现跨额头眼圈条带、俯视眼圈展开。eyes=null，无head_projection/body_uv_patches。普通侧面UV随身体整个截面投影，眼纹不能由独立左右眼局部表示；当前待独立UV复核。不归因不存在的眼球网格。
- 最小失败证据：tail/eye-comparison.png 与只读原图polygon覆盖；相同采样/相机的front/top重现条带。未修改动作、碰撞门、身体几何或模型。
- 独立reviewer：fin_clearance_review，Phase1最终审核待。

## Phase1独立审核 APPROVED

尾鳍与眼部根因均有原生几何/实际GPU/源UV证据，详见feature-recheck.validation.json。已通过正式volume render重开大黄鱼视觉审核，旧accepted快照保留；当前8接受3待修。

## Phase2/最小实验设计审核

只读实验设计APPROVED，不等于允许生产构建或候选通过。拟比较局部眼片+原眼皮肤去重，须检查整个三角UV域（不能仅点采样）、体表BVH边缘浮离/截半与同坐标侧视眼心/外圈；front/top不可再有眼纹条带。同类未接受profile不可当成功范例。未修改身体/鳍/动作/检查界限。尾型待用户回答后才能做依赖的修正。

## 082h Phase1修订、Phase2/3与首次候选

进一步发现主根因：真鲷u=.85～.93头顶比实际source alpha向内缩49～69像素，底部25～30像素。旧错误包络使canonical UV在头顶直接采到眼圈；不能仅归咎投影方式。独立shadow同坐标IoU .8394→.9895，近似眼域12→0，Phase1修订APPROVED。

暂停独立眼片：只读薄椭球试算边缘最大离体3.055mm，不以局部锚定证明贴体。

Yellow Phase2/3 APPROVED：沿r2源尾真实alpha边界补外轮廓，保留baseline；阈值128覆盖(u<.1)88.10%→100%，肩部(.1～.14)65.93%→100%，99点，约1像素外余量；source_t归一化分母.137→.13851，必须重冻和490。统计阈值不同于前次243，不替换历史结果。

Red首提案在嘴端取最长opaque run导致口线落体外，独立review REJECTED（生产前输入拒绝，不记模型修复strike）。修为u=.76～.80渐入source包络，.80～.94匹配source，.94～.97回原嘴端包络，>=.97原rows完全保留。原口部校验PASS。独立Phase2/3 APPROVED；原宽度、嘴参数、rig、鱼鳍与动作不变，不增加眼片/去眼皮肤。

两鱼正式CLI plan/build/validate/render均已通过，仍pending视觉。082h同源画布REST head ROI IoU旧.82519→新.99226。近似矩形眼域仍1点，但采样RGB[153,56,51]为红皮，不是眼纹；此矩形诊断不可直接当眼纹像素判据，保留该原始数值，不事后挪阈值。需独立审核真实源眼mask/实际front/top。身体/全鳍/游戏动态复验尚未完成。

## Phase4 最终验证 — APPROVED（仅本视觉修复范围）

- 两鱼正式CLI构建、验证、多视与实际Godot四动作20秒/鱼已完成；23鱼身体/动作/材质门通过。
- Yellow实际490根/全鳍面通过，082h已执行volume accept。Source polygon free/肩部100%；同坐标实际render free99.9026%（24像素边），肩部97.378%（539像素残差），目标相机无可见平切/断裂，独立终审同意接受。未把残差隐藏或改成完全一致。
- Red同坐标headROI IoU .82519→.99226，眼圈金色中心误差.102px；实际front/top/双侧复核眼圈不再跨额头。原rectangle heuristic false1保留，源定位为红皮[153,56,51]；另写独立视觉复核说明误报，未改原门槛。
- Red重建导致median细小坐标变化，未谎称逐值保留；其余鳍参数未改，完整490所有median/尾/腹鳍通过，原胸鳍7/10样本失败及.02836/.041642mm原样保留，不accept整鱼。两处用户指出的视觉问题独立关闭，不继续胸鳍第四轮修复。
- 主报告更新9接受/2待修；原12模型SHA一致；本轮没有维护中的通用代码变更。新源profile位于resources/volume-fish/*-082h.profile.json。
