"""List / show Foundry agent & brief conversation sessions (IT read path)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_turn import ROLE_KINDS, conversations_dir as agent_conversations_dir
from host_chat import conversations_dir as brief_conversations_dir
from inspect_ops import redact_secrets

ROLE_ALIASES = {
    "brief": "brief",
    "策划": "brief",
    "it": "it",
    "运维": "it",
    "programmer": "programmer",
    "程序员": "programmer",
    "product_host": "product_host",
    "项目经理": "product_host",
    "pm": "product_host",
}


class ConversationsError(ValueError):
    """User-facing conversations failure."""


def normalize_role(raw: str) -> str:
    key = (raw or "").strip().lower()
    if key in ROLE_ALIASES:
        return ROLE_ALIASES[key]
    if key == "brief" or key in ROLE_KINDS:
        return key
    raise ConversationsError(f"unknown role: {raw!r} (brief|it|programmer|product_host)")


def role_dir(role: str) -> Path:
    role = normalize_role(role)
    if role == "brief":
        return brief_conversations_dir()
    return agent_conversations_dir(role)


def list_sessions(role: str, *, limit: int = 30) -> dict[str, Any]:
    root = role_dir(role)
    if not root.is_dir():
        return {"ok": True, "role": normalize_role(role), "path": str(root), "sessions": [], "count": 0}
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    sessions: list[dict[str, Any]] = []
    for path in files[: max(1, limit)]:
        if path.name.startswith("_"):
            continue
        meta: dict[str, Any] = {
            "id": path.stem,
            "path": str(path),
            "mtime": path.stat().st_mtime,
            "size": path.stat().st_size,
        }
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                meta["message_count"] = len(data.get("messages") or [])
                meta["updated_at"] = data.get("updated_at")
                meta["title"] = (
                    (data.get("draft_brief") or {}).get("title")
                    if isinstance(data.get("draft_brief"), dict)
                    else data.get("title")
                )
                meta["summary"] = str(data.get("summary") or "")[:200]
        except (OSError, json.JSONDecodeError):
            pass
        sessions.append(meta)
    return {
        "ok": True,
        "role": normalize_role(role),
        "path": str(root),
        "count": len(sessions),
        "sessions": sessions,
    }


def show_session(
    role: str,
    session_id: str,
    *,
    tail: int = 40,
) -> dict[str, Any]:
    role_n = normalize_role(role)
    sid = (session_id or "").strip()
    if not sid:
        raise ConversationsError("session_id is required")
    root = role_dir(role_n)
    path = root / f"{sid}.json"
    if not path.is_file():
        matches = [p for p in root.glob(f"*{sid}*.json") if not p.name.startswith("_")]
        if len(matches) == 1:
            path = matches[0]
        else:
            raise ConversationsError(f"session not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConversationsError("session root must be object")
    messages = list(data.get("messages") or [])
    tail_n = max(1, int(tail))
    sliced = messages[-tail_n:]
    draft = data.get("draft_brief")
    draft_summary = None
    if isinstance(draft, dict):
        draft_summary = {
            "title": draft.get("title"),
            "asset_count": len(draft.get("assets") or []) if isinstance(draft.get("assets"), list) else None,
        }
    return {
        "ok": True,
        "role": role_n,
        "path": str(path),
        "id": data.get("id") or path.stem,
        "updated_at": data.get("updated_at"),
        "message_count": len(messages),
        "tail": len(sliced),
        "summary": data.get("summary"),
        "draft_brief": draft_summary,
        "messages": redact_secrets(sliced),
    }
