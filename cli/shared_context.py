"""Shared context passed to every role (orchestrator, prompt-crafter, etc.).

Roles use different skills but receive the same project + asset facts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brief import (
    ANIMATION_METHOD_VIDEO,
    AssetSpec,
    AssetType,
    ProjectContext,
    find_asset,
    load_brief,
    resolve_generate_method,
)


def project_to_dict(project: ProjectContext) -> dict[str, Any]:
    data: dict[str, Any] = {
        "title": project.title,
        "description": project.description,
        "art_direction": project.art_direction,
        "dimension": project.dimension,
        "genre": project.genre,
        "gameplay_loop": project.gameplay_loop,
        "session_goal": project.session_goal,
        "player_asset": project.player_asset,
        "controls": project.controls,
        "viewport": project.viewport,
    }
    if project.camera:
        data["camera"] = project.camera
    if project.visual_reference:
        data["visual_reference"] = project.visual_reference
    if project.hud:
        data["hud"] = project.hud
    return data


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
    if spec.animation_name:
        data["animation_name"] = spec.animation_name
    if spec.animation_loop is not None:
        data["animation_loop"] = spec.animation_loop
    if spec.usage:
        data["usage"] = spec.usage
    if spec.usage_description:
        data["usage_description"] = spec.usage_description
    method = spec.generate_method.strip().lower() or resolve_generate_method(spec)
    if method:
        data["generate_method"] = method
    if spec.parallax_order is not None:
        data["parallax_order"] = spec.parallax_order
    if spec.scroll_factor is not None:
        data["scroll_factor"] = spec.scroll_factor
    if spec.audio_loop is not None:
        data["audio_loop"] = spec.audio_loop
    if spec.type == AssetType.AUDIO and spec.duration_seconds > 0:
        data["duration_seconds"] = spec.duration_seconds
    if spec.sprite_frames > 0:
        data["sprite_frames"] = spec.sprite_frames
    if spec.video_model:
        data["video_model"] = spec.video_model
    if spec.video_resolution:
        data["video_resolution"] = spec.video_resolution
    if spec.video_ratio:
        data["video_ratio"] = spec.video_ratio
    if spec.generate_audio is not None:
        data["generate_audio"] = spec.generate_audio
    if spec.watermark is not None:
        data["watermark"] = spec.watermark
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
