"""Build playtest command JSON from brief / design doc (godogen-style harness)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from brief import load_brief_full

PLAYTEST_SCHEMA_VERSION = 1

# Locomotion: hold key; discrete actions: short tap
_HOLD_ACTIONS = frozenset({"move_left", "move_right", "move_up", "move_down"})
_TAP_MS = 250
_HOLD_MS = 1200


def _slug_from_brief(brief_path: Path, project) -> str:
    title = (project.title or brief_path.stem).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or brief_path.stem.replace(".json", "")


def _acceptance_from_brief(project) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for source, text in (
        ("brief.project.session_goal", project.session_goal),
        ("brief.project.gameplay_loop", project.gameplay_loop),
        ("brief.project.description", project.description),
    ):
        if text and str(text).strip():
            out.append({"source": source, "criterion": str(text).strip()})
    if not out:
        out.append(
            {
                "source": "default",
                "criterion": "Main scene loads; player sprite visible on screen.",
            }
        )
    return out


def _ordered_control_actions(controls: dict[str, list[str]]) -> list[str]:
    """Stable order: move_right before move_left (godogen-style exercise flow)."""
    names = [k for k in controls if str(k).strip()]
    priority = {
        "move_right": 0,
        "move_left": 1,
        "jump": 2,
        "attack": 3,
    }
    return sorted(names, key=lambda a: (priority.get(a, 50), a))


def build_playtest_from_brief(brief_path: Path) -> dict[str, Any]:
    """
    Derive a minimal playtest script from frozen brief (Design + Production embedded).

    Mirrors godogen per-task harness: load scene → exercise controls → capture frames.
    """
    project, assets, _graphs = load_brief_full(brief_path)
    controls = dict(project.controls or {})
    actions = _ordered_control_actions(controls)

    steps: list[dict[str, Any]] = [
        {"op": "wait_frames", "frames": 30, "note": "scene settle"},
        {"op": "screenshot", "name": "boot"},
    ]

    for action in actions:
        duration = _HOLD_MS if action in _HOLD_ACTIONS else _TAP_MS
        steps.append({"op": "press", "action": action, "duration_ms": duration})
        steps.append({"op": "wait_frames", "frames": 15})
        steps.append({"op": "screenshot", "name": f"after_{action}"})

    visual_checks: list[dict[str, str]] = [
        {
            "screenshot": "boot",
            "source": "brief.project.description",
            "criterion": f"Game scene visible matching: {project.description or project.title}",
        },
    ]
    if "move_right" in actions:
        visual_checks.append(
            {
                "screenshot": "after_move_right",
                "source": "brief.project.gameplay_loop",
                "criterion": "Player character appears to have moved right compared to boot frame.",
            }
        )
    if "attack" in actions:
        visual_checks.append(
            {
                "screenshot": "after_attack",
                "source": "brief.project.session_goal",
                "criterion": "Attack action triggered visible change (pose, effect, or animation).",
            }
        )

    return {
        "schema_version": PLAYTEST_SCHEMA_VERSION,
        "playtest_id": f"{_slug_from_brief(brief_path, project)}-smoke",
        "brief_path": str(brief_path.resolve()),
        "design_sources": {
            "title": project.title,
            "gameplay_loop": project.gameplay_loop,
            "session_goal": project.session_goal,
            "genre": project.genre,
        },
        "acceptance_criteria": _acceptance_from_brief(project),
        "input_actions": actions,
        "steps": steps,
        "visual_checks": visual_checks,
        "notes": (
            "Generated from brief.controls + session_goal. "
            "Aligns with godogen task harness (exercise feature + screenshots). "
            "Refine with `test plan --craft` or edit steps manually."
        ),
    }


def save_playtest_plan(plan: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path.resolve()


def load_playtest_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("playtest plan must be a JSON object")
    if "steps" not in data or not isinstance(data["steps"], list):
        raise ValueError("playtest plan missing steps[]")
    return data
