"""Foundry sitecustomize — fix Hermes ACP permission bridge (0.13.x).

Two upstream bugs prevent ``session/request_permission`` from reaching clients:

1. ``prompt_dangerous_approval`` passes ``allow_permanent=`` but ACP callback
   only accepts ``(command, description)`` → TypeError → silent deny.
2. ``make_approval_callback`` builds ``ToolCallStart`` via ``start_tool_call``,
   but ACP ``RequestPermissionRequest.tool_call`` requires ``ToolCallUpdate``
   → pydantic validation error → silent deny.

Foundry loads this via PYTHONPATH when spawning the Hermes *venv* binary
(``~/.local/bin/hermes`` unsets PYTHONPATH).
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Callable

_log = logging.getLogger("foundry.hermes_acp_runtime")
_patched = False

_KIND_TO_HERMES = {
    "allow_once": "once",
    "allow_always": "always",
    "reject_once": "deny",
    "reject_always": "deny",
}


def _foundry_make_approval_callback(
    request_permission_fn: Callable,
    loop: asyncio.AbstractEventLoop,
    session_id: str,
    timeout: float = 60.0,
) -> Callable[..., str]:
    def _callback(command: str, description: str, allow_permanent: bool = True, **_extra) -> str:
        from acp.schema import AllowedOutcome, PermissionOption, ToolCallUpdate

        options = [
            PermissionOption(option_id="allow_once", kind="allow_once", name="Allow once"),
            PermissionOption(option_id="allow_always", kind="allow_always", name="Allow always"),
            PermissionOption(option_id="deny", kind="reject_once", name="Deny"),
        ]
        # RequestPermissionRequest requires ToolCallUpdate (not ToolCallStart).
        tool_call = ToolCallUpdate(
            toolCallId="perm-check",
            title=str(command or description or "command"),
            kind="execute",
            status="pending",
        )
        coro = request_permission_fn(
            session_id=session_id,
            tool_call=tool_call,
            options=options,
        )
        try:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            response = future.result(timeout=timeout)
        except (FutureTimeout, Exception) as exc:
            _log.warning("Foundry Hermes ACP permission request failed: %s", exc)
            return "deny"

        if response is None:
            return "deny"

        outcome = response.outcome
        if isinstance(outcome, AllowedOutcome):
            option_id = outcome.option_id
            for opt in options:
                if opt.option_id == option_id:
                    return _KIND_TO_HERMES.get(opt.kind, "deny")
            return "once"
        return "deny"

    return _callback


def _patch_module(mod) -> bool:
    global _patched
    if getattr(mod.make_approval_callback, "_foundry_permission_bridge", False):
        _patched = True
        return True
    replacement = _foundry_make_approval_callback
    replacement._foundry_permission_bridge = True  # type: ignore[attr-defined]
    mod.make_approval_callback = replacement
    _patched = True
    _log.info("Foundry patched acp_adapter.permissions.make_approval_callback")
    return True


def _try_patch_now() -> None:
    try:
        import acp_adapter.permissions as perm

        _patch_module(perm)
    except Exception as exc:  # noqa: BLE001
        _log.debug("defer hermes ACP permission patch: %s", exc)


_try_patch_now()

# Re-patch if hermes reloads the module later.
import builtins

_orig_import = builtins.__import__


def __import__(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A001
    mod = _orig_import(name, globals, locals, fromlist, level)
    if name == "acp_adapter.permissions":
        _patch_module(mod)
    elif name == "acp_adapter" and fromlist and "permissions" in fromlist:
        perm = getattr(mod, "permissions", None)
        if perm is not None:
            _patch_module(perm)
    return mod


builtins.__import__ = __import__
