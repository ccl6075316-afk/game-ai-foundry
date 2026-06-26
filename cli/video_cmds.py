"""Video generation (Seedance) and frame extraction for gamefactory CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
import requests

from proxy_utils import activate_proxy, resolve_config_proxy
from seedance_api import SEEDANCE_MODELS, SeedanceError, generate_video, resolve_model


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


def _video_settings(config: dict, cli_key: str | None, cli_base: str | None) -> tuple[str | None, str]:
    video_cfg = config.get("video", {}) if isinstance(config.get("video"), dict) else {}
    api_key = (
        cli_key
        or video_cfg.get("api_key")
        or config.get("ark_api_key")
    )
    api_base = (
        cli_base
        or video_cfg.get("api_base")
        or "https://ark.cn-beijing.volces.com/api/v3"
    )
    return api_key, str(api_base)


def _status_echo(status: str, task: dict) -> None:
    click.echo(f"task status: {status}", err=True)


@click.command("models")
def models_cmd() -> None:
    """List built-in Seedance 2.0 model ids (pro / fast / mini)."""
    for alias, model_id in SEEDANCE_MODELS.items():
        click.echo(f"{alias}\t{model_id}")


@click.command("generate")
@click.option(
    "--model",
    default=None,
    help="Model id or alias: pro, fast, mini (default from config).",
)
@click.option("--prompt", default=None, help="Motion / scene description.")
@click.option(
    "--plan-file",
    "plan_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Handoff JSON from `prompt craft --animation` (video-generator agent).",
)
@click.option(
    "--reference-image",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Local PNG/JPG — first-frame image-to-video (uploaded via Files API).",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Output MP4 path.",
)
@click.option("--duration", type=int, default=None, help="Seconds (Seedance 2.0: 4–15).")
@click.option(
    "--resolution",
    default=None,
    type=click.Choice(["480p", "720p", "1080p"]),
    help="Output resolution (default 720p).",
)
@click.option(
    "--ratio",
    default=None,
    help="Aspect ratio: 16:9, 9:16, 1:1, auto (infer from --reference-image), etc.",
)
@click.option("--generate-audio/--no-generate-audio", default=None, help="Sync audio (default from config/plan).")
@click.option("--watermark/--no-watermark", default=None, help="AI watermark (default from config/plan).")
@click.option("--api-key", default=None, help="Volcengine Ark API key override.")
@click.option("--api-base", default=None, help="Ark API base override.")
@click.option("--poll-interval", type=float, default=10.0, help="Task poll seconds.")
@click.option("--timeout", type=float, default=600.0, help="Max wait seconds.")
def generate_cmd(
    model: str | None,
    prompt: str | None,
    plan_path: Path | None,
    reference_image: Path | None,
    output_path: Path,
    duration: int | None,
    resolution: str | None,
    ratio: str | None,
    generate_audio: bool | None,
    watermark: bool | None,
    api_key: str | None,
    api_base: str | None,
    poll_interval: float,
    timeout: float,
) -> None:
    """video-generator agent: Seedance image-to-video / text-to-video."""
    from plan_io import load_video_handoff, video_params_from_handoff
    from video_config import resolve_video_generate_settings

    config = _load_config()
    proxy = resolve_config_proxy(config)
    resolved_key, resolved_base = _video_settings(config, api_key, api_base)

    plan_overrides: dict[str, Any] = {}
    resolved_prompt = prompt
    ref_image = reference_image

    if plan_path is not None:
        if prompt:
            click.echo("Error: use either --plan-file or --prompt, not both.", err=True)
            sys.exit(1)
        try:
            handoff = load_video_handoff(plan_path)
            params = video_params_from_handoff(handoff)
            resolved_prompt = params["prompt"]
            for key in ("model", "duration", "resolution", "ratio", "generate_audio", "watermark"):
                if params.get(key) is not None:
                    plan_overrides[key] = params[key]
            if ref_image is None and params.get("reference_image"):
                ref_image = Path(params["reference_image"])
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    try:
        video = resolve_video_generate_settings(
            config,
            model=model or plan_overrides.get("model"),
            duration=duration if duration is not None else plan_overrides.get("duration"),
            resolution=resolution or plan_overrides.get("resolution"),
            ratio=ratio if ratio is not None else plan_overrides.get("ratio"),
            generate_audio=(
                generate_audio
                if generate_audio is not None
                else plan_overrides.get("generate_audio")
            ),
            watermark=(
                watermark if watermark is not None else plan_overrides.get("watermark")
            ),
            reference_image=ref_image,
            cli_ratio=ratio is not None,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if ref_image is None and video.get("ratio_source") != "cli":
        click.echo(
            "Warning: no --reference-image; ratio from plan/config, not still dimensions.",
            err=True,
        )
    elif video.get("ratio_source") == "reference_image":
        dims = video.get("reference_dimensions", [])
        mode = video.get("ratio_mode", video["ratio"])
        nearest = video.get("nearest_standard_ratio")
        extra = f", nearest standard {nearest}" if nearest else ""
        click.echo(
            f"ratio {video['ratio']} ({mode}) from reference {dims[0]}x{dims[1]} "
            f"(aspect {video.get('reference_aspect')}{extra})",
            err=True,
        )

    if not resolved_prompt:
        click.echo(
            "Error: provide --prompt or --plan-file with video_prompt.",
            err=True,
        )
        sys.exit(1)

    if not resolved_key:
        click.echo(
            "Error: Ark API key not found. Set video.api_key in ~/.gamefactory/config.json "
            "or pass --api-key.",
            err=True,
        )
        sys.exit(1)

    try:
        result = generate_video(
            model=video["model"],
            prompt=resolved_prompt,
            output_path=output_path,
            api_key=resolved_key,
            api_base=resolved_base,
            proxy=proxy,
            reference_image=ref_image,
            duration=video["duration"],
            resolution=video["resolution"],
            ratio=video["ratio"],
            generate_audio=video["generate_audio"],
            watermark=video["watermark"],
            poll_interval=poll_interval,
            timeout=timeout,
            status_cb=_status_echo,
        )
    except (SeedanceError, requests.RequestException) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(
        json.dumps(
            {
                "output": str(output_path.resolve()),
                "task_id": result["task_id"],
                "model": resolve_model(video["model"]),
                "duration": video["duration"],
                "resolution": video["resolution"],
                "ratio": video["ratio"],
                "ratio_source": video.get("ratio_source"),
                "reference_dimensions": video.get("reference_dimensions"),
                "generate_audio": video["generate_audio"],
            },
            ensure_ascii=False,
        )
    )


@click.command("split-frames")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source video file.")
@click.option("--output-dir", required=True, type=click.Path(path_type=Path),
              help="Output directory for frames.")
@click.option(
    "--frames",
    type=int,
    default=None,
    help="Target sprite frame count — evenly spaced across the clip (game default: 8).",
)
@click.option(
    "--fps",
    type=float,
    default=None,
    help="Extract at fixed fps (alternative to --frames; do not use both).",
)
@click.option(
    "--duration",
    "duration_seconds",
    type=float,
    default=None,
    help="Override video duration for --frames (seconds); auto-detected if omitted.",
)
@click.option("--format", "fmt", default="png", help="Output image format (png, jpg).")
def split_frames_cmd(
    input_path: Path,
    output_dir: Path,
    frames: int | None,
    fps: float | None,
    duration_seconds: float | None,
    fmt: str,
) -> None:
    """Extract sprite frames from video (default: config video.split_frames.frames, usually 8)."""
    from video_frames import SplitFramesError, split_video_to_frames

    config = _load_config()
    try:
        result = split_video_to_frames(
            input_path,
            output_dir,
            config=config,
            fps=fps,
            frames=frames,
            duration_seconds=duration_seconds,
            fmt=fmt,
        )
    except SplitFramesError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(json.dumps({k: v for k, v in result.items() if k != "paths"}, ensure_ascii=False))
    for path in result["paths"]:
        click.echo(path)


def _load_config_for_matting() -> dict:
    config_path = Path.home() / ".gamefactory" / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


@click.command("matte-frames")
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory of extracted video frames (frame_0001.png …).",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Output directory for RGBA frames.",
)
@click.option(
    "--engine",
    type=click.Choice(["ai", "soft-key"]),
    default="ai",
    show_default=True,
    help="ai = rembg (BiRefNet/ISNet); soft-key = gray/off-white color key fallback.",
)
@click.option("--model", default=None, help="rembg model (default birefnet-general).")
@click.option("--pattern", default="frame_*.png", show_default=True)
@click.option("--trim/--no-trim", default=False, help="Trim margins before matting (default: off — keep full frame).")
@click.option("--validate/--no-validate", default=True, help="Relaxed RGBA QA after each frame.")
@click.option("--threshold", type=int, default=None, help="soft-key brightness threshold.")
@click.option("--fuzz", type=float, default=None, help="soft-key color tolerance.")
def matte_frames_cmd(
    input_dir: Path,
    output_dir: Path,
    engine: str,
    model: str | None,
    pattern: str,
    trim: bool,
    validate: bool,
    threshold: int | None,
    fuzz: float | None,
) -> None:
    """Batch-matte video frames (AI matting — not studio white color-key)."""
    from video_matting import VideoMattingError, matte_frames_batch

    config = _load_config_for_matting()
    overrides: dict = {}
    if model:
        overrides["model"] = model
    if threshold is not None:
        overrides["threshold"] = threshold
    if fuzz is not None:
        overrides["fuzz"] = fuzz

    try:
        results = matte_frames_batch(
            input_dir,
            output_dir,
            engine=engine,  # type: ignore[arg-type]
            config=config,
            pattern=pattern,
            trim=trim,
            validate=validate,
            **overrides,
        )
    except VideoMattingError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(
        json.dumps(
            {
                "count": len(results),
                "engine": engine,
                "output_dir": str(output_dir.resolve()),
            },
            ensure_ascii=False,
        )
    )
    for item in results:
        click.echo(item["output"])
