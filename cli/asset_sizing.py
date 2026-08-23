"""Generation image_size + display_size validation (godogen sizing rules)."""

from __future__ import annotations

import re
from typing import Any

from brief import AssetSpec, AssetType, ProjectContext
from display_size import DisplaySize, display_size_from_viewport, parse_display_size

# Known model → size multiple (optional; unknown models rely on error-driven snap).
MODEL_SIZE_MULTIPLES: dict[str, int] = {
    "openai/gpt-image-2": 16,
    "openai/gpt-image-1": 16,
}

API_SIZE_MULTIPLE = 16
_DIVISIBLE_RE = re.compile(r"divisible by\s+(\d+)|multiple of\s+(\d+)", re.I)

# Long-edge caps per asset family (generation API pixels).
_GEN_LONG_CHARACTER = (1024, 2048, 8)  # min, max, display_edge_multiplier
_GEN_LONG_TEXTURE = (128, 512, 2)
_GEN_LONG_DEFAULT = (512, 1024, 8)
_MIN_GEN_SHORT = 512

_HORIZONTAL_CONTENT_CLASSES = frozenset({"weapon", "tool"})


def snap_dim_to_multiple(value: int, multiple: int = API_SIZE_MULTIPLE) -> int:
    """Round a dimension to the nearest positive multiple (min = multiple)."""
    if value <= 0:
        return multiple
    rounded = int(round(value / multiple) * multiple)
    return max(multiple, rounded)


def snap_api_image_size(size: str, *, multiple: int = API_SIZE_MULTIPLE) -> str:
    """Normalize ``WxH`` so both sides are divisible by ``multiple``."""
    raw = (size or "").strip().lower().replace(" ", "")
    if "x" not in raw:
        return size
    left, right = raw.split("x", 1)
    try:
        w, h = int(left), int(right)
    except ValueError:
        return size
    return f"{snap_dim_to_multiple(w, multiple)}x{snap_dim_to_multiple(h, multiple)}"


def size_multiple_for_model(model: str, config: dict[str, Any] | None = None) -> int | None:
    """Return required size multiple from config or known model profile."""
    cfg = (config or {}).get("image") if isinstance(config, dict) else None
    if isinstance(cfg, dict):
        constraints = cfg.get("constraints")
        if isinstance(constraints, dict) and constraints.get("size_multiple"):
            try:
                return int(constraints["size_multiple"])
            except (TypeError, ValueError):
                pass
    key = (model or "").strip().lower()
    if not key:
        return None
    if key in MODEL_SIZE_MULTIPLES:
        return MODEL_SIZE_MULTIPLES[key]
    for mid, mult in MODEL_SIZE_MULTIPLES.items():
        if key.endswith(mid) or (mid.endswith(key) and len(key) >= 8):
            return mult
    return None


def parse_size_multiple_from_error(message: str) -> int | None:
    m = _DIVISIBLE_RE.search(message or "")
    if not m:
        return None
    for g in m.groups():
        if g:
            return int(g)
    return None


def parse_aspect_ratio(raw: str) -> tuple[int, int]:
    """Parse ``16:9``, ``16/9``, or ``1920x1080`` style ratios."""
    s = (raw or "1:1").strip().lower().replace(" ", "")
    if not s:
        return 1, 1
    for sep in (":", "/", "x"):
        if sep in s:
            left, right = s.split(sep, 1)
            try:
                aw, ah = int(left), int(right)
                if aw > 0 and ah > 0:
                    return aw, ah
            except ValueError:
                break
    return 1, 1


def effective_aspect_ratio(spec: AssetSpec) -> tuple[int, int]:
    """Aspect for generation — weapon/tool default horizontal unless brief overrides."""
    cc = (spec.content_class or "").strip().lower()
    if cc in _HORIZONTAL_CONTENT_CLASSES and (spec.aspect_ratio or "1:1").strip() in ("", "1:1"):
        return 16, 9
    return parse_aspect_ratio(spec.aspect_ratio)


