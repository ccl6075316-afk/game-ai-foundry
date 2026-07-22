#!/usr/bin/env python3
"""Game AI Foundry CLI — AI-powered game asset generation pipeline.

Image generation (OpenRouter), image processing (OpenCV/rembg),
video generation (Seedance), and Godot project management.
"""

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

from proxy_utils import (
    activate_proxy,
    http_get,
    http_post,
    region_error_hint,
    resolve_config_proxy,
)

DEFAULT_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_SIZE = "1024x1024"
DEFAULT_STYLE_IMG2IMG_STRENGTH = 0.25

# Dedicated image models (OpenRouter Images API / OpenAI images.generations).
# NOT multimodal chat hybrids like openai/gpt-5.4-image-2.
_DEDICATED_IMAGE_MODEL_RE = re.compile(
    r"(^|/)gpt-image(?:-1(?:-mini)?|-2)?(?:$|/)",
    re.IGNORECASE,
)

_OPENROUTER_IMAGE_ALIASES = {
    "gptimage 2": "openai/gpt-image-2",
    "gptimage2": "openai/gpt-image-2",
    "gpt-image-2": "openai/gpt-image-2",
    "gpt image 2": "openai/gpt-image-2",
    "gpt-image-1": "openai/gpt-image-1",
    "gpt-image-1-mini": "openai/gpt-image-1-mini",
}


def normalize_image_model(model: str, api_base: str | None = None) -> str:
    """Map common nicknames to OpenRouter/OpenAI slugs."""
    raw = (model or "").strip()
    if not raw:
        return raw
    # Repair accidental "images/" prefix (endpoint path pasted into model field).
    raw = re.sub(r"^images/", "", raw, flags=re.IGNORECASE)
    key = re.sub(r"\s+", " ", raw.lower())
    aliased = _OPENROUTER_IMAGE_ALIASES.get(key)
    if aliased:
        base = (api_base or "").lower()
        if "openai.com" in base and aliased.startswith("openai/"):
            return aliased.split("/", 1)[1]
        return aliased
    return raw


def uses_dedicated_images_api(model: str) -> bool:
    """True for models that must use /images (not chat/completions + modalities)."""
    return bool(_DEDICATED_IMAGE_MODEL_RE.search((model or "").strip()))


def images_api_endpoint(api_base: str) -> str:
    base = api_base.rstrip("/") + "/"
    if "openrouter.ai" in api_base.lower():
        return urljoin(base, "images")
    return urljoin(base, "images/generations")


CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"

from llm_config import resolve_prompt_api_settings


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


def resolve_image_proxy(
    config: dict[str, Any],
    cli_value: str | None = None,
) -> str | None:
    """Resolve image API proxy: CLI > config > shell env > macOS system proxy."""
    return resolve_config_proxy(config, cli_value)


def resolve_style_img2img_strength(config: dict[str, Any] | None) -> float | None:
    """Resolve image.style_img2img_strength; default 0.25 when key is missing."""
    image_cfg = (config or {}).get("image")
    if not isinstance(image_cfg, dict):
        return DEFAULT_STYLE_IMG2IMG_STRENGTH
    if "style_img2img_strength" not in image_cfg:
        return DEFAULT_STYLE_IMG2IMG_STRENGTH
    raw = image_cfg.get("style_img2img_strength")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, value))


def apply_style_img2img_strength(
    payload: dict[str, Any],
    config: dict[str, Any] | None,
    *,
    has_reference: bool,
) -> float | None:
    """Best-effort merge image_config.strength when a reference image is used."""
    if not has_reference:
        return None
    strength = resolve_style_img2img_strength(config)
    if strength is None:
        return None
    image_config = payload.get("image_config")
    if not isinstance(image_config, dict):
        image_config = {}
    else:
        image_config = dict(image_config)
    image_config["strength"] = strength
    payload["image_config"] = image_config
    print(f"style img2img strength={strength}", file=sys.stderr)
    return strength


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
        markdown_match = re.search(r"!\[[^\]]*\]\((https?://[^)]+)\)", content)
        if markdown_match:
            return markdown_match.group(1)
        url_match = re.search(r"https?://[^\s)\"'<>]+", content)
        if url_match:
            return url_match.group(0)

    raise ValueError(f"Could not extract image from response")


def extract_images_api_payload(response_data: dict[str, Any]) -> str:
    """Extract image URL/data-URL from OpenAI/OpenRouter Images API response."""
    data = response_data.get("data")
    if isinstance(data, list) and data:
        first = data[0] if isinstance(data[0], dict) else {}
        b64 = first.get("b64_json")
        if isinstance(b64, str) and b64.strip():
            return f"data:image/png;base64,{b64.strip()}"
        url = first.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    # Some gateways nest under output / images
    images = response_data.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, str) and first.startswith("data:"):
            return first
        if isinstance(first, dict):
            url = first.get("url") or first.get("image_url", {}).get("url")
            if url:
                return str(url)
    raise ValueError("Could not extract image from Images API response")


