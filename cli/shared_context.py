"""Shared context passed to every role (orchestrator, prompt-crafter, etc.).

Roles use different skills but receive the same project + asset facts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brief import AssetSpec, ProjectContext, find_asset, load_brief


def project_to_dict(project: ProjectContext) -> dict[str, Any]:
    return {
        "title": project.title,
        "description": project.description,
        "art_direction": project.art_direction,
        "dimension": project.dimension,
    }


def asset_to_dict(spec: AssetSpec) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": spec.name,
        "type": spec.type.value,
        "description": spec.description,
        "display_size": spec.display_size,
        "aspect_ratio": spec.aspect_ratio,
    }
    if spec.items:
        data["items"] = spec.items
        data["grid"] = spec.grid
    if spec.reference_asset:
        data["reference_asset"] = spec.reference_asset
    if spec.action:
        data["action"] = spec.action
        data["animation_method"] = spec.animation_method
        data["duration_seconds"] = spec.duration_seconds
    return data


def build_role_context(project: ProjectContext, spec: AssetSpec) -> dict[str, Any]:
    """Canonical payload every role receives."""
    return {
        "project": project_to_dict(project),
        "asset": asset_to_dict(spec),
    }


def load_role_context(brief_path: Path, asset_name: str) -> dict[str, Any]:
    project, assets = load_brief(brief_path)
    spec = find_asset(assets, asset_name)
    return build_role_context(project, spec)


def dump_role_context(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2)
