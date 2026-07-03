"""Resolve bundled toolchain binaries under ~/.gamefactory/toolchain."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

TOOLCHAIN_ROOT = Path.home() / ".gamefactory" / "toolchain"
BIN_DIR = TOOLCHAIN_ROOT / "bin"

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
