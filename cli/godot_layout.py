"""Apply production.layout placements into Godot main-scene fragments.

Consumes layout data only — no genre heuristics. Callers supply viewport and
optional texture res paths (after import/copy).
"""

from __future__ import annotations

import re
from typing import Any


def prop_texture_res_path(asset: str) -> str:
    """Conventional Godot path for a placed prop texture."""
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", (asset or "prop").strip()) or "prop"
    return f"assets/props/{safe}_nobg.png"


def sanitize_prop_node_name(asset: str) -> str:
    """Godot node name from placement asset id/name."""
    raw = (asset or "Prop").strip() or "Prop"
    parts = re.split(r"[_\-\s]+", raw)
    name = "".join(p.capitalize() for p in parts if p) or "Prop"
    if name[0].isdigit():
        name = f"Prop{name}"
    return name


def xy_norm_to_pixels(xy_norm: list[Any] | tuple[Any, ...], viewport: dict[str, Any]) -> tuple[int, int]:
    w = int(viewport.get("width", 1280) or 1280)
    h = int(viewport.get("height", 720) or 720)
    x = float(xy_norm[0]) if len(xy_norm) >= 1 else 0.5
    y = float(xy_norm[1]) if len(xy_norm) >= 2 else 0.5
    return int(round(x * w)), int(round(y * h))


def layout_placements(layout: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(layout, dict):
        return []
    raw = layout.get("placements")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        asset = str(item.get("asset", "")).strip()
        xy = item.get("xy_norm")
        if not asset or not isinstance(xy, list) or len(xy) < 2:
            continue
        out.append(item)
    return out


def build_layout_world_fragments(
    layout: dict[str, Any] | None,
    viewport: dict[str, Any],
    *,
    texture_by_asset: dict[str, str] | None = None,
    ext_id_start: int = 10,
) -> tuple[list[str], list[str], int]:
    """Build ext_resource + node lines for props under an existing World parent.

    Returns (ext_resource_lines, node_lines, next_ext_id).
    Node lines use parent=\"World\". Texture paths come from texture_by_asset
    when present; otherwise the conventional prop_texture_res_path is referenced
    (file may be missing until import).
    """
    textures = texture_by_asset or {}
    ext_lines: list[str] = []
    node_lines: list[str] = []
    next_id = ext_id_start
    used_names: set[str] = set()

    for placement in layout_placements(layout):
        asset = str(placement.get("asset", "")).strip()
        xy = placement.get("xy_norm") or [0.5, 0.5]
        px, py = xy_norm_to_pixels(xy, viewport)
        base_name = sanitize_prop_node_name(asset)
        node_name = base_name
        n = 2
        while node_name in used_names:
            node_name = f"{base_name}{n}"
            n += 1
        used_names.add(node_name)

        res = textures.get(asset) or prop_texture_res_path(asset)
        ext_id = f"{next_id}_prop"
        next_id += 1
        ext_lines.append(f'[ext_resource type="Texture2D" path="res://{res}" id="{ext_id}"]')
        node_lines.extend(
            [
                f'[node name="{node_name}" type="Sprite2D" parent="World"]',
                f"position = Vector2({px}, {py})",
                f'texture = ExtResource("{ext_id}")',
                "",
            ]
        )

    return ext_lines, node_lines, next_id
