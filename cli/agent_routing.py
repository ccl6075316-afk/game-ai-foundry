"""Agent role → executor / Hermes skill package resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roles import ALL_ROLES, GODOT_ASSEMBLER_ROLE

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXAMPLE_AGENTS = _REPO_ROOT / "resources" / "agents.example.json"

VALID_EXECUTORS = frozenset({"pipeline", "hermes", "cursor", "codex"})

ROLE_TO_HERMES_PACKAGE: dict[str, str] = {
    "orchestrator": "game-factory-orchestrator",
    "prompt-crafter": "game-factory-prompt-crafter",
    "image-generator": "game-factory-image-generator",
    "video-generator": "game-factory-video-generator",
    "godot-assembler": "game-factory-godot-assembler",
    "godot-developer": "game-factory-godot-developer",
}

DEFAULT_AGENTS: dict[str, dict[str, str]] = {
    "orchestrator": {"executor": "hermes", "skill": "game-factory-orchestrator"},
    "prompt-crafter": {"executor": "hermes", "skill": "game-factory-prompt-crafter"},
    "image-generator": {"executor": "pipeline", "skill": "game-factory-image-generator"},
    "video-generator": {"executor": "pipeline", "skill": "game-factory-video-generator"},
    "godot-assembler": {"executor": "pipeline", "skill": "game-factory-godot-assembler"},
    "godot-developer": {"executor": "codex", "skill": "game-factory-godot-developer"},
}


def _load_example_agents() -> dict[str, Any]:
    if not _EXAMPLE_AGENTS.is_file():
        return {"agents": DEFAULT_AGENTS}
    try:
        data = json.loads(_EXAMPLE_AGENTS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"agents": DEFAULT_AGENTS}
    return data if isinstance(data, dict) else {"agents": DEFAULT_AGENTS}


def resolve_agent(role: str, config: dict[str, Any] | None = None) -> dict[str, str]:
    """Merge config.agents[role] over defaults."""
    if role not in ALL_ROLES:
        raise ValueError(f"Unknown role '{role}'. Known: {', '.join(ALL_ROLES)}")

    defaults = dict(DEFAULT_AGENTS.get(role, {}))
    cfg = config or {}
    agents_block = cfg.get("agents", {})
    if not isinstance(agents_block, dict):
        agents_block = {}

    role_cfg = agents_block.get(role, {})
    if not isinstance(role_cfg, dict):
        role_cfg = {}

    executor = str(role_cfg.get("executor") or defaults.get("executor") or "pipeline")
    if executor not in VALID_EXECUTORS:
        executor = defaults.get("executor", "pipeline")

    skill = str(
        role_cfg.get("skill")
        or defaults.get("skill")
        or ROLE_TO_HERMES_PACKAGE.get(role, "")
    )

    return {
        "role": role,
        "executor": executor,
        "skill": skill,
        "skills_dir": f"resources/skills/{role}",
    }


def all_agents(config: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    return {role: resolve_agent(role, config) for role in ALL_ROLES}


def default_godot_executor() -> str:
    return resolve_agent(GODOT_ASSEMBLER_ROLE, {})["executor"]
