"""Generation image_size + display_size validation (godogen sizing rules)."""

from __future__ import annotations

from typing import Any

from brief import AssetSpec, AssetType, ProjectContext
from display_size import DisplaySize, display_size_from_viewport


def resolve_generation_image_size(spec: AssetSpec, project: ProjectContext) -> str:
    """API generation size — separate from in-game display."""
    display = spec.display_size if not spec.display_size.is_empty() else None
    usage = (spec.usage or "").strip()

    if spec.type in (AssetType.CHARACTER, AssetType.CHARACTER_POSE):
        edge = max(display.width, display.height) if display else 128
        gen = max(1024, min(2048, edge * 8))
        return f"{gen}x{gen}"

    if spec.type == AssetType.ICON_KIT:
        return "1024x1024"

    if spec.type == AssetType.TEXTURE:
        edge = max(display.width, display.height) if display else 128
        gen = max(128, min(512, edge * 2))
        return f"{gen}x{gen}"

    if spec.type == AssetType.BACKGROUND:
        if display:
            return display.to_api_string()
        if usage == "parallax_layer":
            vp = display_size_from_viewport(project.viewport)
            return f"{max(vp.width * 2, vp.width)}x{vp.height}"
        return display_size_from_viewport(project.viewport).to_api_string()

    edge = max(display.width, display.height) if display else 128
    gen = max(512, min(1024, edge * 8))
    return f"{gen}x{gen}"


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
