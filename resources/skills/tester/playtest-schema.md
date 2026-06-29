# Playtest JSON schema (v1)

Steps use Godot **InputMap** action names from `brief.project.controls`.

| `op` | Fields | Notes |
|------|--------|-------|
| `wait_frames` | `frames` (int) | Let physics/animations settle |
| `press` | `action`, `duration_ms` | `Input.action_press` for duration |
| `screenshot` | `name` | Saves `<name>.png` under run directory |

`visual_checks[]` tie each screenshot name to a criterion string for vision QA.

Generate with `python gamefactory.py test plan --brief <brief.json>`.
