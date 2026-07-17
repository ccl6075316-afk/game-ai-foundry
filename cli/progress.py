"""Project progress ledger — task + validation state for agent resume."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from production import load_production

PROGRESS_SCHEMA_VERSION = 1
_REPO_ROOT = Path(__file__).resolve().parent.parent


def default_progress_path(*, brief_path: Path | None = None, production_path: Path | None = None) -> Path:
    if production_path and production_path.is_file():
        data = load_production(production_path)
        slug = (data.get("production_doc") or {}).get("slug")
        if slug:
            return _REPO_ROOT / "plans" / f"progress_{slug}.json"
    if brief_path:
        stem = brief_path.stem.replace(".json", "")
        return _REPO_ROOT / "plans" / f"progress_{stem}.json"
    return _REPO_ROOT / "plans" / "progress.json"


def load_progress(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("progress file must be a JSON object")
    return data


def save_progress(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.resolve()


def init_progress(
    *,
    brief_path: Path | None,
    production_path: Path,
    project_path: Path | None = None,
) -> dict[str, Any]:
    production_path = production_path.resolve()
    prod = load_production(production_path)
    doc = prod.get("production_doc") or {}
    meta = prod.get("production_meta") or {}
    slug = str(doc.get("slug") or "game")

    tasks = []
    for task in doc.get("godot_tasks") or []:
        if not isinstance(task, dict):
            continue
        tasks.append(
            {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": str(task.get("status") or "pending"),
                "depends_on": list(task.get("depends_on") or []),
                "verify": list(task.get("verify") or []),
                "last_error": None,
                "updated_at": None,
            }
        )

    brief = str(brief_path.resolve()) if brief_path else meta.get("brief_path")
    proj = str(project_path.resolve()) if project_path else str((_REPO_ROOT / "games" / slug).resolve())

    return {
        "progress_meta": {
            "schema_version": PROGRESS_SCHEMA_VERSION,
            "slug": slug,
            "brief_path": brief,
            "production_path": str(production_path),
            "project_path": proj,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "phases": {
            "production_derived": {"status": "done", "at": meta.get("derived_at")},
            "scaffold": {"status": "pending", "at": None},
            "pipeline_run": {"status": "pending", "at": None},
            "godot_tasks": tasks,
            "validation": {
                "validate": "not_run",
                "unit": "not_run",
                "playtest": "not_run",
                "regression": "not_run",
                "last_failure": None,
                "last_report": None,
                "regression_snapshots": [],
            },
        },
        "memory": [],
    }


def update_phase(progress: dict[str, Any], phase: str, *, status: str, at: str | None = None) -> None:
    phases = progress.setdefault("phases", {})
    entry = phases.setdefault(phase, {})
    if isinstance(entry, dict):
        entry["status"] = status
        entry["at"] = at or datetime.now(timezone.utc).isoformat()


def update_task_status(
    progress: dict[str, Any],
    task_id: str,
    status: str,
    *,
    error: str | None = None,
) -> None:
    tasks = progress.get("phases", {}).get("godot_tasks") or []
    for task in tasks:
        if isinstance(task, dict) and task.get("id") == task_id:
            task["status"] = status
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            if error:
                task["last_error"] = error
            return
    raise ValueError(f"unknown godot_task id: {task_id}")


def update_validation_layer(
    progress: dict[str, Any],
    layer: str,
    status: str,
    *,
    error: str | None = None,
    report_path: str | None = None,
) -> None:
    validation = progress.setdefault("phases", {}).setdefault("validation", {})
    if not isinstance(validation, dict):
        return
    validation[layer] = status
    if error:
        validation["last_failure"] = error
    if report_path:
        validation["last_report"] = report_path


def append_memory(progress: dict[str, Any], note: str) -> None:
    memory = progress.setdefault("memory", [])
    if not isinstance(memory, list):
        progress["memory"] = memory = []
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    memory.append(f"[{stamp}] {note.strip()}")


def sync_progress_from_production(
    progress: dict[str, Any],
    production: dict[str, Any],
) -> dict[str, Any]:
    """Append new production.godot_tasks into progress (do not overwrite existing ids).

    Returns {"added": [task_ids], "skipped": [task_ids]}.
    """
    doc = production.get("production_doc") if isinstance(production.get("production_doc"), dict) else {}
    prod_tasks = doc.get("godot_tasks") if isinstance(doc.get("godot_tasks"), list) else []
    phases = progress.setdefault("phases", {})
    if not isinstance(phases, dict):
        phases = {}
        progress["phases"] = phases
    existing = phases.get("godot_tasks")
    if not isinstance(existing, list):
        existing = []
        phases["godot_tasks"] = existing
    have = {str(t.get("id")) for t in existing if isinstance(t, dict) and t.get("id")}
    added: list[str] = []
    skipped: list[str] = []
    for task in prod_tasks:
        if not isinstance(task, dict) or not task.get("id"):
            continue
        tid = str(task["id"])
        if tid in have:
            skipped.append(tid)
            continue
        existing.append(
            {
                "id": tid,
                "title": task.get("title"),
                "status": str(task.get("status") or "pending"),
                "depends_on": list(task.get("depends_on") or []),
                "verify": list(task.get("verify") or []),
                "last_error": None,
                "updated_at": None,
                "source_change_id": task.get("source_change_id"),
            }
        )
        have.add(tid)
        added.append(tid)
    if added:
        append_memory(progress, f"从 production 同步新任务：{', '.join(added)}")
    return {"added": added, "skipped": skipped}
