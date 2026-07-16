"""Genre presets — default engineering values for production derive."""

from __future__ import annotations

from typing import Any

GENRE_PRESETS: dict[str, dict[str, Any]] = {
    "2d_platformer_v1": {
        "genre": "2d_platformer",
        "world": {
            "tile_size": 16,
            "gravity": 980,
            "ground_y": 600,
            "level_length": 2400,
        },
        "player": {
            "move_speed": 180,
            "jump_velocity": -420,
            "health": 3,
            "hitbox": {"width": 28, "height": 44},
            "anchor": "bottom_center",
        },
        "physics_layers": {
            "player": 1,
            "world": 2,
            "enemy": 4,
            "pickup": 8,
            "hazard": 16,
        },
    },
    "top_down_v1": {
        "genre": "top_down",
        "world": {
            "tile_size": 16,
            "gravity": 0,
        },
        "player": {
            "move_speed": 200,
            "health": 3,
            "hitbox": {"width": 24, "height": 24},
            "anchor": "center",
        },
        "physics_layers": {
            "player": 1,
            "world": 2,
            "enemy": 4,
            "pickup": 8,
        },
    },
    "default_v1": {
        "genre": "generic",
        "world": {"gravity": 980},
        "player": {
            "move_speed": 150,
            "health": 1,
            "hitbox": {"width": 32, "height": 32},
            "anchor": "bottom_center",
        },
        "physics_layers": {
            "player": 1,
            "world": 2,
        },
    },
}

_GENRE_TO_PRESET: dict[str, str] = {
    "2d_platformer": "2d_platformer_v1",
    "side_scroller": "2d_platformer_v1",
    "endless_runner": "2d_platformer_v1",
    "top_down": "top_down_v1",
    "shooter": "top_down_v1",
    "rpg": "top_down_v1",
}


def resolve_preset_id(genre: str) -> str:
    key = (genre or "").strip().lower()
    return _GENRE_TO_PRESET.get(key, "default_v1")


def get_genre_preset(genre: str) -> tuple[str, dict[str, Any]]:
    """Return (preset_id, preset dict)."""
    preset_id = resolve_preset_id(genre)
    return preset_id, dict(GENRE_PRESETS[preset_id])