def _dims_from_long_edge(
    long_edge: int,
    aspect_w: int,
    aspect_h: int,
    *,
    min_short: int = _MIN_GEN_SHORT,
) -> tuple[int, int]:
    if aspect_w >= aspect_h:
        w = long_edge
        h = max(min_short, int(round(long_edge * aspect_h / aspect_w)))
    else:
        h = long_edge
        w = max(min_short, int(round(long_edge * aspect_w / aspect_h)))
    return max(1, w), max(1, h)


def _long_edge_from_display(
    display: DisplaySize | None,
    *,
    default_edge: int,
    min_long: int,
    max_long: int,
    multiplier: int,
) -> int:
    edge = max(display.width, display.height) if display and not display.is_empty() else default_edge
    return max(min_long, min(max_long, edge * multiplier))


def _parse_baseline(project: ProjectContext) -> tuple[float, DisplaySize] | None:
    raw = getattr(project, "size_baseline", None) or {}
    if not isinstance(raw, dict):
        return None
    try:
        base_len = float(raw.get("real_length_cm") or 0)
    except (TypeError, ValueError):
        return None
    if base_len <= 0:
        return None
    base_disp = parse_display_size(raw.get("display_size"))
    if not base_disp or base_disp.is_empty():
        return None
    return base_len, base_disp


def resolve_effective_display_size(spec: AssetSpec, project: ProjectContext) -> DisplaySize:
    """Canonical in-game pixels — baseline ratio, else brief display_size."""
    parsed = _parse_baseline(project)
    asset_len = float(spec.real_length_cm or 0)
    if parsed and asset_len > 0:
        base_len, base_disp = parsed
        ratio = asset_len / base_len
        h = max(1, int(round(base_disp.height * ratio)))
        aw, ah = effective_aspect_ratio(spec)
        w = max(1, int(round(h * aw / ah)))
        return DisplaySize(w, h)
    if not spec.display_size.is_empty():
        return spec.display_size
    return DisplaySize.empty()


