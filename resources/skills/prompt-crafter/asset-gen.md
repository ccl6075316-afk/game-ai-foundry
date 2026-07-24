# Asset Generator — compatibility index

> **Prefer class skills via loader** (`shared-locks` + `class-*`). This file remains for legacy `load_role_skills` fallback only.

## Where rules live now

| Topic | File |
|-------|------|
| Global bans, art_tokens, structured fields | `shared-locks.md` |
| Characters / player stills | `class-character.md` |
| Tiles | `class-tiles.md` |
| Props / weapons / tools | `class-props.md` |
| Backgrounds | `class-backdrops.md` |
| UI / icon_kit | `class-ui.md` |
| Routing table | `asset-planner.md` |

## Still relevant cross-cutting notes

- **`display_size`** = in-game pixels; **`image_size`** = API size (pipeline-derived).
- **`project.visual_reference`**: match palette/line/mood — characters/icons still use white studio, not full screenshot paste.
- **Style group img2img**: followers get low-influence wording; `identity_anchor` locks who, not composition copy.
- **`character_pose` / animation video**: img2img / i2v — describe only motion or pose delta.

For full historical cheatsheet detail, see git history of this file before class split.
