# Visual Target (full-screen gameplay mock)

Craft **structured fields** for a predicted **in-engine gameplay screenshot** — the visual north star (`visual_reference`), not asset sprites.

## Provenance (do not invent a new school)

Distilled for Foundry CLI from:

- OpenAI Image generation prompting guide (wide → narrow; labeled segments)
- GPT Image 2 Scene / Subject / Details / Use case / Constraints pattern
- Community **game screenshot** prompt archetypes
- Godogen Visual Target semantics (one north-star frame anchors the project)

Python will **assemble** your JSON fields into the final image prompt in that order. Fill fields; do not write a free-form essay as `prompt`.

## Goal

One **full viewport** frame that looks like a **runtime framebuffer capture** (player paused mid-game), not key art, not a store poster, not a hero render.

Match:

- `project.art_direction`, `genre`, `gameplay_loop`, `session_goal`
- Variant focus (`opening_moment` / `action_beat` / `session_goal` / …)
- `project.dimension` (2d / 3d)
- `project.player_asset` as the **visual hero** (largest or most readable focal character)
- `project.camera` for viewpoint language when present
- `project.hud` only for in-game HUD chips (never outer app chrome)

## JSON fields (English, concrete visual facts)

```json
{
  "use_case": "in-engine 16:9 gameplay screenshot / framebuffer capture",
  "scene": "environment, time of day, readable level props",
  "hero": "player_asset name + pose/action + ~screen-height %",
  "gameplay_beat": "what the player is doing THIS frame (core loop readable)",
  "details": "camera/lens feel, lighting, materials; lock art_direction traits",
  "hud": "only brief.hud elements, or empty string if none should show",
  "style_lock": "short hard locks from art_direction (silhouette, outline, palette mood)",
  "constraints": "comma-separated must-nots"
}
```

Field rules:

| Field | Must |
|-------|------|
| `use_case` | Prefer the default above; say screenshot / framebuffer, never "poster" / "concept art" |
| `scene` | Readable space; tiling vs layered props as distinct objects if relevant |
| `hero` | Name the `player_asset`; approximate % of screen height; clear action |
| `gameplay_beat` | One beat from the loop (e.g. foul decision QTE), not a generic "exciting match" |
| `details` | Camera from `project.camera` when set; concrete light; no vague "cinematic" alone |
| `hud` | Only listed HUD; empty if this variant should hide HUD |
| `style_lock` | Rephrase `art_direction` into enforceable locks (chibi scale, outline, palette) |
| `constraints` | Always include: no poster borders, no letterbox bars, no watermark, no pure-white studio |

## Must NOT (also put into `constraints`)

- Pure white (#FFFFFF) studio / character isolate on white
- Transparent or checkerboard background
- Movie letterbox / cinematic black bars
- Store key-art composition, big title typography, "GAME SCREENSHOT" labels
- Outer phone/PC chrome, fake Steam overlay
- Multiple unrelated compositions in one image
- Ignoring `player_asset` (hero must be obvious at a glance)

## Variant hints

| Variant | Emphasis |
|---------|----------|
| `opening_moment` | Level start, environment readable, calm setup, player visible |
| `action_beat` | Core loop energy — the verb of the game happening now |
| `session_goal` | Win-condition / stakes mood readable in one glance |
| `alternate_composition` | Same game identity; different framing/lighting only |

## Image size

- Always match `visual_target.target_image_size` / `project.viewport` (e.g. 1280x720).
- Do not ask for square sprites or character sheet layouts.

## Output

Respond with **ONLY** the JSON object above (no markdown fences, no wrapper `prompt` field). Keep each field to 1–2 short sentences.
