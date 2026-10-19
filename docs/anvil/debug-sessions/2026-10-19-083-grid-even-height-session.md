# 083 十鱼网格视频编码：奇数高度

Normal mode，2026-10-19。用户要求其余10条新鱼按像素亲近感方向轻调。

## Phase1 evidence / root cause

各鱼1280x756新旧对照及160秒串接成功；总览2列5行，每格640x189，输出1280x945。实际完整FFmpeg命令负例可复现exit187，/tmp/083-grid-negative.log明确报 `[libx264] height not divisible by 2 (1280x945)`。素材、动作、GLB不涉及。原Python打包器把stderr丢弃，异常只有命令；已额外只读复现取得明确错误。

## Phase2 pattern

已成功的单鱼视频宽高均偶数，失败网格高189×5=945；相同libx264/yuv420p，变化只有网格尺寸。

## Phase3 hypothesis / proposed minimal test

假设yuv420p/H264偶数尺寸条件导致失败。拟仅在xstack后pad=ceil(iw/2)*2:ceil(ih/2)*2，把945补成946，不拉伸、不裁鱼。独立reviewer对Phase1/2/3进行审核；未执行正式修订。

Phase1/2/3 independent reviewer APPROVED. Independent lavfi negative reproduces187 and positive pad produces1280x946/yuv420p/1frame. Evidence /tmp/review083-grid-dimension.validation.json. Executed only xstack filter padding change; no body/material/motion edits.

Phase4 independent APPROVED。正式重跑10单鱼视频均192帧/16s/1280x756，串接1920帧/160s，总览192帧/16s/1280x946/yuv420p/12fps。独立报告 projects/fishing-2d/plans/reviews/083-friendly/083-encoding-review.validation.json；已修正媒体scope：总览取after下半屏并0.5等比缩小，静态板另有统一中央裁剪，不能称裁切只发生于静态板。修复本身只在底部补1像素。终态SUCCESS，模型/动作配置不涉及。
