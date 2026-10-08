"""Record a Godot scene as a PNG sequence at a fixed frame rate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from godot_screenshot import _load_config, get_godot_exe
from toolchain_paths import toolchain_env


def capture_frames(
    project_path: Path,
    output_dir: Path,
    *,
    scene: str | None = None,
    fps: int = 12,
    frames: int = 48,
    timeout: int = 180,
) -> dict:
    """Run a scene and let it save one PNG per frame under output_dir.

    The scene reads ``--gf-frame-dir=<abs>`` from user args. A window is used
    because a headless framebuffer is often empty.
    """
    project_path = project_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    godot = get_godot_exe().replace("_console.exe", ".exe")
    fps = max(1, fps)
    frames = max(1, frames)
    cmd = [
        godot,
        "--path",
        str(project_path),
        "--fixed-fps",
        str(fps),
        "--quit-after",
        str(frames),
        "--",
        f"--gf-frame-dir={output_dir}",
    ]
    if scene:
        cmd.insert(3, scene)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=toolchain_env(_load_config()),
    )
    saved = sorted(output_dir.glob("frame_*.png"))
    combined = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 or not saved:
        tail = "\n".join(combined.splitlines()[-20:])
        raise RuntimeError(f"Frame capture failed ({result.returncode}):\n{tail}")

    video = _write_video(output_dir, fps)
    payload = {
        "ok": True,
        "project_path": str(project_path),
        "scene": scene or "",
        "output_dir": str(output_dir),
        "fps": fps,
        "frames": len(saved),
        "first": str(saved[0]),
        "last": str(saved[-1]),
    }
    if video is not None:
        payload["video"] = str(video)
    return payload


def _write_video(output_dir: Path, fps: int) -> Path | None:
    """Stitch frame_*.png into capture.mp4 when ffmpeg is on PATH."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    dest = output_dir / "capture.mp4"
    pattern = str(output_dir / "frame_%04d.png")
    result = subprocess.run(
        [
            ffmpeg, "-y",
            "-framerate", str(fps),
            "-start_number", "1",
            "-i", pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(dest),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not dest.is_file():
        return None
    return dest
