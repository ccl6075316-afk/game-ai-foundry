"""Project brief types — shared input for all roles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

ANIMATION_METHOD_VIDEO = "video"
ANIMATION_METHOD_IMG2IMG = "img2img"
FORBIDDEN_ANIMATION_METHODS = frozenset({"spritesheet", "sheet", "grid_actions"})


class AssetType(str, Enum):
    CHARACTER = "character"
    ICON_KIT = "icon_kit"
    TEXTURE = "texture"
    BACKGROUND = "background"
    CHARACTER_POSE = "character_pose"


@dataclass
class ProjectContext:
    title: str = ""
    description: str = ""
    art_direction: str = ""
    dimension: str = "2d"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectContext:
        return cls(
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            art_direction=str(data.get("art_direction", "")),
            dimension=str(data.get("dimension", "2d")),
        )


@dataclass
class AssetSpec:
    name: str
    type: AssetType
    description: str = ""
    items: list[str] = field(default_factory=list)
    grid: str = "2x2"
    aspect_ratio: str = "1:1"
    display_size: str = ""
    action: str = ""
    animation_method: str = ANIMATION_METHOD_VIDEO
    reference_asset: str = ""
    duration_seconds: float = 2.0
    sprite_frames: int = 0
    video_model: str = ""
    video_resolution: str = ""
    video_ratio: str = ""
    generate_audio: bool | None = None
    watermark: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetSpec:
        raw_type = str(data.get("type", "character"))
        try:
            asset_type = AssetType(raw_type)
        except ValueError as exc:
            raise ValueError(
                f"Unknown asset type '{raw_type}'. "
                f"Use: {', '.join(t.value for t in AssetType)}"
            ) from exc

        method = str(data.get("animation_method", ANIMATION_METHOD_VIDEO)).lower()
        if method in FORBIDDEN_ANIMATION_METHODS:
            raise ValueError(
                f"animation_method '{method}' is forbidden. "
                "Never generate multiple action frames in one image. "
                f"Use '{ANIMATION_METHOD_VIDEO}' or '{ANIMATION_METHOD_IMG2IMG}'."
            )

        return cls(
            name=str(data["name"]),
            type=asset_type,
            description=str(data.get("description", "")),
            items=[str(x) for x in data.get("items", [])],
            grid=str(data.get("grid", "2x2")),
            aspect_ratio=str(data.get("aspect_ratio", "1:1")),
            display_size=str(data.get("display_size", "")),
            action=str(data.get("action", "")),
            animation_method=method,
            reference_asset=str(data.get("reference_asset", "")),
            duration_seconds=float(data.get("duration_seconds", 2.0)),
            sprite_frames=int(data.get("sprite_frames", 0)),
            video_model=str(data.get("video_model", "")),
            video_resolution=str(data.get("video_resolution", "")),
            video_ratio=str(data.get("video_ratio", "")),
            generate_audio=bool(data["generate_audio"]) if "generate_audio" in data else None,
            watermark=bool(data["watermark"]) if "watermark" in data else None,
        )


def load_brief(path: Path) -> tuple[ProjectContext, list[AssetSpec]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    project = ProjectContext.from_dict(data.get("project", data))
    assets_raw = data.get("assets", [])
    if not assets_raw:
        raise ValueError("Brief must contain an 'assets' array.")
    assets = [AssetSpec.from_dict(item) for item in assets_raw]
    return project, assets


def find_asset(assets: list[AssetSpec], name: str) -> AssetSpec:
    for asset in assets:
        if asset.name == name:
            return asset
    known = ", ".join(a.name for a in assets)
    raise ValueError(f"Asset '{name}' not found in brief. Known: {known}")
