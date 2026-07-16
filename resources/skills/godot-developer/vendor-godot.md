# Godot C# — vendored engine skills

Game AI Foundry uses **C# / Godot 4 .NET** for Pass 4. Read these vendored skills before writing or reviewing `.cs` files.

## Vendored sources (run once)

```bash
bash scripts/vendor-godot-skills.sh
```

Upstream: [fetasty/godot-skills](https://github.com/fetasty/godot-skills) (MIT)

| Skill | Path | Use when |
|-------|------|----------|
| `godot` | `vendor/fetasty-godot-skills/godot/SKILL.md` | Scene tree, signals, resources, project settings |
| `godot-csharp` | `vendor/fetasty-godot-skills/godot-csharp/SKILL.md` | **C# patterns**, partial classes, Signal delegates, async |

If vendor files are missing, run the script above — do not guess Godot C# APIs.

## Foundry-specific constraints (override vendor when they conflict)

1. **C# only** — no new GDScript gameplay files.
2. **Authoritative sources** — `brief.json`, `production.json` (if present), `assets-manifest`, assembled project.
3. **`production.godot_tasks`** — implement in dependency order; each task's `verify[]` is acceptance for that step.
4. **`production.scenes` / `production.systems`** — scaffold blueprint; align new nodes/scripts with these paths.
5. **Assets** — use `runtime_bindings` for SpriteFrames / `res://` paths; never call image/video APIs.
6. After edits: `python gamefactory.py godot validate --project <project>`.

## Genre preset hints (from production derive)

When `production_doc.genre` is `2d_platformer`:

- Player root: `CharacterBody2D` + `CollisionShape2D` + `AnimatedSprite2D`
- Movement in `_PhysicsProcess`; gravity from `production.world.gravity`
- Jump velocity from `production.player.jump_velocity` when `jump` is in `brief.controls`
- Camera: `CameraFollow` on `Main/Camera2D` when `brief.camera.mode` is `follow_player`

When `top_down`:

- Use `move_speed` for 8-way or 4-way movement; gravity typically 0.

## Harness (tester)

After implementing a task, orchestrator may run:

```bash
python gamefactory.py test play --project ... --plan plans/playtest_<brief>.json
```

Criteria should match `production.validation.acceptance_criteria` when production exists.
