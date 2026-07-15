"""Resolve FFmpeg download URLs with platform fallbacks."""

from __future__ import annotations

import json
import platform
import re
import sys
import urllib.error
import urllib.request
from typing import Any

_GITHUB_API = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
_USER_AGENT = "game-ai-foundry-toolchain/1.0"


def platform_key() -> str:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        if machine in ("arm64", "aarch64"):
            return "macos_arm64"
        return "macos_x64"
    if sys.platform == "win32":
        return "win64"
    return "linux64"


def _http_get_json(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def _head_ok(url: str) -> bool:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 400
    except urllib.error.URLError:
        return False


def _btbn_asset_url(key: str) -> str | None:
    release = _http_get_json(_GITHUB_API)
    if not release:
        return None
    patterns: dict[str, list[str]] = {
        "macos_arm64": [r"macosarm64.*gpl\.zip$", r"macosaarch64.*gpl\.zip$"],
        "macos_x64": [r"macos64.*gpl\.zip$", r"macosx64.*gpl\.zip$"],
        "win64": [r"win64.*gpl\.zip$", r"win64.*gpl\.zip$"],
        "linux64": [r"linux64.*gpl\.tar\.xz$"],
    }
    wanted = patterns.get(key, [])
    for asset in release.get("assets") or []:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if not url:
            continue
        for pattern in wanted:
            if re.search(pattern, name, re.I):
                return url
    return None


def _evermeet_sources() -> list[dict[str, str]]:
    return [
        {"url": "https://evermeet.cx/ffmpeg/getrelease/zip", "kind": "zip", "label": "evermeet-ffmpeg"},
        {"url": "https://evermeet.cx/ffprobe/getrelease/zip", "kind": "zip", "label": "evermeet-ffprobe"},
    ]


def ffmpeg_download_sources(key: str | None = None) -> list[dict[str, str]]:
    """Ordered download sources: each entry has url, kind (zip|tar.xz), label."""
    key = key or platform_key()
    sources: list[dict[str, str]] = []

    btbn = _btbn_asset_url(key)
    if btbn:
        kind = "tar.xz" if btbn.endswith(".tar.xz") else "zip"
        sources.append({"url": btbn, "kind": kind, "label": "BtbN-GitHub"})

    if key.startswith("macos"):
        for item in _evermeet_sources():
            sources.append(item)

    # Legacy pinned names (some mirrors still mirror these)
    legacy_base = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
    legacy_names = {
        "macos_arm64": f"{legacy_base}/ffmpeg-master-latest-macosarm64-gpl.zip",
        "macos_x64": f"{legacy_base}/ffmpeg-master-latest-macos64-gpl.zip",
        "win64": f"{legacy_base}/ffmpeg-master-latest-win64-gpl.zip",
        "linux64": f"{legacy_base}/ffmpeg-master-latest-linux64-gpl.tar.xz",
    }
    legacy = legacy_names.get(key)
    if legacy and _head_ok(legacy):
        kind = "tar.xz" if legacy.endswith(".tar.xz") else "zip"
        sources.append({"url": legacy, "kind": kind, "label": "BtbN-legacy"})

    # Deduplicate by url
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for src in sources:
        if src["url"] in seen:
            continue
        seen.add(src["url"])
        unique.append(src)
    return unique
