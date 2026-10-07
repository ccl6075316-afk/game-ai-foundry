# Layered backdrop split（工具配方）

> 何时用：整幅背景要拆成可独立动效 / 可单独 i2v 的水平带（天空、远景、水面等）。  
> 跨会话流程规则见用户 SOP：`layered-backdrop-split`（`~/.ssbun-skills/sops/layered-backdrop-split.md`）。

## 原则

1. **先生成完整母图**，固定地平线、透视、光色与像素密度；母图只当参考与底衬，不当最终唯一动效载体。
2. 每个拆层资产在 Brief 写 `content_class: scene_layer`、`scene_master`、`scene_box_norm: [x,y,w,h]`、`scene_scale`。Pipeline 从母图原像素裁参考图，强制图生图依赖；不允许独立文生图。
3. 山、树、石等不规则层用 `type: character`：参考裁切画布内只保留该元素，其余纯白，抠图但不裁掉画布；大片连续水面用 `type: background` 的不透明矩形带。`display_size` 对应母图框的原始显示尺寸，额外大小变化只用 runtime `scene_scale`，不可在 PNG 中烤缩放。
4. 图生图只负责提供不规则 alpha 初稿，不能把它重新画出的颜色直接盖回母图。Pipeline 的 `image scene-reproject` 用母图裁切的原始像素替换拆层 RGB，仅保留生成层 alpha；水层直接从母图裁取。`image scene-compose --require-exact` 要求 `scene_scale=1` 时回拼与母图逐像素一致，资产表以 `*_plate_locked.png` 为交付层。
5. 需要前后遮挡时给两层留源框交叠，前层写 `scene_z` 与 `scene_occludes`；叶缘、山脊、岸石用透明 alpha 轮廓咬进后层，不靠矩形压块。每个钓点的母图先写真实地貌/人文视觉锚点，验收时能在不看名称的情况下区分地点。
6. **前景资产另挂**（船/竿/近景），不进背景层。
7. **断层先诊断再补**：行带 alpha 空洞 → 底衬或加大层重叠后重生。
8. **水面动画用水层**，不用整图 i2v。若层将产生大幅视差，必须先审 alpha 与无遮挡底衬；“静态逐像素回拼”不等于移动后不会露出母图中的原物体。

## Prompt 要点（每层）

| 层 | 保留 | 强制 |
|----|------|------|
| sky | 天、云、日/月色 | 地平线以下纯白；无树无水无船 |
| distant | 远山、岸线树带 | 天与大面积水纯白；与 sky/water **留重叠带** |
| water | 水面涟漪与反光 | 上半纯白；无天无树无船；地平线可齐 |

共用：锁定同一母图的构图、光色、像素密度与地平线；`requires_reference_image: true`。strength 只控制模型参考强度，不能替代 `scene_box_norm` / `scene_scale` 的几何约束。

## CLI

```bash
python gamefactory.py image generate --prompt '...' --reference-image <full.png> \
  --output <layer>_raw.png --size 1920x1080
python gamefactory.py image remove-bg --input <layer>_raw.png \
  --output <layer>_nobg.png --mode color
python gamefactory.py image scene-reproject --master <full.png> \
  --mask <layer>_nobg.png --box <x> <y> <w> <h> \
  --output <layer>_plate_locked.png
```

可选：

```bash
python gamefactory.py video generate --reference-image water_raw.png --prompt '...' \
  --output water_loop.mp4 --duration 5
python gamefactory.py video split-frames --input water_loop.mp4 --output-dir frames --frames 24
```

## 引擎

- z：`underlay(full) → sky → distant → water → foreground`
- 动效只绑 water（shader 或审片通过后的帧循环）
- 灰缝 = 透明叠在清屏色上，不是「生出了灰」

## 与 `backdrop_sparse` / `backdrop_full` 关系

- 单图氛围仍走 [`class-backdrops.md`](class-backdrops.md)。
- **要分层动效 / 分层 i2v** 时改走本配方；brief 里按层拆多条 backdrop 资产（试点通过后再登记）。

## 试点

`projects/fishing-2d/plans/2026-09-14-bg-layers-pilot.md`
