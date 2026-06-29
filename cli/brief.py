"""Project brief types — shared input for all roles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from display_size import DisplaySize, parse_display_size

ANIMATION_METHOD_VIDEO = "video"
ANIMATION_METHOD_IMG2IMG = "img2img"
FORBIDDEN_ANIMATION_METHODS = frozenset({"spritesheet", "sheet", "grid_actions"})

# Brief export — usage tags (extensible; validate non-empty + recommended set warning in strict mode).
RECOMMENDED_USAGES = frozenset(
    {
        "reference_still",
        "player_idle",
        "player_locomotion",
        "player_attack",
        "player_jump",
        "player_action",
        "world_background",
        "parallax_layer",
        "ui_element",
        "tile_texture",
        "icon",
        "item_icon",
        "prop",
        "vfx",
        "music",
        "sfx",
    }
)
GENERATE_METHODS = frozenset({"image", "video", "procedural", "file"})
AUDIO_USAGES = frozenset({"music", "sfx"})
BRIEF_CONTRACT_VERSION = 1
VALID_DIMENSIONS = frozenset({"2d", "3d"})
RECOMMENDED_GENRES = frozenset(
    {
        "2d_platformer",
        "top_down",
        "endless_runner",
        "side_scroller",
        "puzzle",
        "shooter",
        "rpg",
        "visual_novel",
    }
)
PLAYER_USAGES = frozenset(
    {
        "reference_still",
        "player_idle",
        "player_locomotion",
        "player_attack",
        "player_jump",
        "player_action",
    }
)


class AssetType(str, Enum):
    CHARACTER = "character"
    ICON_KIT = "icon_kit"
    TEXTURE = "texture"
    BACKGROUND = "background"
    CHARACTER_POSE = "character_pose"
    AUDIO = "audio"


@dataclass
class ProjectContext:
    title: str = ""
    description: str = ""
    art_direction: str = ""
    dimension: str = "2d"
    genre: str = ""
    gameplay_loop: str = ""
    session_goal: str = ""
    player_asset: str = ""
    controls: dict[str, list[str]] = field(default_factory=dict)
    viewport: dict[str, Any] = field(default_factory=dict)
    camera: dict[str, Any] = field(default_factory=dict)
    visual_reference: str = ""
    hud: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectContext:
        raw_controls = data.get("controls") or {}
        controls: dict[str, list[str]] = {}
        if isinstance(raw_controls, dict):
            for action, keys in raw_controls.items():
                if isinstance(keys, list):
                    controls[str(action)] = [str(k) for k in keys if str(k).strip()]
                elif keys is not None and str(keys).strip():
                    controls[str(action)] = [str(keys)]
        viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else {}
        camera = data.get("camera") if isinstance(data.get("camera"), dict) else {}
        return cls(
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            art_direction=str(data.get("art_direction", "")),
            dimension=str(data.get("dimension", "2d")),
            genre=str(data.get("genre", "")),
            gameplay_loop=str(data.get("gameplay_loop", "")),
            session_goal=str(data.get("session_goal", "")),
            player_asset=str(data.get("player_asset", "")),
            controls=controls,
            viewport=dict(viewport),
            camera=dict(camera),
            visual_reference=str(data.get("visual_reference", "")).strip(),
            hud=[item for item in (data.get("hud") or []) if isinstance(item, dict)],
        )


@dataclass
class AnimationTransitionEdge:
    from_clip: str
    to_clip: str
    then_clip: str = ""
    bidirectional: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnimationTransitionEdge:
        return cls(
            from_clip=str(data.get("from", data.get("from_clip", ""))).strip(),
            to_clip=str(data.get("to", data.get("to_clip", ""))).strip(),
            then_clip=str(data.get("then", data.get("then_clip", ""))).strip(),
            bidirectional=bool(data.get("bidirectional", False)),
        )


@dataclass
class CharacterAnimationGraph:
    character_asset: str
    default_clip: str = "idle"
    summary: str = ""
    transitions: list[AnimationTransitionEdge] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CharacterAnimationGraph:
        raw_edges = data.get("transitions") or []
        edges: list[AnimationTransitionEdge] = []
        if isinstance(raw_edges, list):
            for item in raw_edges:
                if isinstance(item, dict):
                    edges.append(AnimationTransitionEdge.from_dict(item))
        return cls(
            character_asset=str(data.get("character_asset", "")).strip(),
            default_clip=str(data.get("default_clip", "idle")).strip() or "idle",
            summary=str(data.get("summary", "")).strip(),
            transitions=edges,
        )


@dataclass
class AssetSpec:
    name: str
    type: AssetType
    description: str = ""
    items: list[str] = field(default_factory=list)
    grid: str = "2x2"
    aspect_ratio: str = "1:1"
    display_size: DisplaySize = field(default_factory=DisplaySize.empty)
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
    animation_name: str = ""
    animation_loop: bool | None = None
    usage: str = ""
    usage_description: str = ""
    generate_method: str = ""
    parallax_order: int | None = None
    scroll_factor: float | None = None
    audio_loop: bool | None = None

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
            display_size=parse_display_size(data.get("display_size")) or DisplaySize.empty(),
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
            animation_name=str(data.get("animation_name", "")),
            animation_loop=bool(data["animation_loop"]) if "animation_loop" in data else None,
            usage=str(data.get("usage", "")),
            usage_description=str(data.get("usage_description", "")),
            generate_method=str(data.get("generate_method", "")).lower(),
            parallax_order=int(data["parallax_order"]) if "parallax_order" in data else None,
            scroll_factor=float(data["scroll_factor"]) if "scroll_factor" in data else None,
            audio_loop=bool(data["audio_loop"]) if "audio_loop" in data else None,
        )


def is_video_animation(spec: AssetSpec) -> bool:
    return (
        spec.type == AssetType.CHARACTER
        and bool(spec.action.strip())
        and spec.animation_method == ANIMATION_METHOD_VIDEO
    )


def resolve_generate_method(spec: AssetSpec) -> str:
    explicit = spec.generate_method.strip().lower()
    if spec.type == AssetType.AUDIO:
        allowed = frozenset({"procedural", "file"})
        if explicit:
            if explicit not in allowed:
                raise ValueError(
                    f"Asset '{spec.name}' audio generate_method must be one of: "
                    f"{', '.join(sorted(allowed))}"
                )
            return explicit
        return "procedural"
    if explicit:
        if explicit not in GENERATE_METHODS:
            raise ValueError(
                f"Asset '{spec.name}' generate_method must be one of: {', '.join(sorted(GENERATE_METHODS))}"
            )
        return explicit
    if is_video_animation(spec):
        return "video"
    return "image"


def is_runtime_only_asset(spec: AssetSpec) -> bool:
    """Assets with no image/video pipeline tasks (procedural audio, bundled files)."""
    return spec.type == AssetType.AUDIO and resolve_generate_method(spec) in (
        "procedural",
        "file",
    )


def parse_animation_graphs(data: dict[str, Any]) -> list[CharacterAnimationGraph]:
    raw = data.get("animation_graphs") or []
    if not isinstance(raw, list):
        return []
    return [CharacterAnimationGraph.from_dict(item) for item in raw if isinstance(item, dict)]


def animation_graph_to_dict(graph: CharacterAnimationGraph) -> dict[str, Any]:
    out: dict[str, Any] = {
        "character_asset": graph.character_asset,
        "default_clip": graph.default_clip,
        "transitions": [
            {
                "from": edge.from_clip,
                "to": edge.to_clip,
                **({"then": edge.then_clip} if edge.then_clip else {}),
                **({"bidirectional": True} if edge.bidirectional else {}),
            }
            for edge in graph.transitions
        ],
    }
    if graph.summary:
        out["summary"] = graph.summary
    return out


def character_clip_names(assets: list[AssetSpec], character_asset: str) -> dict[str, AssetSpec]:
    """Map Godot clip name → brief asset for one character (reference still + video clips)."""
    clips: dict[str, AssetSpec] = {}
    for spec in assets:
        if spec.name == character_asset and spec.type == AssetType.CHARACTER:
            clips[resolve_animation_name(spec)] = spec
        elif spec.reference_asset.strip() == character_asset and is_video_animation(spec):
            clips[resolve_animation_name(spec)] = spec
    return clips


def is_platformer_genre(genre: str) -> bool:
    g = genre.strip().lower().replace("-", "_")
    if not g:
        return False
    return "platform" in g or g in {"2d_platformer", "side_scroller", "side_scrolling"}


def required_control_actions(assets: list[AssetSpec]) -> set[str]:
    """Derive required InputMap action names from asset usage tags."""
    usages = {a.usage.strip() for a in assets if a.usage.strip()}
    needed: set[str] = set()
    if usages & {"player_locomotion", "player_idle", "reference_still", "player_action"}:
        needed |= {"move_left", "move_right"}
    if "player_jump" in usages:
        needed.add("jump")
    if "player_attack" in usages:
        needed.add("attack")
    return needed


def audit_project_gameplay(
    project: ProjectContext,
    assets: list[AssetSpec],
    *,
    name_set: set[str],
    has_player_facing: bool,
) -> list[str]:
    errors: list[str] = []
    if not (project.genre or "").strip():
        errors.append("project.genre is required (e.g. 2d_platformer, top_down, endless_runner)")
    if not (project.gameplay_loop or "").strip():
        errors.append("project.gameplay_loop is required (core repeat loop in English)")
    if not (project.session_goal or "").strip():
        errors.append("project.session_goal is required (win/lose or demo scope for this build)")

    vp = project.viewport
    if not vp:
        errors.append("project.viewport is required ({ width, height } in pixels)")
    else:
        width = vp.get("width")
        height = vp.get("height")
        try:
            w, h = int(width), int(height)
            if w <= 0 or h <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append("project.viewport.width and height must be positive integers")

    if not project.controls:
        errors.append("project.controls is required (map action names to key/button labels)")
    else:
        for action, keys in project.controls.items():
            if not str(action).strip():
                errors.append("project.controls contains an empty action name")
            elif not keys:
                errors.append(f"project.controls['{action}'] must list at least one key")
        for action in sorted(required_control_actions(assets)):
            if action not in project.controls:
                errors.append(
                    f"project.controls missing '{action}' (required by asset usage in brief)"
                )

    if has_player_facing:
        if not (project.player_asset or "").strip():
            errors.append("project.player_asset is required when brief has player-facing assets")
        elif project.player_asset not in name_set:
            errors.append(f"project.player_asset '{project.player_asset}' not found in assets[]")

    if has_player_facing and is_platformer_genre(project.genre):
        if not project.camera or not str(project.camera.get("mode", "")).strip():
            errors.append(
                "project.camera.mode is required for platformer genre (e.g. follow_player)"
            )

    return errors


def audit_asset_extensions(
    project: ProjectContext,
    assets: list[AssetSpec],
) -> list[str]:
    """P1 brief fields: parallax layers, audio, UI/hud wiring."""
    errors: list[str] = []
    asset_names = {a.name for a in assets}
    ui_assets: list[str] = []
    hud_asset_refs = {
        str(h.get("asset", "")).strip()
        for h in project.hud
        if isinstance(h, dict) and str(h.get("asset", "")).strip()
    }

    for spec in assets:
        usage = spec.usage.strip()
        if usage == "parallax_layer":
            if spec.parallax_order is None:
                errors.append(
                    f"Asset '{spec.name}' usage parallax_layer requires 'parallax_order' (int, lower = farther back)"
                )
            elif spec.parallax_order < 0:
                errors.append(f"Asset '{spec.name}' parallax_order must be >= 0")
            if spec.scroll_factor is None:
                errors.append(
                    f"Asset '{spec.name}' usage parallax_layer requires 'scroll_factor' (float, 0–1)"
                )
            elif not (0.0 < spec.scroll_factor <= 1.0):
                errors.append(f"Asset '{spec.name}' scroll_factor must be > 0 and <= 1")
        if spec.type == AssetType.TEXTURE and spec.usage.strip() == "tile_texture":
            if spec.display_size.is_empty():
                errors.append(
                    f"Asset '{spec.name}' usage tile_texture requires display_size (single tile in-game pixels)"
                )
        if usage == "ui_element":
            ui_assets.append(spec.name)
            if spec.display_size.is_empty():
                errors.append(f"Asset '{spec.name}' usage ui_element requires 'display_size'")
        if spec.type == AssetType.AUDIO:
            if usage not in AUDIO_USAGES:
                errors.append(
                    f"Asset '{spec.name}' type audio requires usage 'music' or 'sfx' "
                    f"(got '{usage or 'missing'}')"
                )
            if usage == "music" and spec.audio_loop is None:
                errors.append(f"Asset '{spec.name}' music track requires 'audio_loop' (true/false)")

    for name in ui_assets:
        if name not in hud_asset_refs:
            errors.append(
                f"project.hud must include {{\"asset\": \"{name}\", ...}} for ui_element '{name}'"
            )

    for hud in project.hud:
        if not isinstance(hud, dict):
            continue
        asset_ref = str(hud.get("asset", "")).strip()
        if not asset_ref:
            errors.append("project.hud entry missing 'asset' field")
            continue
        if asset_ref not in asset_names:
            errors.append(f"project.hud references unknown asset '{asset_ref}'")
        if not str(hud.get("anchor", "")).strip():
            errors.append(f"project.hud entry for '{asset_ref}' missing 'anchor'")

    return errors


def characters_requiring_animation_graph(assets: list[AssetSpec]) -> set[str]:
    """Characters with reference + at least one action clip need a graph."""
    candidates: set[str] = set()
    for spec in assets:
        if is_video_animation(spec):
            ref = spec.reference_asset.strip()
            if ref:
                candidates.add(ref)
    return {char for char in candidates if len(character_clip_names(assets, char)) >= 2}


def audit_animation_graphs(
    assets: list[AssetSpec],
    graphs: list[CharacterAnimationGraph],
) -> list[str]:
    errors: list[str] = []
    required = characters_requiring_animation_graph(assets)
    by_char = {g.character_asset: g for g in graphs if g.character_asset}

    for char in sorted(required):
        if char not in by_char:
            errors.append(
                f"Character '{char}' has multiple animation clips but no animation_graphs entry"
            )

    names = {a.name for a in assets}
    for graph in graphs:
        if not graph.character_asset:
            errors.append("animation_graphs entry missing character_asset")
            continue
        if graph.character_asset not in names:
            errors.append(
                f"animation_graphs character_asset '{graph.character_asset}' not in assets[]"
            )
            continue
        clips = character_clip_names(assets, graph.character_asset)
        clip_names = set(clips)
        if graph.default_clip not in clip_names:
            errors.append(
                f"animation_graphs '{graph.character_asset}': default_clip "
                f"'{graph.default_clip}' not in clips {sorted(clip_names)}"
            )
        for edge in graph.transitions:
            if edge.from_clip not in clip_names:
                errors.append(
                    f"animation_graphs '{graph.character_asset}': unknown from clip '{edge.from_clip}'"
                )
            if edge.to_clip not in clip_names:
                errors.append(
                    f"animation_graphs '{graph.character_asset}': unknown to clip '{edge.to_clip}'"
                )
            if edge.then_clip and edge.then_clip not in clip_names:
                errors.append(
                    f"animation_graphs '{graph.character_asset}': unknown then clip '{edge.then_clip}'"
                )
            target = clips.get(edge.to_clip)
            if target and not resolve_animation_loop(target) and not edge.then_clip:
                errors.append(
                    f"animation_graphs '{graph.character_asset}': one-shot clip '{edge.to_clip}' "
                    "requires 'then' (return clip after playing)"
                )

    return errors


def audit_brief_for_export(
    project: ProjectContext,
    assets: list[AssetSpec],
    *,
    animation_graphs: list[CharacterAnimationGraph] | None = None,
) -> list[str]:
    """Return missing required fields. Empty list means brief is complete enough to freeze."""
    errors: list[str] = []
    if not (project.title or "").strip():
        errors.append("project.title is required")
    if not (project.description or "").strip():
        errors.append("project.description is required (gameplay / scope in English)")
    if not (project.art_direction or "").strip():
        errors.append("project.art_direction is required (visual style in English)")
    dim = (project.dimension or "").strip().lower()
    if not dim:
        errors.append("project.dimension is required (2d or 3d)")
    elif dim not in VALID_DIMENSIONS:
        errors.append(f"project.dimension must be one of: {', '.join(sorted(VALID_DIMENSIONS))}")

    if not assets:
        errors.append("assets[] must contain at least one entry")
        return errors

    names: list[str] = []
    for spec in assets:
        if not spec.name.strip():
            errors.append("Every asset needs a non-empty 'name'")
            continue
        if spec.name in names:
            errors.append(f"Duplicate asset name '{spec.name}'")
        names.append(spec.name)

    name_set = set(names)
    has_player_facing = False
    for spec in assets:
        if not spec.usage.strip():
            errors.append(f"Asset '{spec.name}' missing required field 'usage'")
        elif spec.usage.strip() in PLAYER_USAGES:
            has_player_facing = True
        if spec.display_size.is_empty() and spec.type in (
            AssetType.CHARACTER,
            AssetType.CHARACTER_POSE,
            AssetType.BACKGROUND,
            AssetType.ICON_KIT,
        ):
            errors.append(f"Asset '{spec.name}' missing required 'display_size'")
        if not (spec.usage_description or spec.description).strip():
            errors.append(f"Asset '{spec.name}' needs 'usage_description' or 'description'")
        if spec.type == AssetType.ICON_KIT and not spec.items:
            errors.append(f"Asset '{spec.name}' icon_kit requires non-empty 'items' list")

        method = resolve_generate_method(spec)
        if method == "video":
            if not spec.reference_asset.strip():
                errors.append(f"Asset '{spec.name}' video animation requires 'reference_asset'")
            if not spec.action.strip():
                errors.append(f"Asset '{spec.name}' video animation requires 'action'")
            if spec.reference_asset and spec.reference_asset not in name_set:
                errors.append(
                    f"Asset '{spec.name}' references unknown asset '{spec.reference_asset}'"
                )
        if method == "image" and spec.type == AssetType.CHARACTER_POSE:
            if not spec.reference_asset.strip():
                errors.append(f"Asset '{spec.name}' character_pose requires 'reference_asset'")
            if not spec.action.strip():
                errors.append(f"Asset '{spec.name}' character_pose requires 'action'")

    if any(resolve_generate_method(a) == "video" for a in assets) and not has_player_facing:
        errors.append(
            "Brief has video animations but no player-facing asset "
            f"(usage one of: {', '.join(sorted(PLAYER_USAGES))})"
        )

    errors.extend(
        audit_project_gameplay(
            project,
            assets,
            name_set=name_set,
            has_player_facing=has_player_facing,
        )
    )
    errors.extend(audit_animation_graphs(assets, animation_graphs or []))
    errors.extend(audit_asset_extensions(project, assets))
    from asset_sizing import audit_display_size_consistency

    errors.extend(
        audit_display_size_consistency(
            assets,
            animation_graphs=animation_graphs,
            viewport=project.viewport,
        )
    )

    return errors


def validate_brief_for_export(
    project: ProjectContext,
    assets: list[AssetSpec],
    *,
    animation_graphs: list[CharacterAnimationGraph] | None = None,
) -> None:
    """Raise ValueError if brief is missing required fields — gate for export and pipeline plan."""
    errors = audit_brief_for_export(project, assets, animation_graphs=animation_graphs)
    if errors:
        raise ValueError("Brief validation failed:\n- " + "\n- ".join(errors))


def finalize_brief_export(data: dict[str, Any], *, source: str = "manual") -> dict[str, Any]:
    """Validate and stamp brief_meta — frozen contract; downstream reads only this file."""
    from shared_context import asset_to_dict, project_to_dict

    project = ProjectContext.from_dict(data.get("project", {}))
    assets_raw = data.get("assets") or []
    if not assets_raw:
        raise ValueError("Brief must contain an 'assets' array.")
    assets = [AssetSpec.from_dict(item) for item in assets_raw]
    graphs = parse_animation_graphs(data)
    validate_brief_for_export(project, assets, animation_graphs=graphs)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out: dict[str, Any] = {
        "brief_meta": {
            "contract_version": BRIEF_CONTRACT_VERSION,
            "frozen_at": now,
            "source": source,
        },
        "project": project_to_dict(project),
        "assets": [asset_to_dict(a) for a in assets],
    }
    if graphs:
        out["animation_graphs"] = [animation_graph_to_dict(g) for g in graphs]
    return out


def load_brief_document(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_brief_document(
    data: dict[str, Any],
) -> tuple[ProjectContext, list[AssetSpec], list[CharacterAnimationGraph]]:
    project = ProjectContext.from_dict(data.get("project", data))
    assets_raw = data.get("assets", [])
    if not assets_raw:
        raise ValueError("Brief must contain an 'assets' array.")
    assets = [AssetSpec.from_dict(item) for item in assets_raw]
    graphs = parse_animation_graphs(data)
    return project, assets, graphs


def load_brief_full(
    path: Path,
) -> tuple[ProjectContext, list[AssetSpec], list[CharacterAnimationGraph]]:
    return parse_brief_document(load_brief_document(path))


def resolve_animation_name(spec: AssetSpec) -> str:
    """Godot SpriteFrames clip name — from brief field or derived from asset naming."""
    explicit = spec.animation_name.strip()
    if explicit:
        return explicit
    if spec.type == AssetType.CHARACTER and not spec.action.strip():
        return "idle"
    ref = spec.reference_asset.strip()
    if ref and spec.name.startswith(f"{ref}_"):
        return spec.name[len(ref) + 1 :]
    if ref and spec.name == ref:
        return "idle"
    return spec.name


def resolve_animation_loop(spec: AssetSpec) -> bool:
    """Whether the clip loops in Godot (brief may set false for one-shot actions)."""
    if spec.animation_loop is not None:
        return spec.animation_loop
    return True


def load_brief(path: Path) -> tuple[ProjectContext, list[AssetSpec]]:
    project, assets, _ = load_brief_full(path)
    return project, assets


def find_asset(assets: list[AssetSpec], name: str) -> AssetSpec:
    for asset in assets:
        if asset.name == name:
            return asset
    known = ", ".join(a.name for a in assets)
    raise ValueError(f"Asset '{name}' not found in brief. Known: {known}")
