"""Handoff packages — 项目经理 → 程序员（文件总线，非聊天记忆）。

Files live at plans/handoffs/<id>.json
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HANDOFF_DIR = _REPO_ROOT / "plans" / "handoffs"

HANDOFF_SCHEMA_VERSION = 1
VALID_TRIAGE = frozenset({"bug", "asset", "brief_mismatch", "design_change", "unknown"})
VALID_DISPATCH_TO = frozenset({"programmer", "pipeline", "brief_tab", "none"})
VALID_STATUS = frozenset({"open", "claimed", "done", "cancelled"})


class HandoffError(RuntimeError):
    pass


def handoffs_dir() -> Path:
    return _HANDOFF_DIR


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sanitize_id(raw: str) -> str:
    s = (raw or "").strip()
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", s).strip("-")
    if not cleaned:
        cleaned = uuid.uuid4().hex[:10]
    return cleaned[:64]


def handoff_path(handoff_id: str, *, base_dir: Path | None = None) -> Path:
    root = base_dir or _HANDOFF_DIR
    return root / f"{sanitize_id(handoff_id)}.json"


def create_handoff(
    *,
    triage: str,
    title: str,
    summary: str,
    task_id: str | None = None,
    asset_names: list[str] | None = None,
    cli_hints: list[str] | None = None,
    target_role: str = "programmer",
    target_instance_id: str | None = None,
    from_session_id: str | None = None,
    progress_path: str | None = None,
    brief_path: str | None = None,
    handoff_id: str | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    triage_n = (triage or "unknown").strip().lower()
    if triage_n not in VALID_TRIAGE:
        triage_n = "unknown"
    hid = sanitize_id(handoff_id or task_id or f"ho-{uuid.uuid4().hex[:8]}")
    now = _utc_now()
    doc: dict[str, Any] = {
        "handoff_meta": {
            "schema_version": HANDOFF_SCHEMA_VERSION,
            "id": hid,
            "created_at": now,
            "updated_at": now,
            "status": "open",
            "from_role": "product_host",
            "from_session_id": from_session_id,
            "target_role": target_role,
            "target_instance_id": target_instance_id,
            "progress_path": progress_path,
            "brief_path": brief_path,
        },
        "triage": triage_n,
        "title": (title or hid).strip()[:120],
        "summary": (summary or "").strip(),
        "task_id": task_id,
        "asset_names": list(asset_names or []),
        "cli_hints": list(cli_hints or []),
    }
    path = handoff_path(hid, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc["_path"] = str(path.resolve())
    return doc


def load_handoff(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HandoffError("handoff must be a JSON object")
    return data


def save_handoff(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = data.setdefault("handoff_meta", {})
    if isinstance(meta, dict):
        meta["updated_at"] = _utc_now()
    # strip runtime-only
    clean = {k: v for k, v in data.items() if not str(k).startswith("_")}
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.resolve()


def set_handoff_status(path: Path, status: str) -> dict[str, Any]:
    if status not in VALID_STATUS:
        raise HandoffError(f"invalid status: {status}")
    data = load_handoff(path)
    meta = data.setdefault("handoff_meta", {})
    if isinstance(meta, dict):
        meta["status"] = status
    save_handoff(data, path)
    data["_path"] = str(path.resolve())
    return data


def list_handoffs(
    *,
    status: str | None = "open",
    target_role: str | None = "programmer",
    target_instance_id: str | None = None,
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """List handoffs.

    When ``target_instance_id`` is set, include:
    - handoffs aimed at that instance, and
    - handoffs with empty/null target (broadcast / legacy).
    """
    root = base_dir or _HANDOFF_DIR
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = load_handoff(path)
        except (json.JSONDecodeError, OSError, HandoffError):
            continue
        meta = data.get("handoff_meta") if isinstance(data.get("handoff_meta"), dict) else {}
        if status and meta.get("status") != status:
            continue
        if target_role and meta.get("target_role") not in (None, target_role):
            continue
        tid = meta.get("target_instance_id")
        tid_s = str(tid).strip() if tid else ""
        if target_instance_id:
            want = str(target_instance_id).strip()
            if tid_s and tid_s != want:
                continue
        item = {
            "id": meta.get("id") or path.stem,
            "path": str(path.resolve()),
            "status": meta.get("status"),
            "triage": data.get("triage"),
            "title": data.get("title"),
            "task_id": data.get("task_id"),
            "target_instance_id": tid_s or None,
            "updated_at": meta.get("updated_at"),
            "cli_hints": list(data.get("cli_hints") or []) if isinstance(data.get("cli_hints"), list) else [],
        }
        out.append(item)
    return out


def open_handoffs_for_prompt(
    *,
    limit: int = 5,
    target_instance_id: str | None = None,
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Full handoff docs for injecting into programmer prompt."""
    items = list_handoffs(
        status="open",
        target_role="programmer",
        target_instance_id=target_instance_id,
        base_dir=base_dir,
    )[:limit]
    docs: list[dict[str, Any]] = []
    for item in items:
        path = Path(item["path"])
        try:
            data = load_handoff(path)
            data["_path"] = str(path)
            docs.append(data)
        except (json.JSONDecodeError, OSError, HandoffError):
            continue
    return docs


