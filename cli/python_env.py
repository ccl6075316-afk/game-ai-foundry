"""Resolve and bootstrap a repo-local Python for the gamefactory CLI.

Avoid Windows Store ``python.exe`` stubs and prefer ``.venv`` so external agents
do not depend on GUI/Hermes PATH injection.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VENV_DIR = _REPO_ROOT / ".venv"
_REQUIREMENTS = _REPO_ROOT / "cli" / "requirements.txt"


def repo_root() -> Path:
    return _REPO_ROOT


def venv_dir() -> Path:
    return _VENV_DIR


def venv_python() -> Path:
    if os.name == "nt":
        return _VENV_DIR / "Scripts" / "python.exe"
    return _VENV_DIR / "bin" / "python"


def is_windows_store_stub(python_path: Path | str | None) -> bool:
    text = str(python_path or "").replace("/", "\\").lower()
    return "windowsapps\\python" in text or "windowsapps\\py.exe" in text


def _probe_imports(python_exe: Path) -> dict[str, Any]:
    code = (
        "import importlib.util, json, sys;"
        "mods=['click','requests','cv2','numpy'];"
        "print(json.dumps({"
        "'version': sys.version.split()[0],"
        "'modules': {m: importlib.util.find_spec(m) is not None for m in mods}"
        "}))"
    )
    try:
        proc = subprocess.run(
            [str(python_exe), "-c", code],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "modules": {}}
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": (proc.stderr or proc.stdout or "probe failed").strip()[:300],
            "modules": {},
        }
    try:
        import json

        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"ok": False, "error": "invalid probe output", "modules": {}}
    modules = payload.get("modules") if isinstance(payload.get("modules"), dict) else {}
    missing = [name for name, present in modules.items() if not present]
    return {
        "ok": not missing,
        "version": payload.get("version"),
        "modules": modules,
        "missing": missing,
    }


def candidate_base_pythons() -> list[Path]:
    """Ordered interpreters that may create/run the repo venv."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path | str | None) -> None:
        if not path:
            return
        p = Path(path)
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            return
        if is_windows_store_stub(p):
            return
        if not p.exists():
            return
        seen.add(key)
        found.append(p)

    add(os.environ.get("GAMEFACTORY_PYTHON"))
    add(venv_python())

    # Explicit common installs before PATH (PATH often hits Store stubs first).
    local = Path.home() / "AppData" / "Local"
    add(local / "Programs" / "Python" / "Python312" / "python.exe")
    add(local / "Programs" / "Python" / "Python311" / "python.exe")
    add(local / "Python" / "bin" / "python.exe")
    add(local / "hermes" / "hermes-agent" / "venv" / "Scripts" / "python.exe")

    which = shutil.which("python")
    if which and not is_windows_store_stub(which):
        add(which)

    # py launcher: prefer 3.12/3.11 without Store fallback.
    py = shutil.which("py")
    if py and not is_windows_store_stub(py):
        for spec in ("-3.12", "-3.11", "-3"):
            try:
                proc = subprocess.run(
                    [py, spec, "-c", "import sys; print(sys.executable)"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if proc.returncode == 0:
                line = (proc.stdout or "").strip().splitlines()
                if line:
                    add(line[-1].strip())

    add(sys.executable)
    return found


def diagnose_python_env() -> dict[str, Any]:
    current = Path(sys.executable)
    probe = _probe_imports(current)
    vpy = venv_python()
    venv_probe = _probe_imports(vpy) if vpy.exists() else None
    usable = bool(probe.get("ok")) and not is_windows_store_stub(current)
    notes: list[str] = []
    if is_windows_store_stub(current):
        notes.append(
            "Current python is a Windows Store stub; use .\\gamefactory.cmd or "
            "`setup ensure-python` to create repo .venv."
        )
    if not probe.get("ok"):
        notes.append(
            "CLI dependencies missing (need click/requests/opencv/numpy). "
            "Run `setup ensure-python` or install cli/requirements.txt into .venv."
        )
    if vpy.exists() and venv_probe and venv_probe.get("ok") and current.resolve() != vpy.resolve():
        notes.append(f"Repo venv is ready at {vpy}; prefer launcher over bare `python`.")

    return {
        "current_python": str(current),
        "current_is_store_stub": is_windows_store_stub(current),
        "current_probe": probe,
        "venv_python": str(vpy),
        "venv_exists": vpy.exists(),
        "venv_probe": venv_probe,
        "usable_for_cli": usable,
        "candidates": [str(p) for p in candidate_base_pythons()],
        "notes": notes,
        "launcher": {
            "windows_cmd": str(_REPO_ROOT / "gamefactory.cmd"),
            "windows_ps1": str(_REPO_ROOT / "gamefactory.ps1"),
            "unix_sh": str(_REPO_ROOT / "gamefactory"),
        },
    }


def ensure_python_env(*, recreate: bool = False) -> dict[str, Any]:
    """Create ``.venv`` if needed and install ``cli/requirements.txt``."""
    report: dict[str, Any] = {
        "ok": False,
        "venv_dir": str(_VENV_DIR),
        "venv_python": str(venv_python()),
        "actions": [],
        "errors": [],
    }
    base_candidates = [p for p in candidate_base_pythons() if p.resolve() != venv_python().resolve() or not venv_python().exists()]
    # Prefer non-venv bases for creation.
    creators = [
        p
        for p in candidate_base_pythons()
        if ".venv" not in str(p).replace("\\", "/").lower()
        and "hermes-agent\\venv" not in str(p).replace("/", "\\").lower()
    ]
    if not creators:
        # Last resort: hermes venv can still `python -m venv`.
        creators = candidate_base_pythons()
    if not creators:
        report["errors"].append(
            "No usable base Python found (Windows Store stub ignored). "
            "Install Python 3.11+ from python.org and retry."
        )
        return report

    base = creators[0]
    report["base_python"] = str(base)
    report["candidates"] = [str(p) for p in creators]

    vpy = venv_python()
    if recreate and _VENV_DIR.exists():
        shutil.rmtree(_VENV_DIR)
        report["actions"].append("removed_existing_venv")

    if not vpy.exists():
        try:
            # Use stdlib venv via the chosen base interpreter.
            subprocess.run(
                [str(base), "-m", "venv", str(_VENV_DIR)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            report["actions"].append("created_venv")
        except (OSError, subprocess.CalledProcessError) as exc:
            # Fallback: venv module in-process if we are already a real interpreter.
            try:
                venv.EnvBuilder(with_pip=True).create(_VENV_DIR)
                report["actions"].append("created_venv_inprocess")
            except Exception as exc2:  # noqa: BLE001 - surface both errors
                report["errors"].append(f"venv create failed: {exc}; fallback: {exc2}")
                return report

    if not vpy.exists():
        report["errors"].append(f"venv python missing after create: {vpy}")
        return report

    if not _REQUIREMENTS.is_file():
        report["errors"].append(f"requirements missing: {_REQUIREMENTS}")
        return report

    try:
        upgrade = subprocess.run(
            [str(vpy), "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        report["actions"].append(
            {
                "pip_upgrade_exit": upgrade.returncode,
                "stderr_tail": (upgrade.stderr or "")[-400:],
            }
        )
        install = subprocess.run(
            [str(vpy), "-m", "pip", "install", "-r", str(_REQUIREMENTS)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        report["actions"].append(
            {
                "pip_install_exit": install.returncode,
                "stderr_tail": (install.stderr or "")[-600:],
            }
        )
        if install.returncode != 0:
            report["errors"].append("pip install requirements failed")
            return report
    except (OSError, subprocess.TimeoutExpired) as exc:
        report["errors"].append(str(exc))
        return report

    probe = _probe_imports(vpy)
    report["probe"] = probe
    report["ok"] = bool(probe.get("ok"))
    if not report["ok"]:
        report["errors"].append(f"venv still missing modules: {probe.get('missing')}")
    return report
