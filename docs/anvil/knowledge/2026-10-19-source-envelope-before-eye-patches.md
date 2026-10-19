---
type: debug-knowledge
status: SUCCESS
bug_topic: fish source tail clipping and forehead eye texture
date: 2026-10-19
---

# 先核对源图包络，再修眼睛投影

## 根因

082黄鱼profile尾polygon漏掉真实源图下叶和肩部；先前工程门与目视接受未检查source局部覆盖。真鲷头顶比source内缩49～69像素，canonical侧UV因此在头顶采到眼纹。单看侧图眼心或把原因统称全周投影会漏掉输入包络错误。

## 修订与有效性

黄鱼仅沿当前r2源自由边补polygon，保持原baseline/动作/厚度；source_t归一化随polygon变化，故重新freeze与490，不宣称权重完全不变。真鲷仅改无鳍头段包络，渐入source并衔接原嘴端，沿原canonical坐标重新生成UV；不拉伸旧UV、不加眼片遮挡。首输入在嘴端只取最长alpha run使口线落体外，被已有口校验拒绝；生产前保留原嘴端并复核通过。

## 实证

黄鱼free实际render覆盖99.9026%，肩部97.378%残差保留，游戏相机无大块平切，完整490通过并Agent接受。真鲷指定headROI IoU .82519→.99226，眼圈中心误差.102px；实际正面/俯视不再跨眼纹。原胸鳍仍失败，不把局部视觉成功扩大为整鱼成功。

## 预防

在同源画布同姿态下分开验头、眼、嘴、尾尖和肩部；polygon覆盖与最终投影render分开。旧风格参考与新的canonical源发生形态变化时单列设计变化。近似ROI误报要保留原报告并给源像素/多视证据，不事后移动阈值。现有薄眼片参数不是贴体证明，本次只读试算边缘可离体约3mm，故未采用。

## 相关位置与范围

资源：resources/volume-fish/yellow_croaker-082h.profile.json、red_seabream-082h.profile.json；生产构建器原样保留。实验与报告：游戏experiments/blender-fish/082h-validation/、plans/reviews/082h-visual-corrections.validation.json；调查完整记录docs/anvil/debug-sessions/2026-10-19-082-tail-eye-session.md。

结论仅适用于这两处视觉问题；未证明11鱼全部原图保真或实鱼横宽，离散490亦不是连续时间碰撞证明。
