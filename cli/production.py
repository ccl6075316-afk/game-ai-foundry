"""Production doc — engineering blueprint derived from frozen brief."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brief import AssetSpec, CharacterAnimationGraph, ProjectContext, load_brief_full
from genre_presets import get_genre_preset

PRODUCTION_SCHEMA_VERSION = 1


def default_production_path(brief_path: Path) -> Path:
    stem = brief_path.stem.replace(".json", "")
    return Path("..") / "plans" / f"production_{stem}.json"


def _slug(title: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (title or fallback).lower()).strip("-")
    return slug or fallback


def _player_display_size(assets: list[AssetSpec], player_asset: str) -> dict[str, int]:
    for spec in assets:
        if spec.name == player_asset and not spec.display_size.is_empty():
            return spec.display_size.to_dict()
    return {"width": 64, "height": 64}


def _animation_names(graphs: list[CharacterAnimationGraph], player_asset: str) -> list[str]:
    clips: set[str] = set()
    for graph in graphs:
        if graph.character_asset != player_asset:
            continue
        if graph.default_clip:
            clips.add(graph.default_clip)
        for transition in graph.transitions:
            if transition.from_clip:
                clips.add(transition.from_clip)
            if transition.to_clip:
                clips.add(transition.to_clip)
            if transition.then_clip:
                clips.add(transition.then_clip)
    return sorted(clips) if clips else ["idle"]


def _has_collectibles(assets: list[AssetSpec]) -> bool:
    return any(
        spec.usage in {"item_icon", "icon", "pickup"}
        or spec.type.value == "icon_kit"
        for spec in assets
    )


def _has_hud(project: ProjectContext) -> bool:
    return bool(project.hud)


def _build_scenes(project: ProjectContext, player_asset: str) -> list[dict[str, Any]]:
    main_children = [
        {"name": "World", "type": "Node2D", "role": "level_root"},
        {"name": "PlayerSpawn", "type": "Marker2D", "role": "spawn"},
    ]
    if project.camera:
        main_children.append({"name": "Camera2D", "type": "Camera2D", "role": "camera"})
    if _has_hud(project):
        main_children.append({"name": "HUD", "type": "CanvasLayer", "role": "hud"})

    return [
        {
            "path": "scenes/main.tscn",
            "role": "main",
            "root": {"name": "Main", "type": "Node2D"},
            "children": main_children,
        },
        {
            "path": "scenes/player.tscn",
            "role": "player",
            "root": {"name": "Player", "type": "CharacterBody2D"},
            "children": [
                {"name": "CollisionShape2D", "type": "CollisionShape2D", "role": "hitbox"},
                {"name": "AnimatedSprite2D", "type": "AnimatedSprite2D", "role": "sprite"},
            ],
            "script": f"scripts/{_pascal_case(player_asset)}Controller.cs",
            "asset": player_asset,
        },
    ]


def _pascal_case(name: str) -> str:
    parts = re.split(r"[_\-\s]+", name.strip())
    return "".join(p.capitalize() for p in parts if p) or "Player"


def _build_systems(project: ProjectContext, player_asset: str) -> list[dict[str, Any]]:
    systems: list[dict[str, Any]] = [
        {
            "id": "player_controller",
            "script": f"scripts/{_pascal_case(player_asset)}Controller.cs",
            "node": "scenes/player.tscn",
            "responsibility": "Input, movement, animation state, collision response",
        },
        {
            "id": "game_state",
            "script": "scripts/GameState.cs",
            "node": "autoload",
            "responsibility": "Score, health, win/lose flags, session progress",
        },
    ]
    if project.camera.get("mode") == "follow_player":
        systems.append(
            {
                "id": "camera_follow",
                "script": "scripts/CameraFollow.cs",
                "node": "scenes/main.tscn/Camera2D",
                "responsibility": "Follow player with deadzone from brief.camera",
            }
        )
    return systems


def _build_input_map(controls: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {"action": action, "keys": keys}
        for action, keys in sorted(controls.items())
        if action.strip() and keys
    ]


def _build_godot_tasks(
    project: ProjectContext,
    assets: list[AssetSpec],
    graphs: list[CharacterAnimationGraph],
    *,
    has_collectibles: bool,
) -> list[dict[str, Any]]:
    player = project.player_asset or "player"
    tasks: list[dict[str, Any]] = []

    def add(
        task_id: str,
        title: str,
        *,
        depends_on: list[str] | None = None,
        verify: list[str] | None = None,
    ) -> None:
        tasks.append(
            {
                "id": task_id,
                "title": title,
                "depends_on": depends_on or [],
                "verify": verify or [],
                "status": "pending",
            }
        )

    add(
        "input_map",
        "Wire InputMap actions from brief.controls",
        verify=[f"InputMap contains: {', '.join(sorted(project.controls))}" if project.controls else "InputMap configured"],
    )
    add(
        "player_controller",
        f"Implement {_pascal_case(player)}Controller (CharacterBody2D) with brief.controls",
        depends_on=["input_map"],
        verify=[
            "Player moves left/right when move actions pressed",
            "Player collides with world layer",
        ],
    )
    if project.genre in {"2d_platformer", "side_scroller", "endless_runner"} and "jump" in project.controls:
        tasks[-1]["verify"].append("Player can jump when jump action pressed")

    clips = _animation_names(graphs, player)
    if clips:
        add(
            "animation_states",
            f"Bind SpriteFrames clips ({', '.join(clips)}) per animation_graphs",
            depends_on=["player_controller"],
            verify=[f"AnimatedSprite2D plays clip: {c}" for c in clips[:4]],
        )

    if project.camera:
        add(
            "camera",
            f"Configure camera: {project.camera}",
            depends_on=["player_controller"],
            verify=["Camera follows or frames player as specified in production.camera"],
        )

    if has_collectibles:
        add(
            "collectibles",
            "Create pickup areas for item_icon / icon_kit assets",
            depends_on=["player_controller"],
            verify=["Player can collect at least one pickup and counter updates"],
        )

    if _has_hud(project):
        add(
            "hud",
            "Wire HUD elements from brief.project.hud",
            depends_on=["player_controller"],
            verify=["HUD elements visible per brief.hud anchors"],
        )

    session = (project.session_goal or "").strip()
    prior_ids = [t["id"] for t in tasks if t["id"] != "input_map"]
    add(
        "session_goal",
        f"Implement session goal: {session or 'playable demo'}",
        depends_on=prior_ids,
        verify=[
            "main scene loads without errors",
            session or "core loop from brief.session_goal is reachable",
        ],
    )

    return tasks


def _build_validation(project: ProjectContext, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    criteria: list[str] = [
        "main scene loads",
        "godot validate passes",
    ]
    if project.controls:
        criteria.append("all brief.controls actions work in playtest harness")
    if (project.session_goal or "").strip():
        criteria.append(project.session_goal.strip())
    if (project.gameplay_loop or "").strip():
        criteria.append(f"core loop: {project.gameplay_loop.strip()}")

    for task in tasks:
        for item in task.get("verify") or []:
            text = str(item).strip()
            if text and text not in criteria:
                criteria.append(text)

    return {
        "acceptance_criteria": criteria,
        "regression_checks": [],
    }


def derive_production(brief_path: Path) -> dict[str, Any]:
    """Derive production.json from frozen brief + genre preset."""
    brief_path = brief_path.resolve()
    project, assets, graphs = load_brief_full(brief_path)
    preset_id, preset = get_genre_preset(project.genre)

    player_asset = (project.player_asset or "").strip()
    if not player_asset:
        for spec in assets:
            if spec.usage in {"reference_still", "player_idle", "player_locomotion"}:
                player_asset = spec.name
                break
    if not player_asset and assets:
        player_asset = assets[0].name

    viewport = dict(project.viewport) if project.viewport else {"width": 1280, "height": 720}
    display_size = _player_display_size(assets, player_asset) if player_asset else {"width": 64, "height": 64}

    world = dict(preset.get("world") or {})
    if viewport.get("height"):
        world.setdefault("ground_y", int(viewport["height"]) - 120)

    player = dict(preset.get("player") or {})
    player["asset"] = player_asset
    player["display_size"] = display_size
    player.setdefault("collision_size", dict(player.get("hitbox") or {"width": 28, "height": 44}))

    has_collectibles = _has_collectibles(assets)
    systems = _build_systems(project, player_asset)
    if has_collectibles:
        systems.append(
            {
                "id": "collectibles",
                "script": "scripts/Collectible.cs",
                "node": "scenes/main.tscn/World",
                "responsibility": "Area2D pickups for icon_kit / item assets",
            }
        )

    godot_tasks = _build_godot_tasks(
        project, assets, graphs, has_collectibles=has_collectibles
    )

    brief_data = json.loads(brief_path.read_text(encoding="utf-8"))
    brief_meta = brief_data.get("brief_meta") if isinstance(brief_data.get("brief_meta"), dict) else None

    preset_trace = [
        f"genre_preset.{preset_id}.world",
        f"genre_preset.{preset_id}.player",
        f"genre_preset.{preset_id}.physics_layers",
        "brief.project.viewport",
        "brief.project.controls",
        "brief.project.player_asset",
        "brief.animation_graphs",
    ]

    return {
        "production_meta": {
            "schema_version": PRODUCTION_SCHEMA_VERSION,
            "derived_at": datetime.now(timezone.utc).isoformat(),
            "brief_path": str(brief_path),
            "brief_meta": brief_meta,
            "genre_preset": preset_id,
            "preset_trace": preset_trace,
        },
        "production_doc": {
            "title": project.title,
            "slug": _slug(project.title, brief_path.stem),
            "genre": project.genre or preset.get("genre", "generic"),
            "dimension": project.dimension or "2d",
            "viewport": viewport,
            "world": world,
            "player": player,
            "camera": dict(project.camera) if project.camera else {},
            "physics_layers": dict(preset.get("physics_layers") or {}),
            "input_map": _build_input_map(project.controls),
            "scenes": _build_scenes(project, player_asset),
            "systems": systems,
            "animation_graphs": [
                {
                    "character_asset": g.character_asset,
                    "default_clip": g.default_clip,
                    "summary": g.summary,
                    "transitions": [
                        {
                            "from": e.from_clip,
                            "to": e.to_clip,
                            "then": e.then_clip or None,
                            "bidirectional": e.bidirectional,
                        }
                        for e in g.transitions
                    ],
                }
                for g in graphs
            ],
            "godot_tasks": godot_tasks,
            "validation": _build_validation(project, godot_tasks),
            "scaffold": {
                "main_scene": "scenes/main.tscn",
                "scripts_dir": "scripts",
                "autoloads": ["GameState"],
                "language": "csharp",
                "engine": "godot4-dotnet",
            },
        },
    }


def load_production(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("production file must be a JSON object")
    return data


def validate_production(data: dict[str, Any], *, brief_path: Path | None = None) -> list[str]:
    """Return list of validation errors (empty = OK)."""
    errors: list[str] = []

    meta = data.get("production_meta")
    if not isinstance(meta, dict):
        errors.append("missing production_meta object")
        meta = {}

    if meta.get("schema_version") != PRODUCTION_SCHEMA_VERSION:
        errors.append(f"production_meta.schema_version must be {PRODUCTION_SCHEMA_VERSION}")

    doc = data.get("production_doc")
    if not isinstance(doc, dict):
        errors.append("missing production_doc object")
        return errors

    for key in ("genre", "viewport", "scenes", "godot_tasks", "validation"):
        if key not in doc:
            errors.append(f"production_doc missing '{key}'")

    scenes = doc.get("scenes")
    if isinstance(scenes, list):
        if not any(isinstance(s, dict) and s.get("role") == "main" for s in scenes):
            errors.append("production_doc.scenes must include role=main")
    else:
        errors.append("production_doc.scenes must be a list")

    tasks = doc.get("godot_tasks")
    if isinstance(tasks, list):
        if not tasks:
            errors.append("production_doc.godot_tasks must not be empty")
        ids: set[str] = set()
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"godot_tasks[{i}] must be an object")
                continue
            task_id = task.get("id")
            if not task_id:
                errors.append(f"godot_tasks[{i}] missing id")
            elif task_id in ids:
                errors.append(f"duplicate godot_tasks id: {task_id}")
            else:
                ids.add(str(task_id))
            if not str(task.get("title", "")).strip():
                errors.append(f"godot_tasks[{i}] missing title")
            for dep in task.get("depends_on") or []:
                if dep not in ids and dep not in {t.get("id") for t in tasks[:i] if isinstance(t, dict)}:
                    pass  # deps may reference later tasks in same list — check all ids at end
        all_ids = {str(t.get("id")) for t in tasks if isinstance(t, dict) and t.get("id")}
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            for dep in task.get("depends_on") or []:
                if str(dep) not in all_ids:
                    errors.append(f"godot_tasks[{i}] depends_on unknown id: {dep}")
    else:
        errors.append("production_doc.godot_tasks must be a list")

    validation = doc.get("validation")
    if isinstance(validation, dict):
        ac = validation.get("acceptance_criteria")
        if not isinstance(ac, list) or not ac:
            errors.append("production_doc.validation.acceptance_criteria must be non-empty")
    else:
        errors.append("production_doc.validation must be an object")

    scaffold = doc.get("scaffold")
    if isinstance(scaffold, dict):
        if not scaffold.get("main_scene"):
            errors.append("production_doc.scaffold.main_scene required")
    else:
        errors.append("production_doc.scaffold must be an object")

    if brief_path is not None and brief_path.is_file():
        try:
            project, _assets, _graphs = load_brief_full(brief_path)
            if project.player_asset and doc.get("player", {}).get("asset"):
                if project.player_asset != doc["player"]["asset"]:
                    errors.append(
                        "production_doc.player.asset must match brief.project.player_asset"
                    )
            if project.viewport and doc.get("viewport"):
                for dim in ("width", "height"):
                    if dim in project.viewport and project.viewport[dim] != doc["viewport"].get(dim):
                        errors.append(f"production_doc.viewport.{dim} must match brief")
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            errors.append(f"could not cross-check brief: {exc}")

    return errors


def save_production(data: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path.resolve()


def default_delta_path(change_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", (change_id or "change").strip()).strip("-") or "change"
    return Path("..") / "plans" / "changes" / f"{safe}.production-delta.json"


def create_production_delta(
    *,
    change_id: str,
    user_intent: str,
    asset_tasks: list[str] | None = None,
    godot_tasks: list[str] | None = None,
    preserve: list[str] | None = None,
    do_not_touch: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """Build a Production Delta document (construction plan for one Change Request)."""
    cid = (change_id or "").strip()
    if not cid:
        raise ValueError("change_id is required")
    intent = (user_intent or "").strip()
    if not intent:
        raise ValueError("user_intent is required")
    gtasks = [str(t).strip() for t in (godot_tasks or []) if str(t).strip()]
    if not gtasks:
        # One placeholder task from intent so apply can create a progress-facing id
        gtasks = [f"Implement: {intent[:80]}"]
    return {
        "change_request": {
            "source": "user_feedback",
            "user_intent": intent,
            "design_delta": {},
        },
        "production_delta": {
            "change_id": cid,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "asset_tasks": [str(a).strip() for a in (asset_tasks or []) if str(a).strip()],
            "godot_tasks": gtasks,
            "preserve": list(preserve or ["existing accepted gameplay unless explicitly changed"]),
            "do_not_touch": list(do_not_touch or ["unrelated input mappings", "unrelated asset paths"]),
            "acceptance_criteria": [
                str(c).strip()
                for c in (acceptance_criteria or [f"User intent satisfied: {intent[:100]}"])
                if str(c).strip()
            ],
        },
    }


def apply_production_delta(production: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Merge Production Delta into production_doc (append godot_tasks + acceptance).

    Returns a new production dict (does not mutate input).
    """
    import copy

    out = copy.deepcopy(production)
    doc = out.setdefault("production_doc", {})
    if not isinstance(doc, dict):
        raise ValueError("production_doc must be an object")
    pd = delta.get("production_delta") if isinstance(delta.get("production_delta"), dict) else {}
    if not pd:
        raise ValueError("missing production_delta object")
    change_id = str(pd.get("change_id") or "change").strip()
    safe = re.sub(r"[^a-zA-Z0-9_]+", "_", change_id).strip("_")[:40] or "change"

    existing = doc.get("godot_tasks") if isinstance(doc.get("godot_tasks"), list) else []
    existing_ids = {
        str(t.get("id")) for t in existing if isinstance(t, dict) and t.get("id")
    }
    new_tasks: list[dict[str, Any]] = []
    for i, title in enumerate(pd.get("godot_tasks") or []):
        title_s = str(title).strip()
        if not title_s:
            continue
        tid = f"delta_{safe}_{i + 1}"
        n = 1
        while tid in existing_ids:
            n += 1
            tid = f"delta_{safe}_{i + 1}_{n}"
        existing_ids.add(tid)
        new_tasks.append(
            {
                "id": tid,
                "title": title_s,
                "status": "pending",
                "depends_on": [],
                "verify": list(pd.get("acceptance_criteria") or [])[:3] or [title_s],
                "source_change_id": change_id,
            }
        )
    doc["godot_tasks"] = list(existing) + new_tasks

    val = doc.setdefault("validation", {})
    if not isinstance(val, dict):
        val = {}
        doc["validation"] = val
    criteria = val.get("acceptance_criteria") if isinstance(val.get("acceptance_criteria"), list) else []
    for c in pd.get("acceptance_criteria") or []:
        cs = str(c).strip()
        if cs and cs not in criteria:
            criteria.append(cs)
    val["acceptance_criteria"] = criteria

    meta = out.setdefault("production_meta", {})
    if isinstance(meta, dict):
        applied = meta.setdefault("applied_deltas", [])
        if isinstance(applied, list):
            applied.append(
                {
                    "change_id": change_id,
                    "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "tasks_added": [t["id"] for t in new_tasks],
                    "asset_tasks": list(pd.get("asset_tasks") or []),
                }
            )
    return out
