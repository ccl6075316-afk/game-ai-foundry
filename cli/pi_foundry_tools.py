"""Whitelisted gamefactory CLI invocations for embedded Pi (brief / IT).

Pi itself runs with ``--no-tools``; when the model emits a FOUNDRY_TOOL fence,
Foundry executes only allow-listed argv and feeds stdout back into the next turn.

Write gates: ``brief chat export`` requires ``allow_export=True`` and a session that
is ready (or commit mode). Output paths must stay under projects/output/plans.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent

_TOOL_FENCE = re.compile(
    r"<<<FOUNDRY_TOOL\s*\r?\n(?P<body>.*?)\r?\n\s*FOUNDRY_TOOL>>>",
    re.DOTALL | re.IGNORECASE,
)

# Exact argv prefixes (after normalizing). First matching prefix wins.
_ALLOWED_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("doctor",),
    ("setup", "check"),
    ("setup", "pi", "status"),
    ("pipeline", "diagnose"),
    ("pipeline", "status"),
    ("pipeline", "heal"),
    ("brief", "chat", "status"),
    ("brief", "validate"),
    ("brief", "chat", "export"),  # gated separately via allow_export
)

_WRITE_PREFIXES = frozenset({("brief", "chat", "export")})

_EXPORT_ROOT_ALLOW = ("projects", "output", "plans")


def tool_protocol_instructions(*, profile: str = "it") -> str:
    """Append to Pi system prompts.

    ``profile``: ``it`` (ops) or ``brief`` (策划 — status/validate/export with gates).
    """
    if profile == "brief":
        return """
## Foundry tools (brief whitelist)

You have **no** shell. For session/machine facts, emit a fence then wait:

<<<FOUNDRY_TOOL
["brief", "chat", "status", "--session-id", "<SESSION_ID>", "--json"]
FOUNDRY_TOOL>>>

Allowed:
- `brief chat status --session-id <id> --json`
- `brief validate --brief <path> --json` (existing exported brief on disk)
- `brief chat export --session-id <id> -o <path> --json` — **only** after the user
  clearly asked to 落实/导出 **and** the host said export is allowed this turn.
  Output path must be under `projects/`, `output/`, or `plans/`, ending in `.json`.

Rules:
- Prefer `--json`.
- Do **not** claim brief.json was written unless export tool returned ok.
- After tools (or if none needed), your **final** reply must still be the skill JSON
  object (`assistant_message`, `choices`, `draft_brief`, …). No markdown outside JSON.
- Never run `pipeline run` or spend money.
""".strip()

    examples = "\n".join(f"- `{' '.join(p)} …`" for p in _ALLOWED_PREFIXES if p not in _WRITE_PREFIXES)
    return f"""
## Foundry tools (whitelist only)

You have **no** shell/read/write tools. To inspect this machine, emit ONE OR MORE fences
(then stop and wait for results):

<<<FOUNDRY_TOOL
["doctor", "--json"]
FOUNDRY_TOOL>>>

Allowed command prefixes (arguments after the prefix must be flags/paths only; no `;` `|` `&&`):
{examples}
- `brief chat export …` is **not** for IT (use 策划 for export).

Rules:
- Prefer `--json` when available.
- Never invent tool output; wait for the host to paste results.
- After tools, answer the user in Chinese. Do **not** claim you changed config unless a tool did.
- Do **not** run `pipeline run` or any generate/install that spends money or mutates projects
  unless the user explicitly asked and the command is on the allow-list (it is not).
