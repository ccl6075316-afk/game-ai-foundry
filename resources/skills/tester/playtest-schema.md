# Playtest JSON schema (v1)

Steps use Godot **InputMap** action names from `brief.project.controls`.

| `op` | Fields | Notes |
|------|--------|-------|
| `wait_frames` | `frames` (int) | Let physics/animations settle |
| `press` | `action`, `duration_ms` | `Input.action_press` for duration |
| `screenshot` | `name` | Saves `<name>.png` under run directory |
| `assert_action` | `action` | InputMap must contain action (exit 2/3) |
| `assert_node` | `path` | SceneTree node must exist (e.g. `/root/Main/Player`) |
| `assert_property` | `path`, `property`, one of `equals` / `neq` / `gte` / `lte` | Hard assert on node property |

`visual_checks[]` tie each screenshot name to a criterion string for vision QA.

Generate with:

```bash
python gamefactory.py test plan --brief <brief.json>
python gamefactory.py test plan --brief <brief.json> --task player_controller
```

Runner exit codes: `0` ok · `1` error · `2` InputMap missing · `3` assertion failed.
