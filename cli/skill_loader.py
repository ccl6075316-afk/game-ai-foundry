"""Load role-specific skill markdown (orchestrator vs prompt-crafter, etc.)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brief import PLAYER_USAGES
from roles import (
    GODOT_ASSEMBLER_ROLE,
    GODOT_DEVELOPER_ROLE,
    IMAGE_GENERATOR_ROLE,
    ORCHESTRATOR_ROLE,
    PROMPT_CRAFTER_ROLE,
    TESTER_ROLE,
    VIDEO_GENERATOR_ROLE,
)

_SKILLS_ROOT = Path(__file__).resolve().parent.parent / "resources" / "skills"

ROLE_SKILLS: dict[str, tuple[str, ...]] = {
    ORCHESTRATOR_ROLE: ("pipeline", "pipeline-schedule", "matting", "matting-video"),
    PROMPT_CRAFTER_ROLE: ("asset-planner", "asset-gen"),
    IMAGE_GENERATOR_ROLE: ("generate",),
    VIDEO_GENERATOR_ROLE: ("generate",),
    GODOT_ASSEMBLER_ROLE: ("assemble", "import-sprites"),
    GODOT_DEVELOPER_ROLE: ("implement", "vendor-godot"),
    TESTER_ROLE: ("playtest", "vision-analyze", "playtest-schema"),
}

_PROP_CONTENT_CLASSES = frozenset(
    {
        "prop_static",
        "prop_interactable",
        "prop_stateful",
        "weapon",
        "tool",
        "decor",
    }
)
_TILE_CONTENT_CLASSES = frozenset({"floor_tile", "wall_tile"})
_BACKDROP_CONTENT_CLASSES = frozenset({"backdrop_sparse", "backdrop_full"})


def skills_root() -> Path:
    return _SKILLS_ROOT


def role_skills_dir(role: str) -> Path:
    if role not in ROLE_SKILLS:
        raise ValueError(f"Unknown role '{role}'. Known: {', '.join(ROLE_SKILLS)}")
    return _SKILLS_ROOT / role


def load_role_skill(role: str, name: str) -> str:
    path = role_skills_dir(role) / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Skill not found: {path}")
    return path.read_text(encoding="utf-8")


def load_role_skills(role: str) -> str:
    names = ROLE_SKILLS[role]
    return "\n\n---\n\n".join(load_role_skill(role, n) for n in names)


def _spec_field(spec: Any, key: str, default: str = "") -> str:
    if isinstance(spec, dict):
        raw = spec.get(key, default)
    else:
        raw = getattr(spec, key, default)
    if raw is None:
        return ""
    if hasattr(raw, "value"):
        return str(raw.value).strip()
    return str(raw).strip()


def resolve_class_skill_name(spec: Any) -> str:
    """Map asset spec to prompt-crafter class skill stem (without .md)."""
    content_class = _spec_field(spec, "content_class").lower()
    asset_type = _spec_field(spec, "type").lower()
    usage = _spec_field(spec, "usage").lower()

    if content_class in _TILE_CONTENT_CLASSES:
        return "class-tiles"
    if content_class in _BACKDROP_CONTENT_CLASSES:
        return "class-backdrops"
    if content_class in _PROP_CONTENT_CLASSES:
        return "class-props"

    if usage == "ui_element" or asset_type == "icon_kit":
        return "class-ui"
    if usage == "tile_texture":
        return "class-tiles"
    if asset_type == "background":
        return "class-backdrops"
    if asset_type == "character" or usage in PLAYER_USAGES:
        return "class-character"
    return "class-props"


def load_prompt_skills_for_asset(spec: Any, project: Any = None) -> str:
    """Load shared + planner + content-class skill markdown for one asset."""
    del project  # reserved for future project-scoped skill snippets
    parts = [
        load_role_skill(PROMPT_CRAFTER_ROLE, "shared-locks"),
        load_role_skill(PROMPT_CRAFTER_ROLE, "asset-planner"),
        load_role_skill(PROMPT_CRAFTER_ROLE, resolve_class_skill_name(spec)),
    ]
    return "\n\n---\n\n".join(parts)
