# Godot Assembler — import sprites

Import extracted animation frames (or stills) into a Godot project.

**Clarity rule**: import keeps source / matte resolution. Do **not** crush PNGs to Brief `display_size` to encode body size — games scale with `real_length_cm` / runtime placement. Optional `display_size` on import is legacy; prefer identity copy (or subject-stable compose **without** downscaling below source).

**Skip i2v lead-in**: prefer upstream `video split-frames --optimize-loop`. If importing a full extract, use trim flags — never import clip start as idle.

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
| `--skip-lead-ratio` | config | Prefer optimize_loop at split-frames instead |
| `--skip-lead-frames` | 0 | Drop exact N leading frames |

## When to use

- **Standalone**: after manual matte-frames
- **Automatic**: inside `godot assemble` (preferred)

## Not your job

- Do not generate PNGs — upstream video/image pipeline only.
