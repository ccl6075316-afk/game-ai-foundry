"""Inline brief payloads for unit tests — no tracked JSON fixtures on disk."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

EXAMPLE_BRIEF = Path(__file__).resolve().parent.parent / "resources" / "asset-brief.example.json"

# Minimal gameplay contract fields required by validate_brief_for_export.
GAMEPLAY_PROJECT: dict[str, Any] = {
    "genre": "2d_platformer",
    "gameplay_loop": "Move, interact, repeat until session goal is met.",
    "session_goal": "Smoke test: verify pipeline and Godot assemble only.",
    "player_asset": "slime_hero",
    "controls": {
        "move_left": ["A", "Left"],
        "move_right": ["D", "Right"],
    },
    "viewport": {"width": 1280, "height": 720},
    "camera": {"mode": "follow_player"},
}

SMOKE_BRIEF: dict[str, Any] = {
    "project": {
        "title": "E2E Smoke",
        "description": "Minimal single-character smoke test.",
        "art_direction": "flat 2D sprite",
        "dimension": "2d",
        **GAMEPLAY_PROJECT,
    },
    "assets": [
        {
            "name": "slime_hero",
            "type": "character",
            "usage": "player_idle",
            "usage_description": "Single hero for smoke E2E",
            "generate_method": "image",
            "description": "cute blue slime blob, standing pose, facing right",
            "display_size": "128x128 px",
        }
    ],
}

MINIMAL_VIDEO_BRIEF: dict[str, Any] = {
    "project": {
        "title": "Runner Test",
        "description": "Two-asset brief for runner skip tests.",
        "art_direction": "2d",
        "dimension": "2d",
        "genre": "endless_runner",
        "gameplay_loop": "Run to the right; walk cycle loops while moving.",
        "session_goal": "Pipeline test: generate knight still and walk animation.",
        "player_asset": "knight",
        "controls": {
            "move_left": ["A", "Left"],
            "move_right": ["D", "Right"],
        },
        "viewport": {"width": 960, "height": 540},
    },
    "assets": [
        {
            "name": "knight",
            "type": "character",
            "usage": "reference_still",
            "usage_description": "Reference still for walk i2v",
            "generate_method": "image",
            "description": "armored knight",
            "display_size": "128x128 px",
        },
        {
            "name": "knight_walk",
            "type": "character",
            "usage": "player_locomotion",
            "usage_description": "Walk animation for runner tests",
            "generate_method": "video",
            "description": "knight walk",
            "display_size": "128x128 px",
            "reference_asset": "knight",
            "animation_method": "video",
            "action": "walking right",
            "duration_seconds": 4,
            "sprite_frames": 8,
        },
    ],
    "animation_graphs": [
        {
            "character_asset": "knight",
            "default_clip": "idle",
            "transitions": [{"from": "idle", "to": "walk", "bidirectional": True}],
        }
    ],
}


def write_brief(data: dict[str, Any], *, prefix: str = "brief-") -> Path:
    """Write brief dict to a temp file (local only, never committed)."""
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix=prefix,
        delete=False,
        encoding="utf-8",
    )
    json.dump(data, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
    handle.close()
    return Path(handle.name)
