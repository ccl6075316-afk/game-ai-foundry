"""Run playtest plan JSON via headless Godot."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLAYTEST_SCRIPT = _REPO_ROOT / "resources" / "godot-tools" / "playtest_runner.gd"


def _get_godot_exe() -> str:
    from godot_screenshot import get_godot_exe

    return get_godot_exe()


def run_playtest_plan(
    project_path: Path,
    plan_path: Path,
    screenshot_dir: Path,
    *,
    manifest_path: Path | None = None,
    timeout: int = 300,
) -> dict:
    """Execute playtest steps; returns manifest with screenshot paths."""
    if not _PLAYTEST_SCRIPT.is_file():
        raise FileNotFoundError(f"Missing playtest script: {_PLAYTEST_SCRIPT}")

    project_path = project_path.resolve()
    plan_path = plan_path.resolve()
    screenshot_dir = screenshot_dir.resolve()
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    manifest_out = manifest_path or (screenshot_dir / "manifest.json")
    manifest_out = manifest_out.resolve()

    godot = _get_godot_exe()
    from godot_screenshot import _load_config
    from toolchain_paths import toolchain_env

    env = toolchain_env(_load_config())
    cmd = [
        godot,
        "--headless",
        "--path",
        str(project_path),
        "-s",
        str(_PLAYTEST_SCRIPT.resolve()),
        "--",
        f"--gf-playtest-plan={plan_path}",
        f"--gf-screenshot-dir={screenshot_dir}",
        f"--gf-manifest-out={manifest_out}",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    combined = (result.stdout or "") + (result.stderr or "")

    manifest: dict | None = None
    if manifest_out.is_file():
        try:
            manifest = json.loads(manifest_out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = None

    if manifest is None:
        for line in combined.splitlines():
            if line.startswith("playtest_manifest:"):
                manifest = json.loads(line.split(":", 1)[1].strip())
                break

    if result.returncode == 2:
        raise RuntimeError(
            "Playtest failed: InputMap actions missing — godot-developer must bind brief.controls.\n"
            + combined[-1500:]
        )
    if result.returncode == 3:
        raise RuntimeError(
            "Playtest failed: hard assertion failed (assert_node / assert_property / assert_action).\n"
            + combined[-1500:]
        )
    if result.returncode != 0 or not manifest:
        raise RuntimeError(f"Playtest runner failed:\n{combined[-2000:]}")

    manifest["screenshot_dir"] = str(screenshot_dir)
    manifest["manifest_path"] = str(manifest_out)
    return manifest


def parse_manifest_from_output(stdout: str) -> dict | None:
    for line in stdout.splitlines():
        if line.startswith("playtest_manifest:"):
            return json.loads(line.split(":", 1)[1].strip())
    match = re.search(r"playtest_manifest:(\{.*\})", stdout)
    if match:
        return json.loads(match.group(1))
    return None
