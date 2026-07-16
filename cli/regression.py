"""Regression harness — snapshot last-passing playtest plans and re-run them."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from progress import load_progress, save_progress
from production import load_production

_REPO_ROOT = Path(__file__).resolve().parent.parent


def regression_dir_for_slug(slug: str) -> Path:
    return _REPO_ROOT / "plans" / f"regression_{slug}"


def snapshot_passing_plan(
    progress_path: Path,
    plan_path: Path,
    *,
    label: str | None = None,
) -> dict[str, Any]:
    """Copy a passing playtest plan into plans/regression_<slug>/ and record in progress."""
    progress = load_progress(progress_path)
    meta = progress.get("progress_meta") or {}
    slug = str(meta.get("slug") or "game")
    plan_path = plan_path.resolve()
    if not plan_path.is_file():
        raise FileNotFoundError(f"playtest plan not found: {plan_path}")

    dest_dir = regression_dir_for_slug(slug)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = label or plan_path.stem
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    dest = dest_dir / f"{safe}.json"
    shutil.copy2(plan_path, dest)

    entry = {
        "plan_path": str(dest.resolve()),
        "source_plan": str(plan_path),
        "label": safe,
        "snapshotted_at": datetime.now(timezone.utc).isoformat(),
    }
    validation = progress.setdefault("phases", {}).setdefault("validation", {})
    snaps: list[Any] = list(validation.get("regression_snapshots") or [])
    snaps = [s for s in snaps if not (isinstance(s, dict) and s.get("label") == safe)]
    snaps.append(entry)
    validation["regression_snapshots"] = snaps
    validation["regression"] = "pass"
    save_progress(progress, progress_path)
    return entry


def list_regression_plans(
    *,
    progress_path: Path | None = None,
    production_path: Path | None = None,
) -> list[Path]:
    """Collect regression plan paths from progress snapshots and production.validation."""
    paths: list[Path] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        key = str(p.resolve())
        if key not in seen and p.is_file():
            seen.add(key)
            paths.append(p.resolve())

    if progress_path and progress_path.is_file():
        progress = load_progress(progress_path)
        validation = (progress.get("phases") or {}).get("validation") or {}
        for entry in validation.get("regression_snapshots") or []:
            if isinstance(entry, dict) and entry.get("plan_path"):
                _add(Path(str(entry["plan_path"])))
        prod = progress.get("progress_meta", {}).get("production_path")
        if production_path is None and prod:
            production_path = Path(str(prod))

    if production_path and production_path.is_file():
        prod = load_production(production_path)
        doc = prod.get("production_doc") or {}
        validation = doc.get("validation") or {}
        for item in validation.get("regression_checks") or []:
            if isinstance(item, str) and item.strip():
                p = Path(item.strip())
                if not p.is_absolute():
                    p = _REPO_ROOT / p
                _add(p)
            elif isinstance(item, dict) and item.get("plan"):
                p = Path(str(item["plan"]))
                if not p.is_absolute():
                    p = _REPO_ROOT / p
                _add(p)

    return paths


def write_regression_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path.resolve()
