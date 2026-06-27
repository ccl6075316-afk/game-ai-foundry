"""Godot developer handoff — product brief + assembled project for code agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brief import AssetSpec, ProjectContext, load_brief
from pipeline_manifest import rel_to_repo
from shared_context import asset_to_dict, project_to_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _implementation_goals(project: ProjectContext, assets: list[AssetSpec]) -> list[str]:
    goals: list[str] = []
    desc = (project.description or "").strip()
    if desc:
        goals.append(f"Implement gameplay matching product description: {desc}")
    if project.dimension == "2d":
        goals.append("2D Godot 4 .NET (C#) — extend scenes/scripts under res://")
    if project.art_direction:
        goals.append(f"Respect art direction in UI/layout choices: {project.art_direction}")

    has_video = any(a.action and a.animation_method == "video" for a in assets)
    has_character = any(a.type.value == "character" for a in assets)
    if has_character and has_video:
        goals.append("Wire assembled SpriteFrames / idle still into player movement and animation states")
    if has_character:
        goals.append("Player input, collision, and camera as appropriate for the genre")

    goals.append("Use res:// assets produced by godot-assembler; do not call image/video APIs")
    goals.append("Run `python gamefactory.py godot validate --project <project>` after C# edits")
    return goals


def build_godot_dev_plan(
    brief_path: Path,
    *,
    project_path: Path,
    assemble_handoff_path: Path | None = None,
) -> dict[str, Any]:
    """Build implementation plan for godot-developer agent."""
    brief_path = brief_path.resolve()
    project_path = project_path.resolve()
    project, assets = load_brief(brief_path)

    assemble_plan: dict[str, Any] = {}
    if assemble_handoff_path and assemble_handoff_path.is_file():
        data = json.loads(assemble_handoff_path.read_text(encoding="utf-8"))
        if isinstance(data.get("plan"), dict):
            assemble_plan = data["plan"]

    return {
        "project_path": rel_to_repo(project_path),
        "brief_path": rel_to_repo(brief_path),
        "language": "csharp",
        "engine": "godot4-dotnet",
        "main_scene": str(assemble_plan.get("main_scene", "scenes/main.tscn")),
        "scripts_dir": "scripts",
        "product": project_to_dict(project),
        "assets": [asset_to_dict(a) for a in assets],
        "assemble": {
            "animations": assemble_plan.get("animations") or [],
            "backgrounds": assemble_plan.get("backgrounds") or [],
            "idle_still": assemble_plan.get("idle_still"),
        },
        "implementation_goals": _implementation_goals(project, assets),
        "constraints": [
            "C# only — no GDScript",
            "Edit files under the Godot project; do not regenerate PNG/MP4",
            "Preserve godot-assembler resource paths unless refactoring deliberately",
        ],
    }