""".strip()


def extract_foundry_tools(text: str) -> list[list[str]]:
    """Parse FOUNDRY_TOOL fences → list of argv arrays."""
    out: list[list[str]] = []
    for m in _TOOL_FENCE.finditer(text or ""):
        body = (m.group("body") or "").strip()
        if not body:
            continue
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, list) or not parsed:
            continue
        argv = [str(x).strip() for x in parsed if str(x).strip()]
        if argv:
            out.append(argv)
    return out


def strip_foundry_tools(text: str) -> str:
    return _TOOL_FENCE.sub("", text or "").strip()


def _prefix_of(argv: list[str]) -> tuple[str, ...] | None:
    for prefix in _ALLOWED_PREFIXES:
        if len(argv) >= len(prefix) and tuple(argv[: len(prefix)]) == prefix:
            return prefix
    return None


def is_allowed_argv(argv: list[str], *, allow_export: bool = False) -> bool:
    if not argv:
        return False
    joined = " ".join(argv)
    if any(ch in joined for ch in (";", "|", "&", "`", "\n", "\r", "$(", "${")):
        return False
    prefix = _prefix_of(argv)
    if prefix is None:
        return False
    if prefix in _WRITE_PREFIXES and not allow_export:
        return False
    rest = argv[len(prefix) :]
    for tok in rest:
        if tok.startswith("-"):
            continue
        if any(ch in tok for ch in ("*", "?", "<", ">")):
            return False
    if prefix == ("brief", "chat", "export"):
        return _export_argv_ok(argv)
    return True


def _flag_value(argv: list[str], *names: str) -> str | None:
    for i, tok in enumerate(argv):
        if tok in names and i + 1 < len(argv):
            return argv[i + 1]
        for name in names:
            if tok.startswith(f"{name}=") and len(tok) > len(name) + 1:
                return tok.split("=", 1)[1]
    return None


def _export_argv_ok(argv: list[str]) -> bool:
    out = _flag_value(argv, "-o", "--output")
    if not out or not out.lower().endswith(".json"):
        return False
    # Must resolve under repo projects|output|plans (no arbitrary absolute paths).
    try:
        target = Path(out)
        if not target.is_absolute():
            target = (_REPO_ROOT / target).resolve()
        else:
            target = target.resolve()
        root = _REPO_ROOT.resolve()
        try:
            rel = target.relative_to(root)
        except ValueError:
            return False
        top = rel.parts[0].lower() if rel.parts else ""
        if top not in _EXPORT_ROOT_ALLOW:
            return False
    except (OSError, RuntimeError):
        return False
    sid = _flag_value(argv, "--session-id")
    return bool(sid and re.fullmatch(r"[a-zA-Z0-9._-]{1,80}", sid))


def _session_allows_export(session_id: str) -> tuple[bool, str]:
    """Load brief chat session; export only when ready_to_export."""
    try:
        from host_chat import load_session, session_path_for_id

        path = session_path_for_id(session_id)
        if not path.is_file():
            return False, f"session not found: {session_id}"
        session = load_session(path)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

    if session.get("ready_to_export"):
        return True, "ready_to_export"
    return False, "session not ready_to_export (落实完成后再导出)"


def _gamefactory_python() -> str:
    env = (os.environ.get("GAMEFACTORY_PYTHON") or "").strip()
    if env and Path(env).exists():
        return env
    return sys.executable


def run_allowed_gamefactory(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout_sec: float = 120.0,
    allow_export: bool = False,
) -> dict[str, Any]:
    """Run ``python gamefactory.py <argv>`` if allow-listed."""
    if not is_allowed_argv(argv, allow_export=allow_export):
        return {
            "ok": False,
            "argv": argv,
            "error": f"command not on Pi whitelist (or export gated): {argv!r}",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

    prefix = _prefix_of(argv)
    if prefix == ("brief", "chat", "export"):
        sid = _flag_value(argv, "--session-id") or ""
        ok, reason = _session_allows_export(sid)
        if not ok:
            return {
                "ok": False,
                "argv": argv,
                "error": f"export blocked: {reason}",
                "stdout": "",
                "stderr": "",
                "exit_code": None,
            }

    cli = _REPO_ROOT / "cli" / "gamefactory.py"
    if not cli.is_file():
        return {
            "ok": False,
            "argv": argv,
            "error": f"gamefactory.py not found at {cli}",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

    cmd = [_gamefactory_python(), str(cli), *argv]
    work = cwd or _REPO_ROOT
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            cwd=str(work),
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "argv": argv,
            "error": f"timeout after {timeout_sec}s",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }
    except OSError as exc:
        return {
            "ok": False,
            "argv": argv,
            "error": str(exc),
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

    return {
        "ok": proc.returncode == 0,
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "")[-8000:],
        "stderr": (proc.stderr or "")[-2000:],
        "error": None
        if proc.returncode == 0
        else (proc.stderr or proc.stdout or f"exit {proc.returncode}")[-500:],
    }


def run_tool_round(
    text: str,
    *,
    cwd: Path | None = None,
    allow_export: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    """Execute all tools found in ``text``; return (results, text_without_fences)."""
    tools = extract_foundry_tools(text)
    results = [
        run_allowed_gamefactory(argv, cwd=cwd, allow_export=allow_export) for argv in tools
    ]
    return results, strip_foundry_tools(text)
