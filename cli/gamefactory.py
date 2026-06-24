#!/usr/bin/env python3
"""Game Factory CLI — image generation and asset tooling."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import click
import requests

DEFAULT_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_SIZE = "1024x1024"
CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"


def load_config() -> dict[str, Any]:
    """Load config from ~/.gamefactory/config.json, or return empty dict."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Warning: could not read config at {CONFIG_PATH}: {exc}", err=True)
        return {}


def resolve_image_setting(
    config: dict[str, Any],
    cli_value: str | None,
    config_key: str,
    env_key: str,
    default: str | None = None,
) -> str | None:
    """Resolve a setting: CLI override > config > environment > default."""
    if cli_value is not None:
        return cli_value
    image_cfg = config.get("image", {})
    if isinstance(image_cfg, dict) and image_cfg.get(config_key):
        return str(image_cfg[config_key])
    env_value = os.environ.get(env_key)
    if env_value:
        return env_value
    return default


def extract_image_url(response_data: dict[str, Any]) -> str:
    """Extract an image URL or base64 data from a chat completions response."""
    message = response_data.get("choices", [{}])[0].get("message", {})

    # Nano Banana / Gemini format: message.images array with base64
    images = message.get("images")
    if images and isinstance(images, list) and len(images) > 0:
        url = images[0].get("image_url", {}).get("url")
        if url:
            return url  # base64 data URL or http URL

    # Legacy: content-based image extraction
    content = message.get("content")
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url")
                    if url:
                        return url

    if isinstance(content, str) and content.strip():
        import re
        markdown_match = re.search(r"!\[[^\]]*\]\((https?://[^)]+)\)", content)
        if markdown_match:
            return markdown_match.group(1)
        url_match = re.search(r"https?://[^\s)\"'<>]+", content)
        if url_match:
            return url_match.group(0)

    raise ValueError(f"Could not extract image from response")


def download_image(url: str, output_path: Path, timeout: int = 120) -> None:
    """Download or decode an image and save it to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Handle base64 data URL
    if url.startswith("data:"):
        import base64
        _, encoded = url.split(",", 1)
        output_path.write_bytes(base64.b64decode(encoded))
        return

    # Handle HTTP URL
    try:
        response = requests.get(url, timeout=timeout, stream=True)
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download image from {url}: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to download image from {url}: HTTP {response.status_code}"
        )

    try:
        output_path.write_bytes(response.content)
    except OSError as exc:
        raise RuntimeError(f"Failed to write image to {output_path}: {exc}") from exc


def generate_image(
    *,
    model: str,
    prompt: str,
    output: Path,
    size: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
) -> None:
    """Call the chat completions API, extract the image URL, and save the file."""
    endpoint = urljoin(api_base.rstrip("/") + "/", "chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
    }

    try:
        proxies = {"http": proxy, "https": proxy} if proxy else None
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120, proxies=proxies)
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if response.status_code != 200:
        detail = response.text.strip()
        try:
            error_body = response.json()
            detail = error_body.get("error", {}).get("message", detail)
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        raise RuntimeError(f"API error (HTTP {response.status_code}): {detail}")

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in API response: {exc}") from exc

    image_url = extract_image_url(data)
    download_image(image_url, output)


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Game Factory — generate game assets from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config()


@cli.group()
def image() -> None:
    """Image generation commands."""


@image.command("generate")
@click.option("--model", default=None, help="Image model (default from config).")
@click.option("--prompt", required=True, help="The image description.")
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Output file path (e.g. ./assets/player_sprite.png).",
)
@click.option(
    "--size",
    default=None,
    show_default=f"{DEFAULT_SIZE} (from config/env)",
    help="Image dimensions.",
)
@click.option("--api-key", default=None, help="Override API key from config/env.")
@click.option(
    "--api-base",
    default=None,
    help=f"API base URL override (default: {DEFAULT_API_BASE}).",
)
@click.option(
    "--proxy",
    default=None,
    help="HTTP proxy for API requests (e.g. http://127.0.0.1:7897).",
)
@click.pass_context
def generate(
    ctx: click.Context,
    model: str,
    prompt: str,
    output: Path,
    size: str | None,
    api_key: str | None,
    api_base: str | None,
    proxy: str | None,
) -> None:
    """Generate an image via OpenRouter-compatible chat completions."""
    config = ctx.obj["config"]

    resolved_model = resolve_image_setting(
        config, model, "model", "GAMEFACTORY_IMAGE_MODEL"
    )

    resolved_api_key = resolve_image_setting(
        config, api_key, "api_key", "GAMEFACTORY_API_KEY"
    ) or os.environ.get("OPENROUTER_API_KEY")

    resolved_proxy = resolve_image_setting(
        config,
        proxy,
        "proxy",
        "GAMEFACTORY_PROXY",
    )

    resolved_api_base = resolve_image_setting(
        config,
        api_base,
        "api_base",
        "GAMEFACTORY_API_BASE",
        DEFAULT_API_BASE,
    )

    resolved_size = resolve_image_setting(
        config, size, "size", "GAMEFACTORY_IMAGE_SIZE", DEFAULT_SIZE
    )

    if not resolved_model:
        click.echo(
            "Error: model not specified. Set it in ~/.gamefactory/config.json, "
            "GAMEFACTORY_IMAGE_MODEL, or pass --model.",
            err=True,
        )
        sys.exit(1)

    if not resolved_api_key:
        click.echo(
            "Error: API key not found. Set it in ~/.gamefactory/config.json, "
            "GAMEFACTORY_API_KEY, or OPENROUTER_API_KEY, or pass --api-key.",
            err=True,
        )
        sys.exit(1)

    assert resolved_model is not None
    assert resolved_api_base is not None
    assert resolved_size is not None

    try:
        generate_image(
            model=resolved_model,
            prompt=prompt,
            output=output,
            size=resolved_size,
            api_key=resolved_api_key,
            api_base=resolved_api_base,
            proxy=resolved_proxy,
        )
    except (RuntimeError, ValueError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(str(output.resolve()))


@cli.group()
def video() -> None:
    """Video generation and processing commands."""


@cli.group()
def godot() -> None:
    """Godot project management commands."""


# Register image subcommands
from image_cmds import slice_cmd, remove_bg_cmd, resize_cmd  # noqa: E402
image.add_command(slice_cmd)
image.add_command(remove_bg_cmd)
image.add_command(resize_cmd)

# Register video subcommands
from video_cmds import generate_cmd as video_generate_cmd, split_frames_cmd  # noqa: E402
video.add_command(video_generate_cmd)
video.add_command(split_frames_cmd)

# Register godot subcommands
from godot_cmds import init_cmd, inject_cmd, validate_cmd, open_cmd, export_cmd  # noqa: E402
godot.add_command(init_cmd)
godot.add_command(inject_cmd)
godot.add_command(validate_cmd)
godot.add_command(open_cmd)
godot.add_command(export_cmd)

if __name__ == "__main__":
    cli()
