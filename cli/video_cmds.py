"""Video processing subcommands for gamefactory CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click
import requests

from proxy_utils import activate_proxy, http_get, http_post, resolve_config_proxy


def _load_config() -> dict:
    config_path = Path.home() / ".gamefactory" / "config.json"
    if not config_path.exists():
        return {}
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    activate_proxy(config)
    return config


@click.command("generate")
@click.option("--model", required=True, help="Video generation model (e.g., 'seedance').")
@click.option("--prompt", required=True, help="Video description.")
@click.option("--output", "output_path", required=True, type=click.Path(path_type=Path),
              help="Output video file path.")
@click.option("--api-key", default=None, help="API key override.")
@click.option("--api-base", default=None, help="API base URL override.")
@click.option("--fps", type=int, default=24, help="Target frame rate.")
@click.option("--duration", type=int, default=5, help="Video duration in seconds.")
def generate_cmd(model: str, prompt: str, output_path: Path, api_key: str | None,
                 api_base: str | None, fps: int, duration: int) -> None:
    """Generate a video via API."""
    config = _load_config()
    video_cfg = config.get("video", {})
    proxy = resolve_config_proxy(config)

    resolved_key = api_key or video_cfg.get("api_key") or None
    resolved_base = api_base or video_cfg.get("api_base", "https://api.seedance.com/v1")

    if not resolved_key:
        click.echo("Error: API key not found. Set in config or pass --api-key.", err=True)
        sys.exit(1)

    endpoint = f"{resolved_base.rstrip('/')}/generate"
    headers = {"Authorization": f"Bearer {resolved_key}", "Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt, "fps": fps, "duration": duration}

    try:
        resp = http_post(proxy, endpoint, headers=headers, json=payload, timeout=300)
        if resp.status_code != 200:
            detail = resp.text[:300]
            try:
                detail = resp.json().get("error", {}).get("message", detail)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise RuntimeError(f"API error (HTTP {resp.status_code}): {detail}")

        data = resp.json()
        video_url = data.get("url") or data.get("video_url") or \
                    next((c.get("url") for c in data.get("choices", [{}])
                          if c.get("url")), None)

        if not video_url:
            raise RuntimeError("No video URL in API response")

        # Download video
        video = http_get(proxy, video_url, timeout=300)
        video.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(video.content)
        click.echo(str(output_path.resolve()))

    except (requests.RequestException, RuntimeError, json.JSONDecodeError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command("split-frames")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source video file.")
@click.option("--output-dir", required=True, type=click.Path(path_type=Path),
              help="Output directory for frames.")
@click.option("--fps", type=float, default=None,
              help="Frames per second to extract (default: use video's fps).")
@click.option("--format", "fmt", default="png", help="Output image format (png, jpg).")
def split_frames_cmd(input_path: Path, output_dir: Path, fps: float | None, fmt: str) -> None:
    """Extract frames from a video using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_pattern = str(output_dir / f"frame_%04d.{fmt}")

    cmd = ["ffmpeg", "-i", str(input_path), "-y"]
    if fps:
        cmd += ["-vf", f"fps={fps}"]
    cmd += [out_pattern]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running ffmpeg: {e.stderr}", err=True)
        sys.exit(1)

    # List output files
    frames = sorted(output_dir.glob(f"frame_*.{fmt}"))
    for f in frames:
        click.echo(str(f.resolve()))

    if not frames:
        click.echo("Warning: no frames extracted", err=True)
