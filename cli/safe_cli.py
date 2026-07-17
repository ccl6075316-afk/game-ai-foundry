"""Whitelist runner for post-triage next_actions (GUI / CLI).

Only allows a fixed set of `gamefactory.py` subcommands — no shell metacharacters.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

# (subcommand path prefix…) — argv after gamefactory.py
_ALLOWED: tuple[tuple[str, ...], ...] = (
    ("pipeline", "status"),
    ("pipeline", "plan"),
    ("pipeline", "run"),
    ("pipeline", "reset"),
    ("pipeline", "suggest-retry"),
    ("godot", "validate"),
    ("godot", "scaffold"),
    ("test", "unit"),
    ("test", "play"),
    ("test", "regression"),
    ("test", "run"),
    ("project", "progress", "show"),
    ("project", "progress", "init"),
    ("project", "handoff", "list"),
    ("production", "derive"),
    ("production", "validate"),
    ("production", "show"),
    ("production", "delta"),
    ("production", "apply-delta"),
    ("brief", "validate"),
    ("doctor",),
)


class SafeCliError(ValueError):
    pass


def _strip_comment(raw: str) -> str:
    line = (raw or "").strip()
    if not line or line.startswith("#"):
        return ""
    # allow trailing inline comment only after a space+#
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    return line


def parse_gamefactory_argv(raw: str) -> list[str]:
    """Return argv tokens for gamefactory.py (without python / script name)."""
    line = _strip_comment(raw)
    if not line:
        raise SafeCliError("empty command")
    if any(ch in line for ch in (";", "|", "&", "`", "$(", "\n", "\r")):
        raise SafeCliError("shell metacharacters are not allowed")
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        raise SafeCliError(f"cannot parse command: {exc}") from exc
    if not parts:
        raise SafeCliError("empty command")

    # Drop leading python / python3 / path-to-python
    while parts and re.match(r"^(python3?|py)(\.exe)?$", parts[0], re.I):
        parts = parts[1:]
    if not parts:
        raise SafeCliError("missing gamefactory.py")
    # Drop script name
    if parts[0].endswith("gamefactory.py") or parts[0] in ("gamefactory", "gamefactory.py"):
        parts = parts[1:]
    if not parts:
        raise SafeCliError("missing subcommand")
    return parts


def is_allowed_argv(argv: list[str]) -> bool:
    if not argv:
        return False
    for prefix in _ALLOWED:
        if len(argv) >= len(prefix) and tuple(argv[: len(prefix)]) == prefix:
            return True
    return False


def normalize_action(raw: str) -> dict[str, Any]:
    """Validate one next_action string → {ok, argv, label, error?}."""
    try:
        argv = parse_gamefactory_argv(raw)
    except SafeCliError as exc:
        return {"ok": False, "raw": raw, "error": str(exc), "argv": [], "label": ""}
    if not is_allowed_argv(argv):
        return {
            "ok": False,
            "raw": raw,
            "error": f"command not in whitelist: {' '.join(argv[:4])}",
            "argv": argv,
            "label": "",
        }
    label = " ".join(argv[:3]) if len(argv) >= 2 else argv[0]
    return {"ok": True, "raw": raw, "argv": argv, "label": label, "error": None}


def filter_runnable_actions(actions: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in actions:
        line = _strip_comment(str(raw))
        if not line:
            continue
        info = normalize_action(line)
        if info["ok"]:
            out.append(info)
    return out
