"""Godot developer handoff — brief + assets-manifest contract for code agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brief import (
    AssetSpec,
    CharacterAnimationGraph,
    ProjectContext,
    animation_graph_to_dict,
    load_brief_full,
    resolve_animation_loop,
    resolve_animation_name,
)
from pipeline_manifest import rel_to_repo
from shared_context import asset_to_dict as _asset_to_dict
from shared_context import project_to_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent

BRIEF_CONTRACT_RULES = [
    "Read ONLY authoritative_sources files listed in this handoff.",
    "Do NOT use brainstorm session, host conversation memory, or unstated assumptions.",
    "If gameplay or asset usage is unclear, read brief.json — never invent requirements.",
    "Use runtime_bindings for res:// paths and clip names; do not guess output/ filenames.",
    "To change scope, edit brief.json and re-run pipeline plan — do not patch handoff alone.",
]


def _assets_manifest_path(brief_path: Path) -> Path:
    return (_REPO_ROOT / "output" / brief_path.stem / "assets-manifest.json").resolve()


def _load_assets_manifest(brief_path: Path) -> tuple[dict[str, Any] | None, Path | None]:
    path = _assets_manifest_path(brief_path)
    if not path.is_file():
        return None, None
    from assets_manifest import load_assets_manifest

    return load_assets_manifest(path), path


def _runtime_bindings(
    assets: list[AssetSpec],
    manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    manifest_assets = (manifest or {}).get("assets") or {}
    bindings: list[dict[str, Any]] = []
    for spec in assets:
        entry = manifest_assets.get(spec.name) if isinstance(manifest_assets, dict) else None
        brief_snap = (entry or {}).get("brief") if isinstance(entry, dict) else {}
        runtime = (entry or {}).get("runtime") if isinstance(entry, dict) else None
        clip = resolve_animation_name(spec) if spec.action.strip() else "idle"
        binding: dict[str, Any] = {
            "asset": spec.name,
            "type": spec.type.value,
            "usage": spec.usage or (brief_snap or {}).get("usage", ""),
            "usage_description": spec.usage_description or (brief_snap or {}).get("usage_description", ""),
            "display_size": (
                spec.display_size.to_dict()
                if not spec.display_size.is_empty()
                else (brief_snap or {}).get("display_size", "")
            ),
            "clip_name": clip,
            "loop": resolve_animation_loop(spec) if spec.action.strip() else None,
            "generate_method": (brief_snap or {}).get("generate_method"),
            "runtime": runtime,
            "gameplay_ready_path": _latest_gameplay_path(entry),
        }
        bindings.append(binding)
    return bindings


def _latest_gameplay_path(entry: dict[str, Any] | None) -> str | None:
    if not isinstance(entry, dict):
        return None
    for stage in reversed(entry.get("stages") or []):
        if not isinstance(stage, dict):
            continue
        if stage.get("role") == "gameplay_ready" and stage.get("path_repo"):
            return str(stage["path_repo"])
    return None


def _implementation_goals(
    project: ProjectContext,
    assets: list[AssetSpec],
    graphs: list[CharacterAnimationGraph],
) -> list[str]:
    goals: list[str] = []
    if (project.session_goal or "").strip():
        goals.append(f"Session goal: {project.session_goal.strip()}")
    if (project.gameplay_loop or "").strip():
        goals.append(f"Core loop: {project.gameplay_loop.strip()}")
    desc = (project.description or "").strip()
    if desc:
        goals.append(f"Product context: {desc}")
    if project.genre:
        goals.append(f"Genre/archetype: {project.genre}")
    if project.controls:
        actions = ", ".join(sorted(project.controls))
        goals.append(f"Wire InputMap actions from brief.controls: {actions}")
    if project.player_asset:
        goals.append(f"Player node uses asset '{project.player_asset}' and runtime_bindings")
    if project.viewport:
        goals.append(
            f"Design for viewport {project.viewport.get('width')}x{project.viewport.get('height')}"
        )
    if project.camera:
        goals.append(f"Camera: {project.camera}")
    if project.dimension == "2d":
        goals.append("2D Godot 4 .NET (C#) — extend scenes/scripts under res://")
    if project.art_direction:
        goals.append(f"Respect art direction in UI/layout choices: {project.art_direction}")

    has_video = any(a.action and a.animation_method == "video" for a in assets)
    has_character = any(a.type.value == "character" for a in assets)
    if has_character and has_video:
        goals.append(
            "Wire runtime_bindings SpriteFrames / clip_name into player states per animation_graphs"
        )
    for graph in graphs:
        if graph.summary:
            goals.append(f"Animation ({graph.character_asset}): {graph.summary}")
        elif graph.transitions:
            goals.append(
                f"Animation ({graph.character_asset}): implement transitions from brief animation_graphs"
            )
    if has_character:
        goals.append("Player input, collision, and camera as appropriate for the genre")

    goals.append("Use res:// paths from runtime_bindings only; do not call image/video APIs")
    goals.append("Run `python gamefactory.py godot validate --project <project>` after C# edits")
    return goals


def build_godot_dev_plan(
    brief_path: Path,
    *,
    project_path: Path,
    assemble_handoff_path: Path | None = None,
    assets_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Build implementation plan for godot-developer agent."""
    brief_path = brief_path.resolve()
    project_path = project_path.resolve()
    project, assets, graphs = load_brief_full(brief_path)

    manifest: dict[str, Any] | None = None
    manifest_file: Path | None = None
    if assets_manifest_path and assets_manifest_path.is_file():
        from assets_manifest import load_assets_manifest

        manifest = load_assets_manifest(assets_manifest_path.resolve())
        manifest_file = assets_manifest_path.resolve()
    else:
        manifest, manifest_file = _load_assets_manifest(brief_path)

    assemble_plan: dict[str, Any] = {}
    if assemble_handoff_path and assemble_handoff_path.is_file():
        data = json.loads(assemble_handoff_path.read_text(encoding="utf-8"))
        if isinstance(data.get("plan"), dict):
            assemble_plan = data["plan"]

    brief_data = json.loads(brief_path.read_text(encoding="utf-8"))
    brief_meta = brief_data.get("brief_meta") if isinstance(brief_data.get("brief_meta"), dict) else None

    authoritative: dict[str, str | None] = {
        "brief": rel_to_repo(brief_path),
        "assets_manifest": rel_to_repo(manifest_file) if manifest_file else None,
        "godot_project": rel_to_repo(project_path),
    }

    return {
        "project_path": rel_to_repo(project_path),
        "brief_path": rel_to_repo(brief_path),
        "language": "csharp",
        "engine": "godot4-dotnet",
        "main_scene": str(assemble_plan.get("main_scene", "scenes/main.tscn")),
        "scripts_dir": "scripts",
        "authoritative_sources": authoritative,
        "contract_rules": list(BRIEF_CONTRACT_RULES),
        "brief_meta": brief_meta,
        "product": project_to_dict(project),
        "assets": [_asset_to_dict(a) for a in assets],
        "animation_graphs": [animation_graph_to_dict(g) for g in graphs],
        "runtime_bindings": _runtime_bindings(assets, manifest),
        "assemble": {
            "character_asset": assemble_plan.get("character_asset"),
            "animations": assemble_plan.get("animations") or [],
            "backgrounds": assemble_plan.get("backgrounds") or [],
            "idle_still": assemble_plan.get("idle_still"),
        },
        "implementation_goals": _implementation_goals(project, assets, graphs),
        "constraints": [
            "C# only — no GDScript",
            "Edit files under the Godot project; do not regenerate PNG/MP4",
            "Preserve godot-assembler resource paths unless refactoring deliberately",
            "Do not read brainstorm session — brief.json is the only product spec",
        ],
    }
