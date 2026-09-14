# Layered backdrop split（工具配方）

> 何时用：整幅背景要拆成可独立动效 / 可单独 i2v 的水平带（天空、远景、水面等）。  
> 跨会话流程规则见用户 SOP：`layered-backdrop-split`（`~/.ssbun-skills/sops/layered-backdrop-split.md`）。

## 原则

1. **整图只当参考与底衬**，不当最终唯一动效载体。
2. **一层一生图**：保留该带，其余 **纯白**；`remove-bg` 后再叠。
3. **前景资产另挂**（船/竿/近景），不进背景层。
4. **断层先诊断再补**：行带 alpha 空洞 → 底衬或加大层重叠后重生。
5. **水面动画用水层**，不用整图 i2v。

## Prompt 要点（每层）

| 层 | 保留 | 强制 |
|----|------|------|
| sky | 天、云、日/月色 | 地平线以下纯白；无树无水无船 |
| distant | 远山、岸线树带 | 天与大面积水纯白；与 sky/water **留重叠带** |
| water | 水面涟漪与反光 | 上半纯白；无天无树无船；地平线可齐 |

共用：锁定参考图风格（像素风等）；`requires_reference_image: true`；strength ~0.25。

## CLI

```bash
python gamefactory.py image generate --prompt '...' --reference-image <full.png> \
  --output <layer>_raw.png --size 1920x1080
python gamefactory.py image remove-bg --input <layer>_raw.png \
  --output <layer>_nobg.png --mode color
```

可选：

```bash
python gamefactory.py video generate --reference-image water_raw.png --prompt '...' \
  --output water_loop.mp4 --duration 5
python gamefactory.py video split-frames --input water_loop.mp4 --output-dir frames --frames 8
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
