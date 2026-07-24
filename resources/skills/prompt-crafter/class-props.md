# Class: props (`prop_static` / `prop_interactable` / `prop_stateful` / `weapon` / `tool` / `decor`)

Default class for mattable world objects on white studio.

## Technical

- **Pure flat white background (#FFFFFF)**, uniform studio backdrop.
- Single object centered; mattable still; **no environment scenery**.

## `prop_interactable`

- Clear affordance in silhouette (handle, button, lever, pickup read) without scene context.

## `prop_stateful`

- When context includes `asset.state` (expanded multi-state prop): describe **only the state delta** vs the base prop — img2img carries identity from state 0.
- Do not re-describe unchanged parts of the object.

## Style img2img followers

When style group / identity anchor applies: align line weight and palette; low influence — do not copy reference pose or background.

## Negatives

No scenery, no character sprites, no multi-object sheets, no transparent/checkerboard.
