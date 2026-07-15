"""Resolve Godot .NET (mono) portable download URLs from GitHub releases."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from ffmpeg_sources import platform_key

_GITHUB_API = "https://api.github.com/repos/godotengine/godot/releases/latest"
_USER_AGENT = "game-ai-foundry-toolchain/1.0"

_ASSET_PATTERNS: dict[str, re.Pattern[str]] = {
    "macos_arm64": re.compile(r"^Godot_v[\d.]+-stable_mono_macos\.universal\.zip$", re.I),
    "macos_x64": re.compile(r"^Godot_v[\d.]+-stable_mono_macos\.universal\.zip$", re.I),
    "win64": re.compile(r"^Godot_v[\d.]+-stable_mono_win64\.zip$", re.I),
    "linux64": re.compile(r"^Godot_v[\d.]+-stable_mono_linux\.x86_64\.zip$", re.I),
}


def _http_get_json(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def godot_mono_asset_name(key: str | None = None) -> str | None:
    """Return asset filename for the latest stable mono build, if found."""
    key = key or platform_key()
    pattern = _ASSET_PATTERNS.get(key)
    if not pattern:
        return None
    release = _http_get_json(_GITHUB_API)
    if not release:
        return None
    for asset in release.get("assets") or []:
        name = str(asset.get("name") or "")
        if pattern.match(name):
            return name
    return None


def godot_download_source(key: str | None = None) -> dict[str, str] | None:
    """Return {url, kind, label, asset} for the platform mono zip, or None."""
    key = key or platform_key()
    pattern = _ASSET_PATTERNS.get(key)
    if not pattern:
        return None
    release = _http_get_json(_GITHUB_API)
    if not release:
        return None
    tag = str(release.get("tag_name") or "latest")
    for asset in release.get("assets") or []:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if not url or not pattern.match(name):
            continue
        return {
            "url": url,
            "kind": "zip",
            "label": f"godot-{tag}-{name}",
            "asset": name,
            "tag": tag,
        }
    return None
