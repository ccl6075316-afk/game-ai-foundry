"""Install .NET SDK into ~/.gamefactory/toolchain/dotnet via official scripts."""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable

ProgressCb = Callable[[str], None] | None

_INSTALL_SH = "https://dot.net/v1/dotnet-install.sh"
_INSTALL_PS1 = "https://dot.net/v1/dotnet-install.ps1"
_DEFAULT_CHANNEL = "8.0"


def _emit(progress: ProgressCb, message: str) -> None:
    if progress:
        progress(message)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "game-ai-foundry-toolchain/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def install_dotnet_sdk(install_dir: Path, progress: ProgressCb = None) -> Path:
    """Install .NET SDK channel into install_dir. Returns dotnet executable path."""
    install_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        script = install_dir / "dotnet-install.ps1"
        _emit(progress, "下载 dotnet-install.ps1…")
        _download(_INSTALL_PS1, script)
        _emit(progress, f"安装 .NET SDK {_DEFAULT_CHANNEL}…")
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-Channel",
                _DEFAULT_CHANNEL,
                "-InstallDir",
                str(install_dir),
                "-Quality",
                "ga",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    else:
        script = install_dir / "dotnet-install.sh"
        _emit(progress, "下载 dotnet-install.sh…")
        _download(_INSTALL_SH, script)
        script.chmod(0o755)
        _emit(progress, f"安装 .NET SDK {_DEFAULT_CHANNEL}…")
        proc = subprocess.run(
            [
                "bash",
                str(script),
                "--channel",
                _DEFAULT_CHANNEL,
                "--install-dir",
                str(install_dir),
                "--quality",
                "ga",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-800:]
        raise RuntimeError(f".NET SDK 安装失败: {tail}")

    dotnet = install_dir / ("dotnet.exe" if sys.platform == "win32" else "dotnet")
    if not dotnet.is_file():
        raise RuntimeError(f".NET 安装完成但未找到 {dotnet}")
    if sys.platform != "win32":
        dotnet.chmod(0o755)
    return dotnet
