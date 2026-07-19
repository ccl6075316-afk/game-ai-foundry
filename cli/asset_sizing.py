"""Generation image_size + display_size validation (godogen sizing rules)."""

from __future__ import annotations

import re
from typing import Any

from brief import AssetSpec, AssetType, ProjectContext
from display_size import DisplaySize, display_size_from_viewport

# Known model → size multiple (optional; unknown models rely on error-driven snap).
MODEL_SIZE_MULTIPLES: dict[str, int] = {
    "openai/gpt-image-2": 16,
    "openai/gpt-image-1": 16,
}

API_SIZE_MULTIPLE = 16
_DIVISIBLE_RE = re.compile(r"divisible by\s+(\d+)|multiple of\s+(\d+)", re.I)


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
        # Avoid empty-key matching: every str.endswith("") is True.
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


def resolve_generation_image_size(
    spec: AssetSpec,
    project: ProjectContext,
    *,
    model: str | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """API generation size — separate from in-game display.

    Snaps only when the active model/config declares ``size_multiple``.
    Unknown APIs keep raw sizes; generate may snap after a 400 error.
    """
    display = spec.display_size if not spec.display_size.is_empty() else None
    usage = (spec.usage or "").strip()

    if spec.type in (AssetType.CHARACTER, AssetType.CHARACTER_POSE):
        edge = max(display.width, display.height) if display else 128
        gen = max(1024, min(2048, edge * 8))
        size = f"{gen}x{gen}"
    elif spec.type == AssetType.ICON_KIT:
        size = "1024x1024"
    elif spec.type == AssetType.TEXTURE:
        edge = max(display.width, display.height) if display else 128
        gen = max(128, min(512, edge * 2))
        size = f"{gen}x{gen}"
    elif spec.type == AssetType.BACKGROUND:
        if display:
            size = display.to_api_string()
        elif usage == "parallax_layer":
            vp = display_size_from_viewport(project.viewport)
            size = f"{max(vp.width * 2, vp.width)}x{vp.height}"
        else:
            size = display_size_from_viewport(project.viewport).to_api_string()
    else:
        edge = max(display.width, display.height) if display else 128
        gen = max(512, min(1024, edge * 8))
        size = f"{gen}x{gen}"

    multiple = size_multiple_for_model(model or "", config)
    if multiple:
        return snap_api_image_size(size, multiple=multiple)
    return size


def audit_display_size_consistency(
    assets: list[AssetSpec],
    *,
    animation_graphs: list[Any] | None = None,
    viewport: dict[str, Any] | None = None,
) -> list[str]:
    """Godogen: same character family shares one in-game display size."""
    errors: list[str] = []
    by_name = {a.name: a for a in assets}

    def size_key(spec: AssetSpec) -> tuple[int, int] | None:
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
