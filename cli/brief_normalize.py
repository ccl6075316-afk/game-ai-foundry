"""Brief document normalization; independent of model classes and export audit."""
from __future__ import annotations
from typing import Any

def normalize_id_list(raw: Any) -> list[str]:
    """Strip, drop empties, preserve order with unique string ids."""
    if raw is None or not isinstance(raw, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        label = str(item).strip()
        if not label or label in seen:
            continue
        seen.add(label)
        out.append(label)
    return out


def normalize_ui_panels(raw: Any) -> list[dict[str, Any]]:
    """Normalize optional project.ui_panels — drop entries without id and title."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        panel_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not panel_id or not title:
            continue
        entry: dict[str, Any] = {"id": panel_id, "title": title}
        kind = str(item.get("kind", "")).strip()
        if kind:
            entry["kind"] = kind
        anchor = str(item.get("anchor", "")).strip()
        if anchor:
            entry["anchor"] = anchor
        raw_slots = item.get("slots")
        if isinstance(raw_slots, list):
            slots = [str(s).strip() for s in raw_slots if str(s).strip()]
            if slots:
                entry["slots"] = slots
        notes = str(item.get("notes", "")).strip()
        if notes:
            entry["notes"] = notes
        out.append(entry)
    return out


def normalize_scenes(raw: Any) -> list[dict[str, Any]]:
    """Normalize optional project.scenes — drop entries without id and title."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        scene_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not scene_id or not title:
            continue
        path = str(item.get("path", "")).strip()
        if path:
            entry = {"id": scene_id, "title": title, "path": path.replace("\\", "/")}
            out.append(entry)
            continue
        entry: dict[str, Any] = {"id": scene_id, "title": title}
        summary = str(item.get("summary", "")).strip()
        if summary:
            entry["summary"] = summary
        panel_ids = normalize_id_list(item.get("ui_panel_ids"))
        if panel_ids:
            entry["ui_panel_ids"] = panel_ids
        notes = str(item.get("notes", "")).strip()
        if notes:
            entry["notes"] = notes
        vr = str(item.get("visual_reference", "")).strip()
        # Keep non-empty values (path or prose) — same as project.visual_reference.
        # Prose is rejected by audit_visual_reference and cleared into art_direction
        # by apply_deterministic_visual_reference_fixes; do not silently drop here.
        if vr:
            entry["visual_reference"] = vr
        out.append(entry)
    return out


def normalize_systems(raw: Any) -> list[dict[str, Any]]:
    """Normalize optional project.systems — drop entries without id and title."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        system_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not system_id or not title:
            continue
        path = str(item.get("path", "")).strip()
        if path:
            out.append(
                {
                    "id": system_id,
                    "title": title,
                    "path": path.replace("\\", "/"),
                }
            )
            continue
        entry: dict[str, Any] = {"id": system_id, "title": title}
        summary = str(item.get("summary", "")).strip()
        if summary:
            entry["summary"] = summary
        notes = str(item.get("notes", "")).strip()
        if notes:
            entry["notes"] = notes
        out.append(entry)
    return out


def normalize_assets(raw: Any) -> list[dict[str, Any]]:
    """Normalize assets[] — preserve catalog refs (id/name/path only)."""
    if not isinstance(raw, list):
        return []
    from brief_shards import is_catalog_ref

    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        if path and is_catalog_ref(item, kind="asset"):
            aid = str(item.get("id", "")).strip()
            name = str(item.get("name", "")).strip() or aid
            if aid and name:
                out.append({"id": aid, "name": name, "path": path.replace("\\", "/")})
            continue
        out.append(item)
    return out


def normalize_asset_states(raw: Any) -> list[str]:
    """Strip, drop empties, preserve order with unique entries."""
    return normalize_id_list(raw)
