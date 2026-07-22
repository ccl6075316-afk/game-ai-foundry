"""Project brief types — shared input for all roles."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from display_size import DisplaySize, parse_display_size

# English file/task key — required on every asset (paths must stay ASCII).
ASSET_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

ANIMATION_METHOD_VIDEO = "video"
ANIMATION_METHOD_IMG2IMG = "img2img"
FORBIDDEN_ANIMATION_METHODS = frozenset({"spritesheet", "sheet", "grid_actions"})
STYLE_ANCHOR_KINDS = frozenset({"asset", "visual_reference"})
_CLI_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CLI_DIR.parent

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


STYLE_IMG2IMG_ALLOWED_TYPES = frozenset(
    {
        AssetType.CHARACTER,
        AssetType.TEXTURE,
        AssetType.BACKGROUND,
    }
)


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
    art_tokens: dict[str, Any] | None = None
    _art_tokens_errors: list[str] = field(default_factory=list, repr=False, compare=False)

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
        art_tokens, art_tokens_errors = normalize_art_tokens(data.get("art_tokens"))
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
            art_tokens=art_tokens,
            _art_tokens_errors=art_tokens_errors,
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


def parse_icon_grid(grid: str) -> tuple[int, int]:
    """Parse ``ROWxCOL`` (e.g. ``2x3`` → rows=2, cols=3)."""
    parts = (grid or "").strip().lower().replace(" ", "").split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid grid '{grid}', expected ROWxCOL e.g. 2x2")
    rows, cols = int(parts[0]), int(parts[1])
    if rows < 1 or cols < 1:
        raise ValueError(f"Invalid grid '{grid}', rows/cols must be >= 1")
    return rows, cols


def suggest_icon_grid(item_count: int) -> str:
    """Near-square grid that fits ``item_count`` cells (rows x cols)."""
    import math

    n = max(1, int(item_count))
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = max(1, math.ceil(n / cols))
    return f"{rows}x{cols}"


def resolve_icon_grid(grid: str, item_count: int) -> str:
    """Return grid with enough cells for items; upgrade when too small.

    Deprecated for pipeline authority (icon_kit no longer slices). Kept for
    legacy helpers / tests.
    """
    n = max(0, int(item_count))
    if n <= 0:
        return (grid or "2x2").strip() or "2x2"
    try:
        rows, cols = parse_icon_grid(grid or "2x2")
    except ValueError:
        return suggest_icon_grid(n)
    if rows * cols < n:
        return suggest_icon_grid(n)
    return f"{rows}x{cols}"


def slugify_item_label(label: str) -> str:
    """Stable filesystem/task key from an icon_kit item id/label."""
    text = str(label or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text or "item"


def unique_item_slugs(items: list[str]) -> list[str]:
    """Slugify ids/labels; duplicate slugs get _2, _3, …"""
    seen: dict[str, int] = {}
    out: list[str] = []
    for raw in items:
        base = slugify_item_label(raw)
        count = seen.get(base, 0) + 1
        seen[base] = count
        out.append(base if count == 1 else f"{base}_{count}")
    return out


@dataclass
class IconKitItem:
    """One icon_kit entry: stable id + optional prompt label / usage."""

    id: str
    label: str = ""
    usage: str = ""
    usage_description: str = ""
    id_from_object: bool = False

    def __post_init__(self) -> None:
        self.id = str(self.id or "").strip()
        self.label = str(self.label or "").strip() or self.id
        self.usage = str(self.usage or "").strip()
        self.usage_description = str(self.usage_description or "").strip()

    @property
    def prompt_label(self) -> str:
        return self.label or self.id

    def __str__(self) -> str:
        return self.id

    def to_brief(self) -> str | dict[str, str]:
        """Round-trip: plain string when no extras; else object."""
        extras = bool(self.usage or self.usage_description)
        label_differs = bool(self.label) and self.label != self.id
        if not extras and not label_differs and not self.id_from_object:
            return self.id
        if not extras and not label_differs and self.id_from_object:
            # Authored as {"id": "..."} — keep object only if caller cares; string OK.
            return self.id
        data: dict[str, str] = {"id": self.id}
        if label_differs:
            data["label"] = self.label
        if self.usage:
            data["usage"] = self.usage
        if self.usage_description:
            data["usage_description"] = self.usage_description
        return data

    def to_dict(self) -> dict[str, str]:
        data: dict[str, str] = {"id": self.id, "label": self.prompt_label}
        if self.usage:
            data["usage"] = self.usage
        if self.usage_description:
            data["usage_description"] = self.usage_description
        return data


def parse_icon_kit_item(raw: Any) -> IconKitItem:
    """Accept string or {id, label?, usage?, usage_description?}."""
    if isinstance(raw, IconKitItem):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise ValueError("icon_kit item string must be non-empty")
        return IconKitItem(id=text, label=text, id_from_object=False)
    if isinstance(raw, dict):
        has_explicit_id = bool(str(raw.get("id") or raw.get("name") or "").strip())
        id_raw = str(raw.get("id") or raw.get("name") or "").strip()
        label = str(raw.get("label") or "").strip()
        if not id_raw:
            id_raw = label
        if not id_raw:
            raise ValueError("icon_kit item object needs 'id' or 'label'")
        return IconKitItem(
            id=id_raw,
            label=label or id_raw,
            usage=str(raw.get("usage") or "").strip(),
            usage_description=str(raw.get("usage_description") or "").strip(),
            id_from_object=has_explicit_id,
        )
    raise ValueError(f"icon_kit item must be string or object, got {type(raw).__name__}")


def parse_icon_kit_items(raw_items: Any) -> list[IconKitItem]:
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise ValueError("icon_kit 'items' must be a list")
    return [parse_icon_kit_item(x) for x in raw_items]


def find_icon_kit_item(spec: AssetSpec, needle: str) -> IconKitItem | None:
    """Match --item against id or label."""
    key = (needle or "").strip()
    if not key:
        return None
    for item in spec.items:
        if item.id == key or item.label == key or item.prompt_label == key:
            return item
    return None


def unique_kit_item_slugs(items: list[IconKitItem]) -> list[str]:
    """Slug from item.id (identity), with collision suffixes."""
    return unique_item_slugs([it.id for it in items])


def resolve_kit_item_slug(items: list[IconKitItem], item: IconKitItem) -> str:
    """Same slug pipeline/production/craft use for this item row."""
    slugs = unique_kit_item_slugs(items)
    for it, slug in zip(items, slugs, strict=True):
        if it is item:
            return slug
    # Fallback: first matching id (should not happen for list members).
    for it, slug in zip(items, slugs, strict=True):
        if it.id == item.id:
            return slug
    return slugify_item_label(item.id)


@dataclass
class AssetSpec:
    name: str
    type: AssetType
    id: str = ""
    description: str = ""
    items: list[IconKitItem] = field(default_factory=list)
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
    style_group: str = ""
    style_anchor_kind: str = ""
    style_anchor: str = ""
    identity_anchor: str = ""
    use_style_img2img: bool | None = None
    generate_tier: str = ""

    def __post_init__(self) -> None:
        if self.items and any(not isinstance(x, IconKitItem) for x in self.items):
            self.items = [parse_icon_kit_item(x) for x in self.items]

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

        items = parse_icon_kit_items(data.get("items", []))
        grid = str(data.get("grid", "2x2"))
        # grid is legacy metadata only — icon_kit no longer slices by grid.

        tier_raw = str(data.get("generate_tier", "")).strip().lower()
        if tier_raw and tier_raw not in ("default", "bulk"):
            raise ValueError(
                f"generate_tier must be 'default' or 'bulk', got {data.get('generate_tier')!r}"
            )

        return cls(
            name=str(data["name"]),
            type=asset_type,
            id=str(data.get("id", "")).strip(),
            description=str(data.get("description", "")),
            items=items,
            grid=grid,
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
            style_group=str(data.get("style_group", "")).strip(),
            style_anchor_kind=str(data.get("style_anchor_kind", "")).strip().lower(),
            style_anchor=str(data.get("style_anchor", "")).strip(),
            identity_anchor=str(data.get("identity_anchor", "")).strip(),
            use_style_img2img=(
                bool(data["use_style_img2img"]) if "use_style_img2img" in data else None
            ),
            generate_tier=tier_raw,
        )


def resolve_asset_file_key(spec: AssetSpec) -> str:
    """English slug used for disk paths and pipeline task id prefixes."""
    key = (spec.id or "").strip()
    if not key:
        raise ValueError(
            f"Asset '{spec.name}' missing required field 'id' "
            "(English slug matching ^[a-z][a-z0-9_]*$, e.g. referee_run)"
        )
    if not ASSET_ID_PATTERN.match(key):
        raise ValueError(
            f"Asset '{spec.name}' id '{key}' must match ^[a-z][a-z0-9_]*$"
        )
    return key


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


def clip_alias_map(assets: list[AssetSpec], character_asset: str) -> dict[str, str]:
    """Map common wrong labels → canonical Godot clip name for one character."""
    clips = character_clip_names(assets, character_asset)
    aliases: dict[str, str] = {}
    for clip, spec in clips.items():
        aliases[clip] = clip
        aliases[spec.name] = clip
        if character_asset and spec.name.startswith(f"{character_asset}_"):
            suffix = spec.name[len(character_asset) + 1 :]
            if suffix:
                aliases[suffix] = clip
        if spec.animation_name.strip():
            aliases[spec.animation_name.strip()] = clip
        # Full-width / spaced variants of the clip token
        aliases[clip.replace("_", "")] = clip
    return aliases


def apply_deterministic_animation_graph_fixes(
    draft: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Mechanically repair animation_graphs clip mismatches (no LLM).

    Returns (possibly-updated draft, human-readable notes).
    """
    if not isinstance(draft, dict):
        return draft, []

    notes: list[str] = []
    try:
        assets = [
            AssetSpec.from_dict(item)
            for item in (draft.get("assets") or [])
            if isinstance(item, dict)
        ]
    except (ValueError, KeyError, TypeError) as exc:
        return draft, [f"skip deterministic graph fix: {exc}"]

    raw_graphs = draft.get("animation_graphs")
    if not isinstance(raw_graphs, list):
        raw_graphs = []

    # Drop invented states[] (validator ignores it; models keep rewriting it).
    cleaned_graphs: list[dict[str, Any]] = []
    for item in raw_graphs:
        if not isinstance(item, dict):
            continue
        g = dict(item)
        if "states" in g:
            g.pop("states", None)
            notes.append(
                f"removed states[] from animation_graphs '{g.get('character_asset')}' "
                "(Foundry uses clip names only)"
            )
        cleaned_graphs.append(g)

    # Ensure required characters have a graph shell.
    required = characters_requiring_animation_graph(assets)
    by_char = {
        str(g.get("character_asset", "")).strip(): g
        for g in cleaned_graphs
        if str(g.get("character_asset", "")).strip()
    }
    for char in sorted(required):
        if char in by_char:
            continue
        clips = character_clip_names(assets, char)
        clip_list = list(clips.keys())
        default = "idle" if "idle" in clips else (clip_list[0] if clip_list else "idle")
        others = [c for c in clip_list if c != default]
        transitions: list[dict[str, Any]] = []
        if others:
            transitions.append(
                {"from": default, "to": others[0], "bidirectional": True}
            )
        shell = {
            "character_asset": char,
            "default_clip": default,
            "transitions": transitions,
            "summary": "auto-created graph shell",
        }
        cleaned_graphs.append(shell)
        by_char[char] = shell
        notes.append(f"created missing animation_graphs for '{char}'")

    for g in cleaned_graphs:
        char = str(g.get("character_asset", "")).strip()
        if not char:
            continue
        clips = character_clip_names(assets, char)
        clip_names = set(clips)
        aliases = clip_alias_map(assets, char)

        def remap(token: str) -> str:
            t = (token or "").strip()
            if not t:
                return t
            if t in clip_names:
                return t
            if t in aliases:
                return aliases[t]
            # Prefix strip: 球员_普通_跑动 → 跑动 when char is 球员_普通
            if char and t.startswith(f"{char}_"):
                suffix = t[len(char) + 1 :]
                if suffix in clip_names:
                    return suffix
                if suffix in aliases:
                    return aliases[suffix]
            return t

        old_default = str(g.get("default_clip") or "idle").strip() or "idle"
        new_default = remap(old_default)
        if new_default not in clip_names and "idle" in clip_names:
            new_default = "idle"
        elif new_default not in clip_names and clip_names:
            new_default = sorted(clip_names)[0]
        if new_default != old_default:
            notes.append(f"'{char}' default_clip: '{old_default}' → '{new_default}'")
        g["default_clip"] = new_default

        raw_edges = g.get("transitions") if isinstance(g.get("transitions"), list) else []
        new_edges: list[dict[str, Any]] = []
        for edge in raw_edges:
            if not isinstance(edge, dict):
                continue
            fr = remap(str(edge.get("from", edge.get("from_clip", ""))).strip())
            to = remap(str(edge.get("to", edge.get("to_clip", ""))).strip())
            then = remap(str(edge.get("then", edge.get("then_clip", ""))).strip())
            if fr != str(edge.get("from", edge.get("from_clip", ""))).strip() or to != str(
                edge.get("to", edge.get("to_clip", ""))
            ).strip():
                notes.append(f"'{char}' transition remapped → from '{fr}' to '{to}'")
            if fr not in clip_names or to not in clip_names:
                notes.append(
                    f"'{char}' dropped transition '{fr}'→'{to}' "
                    f"(not in clips {sorted(clip_names)})"
                )
                continue
            if then and then not in clip_names:
                then = new_default if new_default in clip_names else ""
            target = clips.get(to)
            if target and not resolve_animation_loop(target) and not then:
                then = new_default if new_default in clip_names else ""
                if then:
                    notes.append(f"'{char}' one-shot '{to}' missing then → '{then}'")
            out_edge: dict[str, Any] = {"from": fr, "to": to}
            if then:
                out_edge["then"] = then
            if edge.get("bidirectional"):
                out_edge["bidirectional"] = True
            new_edges.append(out_edge)
        g["transitions"] = new_edges

    out = dict(draft)
    out["animation_graphs"] = cleaned_graphs
    return out, notes


