"""GUI / CLI bridge for approving mutating FOUNDRY_TOOL calls.

When ``GAMEFACTORY_TOOL_PERMISSION_URL`` is set (Electron loopback), mutating
tools pause for a decision before execution. Turn-scoped allow lives in-process;
session-scoped allow is enforced by the HTTP server (Electron).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

Decision = Literal["once", "turn", "session", "deny"]

DEFAULT_TIMEOUT_SEC = 300.0
ENV_URL = "GAMEFACTORY_TOOL_PERMISSION_URL"
ENV_TOKEN = "GAMEFACTORY_TOOL_PERMISSION_TOKEN"


@dataclass
class PermissionTurnState:
    """In-process memory for one agent turn (one Python process)."""

    turn_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    allow_rest_of_turn: bool = False

    def remember(self, decision: Decision) -> None:
        if decision == "turn":
            self.allow_rest_of_turn = True


PermissionRequester = Callable[[dict[str, Any]], Decision]


def permission_bridge_configured() -> bool:
    return bool((os.environ.get(ENV_URL) or "").strip())


def summarize_argv(argv: list[str]) -> str:
    redacted: list[str] = []
    skip_next = False
    sensitive = {"--api-key", "--key", "--token", "--password"}
    for i, tok in enumerate(argv):
        if skip_next:
            skip_next = False
            redacted.append("***")
            continue
        if tok in sensitive and i + 1 < len(argv):
            redacted.append(tok)
            skip_next = True
            continue
        for name in sensitive:
            if tok.startswith(f"{name}="):
                redacted.append(f"{name}=***")
                break
        else:
            redacted.append(tok)
    return " ".join(redacted)


def _http_request_decision(payload: dict[str, Any], *, timeout_sec: float) -> Decision:
    url = (os.environ.get(ENV_URL) or "").strip()
    if not url:
        return "deny"
    token = (os.environ.get(ENV_TOKEN) or "").strip()
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return "deny"
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return "deny"
    decision = str(data.get("decision") or "").strip().lower()
    if decision in ("once", "turn", "session", "deny"):
        return decision  # type: ignore[return-value]
    return "deny"


def request_mutate_permission(
    argv: list[str],
    *,
    session_id: str = "",
    turn_state: PermissionTurnState | None = None,
    requester: PermissionRequester | None = None,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> Decision:
    """Ask GUI (or ``requester``) whether to run a mutating tool.

    If no bridge URL and no ``requester``, returns ``once`` so legacy
    ``--i-confirm``-in-argv CLI paths keep working.
    """
    state = turn_state or PermissionTurnState()
    if state.allow_rest_of_turn:
        return "once"

    if requester is None and not permission_bridge_configured():
        return "once"

    permission_id = uuid.uuid4().hex
    payload = {
        "permission_id": permission_id,
        "session_id": session_id or "",
        "turn_id": state.turn_id,
        "argv": list(argv),
        "argv_summary": summarize_argv(argv),
    }

    if requester is not None:
        decision = requester(payload)
    else:
        decision = _http_request_decision(payload, timeout_sec=timeout_sec)

    if decision not in ("once", "turn", "session", "deny"):
        decision = "deny"
    state.remember(decision)
    return decision


def ensure_i_confirm(argv: list[str]) -> list[str]:
    if "--i-confirm" in argv:
        return list(argv)
    return [*argv, "--i-confirm"]