def download_image(
    url: str, output_path: Path, timeout: int = 120, proxy: str | None = None
) -> None:
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
        response = http_get(proxy, url, timeout=timeout, stream=True)
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


def _api_error_detail(response: requests.Response) -> str:
    detail = response.text.strip()
    try:
        error_body = response.json()
        err = error_body.get("error", {})
        if isinstance(err, dict):
            detail = str(err.get("message") or err.get("code") or detail)
        elif err:
            detail = str(err)
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    if response.status_code == 403 and "region" in detail.lower():
        detail = f"{detail}\n{region_error_hint()}"
    return detail


def generate_image_via_images_api(
    *,
    model: str,
    prompt: str,
    output: Path,
    size: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    reference_image: Path | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Call OpenRouter /images or OpenAI /images/generations and save the file."""
    import base64

    endpoint = images_api_endpoint(api_base)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }
    size_s = (size or "").strip()
    if size_s:
        payload["size"] = size_s

    if reference_image is not None:
        suffix = reference_image.suffix.lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(suffix, "image/png")
        encoded = base64.b64encode(reference_image.read_bytes()).decode("ascii")
        data_url = f"data:{mime};base64,{encoded}"
        if "openrouter.ai" in api_base.lower():
            payload["input_references"] = [data_url]
        else:
            # OpenAI images edits use a different endpoint; keep generation + note.
            payload["image"] = data_url
        apply_style_img2img_strength(
            payload,
            config if config is not None else load_config(),
            has_reference=True,
        )

    try:
        response = http_post(
            proxy,
            endpoint,
            headers=headers,
            json=payload,
            timeout=300,
        )
    except requests.RequestException as exc:
        hint = ""
        exc_s = str(exc).lower()
        if proxy and ("proxy" in exc_s or "proxyerror" in type(exc).__name__.lower()):
            hint = (
                f"\n当前走代理 {proxy}，代理拒绝或断开了连接。"
                "请确认 Clash/系统代理已开，或在设置里清空 Proxy 后直连重试。"
            )
        raise RuntimeError(f"Images API request failed: {exc}{hint}") from exc

    if response.status_code != 200:
        detail = _api_error_detail(response)
        # Unknown API size rules: if error names a multiple, snap once and retry.
        from asset_sizing import parse_size_multiple_from_error, snap_api_image_size

        multiple = parse_size_multiple_from_error(detail)
        size_now = str(payload.get("size") or "")
        if (
            response.status_code == 400
            and size_now
            and ("divisible" in detail.lower() or "invalid size" in detail.lower() or multiple)
        ):
            snapped = snap_api_image_size(size_now, multiple=multiple or 16)
            if snapped != size_now:
                payload["size"] = snapped
                retry = http_post(
                    proxy,
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=300,
                )
                if retry.status_code == 200:
                    response = retry
                else:
                    raise RuntimeError(
                        f"Images API error (HTTP {retry.status_code}): {_api_error_detail(retry)}\n"
                        f"endpoint={endpoint} model={model} (retried size {size_now} → {snapped})"
                    )
            else:
                raise RuntimeError(
                    f"Images API error (HTTP {response.status_code}): {detail}\n"
                    f"endpoint={endpoint} model={model}"
                )
        else:
            raise RuntimeError(
                f"Images API error (HTTP {response.status_code}): {detail}\n"
                f"endpoint={endpoint} model={model}"
            )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in Images API response: {exc}") from exc

    image_url = extract_images_api_payload(data)
    download_image(image_url, output, proxy=proxy)


def generate_image(
    *,
    model: str,
    prompt: str,
    output: Path,
    size: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    reference_image: Path | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Generate an image via chat modalities or dedicated Images API."""
    model = normalize_image_model(model, api_base)
    if uses_dedicated_images_api(model):
        generate_image_via_images_api(
            model=model,
            prompt=prompt,
            output=output,
            size=size,
            api_key=api_key,
            api_base=api_base,
            proxy=proxy,
            reference_image=reference_image,
            config=config,
        )
        return

    endpoint = urljoin(api_base.rstrip("/") + "/", "chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if reference_image is not None:
        import base64

        suffix = reference_image.suffix.lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(suffix, "image/png")
        encoded = base64.b64encode(reference_image.read_bytes()).decode("ascii")
        content: list[dict[str, Any]] | str = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
        ]
    else:
        content = prompt

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
    }
    if reference_image is not None:
        apply_style_img2img_strength(
            payload,
            config if config is not None else load_config(),
            has_reference=True,
        )

    try:
        response = http_post(
            proxy,
            endpoint,
            headers=headers,
            json=payload,
            timeout=180,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if response.status_code != 200:
        detail = _api_error_detail(response)
        hint = ""
        low = detail.lower()
        if "model" in low and ("not" in low or "invalid" in low or "no endpoints" in low):
            hint = (
                "\n提示：OpenRouter 的 GPT Image 2 请填 `openai/gpt-image-2`"
                "（会走 /images，不是 chat）。"
                "若要 chat 多模态可试 `openai/gpt-5.4-image-2`。"
            )
        raise RuntimeError(f"API error (HTTP {response.status_code}): {detail}{hint}")

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in API response: {exc}") from exc

    image_url = extract_image_url(data)
    download_image(image_url, output, proxy=proxy)


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Game Factory — generate game assets from the command line."""
    ctx.ensure_object(dict)
    config = load_config()
    ctx.obj["config"] = config
    ctx.obj["proxy"] = activate_proxy(config)


@cli.group()
def image() -> None:
    """Image generation commands."""


@image.command("generate")
@click.option("--model", default=None, help="Image model (default from config).")
@click.option(
    "--prompt",
    default=None,
    help="Generation prompt (image-generator: use --plan-file from prompt-crafter instead).",
)
@click.option(
    "--plan-file",
    "plan_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Handoff JSON from `prompt craft` (preferred for image-generator agent).",
)
@click.option(
    "--reference-image",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Reference image for img2img when plan requires it.",
)
@click.option("--validate/--no-validate", default=True, help="Validate output using plan rules (required gate before matting).")
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Output file path.",
)
@click.option("--size", default=None, help="Image dimensions.")
@click.option("--api-key", default=None, help="Image API key override.")
@click.option("--api-base", default=None, help="Image API base override.")
@click.option("--proxy", default=None, help="HTTP proxy for image API.")
@click.pass_context
def generate(
    ctx: click.Context,
    model: str | None,
    prompt: str | None,
    plan_path: Path | None,
    reference_image: Path | None,
    validate: bool,
    output: Path,
    size: str | None,
    api_key: str | None,
    api_base: str | None,
    proxy: str | None,
) -> None:
    """image-generator agent: call image API only. No prompt crafting."""
    from asset_pipeline import AssetType, validate_image
    from plan_io import (
        asset_type_from_handoff,
        image_size_from_handoff,
        load_handoff,
        prompt_from_handoff,
        validation_from_handoff,
    )

    config = ctx.obj["config"]
    resolved_prompt = prompt
    ref_image = reference_image
    validation_rules = None
    asset_type_name = None

    if plan_path is not None:
        if prompt:
            click.echo("Error: use either --plan-file or --prompt, not both.", err=True)
            sys.exit(1)
        try:
            handoff = load_handoff(plan_path)
            plan = handoff["plan"]
            resolved_prompt = prompt_from_handoff(handoff)
            validation_rules = validation_from_handoff(handoff)
            asset_type_name = asset_type_from_handoff(handoff)
            plan_size = image_size_from_handoff(handoff)
            if plan_size and not size:
                size = plan_size
            if plan.get("requires_reference_image") and ref_image is None:
                click.echo(
                    "Error: plan requires --reference-image for img2img.",
                    err=True,
                )
                sys.exit(1)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
    elif not resolved_prompt:
        click.echo(
            "Error: image-generator requires --plan-file (from prompt craft) or --prompt.",
            err=True,
        )
        sys.exit(1)

    resolved_model = resolve_image_setting(
        config, model, "model", "GAMEFACTORY_IMAGE_MODEL"
    )

    resolved_api_key = resolve_image_setting(
        config, api_key, "api_key", "GAMEFACTORY_API_KEY"
    ) or os.environ.get("OPENROUTER_API_KEY")

    resolved_proxy = resolve_image_proxy(config, proxy)

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
    from asset_sizing import size_multiple_for_model, snap_api_image_size

    # Only pre-snap when model/config declares a constraint (not all APIs).
    mult = size_multiple_for_model(str(resolved_model or ""), config if isinstance(config, dict) else None)
    if mult:
        resolved_size = snap_api_image_size(str(resolved_size), multiple=mult)

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
            prompt=resolved_prompt,
            output=output,
            size=resolved_size,
            api_key=resolved_api_key,
            api_base=resolved_api_base,
            proxy=resolved_proxy,
            reference_image=ref_image,
            config=config,
        )
    except (RuntimeError, ValueError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if (
        validate
        and validation_rules is not None
        and asset_type_name
        and not validation_rules.get("skip_validate")
        and asset_type_name != "visual_target"
    ):
        try:
            atype = AssetType(asset_type_name)
        except ValueError:
            atype = AssetType.CHARACTER
        result = validate_image(output, atype, validation_rules)
        click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        if not result.ok:
            sys.exit(2)

    click.echo(str(output.resolve()))


@cli.group()
def prompt() -> None:
    """prompt-crafter agent — write generation prompts (not image API)."""


from prompt_cmds import register_prompt_commands  # noqa: E402

register_prompt_commands(prompt, resolve_prompt_api_settings)


@image.command("validate")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Image to validate.",
)
@click.option(
    "--brief",
    "brief_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Load validation rules from brief asset spec.",
)
@click.option("--asset", default=None, help="Asset name (required with --brief).")
@click.option(
    "--type",
    "asset_type",
    default=None,
    type=click.Choice(
        ["character", "icon_kit", "texture", "background", "character_pose", "audio"],
        case_sensitive=False,
    ),
    help="Asset type when not using --brief.",
)
def validate_cmd(
    input_path: Path,
    brief_path: Path | None,
    asset: str | None,
    asset_type: str | None,
) -> None:
    """Validate a generated image against asset-type rules."""
    from asset_pipeline import (
        AssetType,
        build_prompt_scaffold,
        find_asset,
        load_brief,
        validate_image,
    )

    try:
        if brief_path:
            if not asset:
                click.echo("Error: --asset required with --brief.", err=True)
                sys.exit(1)
            project, assets = load_brief(brief_path)
            spec = find_asset(assets, asset)
            rules = build_prompt_scaffold(project, spec).validation
            atype = spec.type
        elif asset_type:
            atype = AssetType(asset_type.lower())
            rules = None
        else:
            click.echo("Error: pass --brief + --asset or --type.", err=True)
            sys.exit(1)

        result = validate_image(input_path, atype, rules)
        click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        if not result.ok:
            sys.exit(2)
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.command("context")
@click.option(
    "--brief",
    "brief_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Project brief JSON.",
)
@click.option("--asset", required=True, help="Asset name to build shared context for.")
def context_cmd(brief_path: Path, asset: str) -> None:
    """Print shared project+asset context (same payload all roles receive)."""
    from shared_context import dump_role_context, load_role_context

    try:
        click.echo(dump_role_context(load_role_context(brief_path, asset)))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.group()
def video() -> None:
    """Video generation and processing commands."""


@cli.group()
def godot() -> None:
    """Godot project management commands."""


from hermes_cmds import hermes_group  # noqa: E402

cli.add_command(hermes_group)

from agent_cmds import agents_group  # noqa: E402

cli.add_command(agents_group)

from doctor_cmds import doctor_cmd  # noqa: E402

cli.add_command(doctor_cmd)

from setup_cmds import setup_group  # noqa: E402

cli.add_command(setup_group)

from pipeline_cmds import pipeline_group  # noqa: E402

cli.add_command(pipeline_group)

from config_cmds import config_group  # noqa: E402

cli.add_command(config_group)


# Register image subcommands
from image_cmds import (
    slice_cmd,
    trim_cmd,
    remove_bg_cmd,
    resize_cmd,
    validate_matting_cmd,
)  # noqa: E402
image.add_command(trim_cmd)
image.add_command(slice_cmd)
image.add_command(remove_bg_cmd)
image.add_command(validate_matting_cmd)
image.add_command(resize_cmd)

# Register video subcommands
from video_cmds import (  # noqa: E402
    generate_cmd as video_generate_cmd,
    matte_frames_cmd,
    models_cmd,
    split_frames_cmd,
)
video.add_command(video_generate_cmd)
video.add_command(models_cmd)
video.add_command(split_frames_cmd)
video.add_command(matte_frames_cmd)

# Register godot subcommands
from godot_cmds import (
    assemble_cmd,
    dev_context_cmd,
    export_cmd,
    import_sprites_cmd,
    init_cmd,
    open_cmd,
    scaffold_cmd,
    screenshot_cmd as godot_screenshot_cmd,
    validate_cmd,
)  # noqa: E402
godot.add_command(init_cmd)
godot.add_command(import_sprites_cmd)
godot.add_command(assemble_cmd)
godot.add_command(scaffold_cmd)
godot.add_command(dev_context_cmd)
godot.add_command(godot_screenshot_cmd)
godot.add_command(validate_cmd)
godot.add_command(open_cmd)
godot.add_command(export_cmd)

from test_cmds import test_group  # noqa: E402

cli.add_command(test_group)

from brief_cmds import register_brief_commands  # noqa: E402

register_brief_commands(cli)

from agent_cmds import register_agent_commands  # noqa: E402

register_agent_commands(cli)

from production_cmds import register_production_commands  # noqa: E402

register_production_commands(cli)

from project_cmds import register_project_commands  # noqa: E402

register_project_commands(cli)

if __name__ == "__main__":
    cli()
