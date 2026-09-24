"""Discover retained pipeline configuration and local toolchain."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from toolchain_paths import (
    dotnet_root,
    resolve_dotnet,
    resolve_ffmpeg,
    resolve_ffprobe,
    resolve_godot,
    toolchain_bin_dir,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"


def _tool(name: str, path: str | None, *, version_args: tuple[str, ...] = ("--version",)) -> dict[str, Any]:
    if not path:
        return {"name": name, "available": False, "path": None}
    version: str | None = None
    try:
        import subprocess

        proc = subprocess.run(
            [path, *version_args],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or proc.stderr or "").strip().splitlines()
        if out:
            version = out[0][:120]
    except (OSError, subprocess.TimeoutExpired):
        version = None
    return {"name": name, "available": True, "path": path, "version": version}


def _key_status(config: dict[str, Any], *paths: str) -> str:
    node: Any = config
    for part in paths:
        if not isinstance(node, dict):
            return "missing"
        node = node.get(part)
    if node and str(node).strip() and "YOUR_" not in str(node).upper():
        return "set"
    return "missing"


def _provider_key_status(config: dict[str, Any], provider: str | None = None) -> str:
    accounts = config.get("provider_accounts")
    if not isinstance(accounts, dict):
        return "missing"
    candidates = [provider] if provider else list(accounts)
    for provider_id in candidates:
        entry = accounts.get(provider_id)
        if isinstance(entry, dict) and _key_status(entry, "api_key") == "set":
            return "set"
    return "missing"


def discover_pipeline() -> dict[str, Any]:
    return {
        "available": True,
        "reason": "gamefactory CLI (this Python process)",
        "python": sys.executable,
        "repo_root": str(_REPO_ROOT),
    }


def discover_tools(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    return {
        "python": _tool("python", sys.executable, version_args=("-V",)),
        "git": _tool("git", shutil.which("git")),
        "godot": _tool("godot", resolve_godot(config)),
        "dotnet": _tool("dotnet", resolve_dotnet(config)),
        "ffmpeg": _tool("ffmpeg", resolve_ffmpeg(config)),
        "ffprobe": _tool("ffprobe", resolve_ffprobe(config)),
    }


def discover_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    exists = _CONFIG_PATH.is_file()
    loaded = config if config is not None else {}
    if exists and not loaded:
        try:
            loaded = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}

    video_key = _key_status(loaded, "video", "api_key")
    if video_key != "set":
        try:
            from video_route import resolve_video_credentials

            if resolve_video_credentials(loaded).usable:
                video_key = "set"
        except Exception:
            pass

    host_key = _key_status(loaded, "host", "api_key")
    provider_key = _provider_key_status(loaded)
    return {
        "path": str(_CONFIG_PATH),
        "exists": exists,
        "openrouter_key": host_key
        if host_key == "set"
        else _key_status(loaded, "image", "api_key"),
        "host_key": host_key,
        "prompt_key": _key_status(loaded, "prompt", "api_key"),
        "code_key": _key_status(loaded, "code", "api_key"),
        "test_key": _key_status(loaded, "test", "api_key"),
        "seedance_key": video_key,
        "provider_accounts_key": provider_key,
        "godot_engine_path": _key_status(loaded, "godot", "engine_path"),
        "toolchain_bin_dir": str(toolchain_bin_dir(loaded)),
        "toolchain_dotnet_dir": str(dotnet_root(loaded)),
    }


def discover_capabilities(
    config: dict[str, Any] | None = None,
    tools: dict[str, Any] | None = None,
    cfg_status: dict[str, Any] | None = None,
) -> dict[str, bool]:
    tools = tools or discover_tools(config)
    cfg_status = cfg_status or discover_config(config)

    def has_module(name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    image_key = cfg_status["openrouter_key"] == "set" or cfg_status["provider_accounts_key"] == "set"
    prompt_key = cfg_status["host_key"] == "set" or cfg_status["prompt_key"] == "set" or image_key
    code_key = cfg_status["host_key"] == "set" or cfg_status["code_key"] == "set" or image_key
    test_key = cfg_status["host_key"] == "set" or cfg_status["test_key"] == "set" or image_key
    return {
        "pipeline_run": True,
        "image_api": image_key,
        "video_api": cfg_status["seedance_key"] == "set",
        "prompt_api": prompt_key,
        "code_api": code_key,
        "test_api": test_key,
        "ffmpeg": tools["ffmpeg"]["available"],
        "ffprobe": tools["ffprobe"]["available"],
        "godot_assemble": tools["godot"]["available"],
        "dotnet": tools["dotnet"]["available"],
        "toolchain": tools["ffmpeg"]["available"] or tools["godot"]["available"] or tools["dotnet"]["available"],
        "media_validate": has_module("asset_pipeline") and has_module("video_matting"),
        "matting_validate": has_module("matting_validate"),
        "cjk_guard": has_module("prompt_craft"),
        "pipeline_heal": has_module("pipeline_heal"),
    }


def run_doctor(config: dict[str, Any] | None = None) -> dict[str, Any]:
    tools = discover_tools(config)
    cfg_status = discover_config(config)
    return {
        "pipeline": discover_pipeline(),
        "tools": tools,
        "config": cfg_status,
        "capabilities": discover_capabilities(config, tools, cfg_status),
        "notes": [
            "Pipeline execution is available through this CLI process.",
            "API keys are reported by status only and never printed.",
            "FFmpeg, Godot, and .NET readiness are detected from PATH and toolchain config.",
        ],
    }
