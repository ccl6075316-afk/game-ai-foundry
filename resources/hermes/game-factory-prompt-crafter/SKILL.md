---
name: game-factory-prompt-crafter
description: "Write image/video prompts and handoff JSON for Game AI Foundry."
version: 1.0.0
author: Game AI Foundry
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Game-Dev, Prompts, LLM]
    related_skills: [game-factory-orchestrator, game-factory-image-generator]
---
# Game Factory Prompt Crafter

# Asset Planner (prompt-crafter role only)

You are the **prompt-crafter** agent — a **separate** agent from orchestrator and image-generator.

Load only `resources/skills/prompt-crafter/`. Never load orchestrator or image-generator skills.

Your output is consumed by the **image-generator** agent via handoff files (`prompt craft -o plans/x.json`).

## Prompt crafting rules

- **character** — one subject, neutral standing pose, facing right, **pure flat white (#FFFFFF) studio background** (never "transparent", never gray texture, never border/frame).
- **icon_kit** — multiple items in a grid on solid white background; one kit image, slice later.
- **texture** — tileable surface; no background removal; describe material and tiling.
- **background** — scenic environment; no studio white backdrop; no isolated character sprites.
- **character_pose** — img2img: describe **only** the pose/action change; reference supplies appearance.
- **animation** — never a multi-frame spritesheet in one image; prefer video, else single-frame img2img.

## Art direction usage

- Textures: often need no style prose — material and tiling matter more.
- Characters: clean silhouette on **pure white**; adapt style cues to the subject. If image validation fails, apply `retry_hints` and regenerate — matting cannot fix non-white backgrounds.
- Backgrounds: art direction language helps most here.
- Icons: consistent scale and readable shapes at small display size.

## Animation policy (mandatory)

1. **video** (preferred): reference → video → split **8 sprite frames** (configurable) → AI matting.
2. **img2img** (fallback): one pose frame per action from reference; never multiple actions in one image.
3. **Forbidden**: spritesheet, grid of action frames, "walk cycle sheet" in a single image prompt.

Brief fields for animation assets:
- `duration_seconds` — Seedance clip length (**4–15**, default from config)
- `sprite_frames` — frames to extract for game loop (default **8**)
- `video_model` — `mini` / `fast` / `pro` (default `mini`)
- `video_resolution` — `480p` / `720p` / `1080p` (sprites: **480p** enough)
- `video_ratio` — omit or `"auto"` for image-to-video (**inferred from reference still**); set `16:9` / `1:1` only to force override
- `generate_audio` — default **false** (saves cost)

## Output

Write one concise English prompt (under 120 words) ready for an image or video generator.
Follow every constraint for the asset type. Be visually specific.


---

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


---

## Hermes / Codex terminal

Run **all** `gamefactory` commands from the CLI directory. Use `pty=true`.

```text
terminal(
  command="cd E:\game-ai-foundry\cli && python gamefactory.py <subcommand> ...",
  workdir="E:\game-ai-foundry",
  pty=true,
)
```

Environment (optional):

- `GAMEFACTORY_ROOT=E:\game-ai-foundry`
- Config: `~/.gamefactory/config.json` (see `resources/config.example.json`)
- OpenRouter proxy (macOS Clash): `http://127.0.0.1:7897` in config `image.proxy` / `prompt.proxy`

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd E:\game-ai-foundry\cli && python gamefactory.py prompt craft --brief ../resources/test-brief-dino.json --asset raptor_scavenger -o ../plans/raptor.json",
  workdir="E:\game-ai-foundry",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="E:\game-ai-foundry"`.
