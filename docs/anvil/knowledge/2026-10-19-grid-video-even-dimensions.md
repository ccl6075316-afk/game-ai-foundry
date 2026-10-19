---
type: debug-knowledge
status: SUCCESS
bug_topic: Pixel-fish grid movie odd-height encoding
date: 2026-10-19
---

# 多行像素预览网格先确定最终编码尺寸

083每格640x189、2列5行得到1280x945；单鱼1280x756均可编码，总览libx264/yuv420p却报height not divisible by2、exit187。实际完整命令与独立lavfi负例均复现，排除素材和鱼模型问题。

唯一编码修复为xstack后pad=ceil(iw/2)*2:ceil(ih/2)*2。保持内容位置/大小，当前只补底1像素；正式192帧输出1280x946、16秒、12fps、yuv420p通过，独立ffprobe和画面审核通过。单鱼视频与160秒总对照不需改变。

未来按最终网格尺寸检查偶数条件，不能只检查单格或以缩放/裁鱼掩盖失败。媒体报告另须区分整屏对照、仅after半屏的缩略总览和固定裁剪静态板；保留源图不等于显示没有眼UV/体态变化。

相关：resources/scripts/volume-fish/encode_friendly_previews.py；docs/anvil/debug-sessions/2026-10-19-083-grid-even-height-session.md；projects/fishing-2d/plans/reviews/083-friendly/083-encoding-review.validation.json。
