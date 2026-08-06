"""Optional GitHub download mirror (China-friendly reverse proxies).

Config (default off):
  toolchain.download_mirror: bool
  toolchain.download_mirror_prefix: str  # default https://ghproxy.net/

Env override (optional):
  GAMEFACTORY_DOWNLOAD_MIRROR=1|0
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"
DEFAULT_PREFIX = "https://ghproxy.net/"

_MIRRORABLE_HOSTS = frozenset(
    {
        "github.com",
        "api.github.com",
        "objects.githubusercontent.com",
        "raw.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "codeload.github.com",
        "gist.githubusercontent.com",
    }
)


def _load_config() -> dict[str, Any]:
    if not _CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _normalize_prefix(prefix: str) -> str:
    p = (prefix or "").strip() or DEFAULT_PREFIX
    if not p.endswith("/"):
        p += "/"
    return p


def mirror_prefix(config: Mapping[str, Any] | None = None) -> str:
    cfg = config if config is not None else _load_config()
    tc = cfg.get("toolchain") if isinstance(cfg.get("toolchain"), dict) else {}
    return _normalize_prefix(str(tc.get("download_mirror_prefix") or DEFAULT_PREFIX))


def mirror_enabled(config: Mapping[str, Any] | None = None) -> bool:
    env = os.environ.get("GAMEFACTORY_DOWNLOAD_MIRROR", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    cfg = config if config is not None else _load_config()
    tc = cfg.get("toolchain") if isinstance(cfg.get("toolchain"), dict) else {}
    return bool(tc.get("download_mirror"))


def _host_mirrorable(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower()
    if h in _MIRRORABLE_HOSTS:
        return True
    return h.endswith(".githubusercontent.com")


def rewrite_url(
    url: str,
    *,
    enabled: bool | None = None,
    config: Mapping[str, Any] | None = None,
    prefix: str | None = None,
) -> str:
    """Prefix GitHub-family URLs when mirror is on. Idempotent."""
    if not url or not isinstance(url, str):
        return url
    raw = url.strip()
    if not raw.startswith(("http://", "https://")):
        return url

    on = mirror_enabled(config) if enabled is None else bool(enabled)
    if not on:
        return url

    pref = _normalize_prefix(prefix) if prefix is not None else mirror_prefix(config)
    known_prefixes = (
        pref,
        "https://ghproxy.net/",
        "https://ghproxy.com/",
        "https://gh-proxy.com/",
        "https://mirror.ghproxy.com/",
    )
    if any(raw.startswith(p) for p in known_prefixes):
        return raw

    host = urlparse(raw).hostname
    if not _host_mirrorable(host):
        return url
    return f"{pref}{raw}"
