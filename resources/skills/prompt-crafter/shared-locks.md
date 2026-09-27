# Shared locks (all asset classes)

Apply on every craft — Python also injects hard locks; do not contradict them.

## Global bans

- Never prompt for transparent background or checkerboard — generators draw fake transparency.
- Never request a spritesheet or multiple action frames in one image.
- For img2img / style followers: do not re-describe the whole subject — only what changes.

## Structured output (mandatory)

Fill JSON fields; Python assembles the final labeled prompt:

| Field | Role |
|-------|------|
| `subject` | Main readable description |
| `silhouette` | Shape / readability cues |
| `style_lock` | Line weight, palette, art style locks |
| `view` | Camera / facing for this asset |
| `technical` | Background, matting, tile, or scene requirements |
| `negatives` | Forbidden elements and composition mistakes |

Do not output a free-form `prompt` field unless legacy fallback.

## `project.art_tokens` (priority over mood)

When context includes non-empty `project.art_tokens`:

1. **Encode tokens into hard locks first** — map `line`, `palette`, `forbid`, `silhouette` into `style_lock` / `negatives` **before** paraphrasing `art_direction`.
2. **`art_direction` still required** — mood / atmosphere prose only; tokens win on line, palette, forbid, silhouette.
3. **`forbid`** → explicit negatives.
4. **`palette`** — string or list; treat hex / color names as enforceable locks.

## `project.view`

When `project.view` is set (`side` | `top_down` | `three_quarter`), write `view` field to match — do not hardcode side-scroller-only language unless view is `side`.

## Sizing reminder

- **`source` pixels** = generate / matte output — keep this clarity at Godot import.
- **`display_size` / `real_length_cm`** = in-game size **intent** (relative length / layout), consumed as **runtime scale** when placing sprites — **not** a reason to crush PNGs at import.
- Same character family should share length intent (`real_length_cm` / family scale), not necessarily identical baked bitmap sizes.
- Under ~128px **on-screen** target → prompt for flat colors, thick outlines, bold shapes (art direction), still import sharp sources when available.
