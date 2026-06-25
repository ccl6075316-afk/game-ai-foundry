# Asset Generator — prompt cheatsheet

Reference patterns only. **Craft** the final prompt for each asset; do not copy blindly.

## Global prohibitions

- Never prompt for "transparent background" or checkerboard — generators draw fake transparency.
- Never request a spritesheet or multiple action frames in one image.
- For img2img: do not re-describe the whole character — only what changes.

## character (single, white background)

```
{subject}. Single character, full body, neutral standing pose, facing right, centered.
Solid white background. Clean silhouette. {art style cues}.
```

Validation: one subject region, light background, not a horizontal frame strip.

## icon_kit (white background, multiple items)

```
{item1}, {item2}, ... — {rows}x{cols} grid, each item centered in its cell.
Game item icons, consistent scale. Solid white background. {art style cues}.
```

Post: grid slice → remove background per tile.

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

Workflow: reference image → optional pose still → video → ffmpeg frames → loop trim → rembg.

## Small sprite warning

If display size is under 128px, prompt for bold shapes, thick outlines, flat colors — fine detail is lost when downscaled.
