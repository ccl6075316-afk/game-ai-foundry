"""Brief catalog refs and shard file IO (scenes / systems / assets)."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any, Literal

from project_paths import project_root_for_brief

CATALOG_SCENE_KEYS = frozenset({"id", "title", "path"})
CATALOG_SYSTEM_KEYS = frozenset({"id", "title", "path"})
CATALOG_ASSET_KEYS = frozenset({"id", "name", "path"})

_SCENE_BODY_HINT_KEYS = frozenset(
    {
        "summary",
        "notes",
        "ui_panel_ids",
        "visual_reference",
        "ui_panels",
        "asset_ids",
        "plate_fill",
    }
)
_SYSTEM_BODY_HINT_KEYS = frozenset({"summary", "notes", "tuning"})
_ASSET_BODY_HINT_KEYS = frozenset(
    {
        "type",
        "usage",
        "display_size",
        "description",
        "usage_description",
        "generate_method",
        "items",
        "grid",
        "aspect_ratio",
        "action",
        "reference_asset",
        "animation_method",
        "duration_seconds",
        "sprite_frames",
        "video_model",
        "video_resolution",
        "video_ratio",
        "generate_audio",
        "watermark",
        "animation_name",
        "animation_loop",
        "parallax_order",
        "scroll_factor",
        "audio_loop",
        "style_group",
        "style_anchor_kind",
        "style_anchor",
        "identity_anchor",
        "use_style_img2img",
        "generate_tier",
        "content_class",
        "states",
        "state",
        "scene_ids",
        "system_ids",
    }
)

_BODY_HINT_KEYS = _SCENE_BODY_HINT_KEYS | _SYSTEM_BODY_HINT_KEYS | _ASSET_BODY_HINT_KEYS

DESCRIPTION_MAX_CHARS = 800
GAMEPLAY_LOOP_MAX_CHARS = 1200

Kind = Literal["scene", "system", "asset"]


def _nonempty_str(value: Any) -> str:
    return str(value or "").strip()


def _body_keys_for_kind(kind: Kind) -> frozenset[str]:
    if kind == "scene":
        return _SCENE_BODY_HINT_KEYS
    if kind == "system":
        return _SYSTEM_BODY_HINT_KEYS
    return _ASSET_BODY_HINT_KEYS


def _catalog_keys_for_kind(kind: Kind) -> frozenset[str]:
    if kind == "scene":
        return CATALOG_SCENE_KEYS
    if kind == "system":
        return CATALOG_SYSTEM_KEYS
    return CATALOG_ASSET_KEYS


def _has_body_hints(entry: dict[str, Any], kind: Kind) -> bool:
    hints = _body_keys_for_kind(kind)
    catalog = _catalog_keys_for_kind(kind)
    if any(key in entry for key in hints):
        for key in hints:
            val = entry.get(key)
            if val is None:
                continue
            if isinstance(val, (list, dict)):
                if val:
                    return True
            elif _nonempty_str(val):
                return True
    for key in entry:
        if key in catalog:
            continue
        if _nonempty_str(entry.get(key)) or (
            isinstance(entry.get(key), (list, dict)) and entry.get(key)
        ):
            return True
    return False


def is_catalog_ref(entry: dict[str, Any], *, kind: Kind) -> bool:
    """True when entry is a thin catalog mapping (path + id + title/name, no body)."""
    if not isinstance(entry, dict):
        return False
    path = _nonempty_str(entry.get("path"))
    entry_id = _nonempty_str(entry.get("id"))
    if not path or not entry_id:
        return False
    if kind in ("scene", "system"):
        if not _nonempty_str(entry.get("title")):
            return False
    elif kind == "asset":
        name = _nonempty_str(entry.get("name"))
        if not name and not entry_id:
            return False
    if _has_body_hints(entry, kind):
        return False
    allowed = _catalog_keys_for_kind(kind)
    extra = set(entry.keys()) - allowed
    if extra:
        return False
    return True


def _legacy_entry(entry: dict[str, Any], *, kind: Kind) -> bool:
    if not isinstance(entry, dict):
        return False
    path = _nonempty_str(entry.get("path"))
    if path and is_catalog_ref(entry, kind=kind):
        return False
    return _has_body_hints(entry, kind) or (not path and _nonempty_str(entry.get("id")))


def is_legacy_scene_entry(entry: dict[str, Any]) -> bool:
    return _legacy_entry(entry, kind="scene")


def is_legacy_system_entry(entry: dict[str, Any]) -> bool:
    return _legacy_entry(entry, kind="system")


def is_legacy_asset_entry(entry: dict[str, Any]) -> bool:
    if not isinstance(entry, dict):
        return False
    path = _nonempty_str(entry.get("path"))
    if path and is_catalog_ref(entry, kind="asset"):
        return False
    return _has_body_hints(entry, "asset") or bool(_nonempty_str(entry.get("type")))


def resolve_shard_path(project_root: Path, rel: str) -> Path:
    """Resolve POSIX ``rel`` under ``project_root``; reject path escape."""
    root = Path(project_root).resolve()
    rel_norm = str(rel or "").strip().replace("\\", "/")
    if not rel_norm or rel_norm.startswith("/"):
        raise ValueError(f"Invalid shard path: {rel!r}")
    parts = [p for p in rel_norm.split("/") if p]
    if any(p == ".." for p in parts):
        raise ValueError(f"Shard path must not escape project root: {rel!r}")
    resolved = (root.joinpath(*parts)).resolve()
    if not str(resolved).startswith(str(root)):
        raise ValueError(f"Shard path must stay under project root: {rel!r}")
    return resolved


def load_json_shard(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Shard must be a JSON object: {path}")
    return data


def save_json_shard(path: Path, data: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def project_root_for_brief_path(brief_path: Path) -> Path:
    root = project_root_for_brief(brief_path)
    if root is not None:
        return root
    return Path(brief_path).resolve().parent


def _iter_catalog_sections(brief: dict[str, Any]) -> list[tuple[str, Kind, list[Any]]]:
    project = brief.get("project") if isinstance(brief.get("project"), dict) else {}
    sections: list[tuple[str, Kind, list[Any]]] = []
    for key, kind in (("scenes", "scene"), ("systems", "system"), ("assets", "asset")):
        raw = brief.get(key)
        if raw is None and isinstance(project, dict):
            raw = project.get(key)
        if isinstance(raw, list):
            sections.append((key, kind, raw))
    assets_top = brief.get("assets")
    if isinstance(assets_top, list) and not any(s[0] == "assets" for s in sections):
        sections.append(("assets", "asset", assets_top))
    return sections


def audit_catalog_refs(brief: dict[str, Any], project_root: Path) -> list[str]:
    """Hard errors: missing shard file or id mismatch between ref and shard."""
    errors: list[str] = []
    root = Path(project_root).resolve()
    for section_key, kind, items in _iter_catalog_sections(brief):
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            if not is_catalog_ref(item, kind=kind):
                continue
            ref_id = _nonempty_str(item.get("id"))
            rel = _nonempty_str(item.get("path"))
            label = f"{section_key}[{ref_id or idx}]"
            try:
                shard_path = resolve_shard_path(root, rel)
            except ValueError as exc:
                errors.append(f"{label}: {exc}")
                continue
            if not shard_path.is_file():
                errors.append(f"{label}: shard file not found: {rel}")
                continue
            try:
                shard = load_json_shard(shard_path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{label}: cannot read shard: {exc}")
                continue
            shard_id = _nonempty_str(shard.get("id"))
            if shard_id and shard_id != ref_id:
                errors.append(
                    f"{label}: id mismatch — catalog '{ref_id}' vs shard '{shard_id}' in {rel}"
                )
    return errors


def audit_intro_budgets(brief: dict[str, Any]) -> list[str]:
    """Soft warnings for long project.description / gameplay_loop."""
    project = brief.get("project") if isinstance(brief.get("project"), dict) else brief
    if not isinstance(project, dict):
        return []
    warnings: list[str] = []
    desc = str(project.get("description", ""))
    if len(desc) > DESCRIPTION_MAX_CHARS:
        warnings.append(
            f"warning: project.description exceeds budget ({len(desc)} > {DESCRIPTION_MAX_CHARS} chars); "
            "move screen/system detail into scene/system shards"
        )
    loop = str(project.get("gameplay_loop", ""))
    if len(loop) > GAMEPLAY_LOOP_MAX_CHARS:
        warnings.append(
            f"warning: project.gameplay_loop exceeds budget ({len(loop)} > {GAMEPLAY_LOOP_MAX_CHARS} chars); "
            "move rules and tables into system shards or data files"
        )
    return warnings


def _minimal_legacy_asset(entry: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    aid = _nonempty_str(out.get("id"))
    if aid:
        out["id"] = aid
    name = _nonempty_str(out.get("name"))
    if name:
        out["name"] = name
    return out


def resolve_asset_specs(brief_path: Path) -> list[dict[str, Any]]:
    """Load asset specs from catalog shards or inline legacy entries."""
    brief_path = Path(brief_path).resolve()
    data = json.loads(brief_path.read_text(encoding="utf-8"))
    assets_raw = data.get("assets") or []
    if not isinstance(assets_raw, list):
        raise ValueError("Brief must contain an 'assets' array.")
    root = project_root_for_brief_path(brief_path)
    out: list[dict[str, Any]] = []
    for item in assets_raw:
        if not isinstance(item, dict):
            continue
        if is_catalog_ref(item, kind="asset"):
            rel = _nonempty_str(item.get("path"))
            shard_path = resolve_shard_path(root, rel)
            body = load_json_shard(shard_path)
            ref_id = _nonempty_str(item.get("id"))
            if ref_id and not _nonempty_str(body.get("id")):
                body = dict(body)
                body["id"] = ref_id
            name = _nonempty_str(item.get("name"))
            if name and not _nonempty_str(body.get("name")):
                body = dict(body)
                body["name"] = name
            out.append(body)
        else:
            out.append(_minimal_legacy_asset(item))
    return out


def _scene_shard_body(entry: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": _nonempty_str(entry.get("id")),
        "title": _nonempty_str(entry.get("title")),
    }
    for key in _SCENE_BODY_HINT_KEYS:
        if key in entry and entry[key] is not None and _nonempty_str(entry.get(key)):
            body[key] = entry[key]
        elif key in entry and isinstance(entry[key], (list, dict)) and entry[key]:
            body[key] = entry[key]
    return body


def _system_shard_body(entry: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": _nonempty_str(entry.get("id")),
        "title": _nonempty_str(entry.get("title")),
    }
    for key in _SYSTEM_BODY_HINT_KEYS:
        val = entry.get(key)
        if val is None:
            continue
        if isinstance(val, (list, dict)) and val:
            body[key] = val
        elif _nonempty_str(val):
            body[key] = val
    return body


def _asset_shard_body(entry: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in entry.items() if k != "path"}
    aid = _nonempty_str(body.get("id"))
    if aid:
        body["id"] = aid
    name = _nonempty_str(body.get("name")) or aid
    if name:
        body["name"] = name
    return body


def _catalog_ref_from_entry(entry: dict[str, Any], *, kind: Kind, rel_path: str) -> dict[str, Any]:
    ref_id = _nonempty_str(entry.get("id"))
    if kind == "asset":
        name = _nonempty_str(entry.get("name")) or ref_id
        return {"id": ref_id, "name": name, "path": rel_path}
    return {"id": ref_id, "title": _nonempty_str(entry.get("title")), "path": rel_path}


def _section_storage(brief: dict[str, Any], key: str) -> str:
    if isinstance(brief.get(key), list):
        return "top"
    project = brief.get("project")
    if isinstance(project, dict) and isinstance(project.get(key), list):
        return "project"
    return "top"


def _set_section(brief: dict[str, Any], key: str, value: list[dict[str, Any]]) -> None:
    if key == "assets":
        brief["assets"] = value
        return
    where = _section_storage(brief, key)
    if where == "project":
        project = brief.get("project")
        if not isinstance(project, dict):
            project = {}
            brief["project"] = project
        project[key] = value
    else:
        brief[key] = value
        project = brief.get("project")
        if isinstance(project, dict) and key in project:
            project.pop(key, None)


def _get_section(brief: dict[str, Any], key: str) -> list[Any]:
    raw = brief.get(key)
    if isinstance(raw, list):
        return raw
    project = brief.get("project")
    if isinstance(project, dict):
        inner = project.get(key)
        if isinstance(inner, list):
            return inner
    return []


def migrate_brief_to_shards(brief_path: Path, *, backup: bool = True) -> dict[str, Any]:
    """Write shard files from embedded bodies; replace brief entries with catalog refs."""
    brief_path = Path(brief_path).resolve()
    root = project_root_for_brief_path(brief_path)
    data = json.loads(brief_path.read_text(encoding="utf-8"))
    if backup:
        backup_path = brief_path.with_name(f"{brief_path.stem}.pre-shard.json")
        shutil.copy2(brief_path, backup_path)
    report: dict[str, Any] = {
        "ok": True,
        "brief_path": str(brief_path),
        "project_root": str(root),
        "scenes_written": [],
        "systems_written": [],
        "assets_written": [],
        "backup_path": str(brief_path.with_name(f"{brief_path.stem}.pre-shard.json")) if backup else None,
    }

    new_scenes: list[dict[str, Any]] = []
    for entry in _get_section(data, "scenes"):
        if not isinstance(entry, dict):
            continue
        sid = _nonempty_str(entry.get("id"))
        if not sid:
            continue
        if is_catalog_ref(entry, kind="scene"):
            new_scenes.append(dict(entry))
            continue
        rel = f"scenes/{sid}.json"
        shard_path = resolve_shard_path(root, rel)
        save_json_shard(shard_path, _scene_shard_body(entry))
        new_scenes.append(_catalog_ref_from_entry(entry, kind="scene", rel_path=rel))
        report["scenes_written"].append(rel)

    new_systems: list[dict[str, Any]] = []
    for entry in _get_section(data, "systems"):
        if not isinstance(entry, dict):
            continue
        sid = _nonempty_str(entry.get("id"))
        if not sid:
            continue
        if is_catalog_ref(entry, kind="system"):
            new_systems.append(dict(entry))
            continue
        rel = f"systems/{sid}.json"
        shard_path = resolve_shard_path(root, rel)
        save_json_shard(shard_path, _system_shard_body(entry))
        new_systems.append(_catalog_ref_from_entry(entry, kind="system", rel_path=rel))
        report["systems_written"].append(rel)

    new_assets: list[dict[str, Any]] = []
    assets_raw = data.get("assets") or []
    if not isinstance(assets_raw, list):
        assets_raw = []
    for entry in assets_raw:
        if not isinstance(entry, dict):
            continue
        aid = _nonempty_str(entry.get("id")) or _nonempty_str(entry.get("name"))
        if not aid:
            continue
        if is_catalog_ref(entry, kind="asset"):
            new_assets.append(dict(entry))
            continue
        rel = f"assets/{aid}.spec.json"
        shard_path = resolve_shard_path(root, rel)
        save_json_shard(shard_path, _asset_shard_body(entry))
        new_assets.append(_catalog_ref_from_entry(entry, kind="asset", rel_path=rel))
        report["assets_written"].append(rel)

    if new_scenes or _get_section(data, "scenes"):
        _set_section(data, "scenes", new_scenes)
    if new_systems or _get_section(data, "systems"):
        _set_section(data, "systems", new_systems)
    data["assets"] = new_assets

    brief_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(val, dict)
        ):
            out[key] = _deep_merge_dict(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def brief_uses_catalog(brief: dict[str, Any]) -> bool:
    """True if any scene/system/asset entry in the brief is a catalog ref."""
    for _section_key, kind, items in _iter_catalog_sections(brief):
        for item in items:
            if isinstance(item, dict) and is_catalog_ref(item, kind=kind):
                return True
    return False


def upsert_shard_body(
    project_root: Path,
    brief: dict[str, Any],
    kind: Kind,
    entry_id: str,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    """Write merged body to shard file; return thin catalog ref or None for in-memory legacy."""
    root = Path(project_root).resolve()
    eid = _nonempty_str(entry_id)
    if not eid:
        raise ValueError("upsert_shard_body requires entry_id")
    if not isinstance(fields, dict):
        fields = {}

    entry = _find_catalog_entry(brief, kind, eid)
    uses_catalog = brief_uses_catalog(brief)

    if entry is not None and is_catalog_ref(entry, kind=kind):
        rel = _nonempty_str(entry.get("path"))
        shard_path = resolve_shard_path(root, rel)
        body: dict[str, Any] = {}
        if shard_path.is_file():
            body = load_json_shard(shard_path)
        merged = _deep_merge_dict(body, fields)
        merged["id"] = eid
        if kind in ("scene", "system"):
            title = _nonempty_str(fields.get("title")) or _nonempty_str(entry.get("title"))
            if title:
                merged["title"] = title
        elif kind == "asset":
            name = _nonempty_str(fields.get("name")) or _nonempty_str(entry.get("name")) or eid
            merged["name"] = name
        save_json_shard(shard_path, merged)
        ref_entry = dict(entry)
        if kind in ("scene", "system") and _nonempty_str(fields.get("title")):
            ref_entry["title"] = _nonempty_str(fields.get("title"))
        elif kind == "asset" and _nonempty_str(fields.get("name")):
            ref_entry["name"] = _nonempty_str(fields.get("name"))
        return _catalog_ref_from_entry(ref_entry, kind=kind, rel_path=rel)

    if entry is not None and uses_catalog:
        if kind == "scene":
            base_body = _scene_shard_body(entry)
            rel = f"scenes/{eid}.json"
        elif kind == "system":
            base_body = _system_shard_body(entry)
            rel = f"systems/{eid}.json"
        else:
            base_body = _asset_shard_body(entry)
            rel = f"assets/{eid}.spec.json"
        merged = _deep_merge_dict(base_body, fields)
        merged["id"] = eid
        shard_path = resolve_shard_path(root, rel)
        save_json_shard(shard_path, merged)
        return _catalog_ref_from_entry(merged, kind=kind, rel_path=rel)

    if entry is None and uses_catalog:
        if kind == "scene":
            rel = f"scenes/{eid}.json"
            body = _deep_merge_dict(_scene_shard_body({"id": eid, **fields}), fields)
        elif kind == "system":
            rel = f"systems/{eid}.json"
            body = _deep_merge_dict(_system_shard_body({"id": eid, **fields}), fields)
        else:
            rel = f"assets/{eid}.spec.json"
            body = _deep_merge_dict(_asset_shard_body({"id": eid, **fields}), fields)
        body["id"] = eid
        shard_path = resolve_shard_path(root, rel)
        save_json_shard(shard_path, body)
        return _catalog_ref_from_entry(body, kind=kind, rel_path=rel)

    return None


def _find_catalog_entry(
    brief: dict[str, Any], kind: Kind, entry_id: str
) -> dict[str, Any] | None:
    key = {"scene": "scenes", "system": "systems", "asset": "assets"}[kind]
    needle = _nonempty_str(entry_id)
    if not needle:
        return None
    for item in _get_section(brief, key):
        if isinstance(item, dict) and _nonempty_str(item.get("id")) == needle:
            return item
    if kind == "asset":
        for item in brief.get("assets") or []:
            if isinstance(item, dict) and _nonempty_str(item.get("id")) == needle:
                return item
    return None


def load_shard(
    project_root: Path,
    kind: Kind,
    entry_id: str,
    brief: dict[str, Any],
) -> dict[str, Any]:
    """Load shard body from catalog path or legacy inline entry."""
    entry = _find_catalog_entry(brief, kind, entry_id)
    if entry is None:
        raise ValueError(f"No {kind} with id {entry_id!r} in brief catalog.")
    if is_catalog_ref(entry, kind=kind):
        rel = _nonempty_str(entry.get("path"))
        shard_path = resolve_shard_path(Path(project_root), rel)
        if not shard_path.is_file():
            raise ValueError(f"Shard file not found for {kind} {entry_id!r}: {rel}")
        return load_json_shard(shard_path)
    return dict(entry)


def hydrate_brief_for_review(
    draft: dict[str, Any],
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Expand all scene/system bodies for makeability (slow OK; assets stay as index).

    Returns a payload-shaped dict:
    - ``draft_brief``: copy of draft with ``project.scenes`` / ``systems`` replaced by
      full shard bodies (legacy inline entries kept as-is). Safe for Critic skills that
      still read ``project.scenes[].notes``.
    - ``scene_shards`` / ``system_shards``: id → body maps (same content).
    - ``assets_index``: thin ``{id,name,type?}`` list (no full specs).
    - ``hydrate_errors``: missing shard / load failures (non-fatal).
    """
    if not isinstance(draft, dict):
        return {
            "draft_brief": {},
            "scene_shards": {},
            "system_shards": {},
            "assets_index": [],
            "hydrate_errors": ["draft is not an object"],
        }

    out_draft = copy.deepcopy(draft)
    project = out_draft.get("project") if isinstance(out_draft.get("project"), dict) else {}
    if not isinstance(out_draft.get("project"), dict):
        out_draft["project"] = {}
        project = out_draft["project"]

    scene_shards: dict[str, Any] = {}
    system_shards: dict[str, Any] = {}
    errors: list[str] = []
    root = Path(project_root).resolve() if project_root is not None else None

    def _hydrate_list(kind: Kind, section_key: str, bucket: dict[str, Any]) -> list[dict[str, Any]]:
        raw = project.get(section_key) if isinstance(project.get(section_key), list) else []
        # Also accept top-level scenes/systems (rare).
        if not raw and isinstance(out_draft.get(section_key), list):
            raw = out_draft.get(section_key)  # type: ignore[assignment]
        hydrated_rows: list[dict[str, Any]] = []
        for item in raw or []:
            if not isinstance(item, dict):
                continue
            eid = _nonempty_str(item.get("id"))
            if not eid:
                continue
            try:
                if is_catalog_ref(item, kind=kind):
                    if root is None:
                        raise ValueError(f"catalog {kind} {eid!r} needs project_root to load shard")
                    body = load_shard(root, kind, eid, draft)
                else:
                    body = dict(item)
                bucket[eid] = body
                hydrated_rows.append(copy.deepcopy(body))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{kind}:{eid}: {exc}")
                # Keep thin ref so Critic still sees the id exists.
                hydrated_rows.append(copy.deepcopy(item))
        return hydrated_rows

    project["scenes"] = _hydrate_list("scene", "scenes", scene_shards)
    project["systems"] = _hydrate_list("system", "systems", system_shards)

    assets_index: list[dict[str, Any]] = []
    for item in draft.get("assets") or []:
        if not isinstance(item, dict):
            continue
        eid = _nonempty_str(item.get("id")) or _nonempty_str(item.get("name"))
        if not eid:
            continue
        row: dict[str, Any] = {
            "id": _nonempty_str(item.get("id")) or eid,
            "name": _nonempty_str(item.get("name")) or eid,
        }
        typ = _nonempty_str(item.get("type"))
        if typ:
            row["type"] = typ
        elif is_catalog_ref(item, kind="asset") and root is not None:
            try:
                body = load_shard(root, "asset", row["id"], draft)
                typ2 = _nonempty_str(body.get("type"))
                if typ2:
                    row["type"] = typ2
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        assets_index.append(row)

    return {
        "draft_brief": out_draft,
        "scene_shards": scene_shards,
        "system_shards": system_shards,
        "assets_index": assets_index,
        "hydrate_errors": errors,
    }


