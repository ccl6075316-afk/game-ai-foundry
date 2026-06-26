# Godot Assembler — import sprites

Import extracted animation frames into a Godot project as `SpriteFrames` resources.

**Skip i2v lead-in**: use `--skip-lead-ratio 0.15` (or config) to drop early morph frames. Never import clip start as idle.

## Command

```bash
python gamefactory.py godot import-sprites \
  --project ../games/prison-demo \
  --asset prison_inmate_walk \
  --input-dir ../output/prison-test/walk_frames_nobg \
  --fps 12 \
  --animation-name walk
```

## Output layout

```
{project}/
  assets/sprites/{asset}/
    frame_0001.png
    ...
  assets/sprites/{asset}_frames.tres   # SpriteFrames resource
```

Paths are **res://** relative to project root.

## Parameters

| Flag | Default | Notes |
|------|---------|-------|
| `--pattern` | `frame_*.png` | Frame glob |
| `--fps` | 12 | Animation speed in SpriteFrames |
| `--animation-name` | asset name | e.g. `walk`, `idle` |
| `--loop` | true | Loop animation |
| `--skip-lead-ratio` | config (0.15) | Drop leading morph frames from i2v clip |
| `--skip-lead-frames` | 0 | Drop exact N leading frames |

## When to use

- **Standalone**: after manual matte-frames
- **Automatic**: inside `godot assemble` (preferred)

## Not your job

- Do not generate PNGs — upstream video/image pipeline only.
