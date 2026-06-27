"""Inline brief payloads for unit tests — no tracked JSON fixtures on disk."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

EXAMPLE_BRIEF = Path(__file__).resolve().parent.parent / "resources" / "asset-brief.example.json"

SMOKE_BRIEF: dict[str, Any] = {
    "project": {
        "title": "E2E Smoke",
        "description": "Minimal single-character smoke test.",
        "art_direction": "flat 2D sprite",
        "dimension": "2d",
    },
    "assets": [
        {
            "name": "slime_hero",
            "type": "character",
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
    },
    "assets": [
        {
            "name": "knight",
            "type": "character",
            "description": "armored knight",
        },
        {
            "name": "knight_walk",
            "type": "character",
            "description": "knight walk",
            "reference_asset": "knight",
            "animation_method": "video",
            "action": "walking right",
            "duration_seconds": 4,
            "sprite_frames": 8,
        },
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
