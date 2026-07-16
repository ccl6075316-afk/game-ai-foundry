"""Load role-specific skill markdown (orchestrator vs prompt-crafter, etc.)."""

from __future__ import annotations

from pathlib import Path

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
