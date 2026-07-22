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


def _which_cursor_agent() -> str | None:
    return shutil.which("agent") or shutil.which("cursor-agent")


def _which_codex() -> str | None:
    return shutil.which("codex")


def _run(argv: list[str], *, timeout: float = 45.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "NO_COLOR": "1", "CI": "1"},
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
        code, out, err = _run([bin_path, "--list-models"])
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
        hint = (
            "当前 Cursor 账号对 Agent CLI 无可用模型（`agent --list-models` 为空）。"
            "请确认已 `agent login`、订阅含 Agent，或设置 CURSOR_API_KEY 后再点刷新。"
        )
        if "no models available" in combined.lower():
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
