"""Resolve LLM API settings with host → role fallback."""

from __future__ import annotations

import os
from typing import Any

from proxy_utils import resolve_config_proxy

DEFAULT_API_BASE = "https://openrouter.ai/api/v1"


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    block = config.get(name, {})
    return block if isinstance(block, dict) else {}


def _is_set(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and "YOUR_" not in text.upper()


def resolve_host_api_settings(
    config: dict[str, Any],
    *,
    model: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    proxy: str | None = None,
) -> dict[str, str | None]:
    """项目经理 (host) LLM — primary fallback for prompt & code."""
    from prompt_craft import DEFAULT_PROMPT_MODEL

    host_cfg = _section(config, "host")
    image_cfg = _section(config, "image")
    prompt_cfg = _section(config, "prompt")

    resolved_model = (
        model
        or host_cfg.get("model")
        or prompt_cfg.get("model")
        or os.environ.get("GAMEFACTORY_HOST_MODEL")
        or os.environ.get("GAMEFACTORY_PROMPT_MODEL")
        or DEFAULT_PROMPT_MODEL
    )
    resolved_key = (
        api_key
        or host_cfg.get("api_key")
        or prompt_cfg.get("api_key")
        or image_cfg.get("api_key")
        or os.environ.get("GAMEFACTORY_HOST_API_KEY")
        or os.environ.get("GAMEFACTORY_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    resolved_base = (
        api_base
        or host_cfg.get("api_base")
        or image_cfg.get("api_base")
        or os.environ.get("GAMEFACTORY_HOST_API_BASE")
        or os.environ.get("GAMEFACTORY_API_BASE")
        or DEFAULT_API_BASE
    )
    resolved_proxy = resolve_config_proxy(config, proxy)

    return {
        "model": str(resolved_model),
        "api_key": str(resolved_key) if resolved_key else None,
        "api_base": str(resolved_base),
        "proxy": str(resolved_proxy) if resolved_proxy else None,
        "source": "host",
    }


def resolve_prompt_api_settings(
    config: dict[str, Any],
    *,
    prompt_model: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    proxy: str | None = None,
) -> dict[str, str | None]:
    """文案 prompt-crafter — config.prompt overrides, else host."""
    from prompt_craft import DEFAULT_PROMPT_MODEL

    prompt_cfg = _section(config, "prompt")
    host = resolve_host_api_settings(config)

    use_host_key = not _is_set(api_key) and not _is_set(prompt_cfg.get("api_key"))
    use_host_base = not _is_set(api_base) and not _is_set(prompt_cfg.get("api_base"))

    resolved_model = (
        prompt_model
        or prompt_cfg.get("model")
        or os.environ.get("GAMEFACTORY_PROMPT_MODEL")
        or host["model"]
        or DEFAULT_PROMPT_MODEL
    )
    resolved_key = (
        api_key
        or prompt_cfg.get("api_key")
        or (host["api_key"] if use_host_key else None)
        or os.environ.get("GAMEFACTORY_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    resolved_base = (
        api_base
        or prompt_cfg.get("api_base")
        or (host["api_base"] if use_host_base else None)
        or DEFAULT_API_BASE
    )
    resolved_proxy = resolve_config_proxy(config, proxy)

    source = "prompt"
    if use_host_key and resolved_key == host.get("api_key"):
        source = "host"

    return {
        "prompt_model": str(resolved_model),
        "api_key": str(resolved_key) if resolved_key else None,
        "api_base": str(resolved_base),
        "proxy": str(resolved_proxy) if resolved_proxy else None,
        "source": source,
    }


def resolve_code_api_settings(
    config: dict[str, Any],
    *,
    code_model: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    proxy: str | None = None,
) -> dict[str, str | None]:
    """程序员 godot-developer LLM — config.code overrides, else host."""
    code_cfg = _section(config, "code")
    host = resolve_host_api_settings(config)

    use_host_key = not _is_set(api_key) and not _is_set(code_cfg.get("api_key"))
    use_host_base = not _is_set(api_base) and not _is_set(code_cfg.get("api_base"))

    resolved_model = (
        code_model
        or code_cfg.get("model")
        or os.environ.get("GAMEFACTORY_CODE_MODEL")
        or host["model"]
    )
    resolved_key = (
        api_key
        or code_cfg.get("api_key")
        or (host["api_key"] if use_host_key else None)
        or os.environ.get("GAMEFACTORY_CODE_API_KEY")
        or os.environ.get("GAMEFACTORY_HOST_API_KEY")
        or os.environ.get("GAMEFACTORY_API_KEY")
    )
    resolved_base = (
        api_base
        or code_cfg.get("api_base")
        or (host["api_base"] if use_host_base else None)
        or host["api_base"]
        or DEFAULT_API_BASE
    )
    resolved_proxy = resolve_config_proxy(config, proxy)

    source = "code"
    if use_host_key and resolved_key == host.get("api_key"):
        source = "host"

    return {
        "code_model": str(resolved_model) if resolved_model else None,
        "api_key": str(resolved_key) if resolved_key else None,
        "api_base": str(resolved_base),
        "proxy": str(resolved_proxy) if resolved_proxy else None,
        "source": source,
    }


DEFAULT_TEST_VISION_MODEL = "google/gemini-2.5-flash"


def resolve_test_api_settings(
    config: dict[str, Any],
    *,
    vision_model: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    proxy: str | None = None,
) -> dict[str, str | None]:
    """Tester vision LLM — config.test overrides, else host."""
    test_cfg = _section(config, "test")
    host = resolve_host_api_settings(config)

    use_host_key = not _is_set(api_key) and not _is_set(test_cfg.get("api_key"))
    use_host_base = not _is_set(api_base) and not _is_set(test_cfg.get("api_base"))

    resolved_model = (
        vision_model
        or test_cfg.get("vision_model")
        or os.environ.get("GAMEFACTORY_TEST_VISION_MODEL")
        or host["model"]
        or DEFAULT_TEST_VISION_MODEL
    )
    resolved_key = (
        api_key
        or test_cfg.get("api_key")
        or (host["api_key"] if use_host_key else None)
        or os.environ.get("GAMEFACTORY_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    resolved_base = (
        api_base
        or test_cfg.get("api_base")
        or (host["api_base"] if use_host_base else None)
        or DEFAULT_API_BASE
    )
    resolved_proxy = resolve_config_proxy(config, proxy)

    return {
        "model": str(resolved_model),
        "api_key": str(resolved_key) if resolved_key else None,
        "api_base": str(resolved_base),
        "proxy": str(resolved_proxy) if resolved_proxy else None,
        "source": "test",
    }
