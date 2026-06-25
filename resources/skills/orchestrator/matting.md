# Matting & Trim（切图 / 抠透明）

Orchestrator post-process skill. **切图** here means **trim white borders** (tight crop), **not** grid-splitting icon kits.

## Terminology

| 用户说法 | CLI | 作用 |
|----------|-----|------|
| 切图、裁边、去白边（画布） | `image trim` | 按内容外接矩形裁掉四周白边 |
| 抠图、透明底、去背景 | `image remove-bg` | 白底 → 透明 PNG |
| 边缘校验、检查白边 | `image validate-matting` | 1–2px 轮廓带检测白晕 |
| 拆 kit、网格切 | `image slice --mode grid` | icon_kit 2×2 等分（与切图不同） |

## Standard pipeline（必须按顺序）

```bash
python gamefactory.py image trim \
  --input output/asset.png \
  --output output/asset_trimmed.png

python gamefactory.py image remove-bg \
  --input output/asset_trimmed.png \
  --output output/asset_nobg.png
# remove-bg 默认附带 validate-edges；失败 exit 2

# 或单独复检
python gamefactory.py image validate-matting \
  --input output/asset_nobg.png
```

`remove-bg` 成功后 **必须** 通过 `validate-matting`。未通过 → 按下方 escalation 调参重跑 `remove-bg`，不要直接交付。

Optional: `image resize` after matting passes.

## Color-key 算法（`remove-bg --mode color`，默认）

白底黑边精灵专用，无 ML。通过 **`key_scope`** 控制抠白范围：

| `key_scope` | CLI | 行为 |
|-------------|-----|------|
| `exterior`（默认） | `--key-scope exterior` | 只抠与画布边缘连通的外侧白底（魔术棒），角色内部浅色高光/金属反光 **保留** |
| `global` | `--key-scope global` | 所有符合亮度/色差的白色像素都变透明（含角色内部浅色） |

1. 四角采样背景色 → 候选背景像素（亮度 / 色差）
2. **exterior**：从画布四边 flood-fill → 仅外侧背景透明；**global**：候选白 + 内部近白 spill 全透明
3. （仅 exterior）轮廓贴外缘的 1px 白晕再清一次
4. Morph：`erode` / `dilate` / `despeckle`
5. 硬 alpha + 透明区 RGB 清零

**trim** 与 remove-bg 共用 `key_scope` 前景 mask，避免裁切时把内部浅色算进背景。

## Config (`~/.gamefactory/config.json`)

```json
"matting": {
  "trim": { "threshold": 240, "padding": 2 },
  "color_key": {
    "threshold": 235,
    "fuzz": 24,
    "key_scope": "exterior",
    "morph_erode": 2,
    "morph_dilate": 1,
    "despeckle": 1
  },
  "validate_edges": {
    "edge_width": 2,
    "brightness_threshold": 220,
    "max_white_ratio": 0.01,
    "max_semi_transparent": 0
  }
}
```

See `resources/config.example.json`.

### Parameter cheat sheet

| Key | 效果 |
|-----|------|
| `trim.threshold` | 裁边：亮度 ≥ 此值视为白底 |
| `trim.padding` | 裁切后保留外边距像素 |
| `color_key.threshold` | 抠图亮度阈值 |
| `color_key.fuzz` | 与四角背景色的色差容差 |
| `color_key.key_scope` | `exterior` 仅外侧白底；`global` 全部白色透明 |
| `color_key.morph_erode` | 腐蚀 alpha，吃边缘白晕 |
| `color_key.morph_dilate` | 膨胀 alpha，补回主体 |
| `color_key.despeckle` | 开运算，去零散白点 |
| `validate_edges.edge_width` | 边缘检测带宽（默认 2px） |
| `validate_edges.brightness_threshold` | 边缘上亮度 ≥ 此值计为白点 |
| `validate_edges.max_white_ratio` | 边缘带内白点最大占比（默认 1%） |

## 边缘校验（validate-matting）

在 opaque 轮廓 **最外 1–2px** 采样，检查：

- 高亮像素占比是否超过 `max_white_ratio`
- 是否存在半透明 + 高亮的 halo 像素
- 轮廓外一圈是否有残留 alpha

**未通过时自动处理**（不要重生成图）：

1. `remove-bg --erode N+1 --dilate 1 --despeckle 1 --fuzz +2`
2. 或写 config：`morph_erode++`, `threshold: 235`, `fuzz: 24`
3. 重跑 remove-bg → 再 validate-matting
4. 仍失败才考虑 `prompt craft` / `image generate`

## 用户消息 → 自动处理

| 用户说（含同义） | 判断 | 自动动作 |
|------------------|------|----------|
| 白边、白晕、边缘没抠干净 | 色键 halo | `--erode 2`；config `morph_erode: 2`；跑 validate-matting |
| 白点、碎屑、脏点 | 零散高亮 | `--despeckle 1` |
| 抠完太瘦、线变细 | erode 过猛 | `morph_erode: 1`, `morph_dilate: 2` |
| 还有白底 | 阈值太严 | `--fuzz 24`, `threshold: 235`；先 trim |
| 校验不过 / 边缘有问题 | validate 失败 | 按 escalation 调参重跑 remove-bg |
| 四周空白太多 | 画布白边 | `image trim` 后再 remove-bg |

### Escalation recipe（白边）

1. `trim` 已跑？
2. `remove-bg --erode 2 --dilate 1 --despeckle 1 --fuzz 24 --threshold 235`
3. `validate-matting` 必须通过
4. 仍失败 → `morph_erode: 3` 或 `--mode ai`（最后手段）

## CLI reference

```bash
python gamefactory.py image trim -i raw.png -o trimmed.png
python gamefactory.py image remove-bg -i trimmed.png -o nobg.png
python gamefactory.py image validate-matting -i nobg.png
python gamefactory.py image remove-bg -i trimmed.png -o nobg.png \
  --erode 2 --dilate 1 --despeckle 1 --fuzz 24 --no-validate-edges
```

## Not your job

- Do not use `image slice` for single-character trim.
- Do not skip `validate-matting` after `remove-bg` on deliverable assets.
- Do not re-generate art for pure matting / white-edge issues.
