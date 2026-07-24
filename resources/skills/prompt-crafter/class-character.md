# Class: character (mattable still)

For `type: character`, player usages (`player_idle`, `player_locomotion`, …), and mattable cast on white studio.

## View (from `project.view`)

| view | Write in `view` field |
|------|----------------------|
| `side` | Side view, profile facing right, readable side-scroller silhouette |
| `top_down` | Top-down, looking straight down, clear shapes from above |
| `three_quarter` | Three-quarter angle, readable game asset perspective |

Do not assume side view when `project.view` is `top_down` or `three_quarter`.

## Technical / subject

- Single character, full body, neutral standing pose unless brief says otherwise.
- **Pure flat white background (#FFFFFF)**, uniform studio backdrop — no border, vignette, gradient, texture, or ground shadow.
- Centered subject; clean silhouette; **no environment** (no walls, floor scenery, props in frame).
- Small `display_size` (<128px): flat shading, **thick outline**, minimal fine detail.

## Negatives

No scenery, no UI, no multi-character sheets, no transparent/checkerboard background.

## Animation note

Video / pose assets use separate craft paths; still never describe a walk-cycle sheet in one image.
