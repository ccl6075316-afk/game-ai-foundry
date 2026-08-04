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

from tool_permission import (
    PermissionTurnState,
    ensure_i_confirm,
    permission_bridge_configured,
    request_mutate_permission,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

_TOOL_FENCE = re.compile(
    r"<<<FOUNDRY_TOOL\s*\r?\n(?P<body>.*?)\r?\n\s*FOUNDRY_TOOL>>>",
    re.DOTALL | re.IGNORECASE,
)

# Exact argv prefixes (after normalizing). First matching prefix wins —
# list longer/more-specific prefixes before shorter ones that share a stem.
_ALLOWED_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("doctor",),
    ("setup", "check"),
    ("setup", "pi", "status"),
    ("setup", "provider", "upsert"),
    ("setup", "provider", "models"),
    ("setup", "install"),
    ("setup", "ensure"),
    ("setup", "executor", "status"),
    ("setup", "executor", "step"),
    ("setup", "executor", "models"),
    ("setup", "agents", "executors", "upsert"),
    ("setup", "agents", "instances", "upsert"),
    ("pipeline", "diagnose"),
    ("pipeline", "status"),
    ("pipeline", "heal"),
    ("pipeline", "reset"),
    ("pipeline", "plan"),
    ("pipeline", "run"),
    ("pipeline", "suggest-retry"),
    ("brief", "chat", "status"),
    ("brief", "chat", "bind"),
    ("brief", "chat", "zh-doc"),
    ("brief", "chat", "autofix"),
    ("brief", "chat", "makeability"),
    ("brief", "chat", "enrich"),
    ("brief", "zh-doc"),
    ("brief", "validate"),
    ("brief", "chat", "export"),  # gated separately via allow_export; brief profile only in practice
    ("project", "external", "list"),
    ("project", "external", "detect"),
    ("assets", "review", "list"),
    ("assets", "review", "regenerate-plan"),
    # Broad read (IT): conversations + filesystem under repo / ~/.gamefactory
    ("conversations", "list"),
    ("conversations", "show"),
    ("inspect", "list"),
    ("inspect", "read"),
    ("shell", "run"),
)

# Mutating ops: FOUNDRY_TOOL argv must include --i-confirm (stripped before CLI
# except for commands that consume the flag themselves).
_MUTATE_PREFIXES: frozenset[tuple[str, ...]] = frozenset(
    {
        ("setup", "provider", "upsert"),
        ("setup", "install"),
        ("setup", "ensure"),
        ("setup", "executor", "step"),
        ("setup", "agents", "executors", "upsert"),
        ("setup", "agents", "instances", "upsert"),
        ("pipeline", "heal"),
        ("pipeline", "reset"),
        ("pipeline", "plan"),
        ("pipeline", "run"),
        ("brief", "chat", "bind"),
        ("brief", "chat", "zh-doc"),
        ("brief", "chat", "autofix"),
        ("brief", "chat", "enrich"),
        ("brief", "zh-doc"),
        ("shell", "run"),
    }
)

# These Click commands declare --i-confirm; keep the flag in subprocess argv.
_KEEP_I_CONFIRM_PREFIXES: frozenset[tuple[str, ...]] = frozenset(
    {
        ("setup", "provider", "upsert"),
        ("setup", "agents", "executors", "upsert"),
        ("setup", "agents", "instances", "upsert"),
        ("shell", "run"),
    }
)

_WRITE_PREFIXES = frozenset({("brief", "chat", "export")})

# Brief Pi: draft/review/export + read-only local/session lookup.
# Never: shell, pipeline run/plan/heal, setup install/upsert, image spend.
_BRIEF_ALLOWED_PREFIXES = frozenset(
    {
        ("brief", "chat", "status"),
        ("brief", "chat", "makeability"),
        ("brief", "chat", "autofix"),
        ("brief", "chat", "enrich"),
        ("brief", "chat", "zh-doc"),
        ("brief", "chat", "bind"),
        ("brief", "zh-doc"),
        ("brief", "validate"),
        ("brief", "chat", "export"),
        # Session / filesystem / env / board read (no mutate).
        ("conversations", "list"),
        ("conversations", "show"),
        ("inspect", "list"),
        ("inspect", "read"),
        ("doctor",),
        ("setup", "check"),
        ("setup", "pi", "status"),
        ("pipeline", "diagnose"),
        ("pipeline", "status"),
        ("assets", "review", "list"),
    }
)

_EXPORT_ROOT_ALLOW = ("projects", "output", "plans")

_INSTALL_TIMEOUT_SEC = 900.0
_DEFAULT_TOOL_TIMEOUT_SEC = 120.0


