"""Allowlisted config patch helpers for project-manager remediation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

# Dotted keys Hermes / safe CLI may set without user explicitly asking.
# Keep narrow — no API keys, no arbitrary nested writes.
ALLOWED_SET_KEYS: frozenset[str] = frozenset(
    {
        "image.constraints.size_multiple",
        "image.model",
        "image.proxy",
        "proxy",
        "video.proxy",
    }
)


def config_path() -> Path:
    from gamefactory import CONFIG_PATH

    return CONFIG_PATH


def _parse_value(raw: str) -> Any:
    text = (raw or "").strip()
    if text.lower() in ("null", "none", ""):
        return None
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    try:
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
    except ValueError:
        pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def set_dotted(config: dict[str, Any], dotted: str, value: Any) -> dict[str, Any]:
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        raise ValueError("empty key")
    cur: dict[str, Any] = config
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value
    return config


def get_dotted(config: dict[str, Any], dotted: str) -> Any:
    cur: Any = config
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def apply_config_set(key: str, value_raw: str, *, path: Path | None = None) -> dict[str, Any]:
    key = (key or "").strip()
    if key not in ALLOWED_SET_KEYS:
        raise ValueError(
            f"key not allowlisted: {key}. Allowed: {', '.join(sorted(ALLOWED_SET_KEYS))}"
        )
    cfg_path = path or config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if cfg_path.exists():
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config root must be an object")
    value = _parse_value(value_raw)
    before = get_dotted(data, key)
    set_dotted(data, key, value)
    cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "path": str(cfg_path),
        "key": key,
        "before": before,
        "after": value,
    }


@click.group("config")
def config_group() -> None:
    """Read/patch allowlisted keys in ~/.gamefactory/config.json."""


@config_group.command("set")
@click.option("--key", required=True, help="Dotted key (allowlisted only).")
@click.option("--value", required=True, help="Value (JSON or plain string/int).")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON result.")
def config_set_cmd(key: str, value: str, as_json: bool) -> None:
    """Set an allowlisted config key (for PM / pipeline remediation)."""
    try:
        result = apply_config_set(key, value)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"Set {result['key']}: {result['before']!r} → {result['after']!r}")
        click.echo(f"Wrote {result['path']}")


@config_group.command("get")
@click.option("--key", required=True, help="Dotted key.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON result.")
def config_get_cmd(key: str, as_json: bool) -> None:
    """Get a config value (any key; for diagnose)."""
    from gamefactory import load_config

    cfg = load_config()
    val = get_dotted(cfg, key)
    if as_json:
        click.echo(json.dumps({"key": key, "value": val}, ensure_ascii=False, indent=2))
    else:
        click.echo("null" if val is None else json.dumps(val, ensure_ascii=False))
