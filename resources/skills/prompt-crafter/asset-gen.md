# Asset Generator — prompt cheatsheet

Reference patterns only. **Craft** the final prompt for each asset; do not copy blindly.

## Global sizing (godogen)

- **`display_size`** in brief = in-game pixels on `project.viewport` (how big it **looks**).
- **`image_size`** in handoff = generation API size (derived; do not shrink 1K art to tiny tiles in prompt).
- Same character family (`reference_asset` / animation graph) **must share** `display_size`.

- Never prompt for "transparent background" or checkerboard — generators draw fake transparency.
- Never request a spritesheet or multiple action frames in one image.
- For img2img: do not re-describe the whole character — only what changes.

## Asset type separation (mandatory)

Each asset type has **different** prompt rules and **different** post-pipeline. Never mix them.

| Type | Background | Post-process | Forbidden in prompt |
|------|------------|--------------|---------------------|
| **character** | Pure white #FFFFFF studio | trim → remove-bg | scenes, walls, icons, grids |
| **icon_kit** | White studio **single item** (one generate per `items[]`) | per-item trim → remove-bg | characters, scenery, multi-item sheets |
| **background** | Full environment scene | none (no matting) | white studio, character sprites |
| **texture** | Tile fills frame | none | white studio, characters |

## `project.visual_reference` (Visual Target)

When `project.visual_reference` is set (after `brief visual-target pick`):

| Role | How to use |
|------|------------|
| **prompt-crafter** | Read `visual_reference_usage` in context. Match **palette, line weight, mood** from art_direction + north star. Characters/icons still use **white studio** and `assets[].display_size` — never paste the full screenshot into a character prompt. |
| **image-generator** | **Do not** pass `visual_reference` as `--reference-image` **unless** brief sets `style_anchor_kind: visual_reference` on that asset's style group (then pipeline auto-passes the north-star path). Pose / video still use `reference_asset` only. |
| **tester** | Compare headless **viewport screenshot** (same size as `project.viewport`) against visual_reference for mood/composition QA. |

**Pipeline order:** `brief export` → `brief visual-target generate` → `pick` → then `pipeline run` so craft sees `visual_reference`.

## Style group (`style_group` img2img)

Brief fields (orthogonal to `reference_asset`):

| Field | Meaning |
|-------|---------|
| `style_group` | Group id — same-screen cast, icon set, etc. |
| `style_anchor_kind` | `asset` (default) or `visual_reference` |
| `style_anchor` | Anchor asset `name` / `id` when kind=`asset` |
| `identity_anchor` | Optional identity asset `name` / `id` — same character / prop variant lock (single reference slot) |
| `use_style_img2img` | Default **on** when in a group as follower; set `false` to force text-to-image |

**Reference priority (single slot):** When style img2img applies and `identity_anchor` resolves to a valid asset, pipeline passes that asset's **raw** as `--reference-image` — **not** `style_anchor` or `visual_reference`. Without `identity_anchor`, behavior is unchanged (style anchor / north star).

**Type recipe (pipeline default):**

| Asset type | Style img2img |
|------------|---------------|
| `character`, `texture`, `background` | Allowed when style-group follower |
| `icon_kit` | **Not** — per-item singles are orthogonal; style group on icon_kit is invalid |
| `character_pose`, video clips | Never — use `reference_asset` only |

**Soft strength (mandatory in prompt):** Gemini / default OpenRouter stack has **no reliable API strength**. For every style-group follower, append low-influence wording — match **style / identity traits** (line weight, palette, proportions), **do NOT** copy the reference composition, pose, or layout wholesale. Example tail: *"Use the reference only for art style and character identity cues; low influence; do not copy pose, framing, or background from the reference."*

Optional config `image.style_img2img_strength` (default `0.25`) is best-effort for providers that honor `image_config.strength` (e.g. Recraft); Gemini may ignore it — **prompt soft strength remains primary**.

**prompt-crafter:** For followers, align line weight / palette / head-body ratio with the anchor; do not re-describe the whole character — img2img carries style. Anchor asset itself is text-to-image. When `identity_anchor` is set, prompt should lock **who** (identity) while borrowing **how** (style group) via the reference image.

**image-generator:** Pipeline sets `requires_reference_image: true` and passes `--reference-image` for style followers. You do not pick the path from brief JSON.

**Not style img2img:**

- `character_pose` → `reference_asset` (same character still)
- `animation_method: video` → i2v reference from `reference_asset`; style group does not replace that. The reference still may itself be a style-group img2img product first.
- `icon_kit` → never style img2img (see recipe above)

## `project.art_tokens` (structured style locks)

When context includes non-empty `project.art_tokens` (injected via `build_role_context`):

1. **Encode tokens into hard locks first** — map `line`, `palette`, `forbid`, `silhouette` into prompt tails / `style_lock` wording **before** paraphrasing freeform `art_direction`.
2. **`art_direction` still required** — use it for mood / atmosphere prose; do not drop it when tokens exist.
3. **`forbid`** → explicit negative constraints in prompt (same spirit as visual-target `constraints`).
4. **`palette`** — string or string[]; list hex or color names as enforceable locks.
5. Old briefs without `art_tokens` → unchanged behavior (derive locks from `art_direction` only).

**Roadmap:** Phase 2 (`project.art_tokens`) **shipped**; Phase 3 = GUI for anchor / group / toggle visibility.

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

## icon_kit (one object per image)

Pipeline expands `items[]` into **N separate generates** (`image.bulk_model` when configured).
`grid` in brief is **ignored** (legacy). Do not prompt for sheets.

```
Single game icon: {item}. Centered. Consistent scale. Pure flat white background. {art style cues}.
No grid, no other objects.
```

Post: trim → remove-bg **per item** (no `image slice`).

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