def _default_hud_anchor(asset_name: str) -> str:
    n = (asset_name or "").lower()
    if any(k in asset_name for k in ("进度", "条")) or "progress" in n or "bar" in n:
        return "top_center"
    if any(k in asset_name for k in ("箭头", "指示")) or "arrow" in n:
        return "bottom_center"
    if any(k in asset_name for k in ("面板", "菜单")) or "panel" in n or "menu" in n:
        return "center"
    if any(k in asset_name for k in ("图标", "表情", "事件")) or "icon" in n:
        return "top_right"
    return "top_left"


def apply_deterministic_hud_fixes(
    draft: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Ensure project.hud lists every usage=ui_element asset (asset + anchor)."""
    if not isinstance(draft, dict):
        return draft, []

    notes: list[str] = []
    try:
        assets = [
            AssetSpec.from_dict(item)
            for item in (draft.get("assets") or [])
            if isinstance(item, dict)
        ]
    except (ValueError, KeyError, TypeError) as exc:
        return draft, [f"skip deterministic hud fix: {exc}"]

    ui_names = [a.name for a in assets if a.usage.strip() == "ui_element"]
    if not ui_names:
        return draft, []

    project = draft.get("project")
    if not isinstance(project, dict):
        project = {}
    else:
        project = dict(project)

    raw_hud = project.get("hud")
    hud: list[dict[str, Any]] = (
        [dict(h) for h in raw_hud if isinstance(h, dict)] if isinstance(raw_hud, list) else []
    )
    by_asset = {
        str(h.get("asset", "")).strip(): h
        for h in hud
        if str(h.get("asset", "")).strip()
    }

    added: list[str] = []
    for name in ui_names:
        if name in by_asset:
            entry = by_asset[name]
            if not str(entry.get("anchor", "")).strip():
                entry["anchor"] = _default_hud_anchor(name)
                notes.append(f"hud '{name}': filled missing anchor")
            if not str(entry.get("description", "")).strip():
                entry["description"] = f"HUD binding for {name}"
            continue
        entry = {
            "asset": name,
            "anchor": _default_hud_anchor(name),
            "description": f"HUD binding for {name}",
        }
        hud.append(entry)
        by_asset[name] = entry
        added.append(name)

    if added:
        notes.append(f"project.hud: added {len(added)} ui_element binding(s): {', '.join(added)}")

    # Drop orphan hud rows that no longer match any asset (noise from LLM).
    asset_names = {a.name for a in assets}
    pruned = [h for h in hud if str(h.get("asset", "")).strip() in asset_names]
    if len(pruned) != len(hud):
        notes.append(f"project.hud: removed {len(hud) - len(pruned)} unknown asset ref(s)")
        hud = pruned

    out = dict(draft)
    project["hud"] = hud
    out["project"] = project
    return out, notes


_VISUAL_REF_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def looks_like_visual_reference_path(ref: str) -> bool:
    """True if value looks like an image path (not art-direction prose)."""
    s = (ref or "").strip().replace("\\", "/")
    if not s or len(s) > 400 or "://" in s:
        return False
    lower = s.lower()
    if not any(lower.endswith(ext) for ext in _VISUAL_REF_IMAGE_SUFFIXES):
        return False
    # Sentences with spaces but no path separators are almost never file paths.
    if " " in s and "/" not in s and not Path(s).name.endswith(tuple(_VISUAL_REF_IMAGE_SUFFIXES)):
        return False
    return True


def audit_visual_reference(
    project: ProjectContext,
    *,
    brief_path: Path | None = None,
) -> list[str]:
    """visual_reference is optional; when set it must be an image path (not style prose)."""
    ref = (project.visual_reference or "").strip()
    if not ref:
        return []
    if not looks_like_visual_reference_path(ref):
        return [
            "project.visual_reference must be an image file path "
            "(e.g. output/.../visual-target/selected.png), not style prose. "
            "Put art style in project.art_direction; leave visual_reference empty "
            "until `brief visual-target pick` (or GUI「北极星图」)."
        ]
    if brief_path is not None:
        from visual_target import resolve_visual_reference_path

        if resolve_visual_reference_path(brief_path) is None:
            return [
                f"project.visual_reference file not found: {ref}. "
                "Run `brief visual-target generate` then `pick`, or clear the field."
            ]
    return []


def apply_deterministic_visual_reference_fixes(
    draft: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Clear prose mistaken for visual_reference; merge unique text into art_direction."""
    if not isinstance(draft, dict):
        return draft, []
    project = draft.get("project")
    if not isinstance(project, dict):
        return draft, []
    ref = str(project.get("visual_reference") or "").strip()
    if not ref or looks_like_visual_reference_path(ref):
        return draft, []
    notes = [
        "cleared invalid project.visual_reference "
        "(style prose → art_direction; use visual-target pick for the image path)"
    ]
    art = str(project.get("art_direction") or "").strip()
    if ref and ref not in art:
        project = dict(project)
        project["art_direction"] = f"{art}; {ref}".strip("; ").strip() if art else ref
        notes.append("merged cleared visual_reference text into art_direction")
    else:
        project = dict(project)
    project["visual_reference"] = ""
    project.pop("visual_reference_usage", None)
    out = dict(draft)
    out["project"] = project
    return out, notes


def apply_deterministic_brief_fixes(
    draft: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """All mechanical brief repairs used by autofix (graphs + hud + visual_reference)."""
    notes: list[str] = []
    fixed, n1 = apply_deterministic_animation_graph_fixes(draft)
    notes.extend(n1)
    fixed, n2 = apply_deterministic_hud_fixes(fixed)
    notes.extend(n2)
    fixed, n3 = apply_deterministic_visual_reference_fixes(fixed)
    notes.extend(n3)
    return fixed, notes


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


def _cli_relative(path: Path) -> str:
    """Path as used in commands run from cli/ (gamefactory working directory)."""
    path = path.resolve()
    try:
        return str(path.relative_to(_CLI_DIR.resolve()))
    except ValueError:
        pass
    try:
        return "../" + str(path.relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _asset_lookup(assets: list[AssetSpec], ref: str) -> AssetSpec | None:
    key = (ref or "").strip()
    if not key:
        return None
    for asset in assets:
        if asset.name == key or (asset.id and asset.id == key):
            return asset
    return None


def effective_style_anchor_kind(spec: AssetSpec) -> str:
    """Return normalized kind: asset, visual_reference, or empty (anchor candidate)."""
    kind = (spec.style_anchor_kind or "").strip().lower()
    if kind:
        return kind
    if (spec.style_anchor or "").strip():
        return "asset"
    return ""


def is_style_group_anchor(spec: AssetSpec, assets: list[AssetSpec]) -> bool:
    """True when this asset is the style anchor for its group (does not img2img from itself).

    v1 rules:
    - Followers set ``style_anchor`` to another asset name/id, or ``style_anchor_kind:
      visual_reference`` (external north-star — not an in-brief anchor asset).
    - Anchor candidates have empty ``style_anchor`` and kind asset/empty; default anchor
      when no member points elsewhere. Multiple empty-anchor members in one group are all
      treated as anchors (none receive style img2img until followers declare ``style_anchor``).
    """
    group = (spec.style_group or "").strip()
    if not group:
        return False
    kind = effective_style_anchor_kind(spec)
    if kind == "visual_reference":
        return False
    anchor_ref = (spec.style_anchor or "").strip()
    if anchor_ref:
        target = _asset_lookup(assets, anchor_ref)
        if target and (target.name == spec.name or (target.id and target.id == spec.id)):
            return True
        return False
    group_members = [a for a in assets if (a.style_group or "").strip() == group]
    for member in group_members:
        if member.name == spec.name:
            continue
        ref = (member.style_anchor or "").strip()
        if not ref or effective_style_anchor_kind(member) == "visual_reference":
            continue
        target = _asset_lookup(assets, ref)
        if target and (target.name == spec.name or (target.id and target.id == spec.id)):
            return True
    return True


def _resolve_asset_raw_path(target: AssetSpec, brief_path: Path | None) -> str | None:
    """CLI-relative path to an asset's ``_raw.png`` for img2img reference."""
    try:
        file_key = resolve_asset_file_key(target)
    except ValueError:
        return None
    if brief_path is None:
        return None
    from project_paths import default_paths_for_brief

    paths = default_paths_for_brief(brief_path)
    raw = (paths["output_dir"] / f"{file_key}_raw.png").resolve()
    return _cli_relative(raw)


def should_use_style_img2img(
    spec: AssetSpec,
    *,
    project: ProjectContext,
    assets: list[AssetSpec],
) -> bool:
    """Whether still ``image.generate`` should use style-group ``--reference-image``.

    False for ``character_pose``, video animation clips, explicit opt-out, assets outside
    a style group, and the group's anchor asset itself.
    """
    if spec.type == AssetType.CHARACTER_POSE:
        return False
    if is_video_animation(spec):
        return False
    if spec.type not in STYLE_IMG2IMG_ALLOWED_TYPES:
        return False
    if spec.use_style_img2img is False:
        return False
    if not (spec.style_group or "").strip():
        return False
    if is_style_group_anchor(spec, assets):
        return False
    kind = effective_style_anchor_kind(spec)
    if kind == "visual_reference":
        return bool((project.visual_reference or "").strip())
    if kind == "asset":
        return _asset_lookup(assets, spec.style_anchor) is not None
    return False


def should_use_kit_style_img2img(spec: AssetSpec) -> bool:
    """Kit-internal style: N≥2 items follow items[0] raw unless opted out.

    Orthogonal to cross-asset ``style_group`` / ``STYLE_IMG2IMG_ALLOWED_TYPES``.
    """
    if spec.type != AssetType.ICON_KIT:
        return False
    if spec.use_style_img2img is False:
        return False
    return len(spec.items) >= 2


def resolve_style_img2img_path(
    spec: AssetSpec,
    *,
    project: ProjectContext,
    assets: list[AssetSpec],
    brief_path: Path | None = None,
) -> str | None:
    """Resolved ``--reference-image`` path for style img2img, or None when disabled."""
    if not should_use_style_img2img(spec, project=project, assets=assets):
        return None
    identity_ref = (spec.identity_anchor or "").strip()
    if identity_ref:
        identity_target = _asset_lookup(assets, identity_ref)
        if identity_target is not None:
            path = _resolve_asset_raw_path(identity_target, brief_path)
            if path is not None:
                return path
    kind = effective_style_anchor_kind(spec)
    if kind == "visual_reference":
        ref = (project.visual_reference or "").strip()
        if not ref:
            return None
        if brief_path is not None:
            from visual_target import resolve_visual_reference_path

            resolved = resolve_visual_reference_path(brief_path)
            if resolved is not None:
                return _cli_relative(resolved)
        return ref
    target = _asset_lookup(assets, spec.style_anchor)
    if target is None:
        return None
    return _resolve_asset_raw_path(target, brief_path)


def normalize_art_tokens(raw: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse project.art_tokens — known keys type-checked; unknown keys passthrough."""
    errors: list[str] = []
    if raw is None:
        return None, errors
    if not isinstance(raw, dict):
        errors.append("project.art_tokens must be an object")
        return None, errors
    if not raw:
        return None, errors

    result: dict[str, Any] = {}
    known = frozenset({"line", "palette", "forbid", "silhouette"})

    for key in ("line", "silhouette"):
        if key not in raw:
            continue
        val = raw[key]
        if not isinstance(val, str):
            errors.append(f"project.art_tokens.{key} must be a string")
            continue
        stripped = val.strip()
        if stripped:
            result[key] = stripped

    if "palette" in raw:
        val = raw["palette"]
        if isinstance(val, str):
            stripped = val.strip()
            if stripped:
                result["palette"] = stripped
        elif isinstance(val, list):
            items = [str(item).strip() for item in val if str(item).strip()]
            if items:
                result["palette"] = items
        else:
            errors.append("project.art_tokens.palette must be a string or list of strings")

    if "forbid" in raw:
        val = raw["forbid"]
        if not isinstance(val, list):
            errors.append("project.art_tokens.forbid must be a list of strings")
        else:
            items = [str(item).strip() for item in val if str(item).strip()]
            if items:
                result["forbid"] = items

    for key, val in raw.items():
        if key not in known:
            result[key] = val

    if not result:
        return None, errors
    return result, errors


def audit_art_tokens(project: ProjectContext) -> list[str]:
    """Validate project.art_tokens types (optional field)."""
    return list(project._art_tokens_errors)


def audit_style_groups(
    project: ProjectContext,
    assets: list[AssetSpec],
    *,
    brief_path: Path | None = None,
) -> list[str]:
    """Validate style_group / style_anchor fields (v1).

    Old briefs with no ``style_*`` fields on any asset produce no errors from this helper.
    """
    has_any_style = any(
        (a.style_group or "").strip()
        or (a.style_anchor_kind or "").strip()
        or (a.style_anchor or "").strip()
        or (a.identity_anchor or "").strip()
        or a.use_style_img2img is not None
        for a in assets
    )

    errors: list[str] = []
    for spec in assets:
        identity_ref = (spec.identity_anchor or "").strip()
        if identity_ref and _asset_lookup(assets, identity_ref) is None:
            errors.append(
                f"Asset '{spec.name}' identity_anchor '{identity_ref}' not found in assets[]"
            )

    if not has_any_style:
        return errors

    for spec in assets:
        kind_raw = (spec.style_anchor_kind or "").strip().lower()
        if kind_raw and kind_raw not in STYLE_ANCHOR_KINDS:
            errors.append(
                f"Asset '{spec.name}' style_anchor_kind must be 'asset' or 'visual_reference' "
                f"(got '{spec.style_anchor_kind}')"
            )
            continue

        kind = effective_style_anchor_kind(spec)
        anchor_ref = (spec.style_anchor or "").strip()

        if kind == "asset" and anchor_ref:
            if _asset_lookup(assets, anchor_ref) is None:
                errors.append(
                    f"Asset '{spec.name}' style_anchor '{anchor_ref}' not found in assets[]"
                )

        if kind == "visual_reference":
            ref = (project.visual_reference or "").strip()
            if not ref:
                errors.append(
                    f"Asset '{spec.name}' style_anchor_kind visual_reference requires "
                    "project.visual_reference"
                )
            elif brief_path is not None:
                from visual_target import resolve_visual_reference_path

                if resolve_visual_reference_path(brief_path) is None:
                    errors.append(
                        f"Asset '{spec.name}' style group uses visual_reference anchor but "
                        f"project.visual_reference file not found: {ref}"
                    )
            elif not looks_like_visual_reference_path(ref):
                errors.append(
                    f"Asset '{spec.name}' style_anchor_kind visual_reference requires "
                    "project.visual_reference as an image file path"
                )

    return errors


def audit_brief_for_export(
    project: ProjectContext,
    assets: list[AssetSpec],
    *,
    animation_graphs: list[CharacterAnimationGraph] | None = None,
    brief_path: Path | None = None,
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
    ids: list[str] = []
    for spec in assets:
        if not spec.name.strip():
            errors.append("Every asset needs a non-empty 'name'")
            continue
        if spec.name in names:
            errors.append(f"Duplicate asset name '{spec.name}'")
        names.append(spec.name)

        aid = (spec.id or "").strip()
        if not aid:
            errors.append(
                f"Asset '{spec.name}' missing required field 'id' "
                "(English file slug, e.g. referee_run)"
            )
        elif not ASSET_ID_PATTERN.match(aid):
            errors.append(
                f"Asset '{spec.name}' id '{aid}' must match ^[a-z][a-z0-9_]*$"
            )
        elif aid in ids:
            errors.append(f"Duplicate asset id '{aid}'")
        else:
            ids.append(aid)

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
        if spec.type == AssetType.ICON_KIT and spec.items:
            # grid is ignored for generation (per-item singles); invalid grid is not fatal.
            if (spec.grid or "").strip():
                try:
                    parse_icon_grid(spec.grid)
                except ValueError as exc:
                    errors.append(f"Asset '{spec.name}' invalid grid (ignored at runtime): {exc}")
            blank = [i for i in spec.items if not i.id.strip()]
            if blank:
                errors.append(f"Asset '{spec.name}' icon_kit items must have non-empty id")
            # Explicit object ids must be unique among themselves and must not
            # collide with a string item's id. Plain string duplicates still OK
            # (slug suffixes). Group by authored id:
            by_id: dict[str, list[IconKitItem]] = {}
            for item in spec.items:
                by_id.setdefault(item.id.strip(), []).append(item)
            dupes = [
                key
                for key, group in by_id.items()
                if len(group) > 1 and any(i.id_from_object for i in group)
            ]
            if dupes:
                errors.append(
                    f"Asset '{spec.name}' icon_kit duplicate item id(s): {', '.join(sorted(dupes))}"
                )

        if (spec.generate_tier or "").strip() and spec.generate_tier not in (
            "default",
            "bulk",
        ):
            errors.append(
                f"Asset '{spec.name}' generate_tier must be 'default' or 'bulk'"
            )

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
    errors.extend(audit_visual_reference(project, brief_path=brief_path))
    errors.extend(audit_style_groups(project, assets, brief_path=brief_path))
    errors.extend(audit_art_tokens(project))

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
    """Look up by display ``name`` or English ``id`` (CLI --asset accepts either)."""
    key = name.strip()
    for asset in assets:
        if asset.name == key or (asset.id and asset.id == key):
            return asset
    known = ", ".join(f"{a.name}({a.id})" if a.id else a.name for a in assets)
    raise ValueError(f"Asset '{name}' not found in brief. Known: {known}")
