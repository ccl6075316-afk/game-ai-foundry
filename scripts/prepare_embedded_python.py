#!/usr/bin/env python3
"""Create an embedded Python venv for Game AI Foundry release builds."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REQUIREMENTS = _REPO_ROOT / "cli" / "requirements.txt"
_PIP_INSTALL = ["--retries", "10", "--timeout", "300"]
_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"


def _python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _pip_index_args(index_url: str | None) -> list[str]:
    url = (index_url or os.environ.get("PIP_INDEX_URL") or _DEFAULT_INDEX).strip()
    if not url:
        return []
    return ["-i", url]


def _run_pip(
    py: Path,
    args: list[str],
    *,
    index_url: str | None,
    attempts: int = 5,
) -> None:
    base = [str(py), "-m", "pip"]
    if args and args[0] == "install":
        cmd = [*base, "install", *_pip_index_args(index_url), *args[1:]]
    else:
        cmd = [*base, *args]
    last_err: subprocess.CalledProcessError | None = None
    for attempt in range(1, attempts + 1):
        try:
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError as exc:
            last_err = exc
            if attempt >= attempts:
                break
            wait = min(30, 5 * attempt)
            print(f"pip failed (attempt {attempt}/{attempts}), retry in {wait}s …", file=sys.stderr)
            time.sleep(wait)
    assert last_err is not None
    raise last_err


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare embedded Python for release packaging")
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "gui" / "runtime" / "python",
        help="Output venv directory (default: gui/runtime/python)",
    )
    parser.add_argument("--with-rembg", action="store_true", help='Also install rembg[cpu]')
    parser.add_argument(
        "--index-url",
        default=None,
        help=f"PyPI mirror (default: env PIP_INDEX_URL or {_DEFAULT_INDEX})",
    )
    parser.add_argument("--python", default=sys.executable, help="Base Python interpreter")
    args = parser.parse_args()

    output: Path = args.output.resolve()
    if output.exists():
        print(f"Removing existing runtime: {output}")
        shutil.rmtree(output)

    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Creating venv at {output}")
    subprocess.run([args.python, "-m", "venv", str(output)], check=True)

    py = _python(output)
    index = args.index_url
    _run_pip(py, ["install", "--upgrade", "pip", *_PIP_INSTALL], index_url=index)
    _run_pip(
        py,
        ["install", "-r", str(_REQUIREMENTS), *_PIP_INSTALL],
        index_url=index,
    )
    if args.with_rembg:
        _run_pip(py, ["install", "rembg[cpu]", *_PIP_INSTALL], index_url=index)

    print(f"Embedded Python ready: {py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
