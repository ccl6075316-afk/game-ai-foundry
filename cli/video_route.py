"""Resolve video generation credentials and backend from config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

VideoBackend = Literal["seedance", "openai_compat"]

_DEFAULT_SEEDANCE_BASE = "https://ark.cn-beijing.volces.com/api/v3"
_OPENROUTER_BASE_HINT = "openrouter.ai"
_SEEDANCE_BASE_HINTS = ("volces.com", "ark.")
# Apilio catalog ids drop the hyphen after veo (probe: veo3.1, not veo-3.1).
_BARE_MODEL_ALIASES = {
    "veo-3.1": "veo3.1",
    "veo-3.1-fast": "veo3.1-fast",
    "veo-3.1-pro": "veo3.1-pro",
    "veo-3.1-lite": "veo3.1-lite",
}


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


def _provider_account(config: dict[str, Any] | None, provider_id: str) -> dict[str, Any]:
    accounts = _section(config, "provider_accounts")
    acc = accounts.get(provider_id)
    return acc if isinstance(acc, dict) else {}


def infer_video_backend(provider: str, api_base: str) -> VideoBackend:
    pid = str(provider or "").strip().lower()
    base = str(api_base or "").strip().lower().rstrip("/")
    default_base = _DEFAULT_SEEDANCE_BASE.lower().rstrip("/")
    if pid == "seedance":
        return "seedance"
    if any(hint in base for hint in _SEEDANCE_BASE_HINTS):
        return "seedance"
    if not pid and (not base or base == default_base):
        return "seedance"
    return "openai_compat"


def normalize_video_model(model: str, api_base: str | None = None) -> str:
    """Strip vendor prefixes on non-OpenRouter gateways (Apilio-style bare ids)."""
    raw = str(model or "").strip()
    if not raw:
        return raw
    base = str(api_base or "").lower()
    if _OPENROUTER_BASE_HINT in base:
        return raw
    prefixes = (
        "google/",
        "openai/",
        "x-ai/",
        "alibaba/",
        "minimax/",
        "bytedance/",
        "kwaivgi/",
        "runway/",
        "black-forest-labs/",
    )
    lower = raw.lower()
    for prefix in prefixes:
        if lower.startswith(prefix):
            raw = raw.split("/", 1)[1]
            break
    alias = _BARE_MODEL_ALIASES.get(raw.lower())
    return alias if alias else raw


@dataclass(frozen=True)
class VideoCredentials:
    provider: str
    api_key: str | None
    api_base: str
    model: str
    backend: VideoBackend

    @property
    def usable(self) -> bool:
        return _key_usable(self.api_key)


def resolve_video_credentials(
    config: dict[str, Any] | None,
    *,
    explicit_model: str | None = None,
    explicit_key: str | None = None,
    explicit_base: str | None = None,
) -> VideoCredentials:
    """Resolve Key/Base/model/backend for video generation.

    Priority: CLI override > provider_accounts[video.provider] >
    legacy video.api_key/api_base > env.
    Empty ``video.provider`` with a legacy Seedance key is treated as seedance.
    """
    video = _section(config, "video")
    provider = str(video.get("provider") or "").strip()
    acc = _provider_account(config, provider) if provider else {}

    model = ""
    if explicit_model and str(explicit_model).strip():
        model = str(explicit_model).strip()
    elif str(video.get("model") or "").strip():
        model = str(video.get("model")).strip()
    elif str(acc.get("video_model") or "").strip():
        model = str(acc.get("video_model")).strip()

    api_key: str | None = None
    if explicit_key and str(explicit_key).strip():
        api_key = str(explicit_key).strip()
    elif provider and _key_usable(acc.get("api_key")):
        api_key = str(acc.get("api_key")).strip()
    elif _key_usable(video.get("api_key")):
        api_key = str(video.get("api_key")).strip()
    else:
        env_key = os.environ.get("GAMEFACTORY_VIDEO_API_KEY") or os.environ.get(
            "ARK_API_KEY"
        )
        api_key = env_key.strip() if env_key and str(env_key).strip() else None

    if explicit_base and str(explicit_base).strip():
        api_base = str(explicit_base).strip()
    elif provider and str(acc.get("api_base") or "").strip():
        api_base = str(acc.get("api_base")).strip()
    elif str(video.get("api_base") or "").strip():
        api_base = str(video.get("api_base")).strip()
    elif provider == "seedance" or not provider:
        api_base = _DEFAULT_SEEDANCE_BASE
    else:
        api_base = ""

    model = normalize_video_model(model, api_base)
    backend = infer_video_backend(provider, api_base)
    if not provider:
        provider = "seedance" if backend == "seedance" and _key_usable(api_key) else ""
    return VideoCredentials(
        provider=provider,
        api_key=api_key,
        api_base=api_base,
        model=model,
        backend=backend,
    )
