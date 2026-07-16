"""Per-task playtest harness plans from production.godot_tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playtest_plan import PLAYTEST_SCHEMA_VERSION, build_playtest_from_brief, save_playtest_plan
from production import load_production


def _hard_asserts(task_id: str, input_actions: list[str]) -> list[dict[str, Any]]:
    """Structural asserts — fail the harness without vision LLM."""
    asserts: list[dict[str, Any]] = [
        {"op": "assert_node", "path": "/root/GameState", "note": "autoload"},
        {"op": "assert_node", "path": "/root/Main", "note": "main scene root"},
    ]
    if task_id in {"input_map", "player_controller", "session_goal", "animation_states"}:
        for action in input_actions:
            asserts.append({"op": "assert_action", "action": action})
    if task_id in {"player_controller", "camera", "collectibles", "session_goal"}:
        asserts.append({"op": "assert_node", "path": "/root/Main/Player"})
    if task_id == "camera":
        asserts.append({"op": "assert_node", "path": "/root/Main/Player/Camera2D"})
    if task_id in {"player_controller", "session_goal", "collectibles"}:
        asserts.append(
            {
                "op": "assert_property",
                "path": "/root/GameState",
                "property": "Health",
                "gte": 1,
                "note": "player still alive after smoke",
            }
        )
    return asserts


def _steps_for_task(task_id: str, input_actions: list[str]) -> list[dict[str, Any]]:
    base: list[dict[str, Any]] = [
        {"op": "wait_frames", "frames": 30, "note": "scene settle"},
        {"op": "screenshot", "name": "boot"},
    ]
    base.extend(_hard_asserts(task_id, input_actions))
    if task_id == "input_map":
        return base

    locomotion = [a for a in input_actions if a in {"move_right", "move_left", "move_up", "move_down"}]
    discrete = [a for a in input_actions if a not in locomotion]

    if task_id in {"player_controller", "animation_states", "camera", "session_goal"}:
        for action in locomotion or ["move_right"]:
            base.append({"op": "press", "action": action, "duration_ms": 1200 if "move" in action else 250})
            base.append({"op": "wait_frames", "frames": 15})
            base.append({"op": "screenshot", "name": f"after_{action}"})
    if task_id in {"player_controller", "session_goal"} and "attack" in discrete:
        base.append({"op": "press", "action": "attack", "duration_ms": 250})
        base.append({"op": "wait_frames", "frames": 15})
        base.append({"op": "screenshot", "name": "after_attack"})
    if task_id == "collectibles":
        for action in locomotion[:1] or ["move_right"]:
            base.append({"op": "press", "action": action, "duration_ms": 1500})
        base.append({"op": "screenshot", "name": "after_move_collect"})

    return base


def build_playtest_for_task(
    brief_path: Path,
    production_path: Path,
    task_id: str,
) -> dict[str, Any]:
    """Harness plan scoped to one production.godot_tasks entry."""
    prod = load_production(production_path)
    doc = prod.get("production_doc") or {}
    task = next(
        (t for t in (doc.get("godot_tasks") or []) if isinstance(t, dict) and t.get("id") == task_id),
        None,
    )
    if task is None:
        raise ValueError(f"godot_task not found in production: {task_id}")

    plan = build_playtest_from_brief(brief_path, production_path=production_path)
    slug = str(doc.get("slug") or brief_path.stem)
    plan["playtest_id"] = f"{slug}-task-{task_id}"
    plan["task_id"] = task_id
    plan["production_path"] = str(production_path.resolve())
    verify = [str(v).strip() for v in (task.get("verify") or []) if str(v).strip()]
    plan["acceptance_criteria"] = [
        {"source": f"production.godot_tasks.{task_id}", "criterion": v} for v in verify
    ] or plan.get("acceptance_criteria", [])
    plan["steps"] = _steps_for_task(task_id, plan.get("input_actions") or [])
    plan["visual_checks"] = [
        {
            "screenshot": "boot",
            "source": f"production.godot_tasks.{task_id}",
            "criterion": verify[0] if verify else f"Task {task_id} smoke frame",
        }
    ]
    plan["schema_version"] = PLAYTEST_SCHEMA_VERSION
    plan["notes"] = f"Per-task harness for production.godot_tasks.{task_id}"
    return plan


def default_task_playtest_path(brief_path: Path, task_id: str) -> Path:
    stem = brief_path.stem.replace(".json", "")
    return Path("..") / "plans" / f"playtest_{stem}_{task_id}.json"


def save_task_playtest_plan(plan: dict[str, Any], output_path: Path) -> Path:
    return save_playtest_plan(plan, output_path)
