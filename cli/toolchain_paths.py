"""Resolve bundled toolchain binaries under ~/.gamefactory/toolchain."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

TOOLCHAIN_ROOT = Path.home() / ".gamefactory" / "toolchain"
BIN_DIR = TOOLCHAIN_ROOT / "bin"
GODOT_DIR = TOOLCHAIN_ROOT / "godot"
DOTNET_DIR = TOOLCHAIN_ROOT / "dotnet"

_WIN_EXE = ".exe" if sys.platform == "win32" else ""


def toolchain_bin_dir(config: dict[str, Any] | None = None) -> Path:
    config = config or {}
    tc = config.get("toolchain") if isinstance(config.get("toolchain"), dict) else {}
    raw = tc.get("bin_dir") if isinstance(tc, dict) else None
    if raw:
        return Path(os.path.expanduser(str(raw)))
    return BIN_DIR


def resolve_binary(name: str, config: dict[str, Any] | None = None) -> str | None:
    """Prefer ~/.gamefactory/toolchain/bin, then PATH."""
    bin_dir = toolchain_bin_dir(config)
    for candidate in (bin_dir / f"{name}{_WIN_EXE}", bin_dir / name):
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def resolve_ffmpeg(config: dict[str, Any] | None = None) -> str | None:
    return resolve_binary("ffmpeg", config)


def resolve_ffprobe(config: dict[str, Any] | None = None) -> str | None:
    return resolve_binary("ffprobe", config)


def _find_godot_binary(root: Path) -> Path | None:
    if sys.platform == "win32":
        console: Path | None = None
        fallback: Path | None = None
        for path in root.rglob("*.exe"):
            name = path.name.lower()
            if name.endswith("_console.exe") and "godot" in name:
                return path
            if name.startswith("godot") and name.endswith(".exe"):
                if "_console" in name:
                    console = path
                elif fallback is None:
                    fallback = path
        return console or fallback

    preferred: Path | None = None
    fallback: Path | None = None
    for path in root.rglob("Godot"):
        if not path.is_file():
            continue
        parent = path.parent.name.lower()
        if parent == "macos":
            preferred = path
            break
        if fallback is None:
            fallback = path
    found = preferred or fallback
    if found and sys.platform != "win32":
        try:
            found.chmod(found.stat().st_mode | 0o111)
        except OSError:
            pass
    return found if found and (found.is_file()) else None


def resolve_godot(config: dict[str, Any] | None = None) -> str | None:
    """Config engine_path, then toolchain dir, then PATH."""
    config = config or {}
    godot_cfg = config.get("godot") if isinstance(config.get("godot"), dict) else {}
    configured = godot_cfg.get("engine_path")
    if configured and Path(configured).exists():
        return str(configured)
    if GODOT_DIR.is_dir():
        found = _find_godot_binary(GODOT_DIR)
        if found:
            return str(found)
    return shutil.which("godot")


def dotnet_root(config: dict[str, Any] | None = None) -> Path:
    config = config or {}
    tc = config.get("toolchain") if isinstance(config.get("toolchain"), dict) else {}
    raw = tc.get("dotnet_dir") if isinstance(tc, dict) else None
    if raw:
        return Path(os.path.expanduser(str(raw)))
    return DOTNET_DIR


def resolve_dotnet(config: dict[str, Any] | None = None) -> str | None:
    """Prefer toolchain dotnet, then PATH."""
    root = dotnet_root(config)
    for name in ("dotnet.exe", "dotnet"):
        candidate = root / name
        if candidate.is_file():
            return str(candidate)
    return shutil.which("dotnet")


def toolchain_env(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Copy of os.environ with toolchain dotnet/bin prepended to PATH for Godot child processes."""
    env = os.environ.copy()
    prepend: list[str] = []
    dotnet = resolve_dotnet(config)
    if dotnet:
        prepend.append(str(Path(dotnet).resolve().parent))
    root = dotnet_root(config)
    if root.is_dir():
        env.setdefault("DOTNET_ROOT", str(root.resolve()))
    bin_dir = toolchain_bin_dir(config)
    if bin_dir.is_dir():
        prepend.append(str(bin_dir.resolve()))
    if prepend:
        env["PATH"] = os.pathsep.join(prepend) + os.pathsep + env.get("PATH", "")
    return env
