# Asset Generator — prompt cheatsheet

Reference patterns only. **Craft** the final prompt for each asset; do not copy blindly.

## Global prohibitions

- Never prompt for "transparent background" or checkerboard — generators draw fake transparency.
- Never request a spritesheet or multiple action frames in one image.
- For img2img: do not re-describe the whole character — only what changes.

## Asset type separation (mandatory)

Each asset type has **different** prompt rules and **different** post-pipeline. Never mix them.

| Type | Background | Post-process | Forbidden in prompt |
|------|------------|--------------|---------------------|
| **character** | Pure white #FFFFFF studio | trim → remove-bg | scenes, walls, icons, grids |
| **icon_kit** | White studio grid | slice → trim → remove-bg per tile | characters, scenery |
| **background** | Full environment scene | none (no matting) | white studio, character sprites |
| **texture** | Tile fills frame | none | white studio, characters |

## character (single, white background)

```
{subject}. Single character, full body, neutral standing pose, facing right, centered.
Pure flat white background (#FFFFFF), uniform studio backdrop, no border, no frame,
no vignette, no gradient, no texture, no cast shadow on ground. Clean silhouette.
Not a prison scene — no walls, bars, cells, or floor environment. {art style cues}.
```

Validation: **pure white background** (not merely light gray), one subject region, not a horizontal frame strip.

If image-generator reports `require_pure_white_background` failure, append the `retry_hints`
from validation JSON and regenerate — do not send the image to trim/remove-bg.

Post (orchestrator **matting** skill): `trim` → `remove-bg` (color key).

## icon_kit (grid of items, white background)

```
{item1}, {item2}, ... — {rows}x{cols} grid, each item centered in its cell.
Game item icons, consistent scale. Pure flat white background. {art style cues}.
```

No characters, no scenery. Post: grid slice → trim white borders per tile → remove background per tile.

## texture (no white studio bg)

```
{material description}. Top-down view, uniform lighting, no shadows,
seamless tileable texture, clean edges.
```

Use full image as texture — do not remove background.

## background (no white studio bg)

```
{scene description}. Environmental background, {2D parallax | 3D vista}.
Natural lighting, rich detail. No character sprites, no UI, no flat white backdrop.
```

## character_pose (img2img, single frame)

```
{action pose only}, side view, same character as reference, single frame, not a spritesheet.
Solid white background.
```

## animation video prompt

```
{action}, smooth animation, single character, solid white background throughout. Not a spritesheet.
```

Workflow: reference image → video → split-frames → `video matte-frames --engine ai` (not color-key remove-bg).

## Small sprite warning

If display size is under 128px, prompt for bold shapes, thick outlines, flat colors — fine detail is lost when downscaled.
