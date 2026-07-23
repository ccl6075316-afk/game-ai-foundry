"""Resolve which image model / credentials to use (default vs bulk stills)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

GenerateTier = Literal["default", "bulk"]

_LOG = logging.getLogger("gamefactory.image_model_route")

DEFAULT_API_BASE = "https://openrouter.ai/api/v1"


def normalize_generate_tier(raw: str | None) -> GenerateTier | None:
    text = str(raw or "").strip().lower()
    if not text:
        return None
    if text in ("default", "bulk"):
        return text  # type: ignore[return-value]
    raise ValueError(f"generate_tier must be 'default' or 'bulk', got {raw!r}")


def effective_generate_tier(
    *,
    generate_tier: str | None,
    for_icon_kit_item: bool = False,
) -> GenerateTier:
    """Kit expanded items default to bulk; otherwise honor explicit tier or default."""
    normalized = None
    try:
        normalized = normalize_generate_tier(generate_tier)
    except ValueError:
        normalized = None
    if normalized:
        return normalized
    if for_icon_kit_item:
        return "bulk"
    return "default"


def _section(config: dict[str, Any] | None, name: str) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    block = config.get(name)
    return block if isinstance(block, dict) else {}


def _key_usable(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and "YOUR_" not in text.upper()


def resolve_image_provider_id(config: dict[str, Any] | None, tier: GenerateTier) -> str:
    """Pick provider id for tier. Missing bulk_provider falls back to image.provider."""
    image = _section(config, "image")
    host = _section(config, "host")
    if tier == "bulk":
        pid = str(image.get("bulk_provider") or image.get("provider") or "").strip()
    else:
        if image.get("use_text_provider") is True:
            pid = str(host.get("provider") or image.get("provider") or "").strip()
        else:
            pid = str(image.get("provider") or "").strip()
    if not pid:
        pid = str(host.get("provider") or "").strip()
    return pid or "openrouter"


def resolve_image_model_for_tier(
    config: dict[str, Any] | None,
    tier: GenerateTier,
    *,
    explicit_model: str | None = None,
) -> str:
    """Pick model id for generate. ``explicit_model`` (CLI --model) wins."""
    if explicit_model and str(explicit_model).strip():
        return str(explicit_model).strip()
    image_cfg = _section(config, "image")
    default = str(image_cfg.get("model") or "").strip()
    if tier == "bulk":
        bulk = str(image_cfg.get("bulk_model") or "").strip()
        if bulk:
            return bulk
        if default:
            _LOG.info(
                "image.bulk_model unset; falling back to image.model=%s",
                default,
            )
            return default
        return ""
    return default


@dataclass(frozen=True)
class ImageCredentials:
    provider: str
    api_key: str | None
    api_base: str
    model: str
    tier: GenerateTier


def _provider_account(config: dict[str, Any] | None, provider_id: str) -> dict[str, Any]:
    accounts = _section(config, "provider_accounts")
    acc = accounts.get(provider_id)
    return acc if isinstance(acc, dict) else {}


def _known_api_base(provider_id: str) -> str:
    try:
        from provider_upsert import KNOWN_PROVIDERS

        known = KNOWN_PROVIDERS.get(provider_id) or {}
        base = str(known.get("api_base") or "").strip()
        return base
    except Exception:
        return ""


def resolve_image_credentials(
    config: dict[str, Any] | None,
    tier: GenerateTier = "default",
    *,
    explicit_model: str | None = None,
    explicit_key: str | None = None,
    explicit_base: str | None = None,
) -> ImageCredentials:
    """Resolve Key/Base/model for default or bulk image generation.

    Priority for key/base: CLI override > provider_accounts[provider] >
    legacy image.* (when same provider) > host.* > env.
    Missing ``bulk_provider`` uses ``image.provider``.
    """
    provider = resolve_image_provider_id(config, tier)
    image = _section(config, "image")
    host = _section(config, "host")
    acc = _provider_account(config, provider)

    model = resolve_image_model_for_tier(config, tier, explicit_model=explicit_model)
    if not model:
        model = str(acc.get("image_model") or "").strip()

    api_key: str | None = None
    if explicit_key and str(explicit_key).strip():
        api_key = str(explicit_key).strip()
    elif _key_usable(acc.get("api_key")):
        api_key = str(acc.get("api_key")).strip()
    elif _key_usable(image.get("api_key")) and str(image.get("provider") or provider) == provider:
        api_key = str(image.get("api_key")).strip()
    elif _key_usable(host.get("api_key")) and str(host.get("provider") or provider) == provider:
        api_key = str(host.get("api_key")).strip()
    else:
        api_key = (
            os.environ.get("GAMEFACTORY_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or None
        )
        if api_key:
            api_key = api_key.strip() or None

    if explicit_base and str(explicit_base).strip():
        api_base = str(explicit_base).strip()
    elif str(acc.get("api_base") or "").strip():
        api_base = str(acc.get("api_base")).strip()
    elif (
        str(image.get("api_base") or "").strip()
        and str(image.get("provider") or provider) == provider
    ):
        api_base = str(image.get("api_base")).strip()
    elif (
        str(host.get("api_base") or "").strip()
        and str(host.get("provider") or provider) == provider
    ):
        api_base = str(host.get("api_base")).strip()
    else:
        api_base = (
            os.environ.get("GAMEFACTORY_API_BASE")
            or _known_api_base(provider)
            or DEFAULT_API_BASE
        )

    return ImageCredentials(
        provider=provider,
        api_key=api_key,
        api_base=api_base,
        model=model,
        tier=tier,
    )
