"""Discover models from local Codex / Cursor CLIs (no static fake catalogs)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{0,80}$")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text or "")


def _home_bin_candidates(*names: str) -> list[str]:
    """Paths GUIs often miss when PATH lacks shell profile dirs."""
    home = os.path.expanduser("~")
    roots = [
        os.path.join(home, ".local", "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ]
    out: list[str] = []
    for root in roots:
        for name in names:
            out.append(os.path.join(root, name))
    # Cursor Agent versioned installs
    versions = os.path.join(home, ".local", "share", "cursor-agent", "versions")
    if os.path.isdir(versions):
        try:
            kids = sorted(os.listdir(versions))
        except OSError:
            kids = []
        for kid in kids[-3:]:
            for name in names:
                out.append(os.path.join(versions, kid, name))
    return out


def _which_on_path_or_home(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for candidate in _home_bin_candidates(*names):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _which_cursor_agent() -> str | None:
    return _which_on_path_or_home("agent", "cursor-agent")


def _which_codex() -> str | None:
    return _which_on_path_or_home("codex")


def _run(argv: list[str], *, timeout: float = 45.0) -> tuple[int, str, str]:
    try:
        env = {**os.environ, "NO_COLOR": "1", "CI": "1"}
        # Ensure ~/.local/bin stays visible even if parent stripped PATH.
        local_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        path = env.get("PATH") or ""
        if local_bin and local_bin not in path.split(os.pathsep):
            env["PATH"] = local_bin + os.pathsep + path
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=env,
        )
    except FileNotFoundError:
        return 127, "", "executable not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except OSError as exc:
        return 1, "", str(exc)
    return (
        int(proc.returncode),
        _strip_ansi(proc.stdout or ""),
        _strip_ansi(proc.stderr or ""),
    )


def parse_cursor_list_models_text(text: str) -> list[dict[str, str]]:
    """Parse ``agent --list-models`` human/JSON output into ``[{id,label}]``."""
    raw = _strip_ansi(text or "").strip()
    if not raw:
        return []
    low = raw.lower()
    if "no models available" in low:
        return []

    # JSON array or { models: [...] }
    if raw.startswith("{") or raw.startswith("["):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return _normalize_model_entries(data)
        if isinstance(data, dict):
            for key in ("models", "items", "data"):
                if isinstance(data.get(key), list):
                    return _normalize_model_entries(data[key])

    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("loading"):
            continue
        # bullets / numbered
        m = re.match(r"^(?:[-*•]|\d+[.)])\s+(\S+)", line)
        if m:
            mid = m.group(1).strip().strip(",")
        else:
            # "id — label" or "id  label"
            parts = re.split(r"\s{2,}|\s+—\s+|\s+-\s+", line, maxsplit=1)
            mid = parts[0].strip()
            if " " in mid and not _MODEL_ID_RE.match(mid):
                continue
        mid = mid.strip("`\"'")
        if mid.lower() in {"model", "models", "id", "name", "available"}:
            continue
        if not _MODEL_ID_RE.match(mid):
            continue
        if mid in seen:
            continue
        seen.add(mid)
        label = mid
        if m is None and len(parts) > 1 and parts[1].strip():
            label = parts[1].strip()
        out.append({"id": mid, "label": label})
    return out


def _normalize_model_entries(items: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        mid = ""
        label = ""
        if isinstance(item, str):
            mid = item.strip()
            label = mid
        elif isinstance(item, dict):
            mid = str(
                item.get("id")
                or item.get("slug")
                or item.get("model")
                or item.get("name")
                or ""
            ).strip()
            label = str(item.get("display_name") or item.get("label") or mid).strip() or mid
        if not mid or not _MODEL_ID_RE.match(mid) or mid in seen:
            continue
        seen.add(mid)
        out.append({"id": mid, "label": label})
    return out


def parse_codex_debug_models(text: str) -> list[dict[str, str]]:
    """Parse ``codex debug models`` JSON or text."""
    raw = _strip_ansi(text or "").strip()
    if not raw:
        return []
    if raw.startswith("{") or raw.startswith("["):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return _normalize_model_entries(data)
        if isinstance(data, dict):
            for key in ("models", "items", "catalog", "data"):
                val = data.get(key)
                if isinstance(val, list):
                    return _normalize_model_entries(val)
                if isinstance(val, dict):
                    # map slug -> meta
                    entries = []
                    for k, v in val.items():
                        if isinstance(v, dict):
                            entries.append({"id": k, **v})
                        else:
                            entries.append({"id": str(k)})
                    return _normalize_model_entries(entries)
            # flat dict of slug -> something
            if all(isinstance(k, str) for k in data.keys()) and not any(
                k in data for k in ("error", "ok", "message")
            ):
                maybe = _normalize_model_entries(
                    [{"id": k, **(v if isinstance(v, dict) else {})} for k, v in data.items()]
                )
                if maybe:
                    return maybe
    return parse_cursor_list_models_text(raw)


def _cursor_auth_state(bin_path: str) -> str:
    """Return ``logged_in`` | ``logged_out`` | ``unknown`` from ``agent status``."""
    code, out, err = _run([bin_path, "status"], timeout=30.0)
    text = f"{out}\n{err}".lower()
    # Check negatives first — "not logged in" contains "logged in".
    if any(
        s in text
        for s in (
            "not logged in",
            "logged out",
            "please log in",
            "login required",
            "unauthenticated",
        )
    ):
        return "logged_out"
    if any(
        s in text
        for s in (
            "logged in as",
            "logged in",
            "login successful",
            "authenticated as",
            "signed in",
        )
    ):
        return "logged_in"
    if code != 0 and not (out or err).strip():
        return "unknown"
    return "unknown"


def _cursor_empty_models_hint(*, auth_state: str, list_text: str) -> str:
    """Hints distinguish not-logged-in vs logged-in-but-empty-catalog."""
    low = (list_text or "").lower()
    explicit_unauth = any(
        s in low
        for s in (
            "not logged in",
            "unauthenticated",
            "please log in",
            "login required",
            "unauthorized",
        )
    )
    if auth_state == "logged_out" or explicit_unauth:
        return (
            "Cursor Agent 未登录（或 GUI 读不到登录态）。"
            "终端执行 `agent login` 后完全退出并重启 Foundry，再点刷新；"
            "无头环境可设 CURSOR_API_KEY。"
        )
    if auth_state == "logged_in":
        return (
            "CLI 显示已登录，但 `agent --list-models` 仍为空"
            "（常见是会话未完全生效，不一定是订阅权限）。"
            "请在终端再跑一次 `agent login`，确认 `agent --list-models` 有输出后，"
            "重启 Foundry 再刷新；也可改用 CURSOR_API_KEY。"
            "若重登后仍长期为空，再查订阅/团队是否含 Agent。"
        )
    return (
        "未能拿到 Cursor 模型列表。"
        "请终端核对：`agent status` 与 `agent --list-models`；"
        "未登录则 `agent login`；已登录仍空则重登或设 CURSOR_API_KEY，"
        "然后重启 Foundry 再刷新（GUI 需能找到 ~/.local/bin/agent）。"
    )


def list_executor_models(executor_id: str) -> dict[str, Any]:
    """Return ``{ok, executor, models, hint, error, source}``."""
    eid = str(executor_id or "").strip().lower()
    if eid not in {"cursor", "codex"}:
        return {
            "ok": False,
            "executor": eid,
            "models": [],
            "hint": None,
            "error": f"unsupported executor: {eid}",
            "source": None,
        }

    if eid == "cursor":
        bin_path = _which_cursor_agent()
        if not bin_path:
            return {
                "ok": False,
                "executor": eid,
                "models": [],
                "hint": "未找到 Cursor Agent CLI（agent / cursor-agent）。请到环境面板安装并登录。",
                "error": "cli_not_found",
                "source": None,
            }
        # Network + auth handshake can be slow right after login.
        code, out, err = _run([bin_path, "--list-models"], timeout=90.0)
        combined = f"{out}\n{err}".strip()
        models = parse_cursor_list_models_text(out) or parse_cursor_list_models_text(combined)
        if models:
            return {
                "ok": True,
                "executor": eid,
                "models": models,
                "hint": None,
                "error": None,
                "source": "agent --list-models",
            }
        auth_state = _cursor_auth_state(bin_path)
        hint = _cursor_empty_models_hint(auth_state=auth_state, list_text=combined)
        low = combined.lower()
        if "no models available" in low or code == 0:
            return {
                "ok": True,
                "executor": eid,
                "models": [],
                "hint": hint,
                "error": None,
                "source": "agent --list-models",
            }
        return {
            "ok": False,
            "executor": eid,
            "models": [],
            "hint": hint,
            "error": err or out or f"exit {code}",
            "source": "agent --list-models",
        }

    # codex
    bin_path = _which_codex()
    if not bin_path:
        return {
            "ok": False,
            "executor": eid,
            "models": [],
            "hint": "未找到 codex CLI。请到环境面板安装并登录。",
            "error": "cli_not_found",
            "source": None,
        }

    # Prefer machine-readable debug catalog; --json not on all Codex versions.
    attempts = (
        [bin_path, "debug", "models"],
        [bin_path, "debug", "models", "--bundled"],
    )
    last_err = ""
    for argv in attempts:
        code, out, err = _run(argv)
        models = parse_codex_debug_models(out) or parse_codex_debug_models(f"{out}\n{err}")
        if models:
            return {
                "ok": True,
                "executor": eid,
                "models": models,
                "hint": None,
                "error": None,
                "source": " ".join(argv[1:]),
            }
        last_err = err or out or f"exit {code}"
        # Broken npm shim (ENOENT spawn) — stop early with actionable hint
        if "ENOENT" in last_err or "spawn" in last_err.lower():
            return {
                "ok": False,
                "executor": eid,
                "models": [],
                "hint": (
                    "本机 `codex` 包装损坏（缺原生二进制 ENOENT）。"
                    "请卸载坏掉的 npm 包后重装：`npm uninstall -g @openai/codex`，"
                    "再用 `brew install --cask codex` 或官网安装，然后执行 `codex debug models`。"
                ),
                "error": last_err,
                "source": " ".join(argv[1:]),
            }

    return {
        "ok": False,
        "executor": eid,
        "models": [],
        "hint": "无法从 Codex 读取模型目录。请确认 `codex` 可执行且已登录（`codex debug models`）。",
        "error": last_err or "empty_catalog",
        "source": "codex debug models",
    }
