"""Headless Godot viewport screenshot capture."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CAPTURE_SCRIPT = _REPO_ROOT / "resources" / "godot-tools" / "capture_screenshot.gd"


def _load_config() -> dict:
    config_path = Path.home() / ".gamefactory" / "config.json"
    if not config_path.is_file():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


from toolchain_paths import resolve_godot


def get_godot_exe() -> str:
    """Resolve Godot executable (shared with godot_cmds)."""
    resolved = resolve_godot(_load_config())
    return resolved or "godot"


def capture_screenshot(
    project_path: Path,
    output_path: Path,
    *,
    wait_frames: int = 8,
    timeout: int = 180,
) -> dict:
    """Boot main scene headless and save viewport PNG."""
    if not _CAPTURE_SCRIPT.is_file():
        raise FileNotFoundError(f"Missing capture script: {_CAPTURE_SCRIPT}")

    project_path = project_path.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    godot = get_godot_exe()
    cmd = [
        godot,
        "--headless",
        "--path",
        str(project_path),
        "-s",
        str(_CAPTURE_SCRIPT.resolve()),
        f"--gf-screenshot-out={output_path}",
        f"--gf-wait-frames={max(1, wait_frames)}",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    errors = [ln for ln in combined.splitlines() if "ERROR:" in ln or "printerr" in ln.lower()]

    if result.returncode != 0 or not output_path.is_file():
        detail = "\n".join(errors or combined.splitlines()[-15:])
        raise RuntimeError(f"Screenshot capture failed:\n{detail}")

    return {
        "ok": True,
        "project_path": str(project_path),
        "screenshot_path": str(output_path),
        "wait_frames": wait_frames,
        "godot": godot,
    }
