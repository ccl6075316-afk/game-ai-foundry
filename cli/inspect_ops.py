"""Read-only inspect helpers for IT (list/read under allowlisted roots)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GAMEFACTORY_HOME = Path.home() / ".gamefactory"

# Deny bulky / irrelevant trees even inside the repo root.
_DENY_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "release",
        "runtime",
        "dist",
        "build",
        ".tox",
    }
)

_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|password|secret|authorization|bearer)",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"\b(sk-[a-zA-Z0-9_-]{12,}|sk-or-[a-zA-Z0-9_-]{12,})\b",
)

DEFAULT_MAX_BYTES = 200_000
DEFAULT_LIST_LIMIT = 200


class InspectError(ValueError):
    """User-facing inspect failure."""


def repo_root() -> Path:
    return _REPO_ROOT


def allow_roots() -> list[Path]:
    return [_REPO_ROOT.resolve(), _GAMEFACTORY_HOME.resolve()]


def _is_denied_dir(path: Path) -> bool:
    return any(part in _DENY_DIR_NAMES for part in path.parts)


def resolve_readable_path(raw: str | Path, *, must_exist: bool = True) -> Path:
    text = str(raw or "").strip()
    if not text:
        raise InspectError("path is required")
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = (_REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    roots = allow_roots()
    if not any(candidate == root or root in candidate.parents for root in roots):
        raise InspectError(f"path outside allowlisted roots: {candidate}")
    if _is_denied_dir(candidate):
        raise InspectError(f"path under denied directory: {candidate}")
    # Also deny if any parent is a denied name inside repo
    try:
        rel = candidate.relative_to(_REPO_ROOT.resolve())
        if any(part in _DENY_DIR_NAMES for part in rel.parts):
            raise InspectError(f"path under denied directory: {candidate}")
    except ValueError:
        pass

    if must_exist and not candidate.exists():
        raise InspectError(f"path not found: {candidate}")
    return candidate


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if _SECRET_KEY_RE.search(str(k)):
                out[k] = "***"
            else:
                out[k] = redact_secrets(v)
        return out
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub("***", value)
    return value


def list_dir(path: str | Path, *, limit: int = DEFAULT_LIST_LIMIT) -> dict[str, Any]:
    target = resolve_readable_path(path, must_exist=True)
    if not target.is_dir():
        raise InspectError(f"not a directory: {target}")
    entries: list[dict[str, Any]] = []
    children = sorted(target.iterdir(), key=lambda p: p.name.lower())
    total_visible = 0
    for child in children:
        if child.name in _DENY_DIR_NAMES:
            continue
        total_visible += 1
        if len(entries) >= max(1, limit):
            continue
        try:
            st = child.stat()
        except OSError:
            continue
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "type": "dir" if child.is_dir() else "file",
                "size": st.st_size if child.is_file() else None,
            }
        )
    return {
        "ok": True,
        "path": str(target),
        "count": len(entries),
        "entries": entries,
        "truncated": total_visible > len(entries),
    }


def read_file(
    path: str | Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    offset: int = 0,
) -> dict[str, Any]:
    target = resolve_readable_path(path, must_exist=True)
    if not target.is_file():
        raise InspectError(f"not a file: {target}")
    size = target.stat().st_size
    start = max(0, int(offset))
    limit = max(1, int(max_bytes))
    data = target.read_bytes()[start : start + limit]
    truncated = start + len(data) < size
    text: str | None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    payload: dict[str, Any] = {
        "ok": True,
        "path": str(target),
        "size": size,
        "offset": start,
        "bytes_returned": len(data),
        "truncated": truncated,
        "encoding": "utf-8" if text is not None else "binary",
    }
    if text is None:
        payload["content_base64_prefix"] = __import__("base64").b64encode(data[:64]).decode("ascii")
        payload["note"] = "binary file; content not inlined"
        return payload

    text = _SECRET_VALUE_RE.sub("***", text)
    if target.suffix.lower() == ".json" or target.name == "config.json":
        try:
            parsed = json.loads(text)
            payload["json"] = redact_secrets(parsed)
            payload["content"] = None
            return payload
        except json.JSONDecodeError:
            pass
    payload["content"] = text
    return payload
