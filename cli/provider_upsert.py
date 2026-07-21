"""Upsert Foundry provider_accounts entry (IT toolbox write path)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"

KNOWN_PROVIDERS: dict[str, dict[str, str]] = {
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "text_model": "deepseek/deepseek-chat",
    },
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "text_model": "deepseek-chat",
    },
    "kimi": {
        "api_base": "https://api.moonshot.cn/v1",
        "text_model": "kimi-k2.5",
    },
    "glm": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "text_model": "glm-4-flash",
    },
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "text_model": "gpt-4o-mini",
    },
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "text_model": "gemini-2.0-flash",
    },
    "custom": {
        "api_base": "",
        "text_model": "",
    },
}


def _key_usable(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and "YOUR_" not in text.upper()


def _load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or _CONFIG_PATH
    if not cfg_path.is_file():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(cfg: dict[str, Any], path: Path | None = None) -> None:
    cfg_path = path or _CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_api_key(
    *,
    api_key: str | None = None,
    api_key_env: str | None = None,
) -> str | None:
    """Prefer explicit api_key, then named env, then GAMEFACTORY_PROVIDER_API_KEY."""
    if _key_usable(api_key):
        return str(api_key).strip()
    env_name = (api_key_env or "").strip() or "GAMEFACTORY_PROVIDER_API_KEY"
    env_val = os.environ.get(env_name)
    if _key_usable(env_val):
        return str(env_val).strip()
    return None


def upsert_provider_account(
    *,
    provider: str,
    api_key: str | None = None,
    api_key_env: str | None = None,
    api_base: str | None = None,
    text_model: str | None = None,
    set_active_text: bool = True,
    i_confirm: bool = False,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Write provider_accounts[provider] and optionally switch host to that provider.

    Requires ``i_confirm=True``. Never returns the raw api_key.
    """
    provider_id = str(provider or "").strip().lower()
    if not provider_id:
        return {
            "ok": False,
            "provider": None,
            "has_api_key": False,
            "set_active_text": False,
            "error": "缺少 --provider",
        }
    if provider_id not in KNOWN_PROVIDERS:
        return {
            "ok": False,
            "provider": provider_id,
            "has_api_key": False,
            "set_active_text": False,
            "error": f"未知 provider id: {provider_id}（支持: {', '.join(KNOWN_PROVIDERS)}）",
        }
    if not i_confirm:
        return {
            "ok": False,
            "provider": provider_id,
            "has_api_key": False,
            "set_active_text": False,
            "error": "需要用户确认后带 --i-confirm 才能写入",
        }

    key = resolve_api_key(api_key=api_key, api_key_env=api_key_env)
    if not key:
        return {
            "ok": False,
            "provider": provider_id,
            "has_api_key": False,
            "set_active_text": False,
            "error": "未提供可用 API Key（--api-key / 环境 GAMEFACTORY_PROVIDER_API_KEY）",
        }

    defaults = KNOWN_PROVIDERS[provider_id]
    base = (api_base or "").strip() or defaults.get("api_base") or ""
    model = (text_model or "").strip() or defaults.get("text_model") or ""
    if provider_id == "custom" and not base:
        return {
            "ok": False,
            "provider": provider_id,
            "has_api_key": True,
            "set_active_text": False,
            "error": "custom provider 需要 --api-base",
        }

    cfg = _load_config(config_path)
    accounts = cfg.get("provider_accounts") if isinstance(cfg.get("provider_accounts"), dict) else {}
    entry = dict(accounts.get(provider_id) if isinstance(accounts.get(provider_id), dict) else {})
    entry["api_key"] = key
    if base:
        entry["api_base"] = base
    if model:
        entry["text_model"] = model
    accounts = {**accounts, provider_id: entry}
    cfg["provider_accounts"] = accounts

    active = bool(set_active_text)
    if active:
        host = cfg.get("host") if isinstance(cfg.get("host"), dict) else {}
        host = {
            **host,
            "provider": provider_id,
            "api_key": key,
            "api_base": base or host.get("api_base"),
            "model": model or host.get("model"),
        }
        cfg["host"] = host

    _save_config(cfg, config_path)
    return {
        "ok": True,
        "provider": provider_id,
        "has_api_key": True,
        "set_active_text": active,
        "api_base": base or None,
        "text_model": model or None,
        "error": None,
    }