def canonicalize_structure_to_shards(
    candidate: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Move scene/system/asset bodies into shard files; return brief with thin catalog refs."""
    out = copy.deepcopy(candidate)
    root = Path(project_root).resolve()

    def _canonicalize_list(key: str, kind: Kind) -> None:
        items = _get_section(out, key)
        if not items:
            return
        new_rows: list[dict[str, Any]] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            eid = _nonempty_str(entry.get("id"))
            if not eid:
                continue
            if is_catalog_ref(entry, kind=kind):
                new_rows.append(dict(entry))
                continue
            if kind == "scene":
                rel = f"scenes/{eid}.json"
                body = _scene_shard_body(entry)
            elif kind == "system":
                rel = f"systems/{eid}.json"
                body = _system_shard_body(entry)
            else:
                rel = f"assets/{eid}.spec.json"
                body = _asset_shard_body(entry)
            shard_path = resolve_shard_path(root, rel)
            save_json_shard(shard_path, body)
            new_rows.append(_catalog_ref_from_entry(entry, kind=kind, rel_path=rel))
        _set_section(out, key, new_rows)

    _canonicalize_list("scenes", "scene")
    _canonicalize_list("systems", "system")

    assets_raw = out.get("assets")
    if isinstance(assets_raw, list) and brief_uses_catalog(out):
        new_assets: list[dict[str, Any]] = []
        for entry in assets_raw:
            if not isinstance(entry, dict):
                continue
            aid = _nonempty_str(entry.get("id")) or _nonempty_str(entry.get("name"))
            if not aid:
                continue
            if is_catalog_ref(entry, kind="asset"):
                new_assets.append(dict(entry))
                continue
            if _has_body_hints(entry, "asset"):
                rel = f"assets/{aid}.spec.json"
                shard_path = resolve_shard_path(root, rel)
                save_json_shard(shard_path, _asset_shard_body(entry))
                new_assets.append(_catalog_ref_from_entry(entry, kind="asset", rel_path=rel))
            else:
                new_assets.append(dict(entry))
        out["assets"] = new_assets

    return out


def _snippet_around(text: str, query: str, *, max_len: int = 120) -> str:
    lower = text.lower()
    q = query.lower()
    idx = lower.find(q)
    if idx < 0:
        compact = " ".join(text.split())
        return compact[:max_len] + ("…" if len(compact) > max_len else "")
    start = max(0, idx - 40)
    end = min(len(text), idx + len(query) + 40)
    chunk = text[start:end].replace("\n", " ")
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{chunk}{suffix}"


def _entry_search_blob(entry: dict[str, Any], kind: Kind) -> tuple[str, str, str]:
    """Return (id, label, combined searchable text for metadata)."""
    entry_id = _nonempty_str(entry.get("id"))
    if kind == "asset":
        label = _nonempty_str(entry.get("name")) or entry_id
    else:
        label = _nonempty_str(entry.get("title"))
    meta = f"{entry_id} {label}".strip()
    return entry_id, label, meta


def search_shards(
    project_root: Path,
    brief: dict[str, Any],
    query: str,
    *,
    kinds: list[Kind] | tuple[Kind, ...] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Case-insensitive substring search over catalog labels and shard bodies."""
    q = _nonempty_str(query)
    if not q:
        return []
    root = Path(project_root).resolve()
    allowed: set[Kind] | None = set(kinds) if kinds else None
    hits: list[dict[str, Any]] = []

    for _section_key, kind, items in _iter_catalog_sections(brief):
        if allowed is not None and kind not in allowed:
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            entry_id, _label, meta = _entry_search_blob(item, kind)
            if not entry_id:
                continue
            score = 0
            q_lower = q.lower()
            if q_lower in entry_id.lower():
                score += 10
            if q_lower in meta.lower():
                score += 10
            body_text = ""
            rel_path = _nonempty_str(item.get("path"))
            if is_catalog_ref(item, kind=kind) and rel_path:
                try:
                    shard_path = resolve_shard_path(root, rel_path)
                    if shard_path.is_file():
                        body_text = shard_path.read_text(encoding="utf-8")
                except (OSError, ValueError):
                    body_text = ""
            else:
                body_text = json.dumps(item, ensure_ascii=False)
            if q_lower in body_text.lower():
                score += 5 if score == 0 else 3
            if score <= 0:
                continue
            snippet_source = meta if q_lower in meta.lower() else body_text
            hits.append(
                {
                    "kind": kind,
                    "id": entry_id,
                    "path": rel_path or None,
                    "score": score,
                    "snippet": _snippet_around(snippet_source, q),
                }
            )

    hits.sort(key=lambda h: (-int(h["score"]), str(h["kind"]), str(h["id"])))
    return hits[: max(1, int(limit))]


_DECLARED_EDGE_KEYS: tuple[tuple[str, Kind], ...] = (
    ("scene_ids", "scene"),
    ("system_ids", "system"),
    ("asset_ids", "asset"),
)

_KIND_SORT_ORDER: dict[Kind, int] = {"scene": 0, "system": 1, "asset": 2}


def _catalog_row_title(entry: dict[str, Any], kind: Kind) -> str:
    entry_id = _nonempty_str(entry.get("id"))
    if kind == "asset":
        return _nonempty_str(entry.get("name")) or entry_id
    return _nonempty_str(entry.get("title")) or entry_id


def _declared_ids_from_sources(*sources: dict[str, Any] | None) -> dict[Kind, set[str]]:
    out: dict[Kind, set[str]] = {"scene": set(), "system": set(), "asset": set()}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, target_kind in _DECLARED_EDGE_KEYS:
            raw = source.get(key)
            if not isinstance(raw, list):
                continue
            for item in raw:
                item_id = _nonempty_str(item)
                if item_id:
                    out[target_kind].add(item_id)
    return out


def _focus_shard_text(
    project_root: Path,
    kind: Kind,
    entry: dict[str, Any],
    body: dict[str, Any],
) -> str:
    if is_catalog_ref(entry, kind=kind):
        rel = _nonempty_str(entry.get("path"))
        if rel:
            try:
                shard_path = resolve_shard_path(project_root, rel)
                if shard_path.is_file():
                    return shard_path.read_text(encoding="utf-8")
            except (OSError, ValueError):
                pass
    return json.dumps(body, ensure_ascii=False)


def _mention_pattern(entry_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"(^|[^a-z0-9_]){re.escape(entry_id)}([^a-z0-9_]|$)",
        re.IGNORECASE,
    )


def _load_entry_body(
    project_root: Path,
    brief: dict[str, Any],
    kind: Kind,
    entry_id: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    try:
        return load_shard(project_root, kind, entry_id, brief)
    except (OSError, ValueError, json.JSONDecodeError):
        if is_catalog_ref(entry, kind=kind):
            raise
        return dict(entry)


def related_shards(
    project_root: Path,
    brief: dict[str, Any],
    kind: Kind,
    entry_id: str,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return related catalog rows for focus (kind, entry_id). Never includes self."""
    focus_id = _nonempty_str(entry_id)
    if not focus_id:
        return []
    focus_entry = _find_catalog_entry(brief, kind, focus_id)
    if focus_entry is None:
        return []

    root = Path(project_root).resolve()
    focus_body = _load_entry_body(root, brief, kind, focus_id, focus_entry)
    focus_text = _focus_shard_text(root, kind, focus_entry, focus_body)

    catalog_rows: list[tuple[Kind, str, dict[str, Any]]] = []
    for _section_key, row_kind, items in _iter_catalog_sections(brief):
        for item in items:
            if not isinstance(item, dict):
                continue
            row_id = _nonempty_str(item.get("id"))
            if not row_id:
                continue
            catalog_rows.append((row_kind, row_id, item))

    row_by_key = {(row_kind, row_id): item for row_kind, row_id, item in catalog_rows}

    hits: dict[tuple[Kind, str], dict[str, Any]] = {}

    def _ensure_hit(target_kind: Kind, target_id: str, via: str) -> None:
        if target_kind == kind and target_id == focus_id:
            return
        key = (target_kind, target_id)
        row = row_by_key.get(key)
        if row is None:
            return
        existing = hits.get(key)
        if existing is None:
            hits[key] = {
                "kind": target_kind,
                "id": target_id,
                "title": _catalog_row_title(row, target_kind),
                "via": [via],
                "path": _nonempty_str(row.get("path")) or None,
            }
            return
        if via not in existing["via"]:
            existing["via"].append(via)

    forward = _declared_ids_from_sources(focus_entry, focus_body)
    for target_kind, ids in forward.items():
        for target_id in ids:
            _ensure_hit(target_kind, target_id, "declared")

    for row_kind, row_id, row in catalog_rows:
        if row_kind == kind and row_id == focus_id:
            continue
        try:
            row_body = _load_entry_body(root, brief, row_kind, row_id, row)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        reverse = _declared_ids_from_sources(row, row_body)
        for target_kind, ids in reverse.items():
            if target_kind == kind and focus_id in ids:
                _ensure_hit(row_kind, row_id, "declared")

    for row_kind, row_id, row in catalog_rows:
        if row_kind == kind and row_id == focus_id:
            continue
        if len(row_id) < 3:
            continue
        if _mention_pattern(row_id).search(focus_text):
            _ensure_hit(row_kind, row_id, "mention")

    ordered = list(hits.values())
    for hit in ordered:
        via = hit["via"]
        if "declared" in via and "mention" in via:
            hit["via"] = ["declared", "mention"]
        elif "declared" in via:
            hit["via"] = ["declared"]
        else:
            hit["via"] = ["mention"]

    ordered.sort(
        key=lambda h: (
            0 if "declared" in h["via"] else 1,
            _KIND_SORT_ORDER.get(h["kind"], 99),  # type: ignore[arg-type]
            str(h["id"]),
        )
    )
    cap = max(1, int(limit))
    return ordered[:cap]


_PROJECT_INTRO_KEYS = frozenset(
    {
        "title",
        "description",
        "gameplay_loop",
        "art_direction",
        "dimension",
        "session_goal",
        "genre",
        "platform",
        "camera",
        "perspective",
    }
)


def _thin_catalog_list(items: list[Any], *, kind: Kind) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        entry_id = _nonempty_str(item.get("id"))
        if not entry_id:
            continue
        if is_catalog_ref(item, kind=kind):
            out.append(dict(item))
            continue
        if kind == "asset":
            name = _nonempty_str(item.get("name")) or entry_id
            out.append({"id": entry_id, "name": name})
        else:
            out.append({"id": entry_id, "title": _nonempty_str(item.get("title"))})
    return out


def _legacy_scene_stub(entry: dict[str, Any]) -> dict[str, Any]:
    stub: dict[str, Any] = {
        "id": _nonempty_str(entry.get("id")),
        "title": _nonempty_str(entry.get("title")),
    }
    if is_catalog_ref(entry, kind="scene"):
        stub["path"] = _nonempty_str(entry.get("path"))
    return stub


def build_focus_context(
    draft: dict[str, Any],
    focus: dict[str, Any] | None,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Thin catalog + short project intro + optional focused shard body."""
    if not isinstance(draft, dict):
        return {}
    project_raw = draft.get("project") if isinstance(draft.get("project"), dict) else {}
    project_intro = {
        k: copy.deepcopy(project_raw[k])
        for k in _PROJECT_INTRO_KEYS
        if k in project_raw
    }
    desc_raw = str(project_intro.get("description") or "")
    if len(desc_raw) > DESCRIPTION_MAX_CHARS:
        project_intro["description"] = desc_raw[:DESCRIPTION_MAX_CHARS] + "…"
        project_intro["description_truncated"] = True
    loop_raw = str(project_intro.get("gameplay_loop") or "")
    if len(loop_raw) > GAMEPLAY_LOOP_MAX_CHARS:
        project_intro["gameplay_loop"] = loop_raw[:GAMEPLAY_LOOP_MAX_CHARS] + "…"
        project_intro["gameplay_loop_truncated"] = True
    scenes_raw = _get_section(draft, "scenes")
    systems_raw = _get_section(draft, "systems")
    assets_raw = draft.get("assets") if isinstance(draft.get("assets"), list) else []

    focus_kind = _nonempty_str(focus.get("kind")) if isinstance(focus, dict) else ""
    focus_id = _nonempty_str(focus.get("id")) if isinstance(focus, dict) else ""

    scenes_out: list[dict[str, Any]] = []
    for entry in scenes_raw:
        if isinstance(entry, dict):
            scenes_out.append(_legacy_scene_stub(entry))

    systems_out: list[dict[str, Any]] = []
    for entry in systems_raw:
        if not isinstance(entry, dict):
            continue
        sid = _nonempty_str(entry.get("id"))
        row: dict[str, Any] = {"id": sid, "title": _nonempty_str(entry.get("title"))}
        if is_catalog_ref(entry, kind="system"):
            row["path"] = _nonempty_str(entry.get("path"))
        systems_out.append(row)

    ctx: dict[str, Any] = {
        "project": project_intro,
        "scenes": scenes_out,
        "systems": systems_out,
        "assets": _thin_catalog_list(assets_raw, kind="asset"),
    }
    if draft.get("animation_graphs") is not None:
        ctx["animation_graphs"] = copy.deepcopy(draft.get("animation_graphs"))
    if draft.get("ui_panels") is not None:
        ctx["ui_panels"] = copy.deepcopy(draft.get("ui_panels"))

    if focus_kind in ("scene", "system", "asset") and focus_id:
        kind_lit: Kind = focus_kind  # type: ignore[assignment]
        ctx["focus"] = {"kind": focus_kind, "id": focus_id}
        try:
            pr = Path(project_root) if project_root is not None else Path(".")
            ctx["focus_shard"] = load_shard(pr, kind_lit, focus_id, draft)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            ctx["focus_error"] = str(exc)
    elif focus_kind == "project":
        ctx["focus"] = {"kind": "project"}
    elif focus_kind in ("visual_target", "intent_gap", "data") and focus_id:
        focus_out: dict[str, Any] = {"kind": focus_kind, "id": focus_id}
        extra = focus.get("extra") if isinstance(focus, dict) else None
        if isinstance(extra, dict) and extra:
            focus_out["extra"] = copy.deepcopy(extra)
        ctx["focus"] = focus_out
    elif focus_kind == "visual_target" and not focus_id:
        focus_out = {"kind": "visual_target", "id": "global"}
        extra = focus.get("extra") if isinstance(focus, dict) else None
        if isinstance(extra, dict) and extra:
            focus_out["extra"] = copy.deepcopy(extra)
        ctx["focus"] = focus_out

    return ctx


def apply_description_write_guard(
    old_draft: dict[str, Any] | None,
    new_draft: dict[str, Any],
) -> dict[str, Any]:
    """Keep previous description when a patch expands past DESCRIPTION_MAX_CHARS."""
    out = copy.deepcopy(new_draft)
    if not isinstance(old_draft, dict):
        return out
    old_project = old_draft.get("project") if isinstance(old_draft.get("project"), dict) else {}
    new_project = out.get("project") if isinstance(out.get("project"), dict) else {}
    if not isinstance(out.get("project"), dict):
        return out
    old_desc = str(old_project.get("description") or "")
    new_desc = str(new_project.get("description") or "")
    if len(new_desc) > DESCRIPTION_MAX_CHARS and len(new_desc) > len(old_desc):
        out["project"]["description"] = old_desc
    return out
