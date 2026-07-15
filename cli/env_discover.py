"""Discover local executors and toolchain — nothing is bundled with the repo."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from agent_routing import all_agents
from hermes_pack import HERMES_PACKAGES, resolve_hermes_install_dir
from roles import ALL_ROLES
from toolchain_paths import resolve_dotnet, resolve_ffmpeg, resolve_ffprobe, resolve_godot

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


def _hermes_skills_status(install_dir: Path) -> dict[str, Any]:
    expected = [name for name, meta in HERMES_PACKAGES.items() if meta.get("role")]
    installed: list[str] = []
    missing: list[str] = []
    for pkg in expected:
        skill_md = install_dir / pkg / "SKILL.md"
        if skill_md.is_file() or (install_dir / pkg).exists():
            installed.append(pkg)
        else:
            missing.append(pkg)
    return {
        "install_dir": str(install_dir),
        "installed_count": len(installed),
        "expected_count": len(expected),
        "installed": installed,
        "missing": missing,
        "skills_ready": len(missing) == 0,
    }


def discover_pipeline() -> dict[str, Any]:
    return {
        "available": True,
        "reason": "gamefactory CLI (this Python process)",
        "python": sys.executable,
        "repo_root": str(_REPO_ROOT),
    }


def discover_hermes() -> dict[str, Any]:
    cli = shutil.which("hermes")
    install_dir = resolve_hermes_install_dir()
    skills = _hermes_skills_status(install_dir)
    skills_ok = skills["skills_ready"]
    available = bool(cli) or skills_ok
    hints: list[str] = []
    if not cli:
        hints.append("Hermes CLI not on PATH — install Hermes Agent separately.")
    if not skills_ok:
        hints.append("Run: cd cli && python gamefactory.py hermes install")
    return {
        "available": available,
        "cli": cli,
        "skills": skills,
        "hints": hints,
    }


def discover_codex() -> dict[str, Any]:
    cli = shutil.which("codex")
    git_ok = (_REPO_ROOT / ".git").is_dir()
    hints: list[str] = []
    if not cli:
        hints.append("Codex CLI not on PATH — install OpenAI Codex CLI separately.")
    if not git_ok:
        hints.append("Codex exec expects a git repo (this project qualifies when cloned).")
    return {
        "available": bool(cli),
        "cli": cli,
        "git_repo": git_ok,
        "hints": hints,
    }


def discover_cursor() -> dict[str, Any]:
    cli = shutil.which("cursor")
    in_cursor = any(
        os.environ.get(k)
        for k in (
            "CURSOR_AGENT",
            "CURSOR_TRACE_ID",
            "CURSOR_SESSION_ID",
            "VSCODE_GIT_IPC_HANDLE",  # often set in Cursor/Electron IDE terminal
        )
    )
    hints: list[str] = []
    if not cli and not in_cursor:
        hints.append(
            "No Cursor CLI or IDE session detected — use Cursor chat manually, "
            "or set agents.*.executor to hermes/codex/pipeline."
        )
    return {
        "available": bool(cli) or in_cursor,
        "cli": cli,
        "in_ide_session": in_cursor,
        "hints": hints,
        "note": "Cursor Agent is not a headless package; discovery means CLI or active IDE terminal.",
    }


def discover_executors() -> dict[str, dict[str, Any]]:
    return {
        "pipeline": discover_pipeline(),
        "hermes": discover_hermes(),
        "codex": discover_codex(),
        "cursor": discover_cursor(),
    }


def _godot_path_from_config(config: dict[str, Any]) -> str | None:
    return resolve_godot(config)


def discover_tools(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    godot_path = _godot_path_from_config(config)
    dotnet = resolve_dotnet(config)
    ffmpeg = resolve_ffmpeg(config)
    ffprobe = resolve_ffprobe(config)
    git = shutil.which("git")
    return {
        "python": _tool("python", sys.executable, version_args=("-V",)),
        "git": _tool("git", git),
        "godot": _tool("godot", godot_path, version_args=("--version",)),
        "dotnet": _tool("dotnet", dotnet),
        "ffmpeg": _tool("ffmpeg", ffmpeg),
        "ffprobe": _tool("ffprobe", ffprobe),
    }


def discover_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    exists = _CONFIG_PATH.is_file()
    loaded = config if config is not None else {}
    if exists and not loaded:
        try:
            import json

            loaded = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = {}
    return {
        "path": str(_CONFIG_PATH),
        "exists": exists,
        "openrouter_key": _key_status(loaded, "host", "api_key")
        if _key_status(loaded, "host", "api_key") == "set"
        else _key_status(loaded, "image", "api_key"),
        "host_key": _key_status(loaded, "host", "api_key"),
        "prompt_key": _key_status(loaded, "prompt", "api_key"),
        "code_key": _key_status(loaded, "code", "api_key"),
        "seedance_key": _key_status(loaded, "video", "api_key"),
        "godot_engine_path": _key_status(loaded, "godot", "engine_path"),
    }


def _suggest_executor(role: str, configured: str, executors: dict[str, dict[str, Any]]) -> str:
    if executors.get(configured, {}).get("available"):
        return configured
    if role in ("image-generator", "video-generator", "godot-assembler"):
        return "pipeline"
    if executors.get("codex", {}).get("available") and role == "godot-developer":
        return "codex"
    if executors.get("hermes", {}).get("available"):
        return "hermes"
    if executors.get("cursor", {}).get("available"):
        return "cursor"
    return "pipeline"


def discover_agents(
    config: dict[str, Any] | None = None,
    executors: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = config or {}
    executors = executors or discover_executors()
    agents_cfg = all_agents(config)
    out: dict[str, Any] = {}
    for role in ALL_ROLES:
        resolved = agents_cfg[role]
        configured = resolved["executor"]
        available = bool(executors.get(configured, {}).get("available"))
        suggested = _suggest_executor(role, configured, executors)
        out[role] = {
            **resolved,
            "configured_executor": configured,
            "executor_available": available,
            "suggested_executor": suggested if suggested != configured or not available else configured,
            "action_required": not available,
        }
    return out


def discover_capabilities(
    config: dict[str, Any] | None = None,
    executors: dict[str, dict[str, Any]] | None = None,
    tools: dict[str, Any] | None = None,
    cfg_status: dict[str, Any] | None = None,
) -> dict[str, bool]:
    executors = executors or discover_executors()
    tools = tools or discover_tools(config)
    cfg_status = cfg_status or discover_config(config)
    return {
        "pipeline_run": executors["pipeline"]["available"],
        "image_api": cfg_status["openrouter_key"] == "set",
        "video_api": cfg_status["seedance_key"] == "set",
        "godot_assemble": tools["godot"]["available"],
        "hermes_orchestration": executors["hermes"]["available"],
        "codex_game_dev": executors["codex"]["available"],
        "cursor_sessions": executors["cursor"]["available"],
    }


def run_doctor(config: dict[str, Any] | None = None) -> dict[str, Any]:
    executors = discover_executors()
    tools = discover_tools(config)
    cfg_status = discover_config(config)
    return {
        "executors": executors,
        "tools": tools,
        "config": cfg_status,
        "agents": discover_agents(config, executors),
        "capabilities": discover_capabilities(config, executors, tools, cfg_status),
        "notes": [
            "Hermes, Codex, and Cursor are not bundled — install separately.",
            "Use `python gamefactory.py doctor` before assigning executors in config.",
            "pipeline executor always available (local subprocess runner).",
        ],
    }
