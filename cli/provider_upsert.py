"""Upsert Foundry provider_accounts entry (IT toolbox write path)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path.home() / ".gamefactory" / "config.json"

_PROVIDER_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")

BUILTIN_PROVIDERS: dict[str, dict[str, str]] = {
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "text_model": "deepseek/deepseek-v4-flash",
    },
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "text_model": "deepseek-v4-flash",
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
}

CUSTOM_PROVIDER_ID = "custom"

KNOWN_PROVIDERS: dict[str, dict[str, str]] = {
    **BUILTIN_PROVIDERS,
    CUSTOM_PROVIDER_ID: {
        "api_base": "",
        "text_model": "",
    },
}


def is_builtin_provider_id(provider_id: str) -> bool:
    return provider_id in BUILTIN_PROVIDERS


def is_valid_provider_slug(provider_id: str) -> bool:
    return bool(_PROVIDER_SLUG_RE.match(provider_id))


def account_kind(provider_id: str, entry: dict[str, Any] | None = None) -> str:
    """Infer account kind: builtin vs user (custom without kind → user)."""
    if is_builtin_provider_id(provider_id):
        return "builtin"
    if provider_id == CUSTOM_PROVIDER_ID:
        return "user"
    if isinstance(entry, dict):
        raw = str(entry.get("kind") or "").strip().lower()
        if raw in ("builtin", "user"):
            return raw
    if is_valid_provider_slug(provider_id):
        return "user"
    return "user"


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


def _accounts_map(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    accounts = cfg.get("provider_accounts")
    if not isinstance(accounts, dict):
        return {}
    return {k: dict(v) for k, v in accounts.items() if isinstance(v, dict)}


def _sanitize_account_public(
    provider_id: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    base = str(entry.get("api_base") or "").strip()
    text_model = str(entry.get("text_model") or "").strip()
    image_model = str(entry.get("image_model") or "").strip()
    label = str(entry.get("label") or "").strip()
    kind = account_kind(provider_id, entry)
    if not label and provider_id in KNOWN_PROVIDERS and kind == "builtin":
        label = provider_id
    return {
        "id": provider_id,
        "kind": kind,
        "label": label or None,
        "has_api_key": _key_usable(entry.get("api_key")),
        "api_base": base or None,
        "text_model": text_model or None,
        "image_model": image_model or None,
    }


def _provider_referenced(cfg: dict[str, Any], provider_id: str) -> list[str]:
    refs: list[str] = []
    host = cfg.get("host") if isinstance(cfg.get("host"), dict) else {}
    if str(host.get("provider") or "").strip() == provider_id:
        refs.append("host.provider")
    image = cfg.get("image") if isinstance(cfg.get("image"), dict) else {}
    if str(image.get("provider") or "").strip() == provider_id:
        refs.append("image.provider")
    if str(image.get("bulk_provider") or "").strip() == provider_id:
        refs.append("image.bulk_provider")
    return refs


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
    image_model: str | None = None,
    label: str | None = None,
    kind: str | None = None,
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
    if not i_confirm:
        return {
            "ok": False,
            "provider": provider_id,
            "has_api_key": False,
            "set_active_text": False,
            "error": "需要用户确认后带 --i-confirm 才能写入",
        }

    is_known = provider_id in KNOWN_PROVIDERS
    is_user_slug = is_valid_provider_slug(provider_id) and not is_builtin_provider_id(provider_id)
    if not is_known and not is_user_slug:
        return {
            "ok": False,
            "provider": provider_id,
            "has_api_key": False,
            "set_active_text": False,
            "error": (
                f"非法 provider id: {provider_id}"
                f"（内置: {', '.join(BUILTIN_PROVIDERS)}；用户 slug: [a-z][a-z0-9_-]{{1,31}}）"
            ),
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

    cfg = _load_config(config_path)
    accounts = _accounts_map(cfg)
    existing = accounts.get(provider_id, {})
    inferred_kind = account_kind(provider_id, existing)
    if is_builtin_provider_id(provider_id):
        entry_kind = "builtin"
    elif provider_id == CUSTOM_PROVIDER_ID or is_user_slug:
        entry_kind = "user"
    else:
        entry_kind = inferred_kind

    kind_text = str(kind or "").strip().lower()
    if kind_text in ("builtin", "user"):
        if kind_text == "builtin" and not is_builtin_provider_id(provider_id):
            return {
                "ok": False,
                "provider": provider_id,
                "has_api_key": True,
                "set_active_text": False,
                "error": f"仅内置 id 可设 kind=builtin: {provider_id}",
            }
        entry_kind = kind_text

    defaults = KNOWN_PROVIDERS.get(provider_id) or {}
    base = (api_base or "").strip() or str(existing.get("api_base") or "").strip()
    if not base:
        base = defaults.get("api_base") or ""

    if entry_kind == "user" and not base:
        return {
            "ok": False,
            "provider": provider_id,
            "has_api_key": True,
            "set_active_text": False,
            "error": "用户账号需要 --api-base",
        }

    model = (text_model or "").strip() or defaults.get("text_model") or ""
    from agent_auth_resolve import normalize_llm_model

    model = normalize_llm_model(model) or ""
    image = (image_model or "").strip() or str(existing.get("image_model") or "").strip()

    entry = dict(existing)
    entry["api_key"] = key
    entry["kind"] = entry_kind
    if base:
        entry["api_base"] = base
    if model:
        entry["text_model"] = model
    if image:
        entry["image_model"] = image
    label_text = (label or "").strip()
    if label_text:
        entry["label"] = label_text

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
    label_out = str(entry.get("label") or "").strip() or None
    return {
        "ok": True,
        "provider": provider_id,
        "kind": entry_kind,
        "has_api_key": True,
        "set_active_text": active,
        "api_base": base or None,
        "text_model": model or None,
        "image_model": image or None,
        "label": label_out,
        "error": None,
    }


def list_provider_accounts(
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """List provider_accounts without exposing raw api_key."""
    cfg = _load_config(config_path)
    accounts = _accounts_map(cfg)
    items = [
        _sanitize_account_public(pid, entry)
        for pid, entry in sorted(accounts.items())
    ]
    return {"ok": True, "accounts": items, "error": None}


def remove_provider_account(
    *,
    provider: str,
    i_confirm: bool = False,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Remove provider_accounts entry after reference guard."""
    provider_id = str(provider or "").strip().lower()
    if not provider_id:
        return {"ok": False, "provider": None, "error": "缺少 --provider"}
    if not i_confirm:
        return {
            "ok": False,
            "provider": provider_id,
            "error": "需要用户确认后带 --i-confirm 才能删除",
        }

    cfg = _load_config(config_path)
    accounts = _accounts_map(cfg)
    if provider_id not in accounts:
        return {
            "ok": False,
            "provider": provider_id,
            "error": f"账号不存在: {provider_id}",
        }

    refs = _provider_referenced(cfg, provider_id)
    if refs:
        return {
            "ok": False,
            "provider": provider_id,
            "error": f"仍被引用（{', '.join(refs)}），请先改绑后再删除",
        }

    del accounts[provider_id]
    cfg["provider_accounts"] = accounts
    _save_config(cfg, config_path)
    return {"ok": True, "provider": provider_id, "error": None}
