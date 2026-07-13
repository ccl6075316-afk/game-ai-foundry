#!/usr/bin/env python3
"""Create an embedded Python venv for Game AI Foundry release builds."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REQUIREMENTS = _REPO_ROOT / "cli" / "requirements.txt"


def _pip(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def _python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare embedded Python for release packaging")
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "gui" / "runtime" / "python",
        help="Output venv directory (default: gui/runtime/python)",
    )
    parser.add_argument("--with-rembg", action="store_true", help='Also install rembg[cpu]')
    parser.add_argument("--python", default=sys.executable, help="Base Python interpreter")
    args = parser.parse_args()

    output: Path = args.output.resolve()
    if output.exists():
        print(f"Removing existing runtime: {output}")
        shutil.rmtree(output)

    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Creating venv at {output}")
    subprocess.run([args.python, "-m", "venv", str(output)], check=True)

    pip = _pip(output)
    py = _python(output)
    subprocess.run([str(pip), "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(pip), "install", "-r", str(_REQUIREMENTS)], check=True)
    if args.with_rembg:
        subprocess.run([str(pip), "install", "rembg[cpu]"], check=True)

    print(f"Embedded Python ready: {py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
