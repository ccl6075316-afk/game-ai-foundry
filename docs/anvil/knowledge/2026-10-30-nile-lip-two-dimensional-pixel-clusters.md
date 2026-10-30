---
type: debug-knowledge
status: local-fix-verified-user-review-pending
bug_topic: Nile upper-lip repeated profile
date: 2026-10-30
---

# 上唇像素材质不能退化成单列色带

## Root Cause Summary
R7沿三维唇弧重复同一33像素横截面，丢失沿唇方向的二维绘画变化；nearest、源RGBA正确和几何贴边都不能恢复它。

## Fix Approach & Why It Works
R8共用实际公共边累计弧长，在原图二维唇区取色；以本鱼6原图像素方块为最小笔触，逐单元记录供体，不连续插值成新色。保留原有65UV岛，静态结果保存blend/GLB，几何/动画不动。6像素是本鱼5—7像素簇观察后的局部美术参数。

## Pattern Identification
单条颜色profile、只用到边距离取色、一个维度零变化、独立三角岛各自重置相位，都会使“RGB来自原图”仍看起来像新画的线。

## Prevention Strategy
独立raster探针应拒绝旧1D域；正例还要核对完整二维供体/原生尺度/实际接头/新导出多视。此次270单元原图RGBA无差异，43个独立沿唇剖面、最小6像素；新GLB几何与54动画通道精确保持。用户仍待看，未安装/未整鱼接受。

## Related Code Locations
paint_nile_upper_lip.py --pixel-clusters；apply_nile_upper_lip.py -- --pixel-clusters；probe_lip_pixel_field.py；实际证据在游戏round8-upper-lip-pixel-clusters。

## Key Takeaway
像素画最小笔触和二维纹样必须在真正映射到曲面的材料里保持，不能用nearest或单列原色来替代。
