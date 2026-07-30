#!/usr/bin/env python3
"""Prepare a *relocatable* embedded Python for Game AI Foundry release builds.

Release installs must run on clean PCs with no system Python. A normal
``python -m venv`` is NOT relocatable on Windows (``pyvenv.cfg`` ``home=``
points at the build machine). This script copies the base interpreter prefix
(standalone CPython / uv python) into ``gui/runtime/python``, then installs
requirements into that copy.
"""

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

_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "Doc",
    "docs",
    "test",
    "tests",
    "idle_test",
)


def _base_prefix(python_exe: str) -> Path:
    raw = subprocess.check_output(
        [python_exe, "-c", "import sys; print(sys.base_prefix)"],
        text=True,
        encoding="utf-8",
        errors="replace",
    ).strip()
    prefix = Path(raw).resolve()
    if not prefix.is_dir():
        raise RuntimeError(f"base_prefix is not a directory: {prefix}")
    return prefix


def _python_in_prefix(prefix: Path) -> Path:
    if sys.platform == "win32":
        for cand in (prefix / "python.exe", prefix / "Scripts" / "python.exe"):
            if cand.is_file():
                return cand
    else:
        for cand in (
            prefix / "bin" / "python3",
            prefix / "bin" / "python",
        ):
            if cand.is_file():
                return cand
    raise RuntimeError(f"No python executable found under {prefix}")


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


def _ensure_pip(py: Path) -> None:
    try:
        subprocess.run([str(py), "-m", "pip", "--version"], check=True, capture_output=True)
        return
    except (subprocess.CalledProcessError, OSError):
        pass
    subprocess.run([str(py), "-m", "ensurepip", "--upgrade"], check=True)


def _assert_relocatable(py: Path, prefix: Path) -> None:
    """Fail the build if the interpreter still depends on an external home."""
    cfg = prefix / "pyvenv.cfg"
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.lower().startswith("home"):
                home = line.split("=", 1)[-1].strip().strip('"')
                home_path = Path(home)
                if not home_path.is_absolute():
                    continue
                try:
                    home_resolved = home_path.resolve()
                except OSError:
                    home_resolved = home_path
                if prefix.resolve() not in home_resolved.parents and home_resolved != prefix.resolve():
                    # Allow home pointing inside the copied prefix.
                    if not str(home_resolved).startswith(str(prefix.resolve())):
                        raise RuntimeError(
                            "Embedded Python still looks like a non-relocatable venv "
                            f"(pyvenv.cfg home={home!r}). Refusing to ship."
                        )
    # Smoke: must run without inheriting a build-machine-only layout.
    subprocess.run(
        [str(py), "-c", "import sys; print(sys.executable); print(sys.prefix)"],
        check=True,
        cwd=str(prefix),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare relocatable embedded Python for release packaging"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "gui" / "runtime" / "python",
        help="Output directory (default: gui/runtime/python)",
    )
    parser.add_argument("--with-rembg", action="store_true", help="Also install rembg[cpu]")
    parser.add_argument(
        "--index-url",
        default=None,
        help=f"PyPI mirror (default: env PIP_INDEX_URL or {_DEFAULT_INDEX})",
    )
    parser.add_argument("--python", default=sys.executable, help="Base Python interpreter")
    args = parser.parse_args()

    output: Path = args.output.resolve()
    base = _base_prefix(args.python)
    if base == output:
        raise RuntimeError(f"--python base_prefix is the same as --output ({output})")

    if output.exists():
        print(f"Removing existing runtime: {output}")
        shutil.rmtree(output)

    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Copying standalone Python from {base} → {output}")
    shutil.copytree(base, output, symlinks=False, ignore=_IGNORE)

    # Drop any venv redirector metadata from accidental nested layouts.
    cfg = output / "pyvenv.cfg"
    if cfg.is_file():
        cfg.unlink()

    # uv / distro markers block pip into the copied tree — this copy is ours to modify.
    for marker in output.rglob("EXTERNALLY-MANAGED"):
        if marker.is_file():
            marker.unlink()
            print(f"Removed {marker.relative_to(output)} so pip can install into the embed copy")

    py = _python_in_prefix(output)
    _ensure_pip(py)
    index = args.index_url
    _run_pip(py, ["install", "--upgrade", "pip", *_PIP_INSTALL], index_url=index)
    _run_pip(
        py,
        ["install", "-r", str(_REQUIREMENTS), *_PIP_INSTALL],
        index_url=index,
    )
    if args.with_rembg:
        _run_pip(py, ["install", "rembg[cpu]", *_PIP_INSTALL], index_url=index)

    _assert_relocatable(py, output)
    print(f"Embedded Python ready (relocatable): {py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
