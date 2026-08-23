"""Fetch OpenAI-compatible /models catalog for a provider account."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from provider_upsert import KNOWN_PROVIDERS, _load_config, resolve_api_key
from proxy_utils import apply_proxy_env, resolve_config_proxy

_TIMEOUT_SEC = 30.0
_SOURCE = "openai-models"
_USER_AGENT = "game-ai-foundry-toolchain/1.0"

HttpGetFn = Callable[[str, str], tuple[int, bytes]]


def resolve_api_base(provider_id: str, entry: dict[str, Any]) -> str:
    """Account api_base first, then builtin/known defaults."""
    base = str(entry.get("api_base") or "").strip()
    if base:
        return base
    defaults = KNOWN_PROVIDERS.get(provider_id) or {}
    return str(defaults.get("api_base") or "").strip()


def build_models_url(api_base: str) -> str:
    """Append ``/models`` without duplicating path segments."""
    return api_base.rstrip("/") + "/models"


def parse_openai_models_payload(data: Any) -> list[dict[str, str]]:
    """Parse OpenAI-style ``{data:[{id:...}]}`` into ``[{id,label}]``."""
    if not isinstance(data, dict):
        return []
    items = data.get("data")
    if not isinstance(items, list):
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip()
        if not mid or mid in seen:
            continue
        seen.add(mid)
        out.append({"id": mid, "label": mid})
    return out


def _default_http_get(url: str, api_key: str) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return int(exc.code), body


def _http_error_message(status: int, *, provider_id: str = "", api_base: str = "") -> str:
    if status == 401:
        hint = "检查 API Key 是否与 api_base 匹配"
        if provider_id and "apilio" in api_base.lower():
            hint += "（Apilio 需用 Apilio Key，不能用 OpenRouter Key）"
        elif provider_id:
            hint += f"（账号 {provider_id}）"
        return f"HTTP 401 未授权 — {hint}"
    if status == 403:
        return "HTTP 403 禁止访问"
    if status == 404:
        return "HTTP 404 — 该网关可能不支持 GET /models，请手填 model id"
    return f"HTTP {status}"


def _account_entry(
    cfg: dict[str, Any],
    provider_id: str,
    *,
    api_key_override: str | None = None,
    api_base_override: str | None = None,
) -> dict[str, Any]:
    accounts_raw = cfg.get("provider_accounts")
    accounts = accounts_raw if isinstance(accounts_raw, dict) else {}
    raw_entry = accounts.get(provider_id)
    entry: dict[str, Any] = dict(raw_entry) if isinstance(raw_entry, dict) else {}

    if api_key_override and str(api_key_override).strip():
        entry["api_key"] = str(api_key_override).strip()
    if api_base_override and str(api_base_override).strip():
        entry["api_base"] = str(api_base_override).strip()

    image = cfg.get("image") if isinstance(cfg.get("image"), dict) else {}
    if str(image.get("provider") or "").strip().lower() == provider_id:
        if not resolve_api_key(api_key=str(entry.get("api_key") or "")):
            legacy = str(image.get("api_key") or "").strip()
            if legacy:
                entry["api_key"] = legacy
        if not str(entry.get("api_base") or "").strip():
            legacy_base = str(image.get("api_base") or "").strip()
            if legacy_base:
                entry["api_base"] = legacy_base
    return entry


def fetch_provider_models(
    *,
    provider: str,
    config_path: Path | None = None,
    http_get: HttpGetFn | None = None,
    api_key_override: str | None = None,
    api_base_override: str | None = None,
) -> dict[str, Any]:
    """Return ``{ok, provider, models, source, error}``; never exposes api_key."""
    provider_id = str(provider or "").strip().lower()
    base: dict[str, Any] = {
        "provider": provider_id or None,
        "models": [],
        "source": _SOURCE,
        "error": None,
    }
    if not provider_id:
        return {**base, "ok": False, "error": "缺少 --provider"}

    cfg = _load_config(config_path)
    entry = _account_entry(
        cfg,
        provider_id,
        api_key_override=api_key_override,
        api_base_override=api_base_override,
    )
    if not entry and not (api_key_override or api_base_override):
        accounts_raw = cfg.get("provider_accounts")
        accounts = accounts_raw if isinstance(accounts_raw, dict) else {}
        if provider_id not in accounts:
            return {**base, "ok": False, "error": f"账号不存在: {provider_id}"}

    api_key = resolve_api_key(api_key=str(entry.get("api_key") or "") or None)
    if not api_key:
        return {**base, "ok": False, "error": f"账号缺少可用 API Key: {provider_id}"}

    api_base = resolve_api_base(provider_id, entry)
    if not api_base:
        return {**base, "ok": False, "error": f"账号缺少 api_base: {provider_id}"}

    url = build_models_url(api_base)
    getter = http_get or _default_http_get

    proxy = resolve_config_proxy(cfg)
    apply_proxy_env(proxy)

    try:
        status, body = getter(url, api_key)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        text = str(reason).strip() or "网络请求失败"
        if "timed out" in text.lower():
            text = "请求超时"
        return {**base, "ok": False, "error": text}
    except OSError as exc:
        return {**base, "ok": False, "error": str(exc).strip() or "网络请求失败"}

    if status >= 400:
        return {
            **base,
            "ok": False,
            "error": _http_error_message(status, provider_id=provider_id, api_base=api_base),
        }

    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {**base, "ok": False, "error": "响应非 JSON"}

    models = parse_openai_models_payload(payload)
    return {**base, "ok": True, "models": models, "error": None}
