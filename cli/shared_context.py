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
from display_size import display_size_from_viewport


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
        vp = project.viewport or {}
        w, h = vp.get("width"), vp.get("height")
        size_hint = f"{w}x{h}" if w and h else "viewport"
        data["visual_reference_usage"] = (
            "North-star full-screen mock at project viewport resolution "
            f"({size_hint}). Align palette, line weight, and mood with "
            "art_direction — not pixel-perfect. Do NOT use as img2img input "
            "for character/icon sprites; those use assets[].display_size on white studio."
        )
    if project.hud:
        data["hud"] = project.hud
    if project.art_tokens:
        data["art_tokens"] = project.art_tokens
    if project.view:
        data["view"] = project.view
    return data


def format_art_tokens_for_prompt(tokens: dict[str, Any]) -> str:
    """Compact one-line summary of known art_tokens keys for skill prompts."""
    parts: list[str] = []
    line = tokens.get("line")
    if isinstance(line, str) and line.strip():
        parts.append(f"line: {line.strip()}")
    palette = tokens.get("palette")
    if isinstance(palette, str) and palette.strip():
        parts.append(f"palette: {palette.strip()}")
    elif isinstance(palette, list):
        items = [str(item).strip() for item in palette if str(item).strip()]
        if items:
            parts.append("palette: " + ", ".join(items))
    forbid = tokens.get("forbid")
    if isinstance(forbid, list):
        items = [str(item).strip() for item in forbid if str(item).strip()]
        if items:
            parts.append("forbid: " + "; ".join(items))
    silhouette = tokens.get("silhouette")
    if isinstance(silhouette, str) and silhouette.strip():
        parts.append(f"silhouette: {silhouette.strip()}")
    return "; ".join(parts)


def asset_to_dict(spec: AssetSpec) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": spec.name,
        "type": spec.type.value,
        "description": spec.description,
        "display_size": spec.display_size.to_dict() if not spec.display_size.is_empty() else None,
        "aspect_ratio": spec.aspect_ratio,
    }
    if spec.id:
        data["id"] = spec.id
    if spec.items:
        data["items"] = [it.to_brief() for it in spec.items]
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
    if spec.style_group:
        data["style_group"] = spec.style_group
    if spec.style_anchor_kind:
        data["style_anchor_kind"] = spec.style_anchor_kind
    if spec.style_anchor:
        data["style_anchor"] = spec.style_anchor
    if spec.identity_anchor:
        data["identity_anchor"] = spec.identity_anchor
    if spec.use_style_img2img is not None:
        data["use_style_img2img"] = spec.use_style_img2img
    if spec.generate_tier:
        data["generate_tier"] = spec.generate_tier
    if spec.content_class:
        data["content_class"] = spec.content_class
    if spec.states:
        data["states"] = list(spec.states)
    if spec.state:
        data["state"] = spec.state
    return data


def build_role_context(
    project: ProjectContext,
    spec: AssetSpec,
    *,
    kit_item: str | None = None,
    kit_item_slug: str | None = None,
    kit_item_id: str | None = None,
    kit_item_usage: str | None = None,
    kit_item_usage_description: str | None = None,
) -> dict[str, Any]:
    """Canonical payload every role receives."""
    asset = asset_to_dict(spec)
    if kit_item is not None:
        usage = (kit_item_usage or "").strip() or spec.usage
        usage_desc = (kit_item_usage_description or "").strip() or spec.usage_description
        asset = {
            **asset,
            "kit_item": kit_item,
            "kit_item_id": kit_item_id or kit_item_slug or "",
            "kit_item_slug": kit_item_slug or "",
            "description": (
                f"Single game icon only: {kit_item}. "
                "Centered, solid white background, no other objects, no grid sheet."
            ),
            "items": [kit_item],
            "usage": usage,
            "usage_description": usage_desc,
        }
        # Drop legacy grid cue so crafter does not emit multi-cell sheets.
        asset.pop("grid", None)
    return {
        "project": project_to_dict(project),
        "asset": asset,
    }


def build_visual_target_context(project: ProjectContext, variant: dict[str, str]) -> dict[str, Any]:
    """Context for visual_target craft (project-level, no asset row)."""
    size = display_size_from_viewport(project.viewport).to_api_string()
    player = (project.player_asset or "").strip() or "player character"
    hud = project.hud if isinstance(project.hud, list) else []
    camera = project.camera if isinstance(project.camera, dict) else {}
    return {
        "project": project_to_dict(project),
        "visual_target": {
            "variant_id": variant["id"],
            "variant_label": variant["label"],
            "variant_focus": variant["focus"],
            "target_image_size": size,
            "player_focus": player,
            "camera": camera,
            "hud": hud,
            "readability_checklist": [
                f"Viewer must instantly recognize '{player}' as the player-controlled focus",
                "This frame must show one concrete beat from gameplay_loop / variant_focus",
                "Environment must be readable as an in-game space, not a poster backdrop",
                "Match art_direction locks; do not invent a new art style",
            ],
            "usage": (
                "Full viewport gameplay mock; becomes project.visual_reference after user pick. "
                "Not a sprite sheet or character isolate. "
                "Fill structured JSON fields; Python assembles the image prompt."
            ),
        },
    }


def load_role_context(brief_path: Path, asset_name: str) -> dict[str, Any]:
    project, assets = load_brief(brief_path)
    spec = find_asset(assets, asset_name)
    return build_role_context(project, spec)


def dump_role_context(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2)