def resolve_generation_image_size(
    spec: AssetSpec,
    project: ProjectContext,
    *,
    model: str | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """API generation size — separate from in-game display.

    Uses optional ``generation_size``, then aspect-aware scaling from effective display.
  """
    if not spec.generation_size.is_empty():
        size = spec.generation_size.to_api_string()
    else:
        display = resolve_effective_display_size(spec, project)
        if display.is_empty() and not spec.display_size.is_empty():
            display = spec.display_size
        usage = (spec.usage or "").strip()
        aspect = effective_aspect_ratio(spec)

        if spec.type in (AssetType.CHARACTER, AssetType.CHARACTER_POSE):
            long_edge = _long_edge_from_display(
                display, default_edge=128, min_long=1024, max_long=2048, multiplier=8
            )
            w, h = _dims_from_long_edge(long_edge, aspect[0], aspect[1])
            size = f"{w}x{h}"
        elif spec.type == AssetType.ICON_KIT:
            size = "1024x1024"
        elif spec.type == AssetType.TEXTURE:
            long_edge = _long_edge_from_display(
                display, default_edge=128, min_long=128, max_long=512, multiplier=2
            )
            w, h = _dims_from_long_edge(long_edge, aspect[0], aspect[1], min_short=128)
            size = f"{w}x{h}"
        elif spec.type == AssetType.BACKGROUND:
            if display and not display.is_empty():
                size = display.to_api_string()
            elif usage == "parallax_layer":
                vp = display_size_from_viewport(project.viewport)
                size = f"{max(vp.width * 2, vp.width)}x{vp.height}"
            else:
                size = display_size_from_viewport(project.viewport).to_api_string()
        else:
            long_edge = _long_edge_from_display(
                display, default_edge=128, min_long=512, max_long=1024, multiplier=8
            )
            w, h = _dims_from_long_edge(long_edge, aspect[0], aspect[1])
            size = f"{w}x{h}"

    multiple = size_multiple_for_model(model or "", config)
    if multiple:
        return snap_api_image_size(size, multiple=multiple)
    return size


def audit_brief_size_warnings(
    project: ProjectContext,
    assets: list[AssetSpec],
) -> list[str]:
    """Soft warnings for sizing contract mismatches (do not block export)."""
    warnings: list[str] = []
    display_groups: dict[tuple[int, int], list[tuple[str, float]]] = {}

    for spec in assets:
        aw, ah = effective_aspect_ratio(spec)
        if spec.type in (AssetType.CHARACTER, AssetType.CHARACTER_POSE) and (aw, ah) != (1, 1):
            gen = resolve_generation_image_size(spec, project)
            parts = gen.lower().split("x")
            if len(parts) == 2 and parts[0] == parts[1]:
                warnings.append(
                    f"Asset '{spec.name}' aspect_ratio={spec.aspect_ratio} but "
                    f"derived generation image_size is square ({gen})"
                )

        if float(spec.real_length_cm or 0) > 0 and not spec.display_size.is_empty():
            key = (spec.display_size.width, spec.display_size.height)
            display_groups.setdefault(key, []).append((spec.name, float(spec.real_length_cm)))

    for (w, h), entries in display_groups.items():
        lengths = {e[1] for e in entries}
        if len(entries) > 1 and len(lengths) > 1:
            names = ", ".join(e[0] for e in entries[:4])
            warnings.append(
                f"Assets share display_size {w}x{h} but differ in real_length_cm ({names}…); "
                "consider size_baseline derive or distinct display_size"
            )

    return warnings


def audit_display_size_consistency(
    assets: list[AssetSpec],
    *,
    animation_graphs: list[Any] | None = None,
    viewport: dict[str, Any] | None = None,
    project: ProjectContext | None = None,
) -> list[str]:
    """Godogen: same character family shares one in-game display size."""
    errors: list[str] = []
    by_name = {a.name: a for a in assets}

    def size_key(spec: AssetSpec) -> tuple[int, int] | None:
        if project is not None:
            eff = resolve_effective_display_size(spec, project)
            if not eff.is_empty():
                return (eff.width, eff.height)
        if spec.display_size.is_empty():
            return None
        return (spec.display_size.width, spec.display_size.height)

    for spec in assets:
        ref_name = spec.reference_asset.strip()
        if not ref_name:
            continue
        ref = by_name.get(ref_name)
        if ref is None:
            continue
        child_sz, ref_sz = size_key(spec), size_key(ref)
        if child_sz and ref_sz and child_sz != ref_sz:
            errors.append(
                f"Asset '{spec.name}' display_size {child_sz[0]}x{child_sz[1]} must match "
                f"reference_asset '{ref_name}' ({ref_sz[0]}x{ref_sz[1]} in-game pixels)"
            )

    for graph in animation_graphs or []:
        char = getattr(graph, "character_asset", "") or ""
        if not char or char not in by_name:
            continue
        family = [a for a in assets if a.name == char or a.reference_asset.strip() == char]
        sizes = {size_key(a) for a in family if size_key(a)}
        if len(sizes) > 1:
            parts = ", ".join(f"{w}x{h}" for w, h in sorted(sizes))
            errors.append(
                f"animation_graphs '{char}': all clips must share display_size (got {parts})"
            )

    vp = display_size_from_viewport(viewport)
    for spec in assets:
        if spec.display_size.is_empty():
            continue
        if spec.type == AssetType.TEXTURE and spec.usage.strip() == "tile_texture":
            edge = max(spec.display_size.width, spec.display_size.height)
            if edge > min(vp.width, vp.height) // 2:
                errors.append(
                    f"Asset '{spec.name}' tile_texture display_size looks too large "
                    f"for a repeating tile ({edge}px); use single-tile dimensions"
                )

    return errors


def effective_display_dict(spec: AssetSpec, project: ProjectContext) -> dict[str, int] | None:
    """Resolved in-game display pixels for pipeline / Godot handoff."""
    eff = resolve_effective_display_size(spec, project)
    return eff.to_dict() if not eff.is_empty() else None


def effective_display_dict(spec: AssetSpec, project: ProjectContext) -> dict[str, int] | None:
    """Resolved in-game display pixels for pipeline / Godot handoff."""
    eff = resolve_effective_display_size(spec, project)
    return eff.to_dict() if not eff.is_empty() else None
