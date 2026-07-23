"""Asset review rows + soft review annotations on assets-manifest."""

from __future__ import annotations

import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from assets_manifest import load_assets_manifest, save_assets_manifest

VALID_STATUS = frozenset({"pending", "accepted", "replaced"})
VALID_SOURCE = frozenset({"pipeline", "regenerate", "local_file"})

DEFAULT_REVIEW: dict[str, str] = {
    "status": "pending",
    "source": "pipeline",
    "updated_at": "",
    "note": "",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_review() -> dict[str, Any]:
    return dict(DEFAULT_REVIEW)


def row_id_for(asset_name: str, kit_item_slug: str | None = None) -> str:
    if kit_item_slug:
        return f"{asset_name}__{kit_item_slug}"
    return asset_name


def _normalize_review(raw: Any) -> dict[str, Any]:
    base = default_review()
    if not isinstance(raw, dict):
        return base
    status = str(raw.get("status") or "pending").strip().lower()
    source = str(raw.get("source") or "pipeline").strip().lower()
    if status not in VALID_STATUS:
        status = "pending"
    if source not in VALID_SOURCE:
        source = "pipeline"
    return {
        "status": status,
        "source": source,
        "updated_at": str(raw.get("updated_at") or ""),
        "note": str(raw.get("note") or ""),
    }


def get_review(
    manifest: dict[str, Any],
    *,
    asset_name: str,
    kit_item_slug: str | None = None,
) -> dict[str, Any]:
    entry = (manifest.get("assets") or {}).get(asset_name) or {}
    if kit_item_slug:
        bag = entry.get("item_reviews") if isinstance(entry.get("item_reviews"), dict) else {}
        return _normalize_review(bag.get(kit_item_slug))
    return _normalize_review(entry.get("review"))


def set_review(
    manifest: dict[str, Any],
    *,
    asset_name: str,
    status: str,
    kit_item_slug: str | None = None,
    source: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    status_n = str(status).strip().lower()
    if status_n not in VALID_STATUS:
        raise ValueError(f"invalid review status: {status!r}")
    assets = manifest.setdefault("assets", {})
    entry = assets.setdefault(asset_name, {})
    current = get_review(manifest, asset_name=asset_name, kit_item_slug=kit_item_slug)
    if source is not None:
        source_n = str(source).strip().lower()
        if source_n not in VALID_SOURCE:
            raise ValueError(f"invalid review source: {source!r}")
        current["source"] = source_n
    if note is not None:
        current["note"] = str(note)
    current["status"] = status_n
    current["updated_at"] = _utc_now()
    if kit_item_slug:
        bag = entry.setdefault("item_reviews", {})
        if not isinstance(bag, dict):
            bag = {}
            entry["item_reviews"] = bag
        bag[kit_item_slug] = current
    else:
        entry["review"] = current
    return deepcopy(current)


def _filtered_stages(
    entry: dict[str, Any],
    *,
    kit_item_slug: str | None = None,
) -> list[dict[str, Any]]:
    stages = entry.get("stages") if isinstance(entry.get("stages"), list) else []
    filtered: list[dict[str, Any]] = []
    for s in stages:
        if not isinstance(s, dict):
            continue
        if kit_item_slug:
            slug = str(s.get("kit_item_slug") or "")
            kid = str(s.get("kit_item_id") or "")
            if slug != kit_item_slug and kid != kit_item_slug:
                continue
        filtered.append(s)
    return filtered


def _stages_summary(entry: dict[str, Any], *, kit_item_slug: str | None = None) -> str:
    names: list[str] = []
    for s in _filtered_stages(entry, kit_item_slug=kit_item_slug):
        stage = str(s.get("stage") or "").strip()
        if stage:
            names.append(stage)
    return ", ".join(names)


def resolve_canonical_path(
    entry: dict[str, Any],
    *,
    kit_item_slug: str | None = None,
) -> str | None:
    filtered = _filtered_stages(entry, kit_item_slug=kit_item_slug)

    def score(s: dict[str, Any]) -> tuple[int, int]:
        role = str(s.get("role") or "")
        stage = str(s.get("stage") or "")
        path = str(s.get("path_repo") or s.get("path_cli") or "")
        pri = 0
        if role == "gameplay_ready":
            pri = 3
        elif "nobg" in stage or path.endswith("_nobg.png"):
            pri = 2
        elif "raw" in stage or "_raw" in path:
            pri = 1
        return (pri, len(path))

    if not filtered:
        return None
    best = max(filtered, key=score)
    path = str(best.get("path_repo") or "").strip()
    return path or None


def iter_review_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    assets = manifest.get("assets") if isinstance(manifest.get("assets"), dict) else {}
    for asset_name, entry in assets.items():
        if not isinstance(entry, dict):
            continue
        brief = entry.get("brief") if isinstance(entry.get("brief"), dict) else {}
        atype = str(brief.get("type") or "")
        items = brief.get("items") if isinstance(brief.get("items"), list) else []
        if atype == "icon_kit" and items:
            for it in items:
                if isinstance(it, dict):
                    slug = str(it.get("slug") or it.get("id") or "").strip()
                    label = str(it.get("label") or it.get("id") or slug)
                    usage = str(it.get("usage") or brief.get("usage") or "")
                else:
                    slug = str(it).strip()
                    label = slug
                    usage = str(brief.get("usage") or "")
                if not slug:
                    continue
                path = resolve_canonical_path(entry, kit_item_slug=slug)
                rows.append(
                    {
                        "row_id": row_id_for(asset_name, slug),
                        "asset_name": asset_name,
                        "kit_item_slug": slug,
                        "label": label,
                        "type": atype,
                        "usage": usage,
                        "preview_path_repo": path,
                        "canonical_path_repo": path,
                        "review": get_review(
                            manifest, asset_name=asset_name, kit_item_slug=slug
                        ),
                        "stages_summary": _stages_summary(entry, kit_item_slug=slug),
                    }
                )
            continue
        path = resolve_canonical_path(entry)
        rows.append(
            {
                "row_id": row_id_for(asset_name),
                "asset_name": asset_name,
                "kit_item_slug": None,
                "label": str(brief.get("name") or asset_name),
                "type": atype,
                "usage": str(brief.get("usage") or ""),
                "preview_path_repo": path,
                "canonical_path_repo": path,
                "review": get_review(manifest, asset_name=asset_name),
                "stages_summary": _stages_summary(entry),
            }
        )
    return rows


def replace_local_file(
    manifest_path: Path,
    *,
    asset_name: str,
    source_abs: Path,
    repo_root: Path,
    kit_item_slug: str | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    source_abs = Path(source_abs)
    repo_root = Path(repo_root)
    if not source_abs.is_file():
        raise FileNotFoundError(f"source file not found: {source_abs}")

    manifest = load_assets_manifest(manifest_path)
    entry = (manifest.get("assets") or {}).get(asset_name)
    if not isinstance(entry, dict):
        raise ValueError(f"unknown asset: {asset_name!r}")

    path_repo = resolve_canonical_path(entry, kit_item_slug=kit_item_slug)
    if not path_repo:
        raise ValueError(f"no canonical path for asset {asset_name!r}")

    dest = (repo_root / path_repo).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_abs, dest)

    review = set_review(
        manifest,
        asset_name=asset_name,
        kit_item_slug=kit_item_slug,
        status="replaced",
        source="local_file",
    )
    save_assets_manifest(manifest_path, manifest)

    return {
        "ok": True,
        "row_id": row_id_for(asset_name, kit_item_slug),
        "path_repo": path_repo,
        "review": review,
    }