def tool_protocol_instructions(*, profile: str = "it") -> str:
    """Append to Pi system prompts.

    ``profile``: ``it`` (ops) or ``brief`` (策划 — draft/review/export tools).
    """
    if profile == "brief":
        return """
## Foundry tools (brief whitelist)

You have **no** shell and **no** pipeline run/plan/heal or setup install/upsert.
When you need session logs or on-disk facts, **emit FOUNDRY_TOOL** — do not guess.

<<<FOUNDRY_TOOL
["brief", "chat", "status", "--session-id", "<SESSION_ID>", "--json"]
FOUNDRY_TOOL>>>

### Draft / export
- `brief chat status --session-id <id> --json`
- `brief chat makeability --session-id <id> --json` — **制作审查**
- `brief chat enrich … --json --i-confirm` — 补全细节
- `brief chat autofix … --json --i-confirm`
- `brief chat zh-doc` / `brief zh-doc` / `brief chat bind` — need `--i-confirm` where mutating
- `brief validate --brief <path> --json`
- `brief chat export …` — **only** when host said export is allowed this turn

### 查日志 / 查本地（只读）
- 会话：`conversations list --role brief --json` → `conversations show --role brief --session-id <id> --tail 40 --json`
- 工程文件：`inspect list --path projects/<slug> --json` → `inspect read --path projects/<slug>/brief.json --json`
- 北极星/产出：`inspect list --path projects/<slug>/output/visual-target --json`；读 `manifest.json` / 文案 plans
- 策划会话落盘：`plans/conversations/brief/`（list/show 或 inspect）
- 环境快照：`doctor --json`；`setup check --json`；`setup pi status --json`
- 看板只读：`pipeline status|diagnose --json`（**不要** plan/run）；`assets review list --json`
- `inspect` / `conversations` 根目录限仓库或 `~/.gamefactory`；密钥已脱敏

Examples:
<<<FOUNDRY_TOOL
["conversations", "list", "--role", "brief", "--json"]
FOUNDRY_TOOL>>>
<<<FOUNDRY_TOOL
["inspect", "read", "--path", "projects/fishing-2d/output/visual-target/manifest.json", "--json"]
FOUNDRY_TOOL>>>

Rules:
- Prefer `--json`. Mutating brief tools need `--i-confirm` (session trust may auto-approve).
- User asks 制作审查 / 缺口 / 能不能导出 → emit **makeability**, not only narration.
- User asks 看看日志 / 本地有没有 / 磁盘上 brief·图·会话 → emit **conversations / inspect**, not only narration.
- Do **not** claim brief.json was written unless export returned ok.
- Final reply must still be skill JSON (`assistant_message`, `choices`, `draft_brief`, …).
- Never `shell run`, `pipeline run|plan|heal`, or image spend via tools.
""".strip()

    examples = "\n".join(f"- `{' '.join(p)} …`" for p in _ALLOWED_PREFIXES if p not in _WRITE_PREFIXES)
    return f"""
## Foundry tools (whitelist only) — IT home ops

You have FOUNDRY_TOOL access (including **shell**). Prefer dedicated tools first; use shell when needed.

<<<FOUNDRY_TOOL
["doctor", "--json"]
FOUNDRY_TOOL>>>

Allowed command prefixes:
{examples}

Home-ops playbooks (Chinese answers):
1. **Environment** — doctor / setup check / install / executor step / provider upsert / agents instances|executors upsert
2. **Project draft** — brief chat bind / zh-doc / status (sync + Chinese doc **before** export)
3. **Export readiness** — autofix / makeability / enrich / validate (do **not** export unless user clearly says 导出)
4. **Board / pipeline** — diagnose / status / heal / reset / plan / **run** (spend API; prefer --jobs 1..4)
5. **Assets** — assets review list / regenerate-plan (guide user; soft annotations)
6. **Read** — `conversations list|show`, `inspect list|read` (secrets redacted)
7. **Shell** — `shell run --command "…" --i-confirm --json` (cwd: repo or ~/.gamefactory; prefer GUI approve when bridge is on, otherwise `--i-confirm` is enough)


Rules:
- Prefer `--json` when available.
- Never invent tool output; wait for host results.
- Answer in Chinese; do not claim config/disk changes unless a tool returned ok.
- **Finish or tool — never fake continue:** if you still need a fact, emit FOUNDRY_TOOL
  in the **same** reply. Do not end with only「我再确认一下… / 让我再查…」.
  When done, write an explicit **结论**.
- Do **not** casually rewrite Foundry/Electron/Pi source or `games/` C# — if needed, say so and keep diffs minimal / ask first.
- Do **not** tell users to install system Python/Node for Release — embed + toolchain auto/IT install.
- **Mutating ops** (including shell) need `--i-confirm`. When the GUI permission
  bridge is connected, the host may ask once/turn/session — prefer approving so
  work can finish. Without a bridge, `--i-confirm` alone is enough. Mask API Keys in chat.
  Example (shell):
  <<<FOUNDRY_TOOL
  ["shell", "run", "--command", "ls -la plans/conversations/brief | head", "--i-confirm", "--json"]
  FOUNDRY_TOOL>>>
  Example (read 策划 session):
  <<<FOUNDRY_TOOL
  ["conversations", "list", "--role", "brief", "--json"]
  FOUNDRY_TOOL>>>
  <<<FOUNDRY_TOOL
  ["conversations", "show", "--role", "brief", "--session-id", "<id>", "--tail", "30", "--json"]
  FOUNDRY_TOOL>>>
  Example (read config redacted / project file):
  <<<FOUNDRY_TOOL
  ["inspect", "read", "--path", "~/.gamefactory/config.json", "--json"]
  FOUNDRY_TOOL>>>
  Example (Key mutate):
  <<<FOUNDRY_TOOL
  ["setup", "provider", "upsert", "--provider", "deepseek", "--api-key", "<KEY>", "--set-active-text", "--i-confirm", "--json"]
  FOUNDRY_TOOL>>>
  Example (Thinking):
  <<<FOUNDRY_TOOL
  ["setup", "agents", "instances", "upsert", "--instance-id", "<id>", "--thinking-level", "medium", "--i-confirm", "--json"]
  FOUNDRY_TOOL>>>
  Example (Hermes for 项目经理):
  <<<FOUNDRY_TOOL
  ["setup", "executor", "step", "hermes", "install_cli", "--i-confirm", "--json"]
  FOUNDRY_TOOL>>>
  Example (pipeline run):
  <<<FOUNDRY_TOOL
  ["pipeline", "run", "--manifest", "projects/<slug>/pipeline/manifest.json", "--jobs", "4", "--json", "--i-confirm"]
  FOUNDRY_TOOL>>>
  Example (Chinese doc before export):
  <<<FOUNDRY_TOOL
  ["brief", "chat", "zh-doc", "--session-id", "<SESSION_ID>", "--brief-rel", "projects/<slug>/brief.json", "--json", "--i-confirm"]
  FOUNDRY_TOOL>>>
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


def is_allowed_argv(
    argv: list[str],
    *,
    allow_export: bool = False,
    profile: str = "it",
) -> bool:
    if not argv:
        return False
    prefix = _prefix_of(argv)
    if prefix is None:
        return False
    if profile == "brief" and prefix not in _BRIEF_ALLOWED_PREFIXES:
        return False
    # Shell commands may contain ; | & — only this prefix is exempt.
    joined = " ".join(argv)
    if prefix != ("shell", "run") and any(
        ch in joined for ch in (";", "|", "&", "`", "\n", "\r", "$(", "${")
    ):
        return False
    # IT never exports; defense-in-depth even if allow_export is mis-set.
    if profile == "it" and prefix in _WRITE_PREFIXES:
        return False
    if prefix in _WRITE_PREFIXES and not allow_export:
        return False
    if prefix in _MUTATE_PREFIXES and "--i-confirm" not in argv:
        return False
    # Glob metacharacters in non-shell argv remain blocked.
    if prefix != ("shell", "run"):
        rest = argv[len(prefix) :]
        for tok in rest:
            if tok.startswith("-"):
                continue
            if any(ch in tok for ch in ("*", "?", "<", ">")):
                return False
    if prefix == ("brief", "chat", "export"):
        return _export_argv_ok(argv)
    if prefix in {
        ("brief", "chat", "zh-doc"),
        ("brief", "chat", "bind"),
        ("brief", "zh-doc"),
    }:
        return _brief_rel_argv_ok(argv)
    return True


def _argv_for_subprocess(argv: list[str], prefix: tuple[str, ...] | None) -> list[str]:
    if prefix in _KEEP_I_CONFIRM_PREFIXES:
        return list(argv)
    return [t for t in argv if t != "--i-confirm"]


def _timeout_for_prefix(prefix: tuple[str, ...] | None) -> float:
    if prefix in {
        ("setup", "install"),
        ("setup", "ensure"),
        ("pipeline", "run"),
        ("brief", "chat", "autofix"),
        ("brief", "chat", "enrich"),
        ("brief", "chat", "makeability"),
        ("shell", "run"),
    }:
        return _INSTALL_TIMEOUT_SEC
    return _DEFAULT_TOOL_TIMEOUT_SEC


def _flag_value(argv: list[str], *names: str) -> str | None:
    for i, tok in enumerate(argv):
        if tok in names and i + 1 < len(argv):
            return argv[i + 1]
        for name in names:
            if tok.startswith(f"{name}=") and len(tok) > len(name) + 1:
                return tok.split("=", 1)[1]
    return None


def _repo_rel_under_allow(rel_or_path: str, *, must_end: str | None = None) -> bool:
    """True if path is under projects|output|plans, or virtual external:<id>/…."""
    raw = str(rel_or_path or "").replace("\\", "/").strip()
    if not raw:
        return False
    if must_end and not raw.lower().endswith(must_end.lower()):
        return False
    if raw.lower().startswith("external:"):
        rest = raw.split(":", 1)[1]
        return bool(rest) and ".." not in Path(rest).parts
    try:
        target = Path(raw)
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
        return top in _EXPORT_ROOT_ALLOW
    except (OSError, RuntimeError):
        return False


def _export_argv_ok(argv: list[str]) -> bool:
    out = _flag_value(argv, "-o", "--output")
    if not out or not _repo_rel_under_allow(out, must_end=".json"):
        return False
    sid = _flag_value(argv, "--session-id")
    return bool(sid and re.fullmatch(r"[a-zA-Z0-9._-]{1,80}", sid))


def _brief_rel_argv_ok(argv: list[str]) -> bool:
    """zh-doc / bind: --brief-rel must stay under allowed roots (same spirit as export)."""
    brief_rel = _flag_value(argv, "--brief-rel")
    if not brief_rel or not _repo_rel_under_allow(brief_rel):
        return False
    sid = _flag_value(argv, "--session-id")
    if sid is not None and not re.fullmatch(r"[a-zA-Z0-9._-]{1,80}", sid):
        return False
    return True


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


def is_mutating_argv(argv: list[str]) -> bool:
    prefix = _prefix_of(argv)
    return prefix is not None and prefix in _MUTATE_PREFIXES


def run_allowed_gamefactory(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout_sec: float | None = None,
    allow_export: bool = False,
    profile: str = "it",
    permission_session_id: str = "",
    permission_turn_state: PermissionTurnState | None = None,
) -> dict[str, Any]:
    """Run ``python gamefactory.py <argv>`` if allow-listed."""
    run_argv_in = list(argv)

    # When the GUI permission bridge is up, ask before mutates (once/turn/session).
    # Bridge unreachable → fall through like no bridge (--i-confirm still required).
    # Without a bridge: do not block — require --i-confirm via is_allowed_argv so
    # headless/CLI Pi can still complete user work (completion > permission theater).
    if is_mutating_argv(run_argv_in) and permission_bridge_configured():
        decision = request_mutate_permission(
            run_argv_in,
            session_id=permission_session_id,
            turn_state=permission_turn_state,
        )
        if decision == "deny":
            return {
                "ok": False,
                "argv": run_argv_in,
                "error": "user denied tool permission (or timed out)",
                "stdout": "",
                "stderr": "",
                "exit_code": None,
                "permission": "deny",
            }
        if decision != "unavailable":
            run_argv_in = ensure_i_confirm(run_argv_in)

    if not is_allowed_argv(run_argv_in, allow_export=allow_export, profile=profile):
        return {
            "ok": False,
            "argv": run_argv_in,
            "error": f"command not on Pi whitelist (or export/confirm gated): {run_argv_in!r}",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

    argv = run_argv_in
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

    run_argv = _argv_for_subprocess(argv, prefix)
    limit = timeout_sec if timeout_sec is not None else _timeout_for_prefix(prefix)
    cmd = [_gamefactory_python(), str(cli), *run_argv]
    work = cwd or _REPO_ROOT
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=limit,
            cwd=str(work),
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "argv": argv,
            "error": f"timeout after {limit}s",
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

    out_stdout = (proc.stdout or "")[-8000:]
    out_stderr = (proc.stderr or "")[-2000:]
    err_tail = None
    if proc.returncode != 0:
        err_tail = (proc.stderr or proc.stdout or f"exit {proc.returncode}")[-500:]
    try:
        from inspect_ops import redact_text

        out_stdout = redact_text(out_stdout)
        out_stderr = redact_text(out_stderr)
        if err_tail is not None:
            err_tail = redact_text(err_tail)
    except Exception:  # noqa: BLE001 — never fail the tool on redact
        pass

    return {
        "ok": proc.returncode == 0,
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout": out_stdout,
        "stderr": out_stderr,
        "error": err_tail,
    }


def run_tool_round(
    text: str,
    *,
    cwd: Path | None = None,
    allow_export: bool = False,
    profile: str = "it",
    permission_session_id: str = "",
    permission_turn_state: PermissionTurnState | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Execute all tools found in ``text``; return (results, text_without_fences)."""
    tools = extract_foundry_tools(text)
    state = permission_turn_state
    if state is None and any(is_mutating_argv(a) for a in tools):
        state = PermissionTurnState()
    results = [
        run_allowed_gamefactory(
            argv,
            cwd=cwd,
            allow_export=allow_export,
            profile=profile,
            permission_session_id=permission_session_id,
            permission_turn_state=state,
        )
        for argv in tools
    ]
    return results, strip_foundry_tools(text)
