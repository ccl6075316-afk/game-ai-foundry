"""Resolve OpenAI Codex CLI download URLs (official GitHub release binaries — no npm)."""

from __future__ import annotations

import json
import platform
import re
import sys
import urllib.error
import urllib.request
from typing import Any

from download_mirror import rewrite_url

_GITHUB_API = "https://api.github.com/repos/openai/codex/releases/latest"
_USER_AGENT = "game-ai-foundry-toolchain/1.0"


def platform_key() -> str:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        if machine in ("arm64", "aarch64"):
            return "macos_arm64"
        return "macos_x64"
    if sys.platform == "win32":
        if machine in ("arm64", "aarch64"):
            return "win_arm64"
        return "win64"
    if machine in ("arm64", "aarch64"):
        return "linux_arm64"
    return "linux64"


def _http_get_json(url: str) -> dict[str, Any] | None:
    url = rewrite_url(url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def _asset_patterns(key: str) -> list[tuple[str, str]]:
    """Ordered (regex, kind) preferences. Prefer direct .exe on Windows, else archive."""
    patterns: dict[str, list[tuple[str, str]]] = {
        "win64": [
            (r"^codex-x86_64-pc-windows-msvc\.exe$", "exe"),
            (r"^codex-x86_64-pc-windows-msvc\.exe\.zip$", "zip"),
        ],
        "win_arm64": [
            (r"^codex-aarch64-pc-windows-msvc\.exe$", "exe"),
            (r"^codex-aarch64-pc-windows-msvc\.exe\.zip$", "zip"),
        ],
        "macos_arm64": [
            (r"^codex-aarch64-apple-darwin\.tar\.gz$", "tar.gz"),
        ],
        "macos_x64": [
            (r"^codex-x86_64-apple-darwin\.tar\.gz$", "tar.gz"),
        ],
        "linux64": [
            (r"^codex-x86_64-unknown-linux-musl\.tar\.gz$", "tar.gz"),
        ],
        "linux_arm64": [
            (r"^codex-aarch64-unknown-linux-musl\.tar\.gz$", "tar.gz"),
        ],
    }
    return patterns.get(key, [])


def codex_download_sources(key: str | None = None) -> list[dict[str, str]]:
    """Ordered download sources: each entry has url, kind (exe|zip|tar.gz), label."""
    key = key or platform_key()
    release = _http_get_json(_GITHUB_API)
    if not release:
        return []

    assets = release.get("assets") or []
    tag = str(release.get("tag_name") or release.get("name") or "latest")
    sources: list[dict[str, str]] = []
    for pattern, kind in _asset_patterns(key):
        for asset in assets:
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            if not url or not re.search(pattern, name, re.I):
                continue
            sources.append(
                {
                    "url": rewrite_url(url),
                    "kind": kind,
                    "label": f"openai/codex {tag} {name}",
                    "name": name,
                }
            )
            break
    return sources
