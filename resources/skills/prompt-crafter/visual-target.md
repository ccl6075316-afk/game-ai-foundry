# Visual Target (full-screen gameplay mock)

Craft prompts for **predicted in-game screenshots** — the visual north star (`visual_reference`), not asset sprites.

## Task

One **full viewport** frame that looks like real gameplay capture:

- Match `project.art_direction`, `genre`, `gameplay_loop`, `session_goal`
- Honor the **variant focus** (opening moment, action beat, session goal, alternate composition)
- **2D or 3D** per `project.dimension`

## Prompt rules

- **Enumerate every game object** — player, enemies, pickups, platforms, props. For each, state **approximate size vs screen** (e.g. player ~18% of screen height, coin ~3% width).
- **Reflect real technical constraints.** Tiling-friendly backgrounds vs layered sprites as distinct objects.

## Must NOT include

- Pure white (#FFFFFF) studio background — **never** (this is not a character sprite)
- Transparent/checkerboard background
- Watermarks, outer UI chrome, title cards, "GAME SCREENSHOT" text
- Multiple unrelated composition variants in one image
- Character-only on white (that is `character` asset type)

## Variant hints

| Variant | Emphasis |
|---------|----------|
| `opening_moment` | Level start, environment readable, calm setup |
| `action_beat` | Core loop energy — move, attack, collect |
| `session_goal` | Win condition mood — progress, tension, reward |
| `alternate_composition` | Same game, different framing/lighting |

Under 120 words. English only.

## Image size

- **Always** match `project.viewport` width×height (e.g. `1280x720`).
- The handoff `image_size` field is passed to image-generator — do not prompt for square or sprite dimensions.
- This image is **not** resized to `assets[].display_size`; it stays full viewport.