def extract_dispatch_payload(text: str) -> dict[str, Any] | None:
    """Parse trailing/fenced JSON dispatch block from assistant text."""
    if not text or not text.strip():
        return None
    # Prefer ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    candidates: list[str] = []
    if fence:
        candidates.append(fence.group(1))
    # Also try last {...} that looks like triage
    for m in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL):
        chunk = m.group(0)
        if "triage" in chunk or "dispatch" in chunk or "progress_note" in chunk:
            candidates.append(chunk)
    for raw in reversed(candidates):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and (
            "triage" in parsed or "dispatch" in parsed or "progress_note" in parsed
        ):
            return parsed
    return None


def strip_dispatch_fence(text: str) -> str:
    """Remove JSON fence from user-visible reply (keep prose)."""
    cleaned = re.sub(r"\n*```(?:json)?\s*\{.*?\}\s*```\s*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip() or text.strip()


def apply_product_host_dispatch(
    payload: dict[str, Any],
    *,
    assistant_message: str,
    progress_path: Path | None,
    brief_path: Path | None,
    from_session_id: str | None,
    default_target_instance_id: str | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Write progress note / task update / handoff from parsed dispatch JSON."""
    from progress import append_memory, load_progress, save_progress, update_task_status

    result: dict[str, Any] = {
        "applied": False,
        "triage": None,
        "progress_note_written": False,
        "task_updated": None,
        "handoff_path": None,
        "handoff_id": None,
        "dispatch_to": None,
        "target_instance_id": None,
        "next_actions": [],
    }

    triage = str(payload.get("triage") or "unknown").strip().lower()
    if triage not in VALID_TRIAGE:
        triage = "unknown"
    result["triage"] = triage

    dispatch = payload.get("dispatch") if isinstance(payload.get("dispatch"), dict) else {}
    to = str(dispatch.get("to") or "none").strip().lower()
    if to not in VALID_DISPATCH_TO:
        to = "none"
    result["dispatch_to"] = to

    note = str(payload.get("progress_note") or "").strip()
    task_id = dispatch.get("task_id")
    task_id_s = str(task_id).strip() if task_id else None
    asset_names = dispatch.get("asset_names") if isinstance(dispatch.get("asset_names"), list) else []
    cli_hints = dispatch.get("cli_hints") if isinstance(dispatch.get("cli_hints"), list) else []
    asset_names = [str(a) for a in asset_names if str(a).strip()]
    cli_hints = [str(c) for c in cli_hints if str(c).strip()]

    target_raw = dispatch.get("target_instance_id")
    target_instance_id = str(target_raw).strip() if target_raw else None
    if not target_instance_id and default_target_instance_id:
        target_instance_id = str(default_target_instance_id).strip() or None
    result["target_instance_id"] = target_instance_id

    # Suggest pipeline / validate CLI when hints empty
    if to == "pipeline" and not cli_hints:
        manifest_rel = None
        if brief_path and brief_path.is_file():
            stem = brief_path.stem
            manifest_rel = f"../pipeline/{stem}.json"
            try:
                from pipeline_retry import suggest_retry_commands

                cli_hints = suggest_retry_commands(
                    manifest_rel=manifest_rel,
                    asset_names=asset_names,
                )
            except Exception:
                cli_hints = [
                    f"python gamefactory.py pipeline status --manifest {manifest_rel} --json",
                    f"python gamefactory.py pipeline run --manifest {manifest_rel} --jobs 2",
                ]
        else:
            cli_hints = ["python gamefactory.py pipeline status --json"]
    elif to == "programmer" and not cli_hints:
        cli_hints = ["python gamefactory.py godot validate --project ../games"]
    result["next_actions"] = list(cli_hints)

    progress_file = progress_path
    if progress_file and progress_file.is_file():
        try:
            prog = load_progress(progress_file)
            if note:
                append_memory(prog, note)
                result["progress_note_written"] = True
            elif triage != "unknown":
                append_memory(prog, f"分诊 {triage}" + (f" → {to}" if to != "none" else ""))
                result["progress_note_written"] = True
            if task_id_s and to == "programmer":
                try:
                    update_task_status(prog, task_id_s, "in_progress")
                    result["task_updated"] = task_id_s
                except ValueError:
                    append_memory(prog, f"派工 task_id={task_id_s}（progress 中无此 id，已写 handoff）")
                    result["progress_note_written"] = True
            save_progress(prog, progress_file)
        except (ValueError, OSError, json.JSONDecodeError):
            pass

    if to == "programmer":
        title = task_id_s or (note[:40] if note else f"分诊-{triage}")
        summary = note or strip_dispatch_fence(assistant_message)[:800]
        doc = create_handoff(
            triage=triage,
            title=title,
            summary=summary,
            task_id=task_id_s,
            asset_names=asset_names,
            cli_hints=cli_hints,
            target_instance_id=target_instance_id,
            from_session_id=from_session_id,
            progress_path=str(progress_file.resolve()) if progress_file and progress_file.is_file() else None,
            brief_path=str(brief_path.resolve()) if brief_path and brief_path.is_file() else None,
            handoff_id=task_id_s,
            base_dir=base_dir,
        )
        result["handoff_path"] = doc.get("_path")
        result["handoff_id"] = doc.get("handoff_meta", {}).get("id")
        result["applied"] = True
    elif note and result["progress_note_written"]:
        result["applied"] = True
    elif to in {"pipeline", "brief_tab"} and (result["progress_note_written"] or cli_hints):
        result["applied"] = True

    return result


def apply_programmer_done(
    handoff_id: str,
    *,
    progress_path: Path | None,
    progress_note: str | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Mark handoff done and write progress task → done when possible."""
    from progress import append_memory, load_progress, save_progress, update_task_status

    result: dict[str, Any] = {
        "handoff_done": handoff_id,
        "handoff_path": None,
        "task_done": None,
        "progress_note_written": False,
    }
    path = handoff_path(handoff_id, base_dir=base_dir)
    if not path.is_file():
        raise HandoffError(f"handoff not found: {handoff_id}")
    data = set_handoff_status(path, "done")
    result["handoff_path"] = str(path.resolve())
    task_id = data.get("task_id")
    task_id_s = str(task_id).strip() if task_id else None
    note = (progress_note or "").strip() or f"程序员完成 handoff {handoff_id}"

    progress_file = progress_path
    if not progress_file or not progress_file.is_file():
        meta = data.get("handoff_meta") if isinstance(data.get("handoff_meta"), dict) else {}
        pp = meta.get("progress_path")
        if pp and Path(str(pp)).is_file():
            progress_file = Path(str(pp))

    if progress_file and progress_file.is_file():
        try:
            prog = load_progress(progress_file)
            append_memory(prog, note)
            result["progress_note_written"] = True
            if task_id_s:
                try:
                    update_task_status(prog, task_id_s, "done")
                    result["task_done"] = task_id_s
                except ValueError:
                    append_memory(prog, f"handoff 关单但 progress 无 task {task_id_s}")
            save_progress(prog, progress_file)
        except (ValueError, OSError, json.JSONDecodeError):
            pass
    return result
