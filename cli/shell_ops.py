"""Shell runner for IT FOUNDRY_TOOL (trusted home-ops)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from inspect_ops import allow_roots

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SECRET_VALUE_RE = re.compile(r"\b(sk-[a-zA-Z0-9_-]{12,}|sk-or-[a-zA-Z0-9_-]{12,})\b")

DEFAULT_TIMEOUT_SEC = 120
MAX_TIMEOUT_SEC = 600
MAX_OUTPUT_CHARS = 100_000


class ShellError(ValueError):
    """User-facing shell failure."""


def resolve_cwd(raw: str | None) -> Path:
    text = (raw or "").strip()
    if not text:
        return _REPO_ROOT.resolve()
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = (_REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.is_dir():
        raise ShellError(f"cwd is not a directory: {candidate}")
    roots = allow_roots()
    if not any(candidate == root or root in candidate.parents for root in roots):
        raise ShellError(
            f"cwd outside allowlisted roots (repo or ~/.gamefactory): {candidate}"
        )
    return candidate


def _redact_text(text: str) -> str:
    return _SECRET_VALUE_RE.sub("***", text or "")


def run_shell(
    command: str,
    *,
    cwd: str | None = None,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    cmd = (command or "").strip()
    if not cmd:
        raise ShellError("command is required")
    work = resolve_cwd(cwd)
    limit = max(1.0, min(float(timeout_sec), float(MAX_TIMEOUT_SEC)))
    env = os.environ.copy()
    # Prefer repo cli on PATH for convenience
    cli_dir = str(_REPO_ROOT / "cli")
    env["PATH"] = cli_dir + os.pathsep + env.get("PATH", "")
    env["GAMEFACTORY_SHELL"] = "1"
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(work),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=limit,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        out = _redact_text((exc.stdout or "") if isinstance(exc.stdout, str) else "")
        err = _redact_text((exc.stderr or "") if isinstance(exc.stderr, str) else "")
        return {
            "ok": False,
            "cwd": str(work),
            "command": cmd,
            "timeout_sec": limit,
            "exit_code": None,
            "stdout": out[:MAX_OUTPUT_CHARS],
            "stderr": (err or f"timed out after {limit}s")[:MAX_OUTPUT_CHARS],
            "truncated": False,
            "error": f"timed out after {limit}s",
        }

    stdout = _redact_text(proc.stdout or "")
    stderr = _redact_text(proc.stderr or "")
    truncated = len(stdout) > MAX_OUTPUT_CHARS or len(stderr) > MAX_OUTPUT_CHARS
    return {
        "ok": proc.returncode == 0,
        "cwd": str(work),
        "command": cmd,
        "timeout_sec": limit,
        "exit_code": proc.returncode,
        "stdout": stdout[:MAX_OUTPUT_CHARS],
        "stderr": stderr[:MAX_OUTPUT_CHARS],
        "truncated": truncated,
    }
