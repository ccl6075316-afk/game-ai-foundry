# Video Frame Matting（视频帧抠图）

Orchestrator post-process skill for **animation frames** extracted from Seedance video.
**Do not** use `image remove-bg --mode color` on video frames — backgrounds drift to gray/off-white.

## Static vs video

| Source | Background | Tool |
|--------|------------|------|
| Studio still (character / icon) | Pure `#FFFFFF` | `image trim` → `image remove-bg --mode color` |
| Seedance video frames | Gray / off-white drift | `video matte-frames --engine ai` |

## Standard animation pipeline

```bash
# After video-generator produces MP4
python gamefactory.py video split-frames \
  --input output/walk.mp4 \
  --output-dir output/walk_frames \
  --frames 8

python gamefactory.py video matte-frames \
  --input-dir output/walk_frames \
  --output-dir output/walk_frames_nobg \
  --engine ai
# default --no-trim: keep full frame after video (do not crop before matting)
```

## Before video (reference still)

| Step | Trim? |
|------|-------|
| `image generate` → raw PNG | No |
| `video generate --reference-image <raw>` | **Never trim** — pass original canvas to Seedance |
| `image trim` / `remove-bg` | Only for **static** sprite delivery, not i2v input |

## After video (frames)

| Step | Trim? |
|------|-------|
| `video split-frames` | No |
| `video matte-frames` | Default **no trim** (`--trim` only if you want tight bbox) |

Optional resize per frame after matting: `image resize` (batch script or loop).

## Engines

### `ai` (default, recommended)

Uses [rembg](https://github.com/danielgatis/rembg) (MIT, 23k+ stars) with **BiRefNet** or ISNet.

```bash
pip install "rembg[cpu]"
```

| Model | Notes |
|-------|-------|
| `birefnet-general` | Default — best general quality |
| `isnet-general-use` | Lighter, good fallback |
| `u2net` | Legacy, fastest |

### `soft-key` (fallback, no ML)

Softer color-key for gray backgrounds when rembg unavailable:

```bash
python gamefactory.py video matte-frames \
  --input-dir output/walk_frames \
  --output-dir output/walk_frames_nobg \
  --engine soft-key \
  --threshold 200 --fuzz 36
```

Uses `key_scope: global` by default (video bg is not studio white).

## Config (`~/.gamefactory/config.json`)

```json
"video": {
  "split_frames": { "frames": 8 }
},
"matting": {
  "video_frames": {
    "engine": "ai",
    "model": "birefnet-general",
    "trim": { "threshold": 200, "padding": 2 },
    "soft_key": {
      "threshold": 200,
      "fuzz": 36,
      "key_scope": "global",
      "morph_erode": 1,
      "morph_dilate": 1,
      "despeckle": 1
    }
  }
}
```

| `--frames` | Game use |
|------------|----------|
| 4 | Minimal idle / simple move |
| 8 | Default walk cycle |
| 12 | Smooth run / detailed motion |

Fewer frames = less AI matting time (8 frames ≈ 1 min vs 61 frames ≈ 7 min on CPU).

## Validation

Video frames use **relaxed QA** (opaque ratio sanity check), not strict white-edge validate.
Do **not** run `require_pure_white_background` on video frames.

## Troubleshooting

| Symptom | Action |
|---------|--------|
| rembg not installed | `pip install "rembg[cpu]"` or `--engine soft-key` |
| Gray halo on edges | Retry `birefnet-general`; or soft-key `--threshold 195 --fuzz 40` |
| Subject eaten / holes | `--engine ai` (avoid soft-key on complex bg) |
| Frame mostly transparent | Check source frame; may be empty/corrupt |
| Still has background | AI model swap to `isnet-general-use`; increase trim threshold |

## Not your job

- Do not use `image remove-bg --mode color` on video frames.
- Do not require pure white background on animation frames before matting.
- Reference still for img2video **must** still pass white-bg validate (separate pipeline).
