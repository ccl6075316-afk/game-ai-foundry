"""Pure resolution of agent provider / model / auth from config dict."""

from __future__ import annotations

from typing import Any

# GUI role_kind → agents config block key
ROLE_KIND_TO_AGENT_KEY: dict[str, str] = {
    "brief": "brief",
    "it": "it",
    "product_host": "orchestrator",
    "programmer": "godot-developer",
}

_PROVIDER_ENV_KEYS: dict[str, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

_DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "openai/gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
}

_OVERLAY_FIELDS = ("executor", "provider", "model", "use_third_party", "role_kind")


def _key_usable(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and "YOUR_" not in text.upper()


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _account_model(acc: dict[str, Any]) -> str | None:
    for field in ("text_model", "textModel", "model"):
        raw = acc.get(field)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def merge_instance_overlay(role_block: dict[str, Any], instance: dict[str, Any] | None) -> dict[str, Any]:
    """Merge instance fields onto role defaults (instance wins when key present)."""
    merged = dict(role_block)
    if not instance:
        return merged
    for key in _OVERLAY_FIELDS:
        if key in instance and instance[key] is not None:
            merged[key] = instance[key]
    return merged


def _provider_env_key(provider_id: str) -> str:
    return _PROVIDER_ENV_KEYS.get(provider_id, "OPENAI_API_KEY")


def _default_model(provider_id: str) -> str | None:
    return _DEFAULT_MODELS.get(provider_id)


def _lookup_credentials(
    config: dict[str, Any],
    provider_id: str,
) -> tuple[str | None, str | None, str | None]:
    """Return (api_key, api_base, account_model) for a provider id."""
    accounts = config.get("provider_accounts") if isinstance(config.get("provider_accounts"), dict) else {}
    acc = accounts.get(provider_id) if isinstance(accounts.get(provider_id), dict) else {}
    host = config.get("host") if isinstance(config.get("host"), dict) else {}
    host_provider = str(host.get("provider") or "").strip().lower()
    host_is_this = host_provider == provider_id

    api_key: str | None = None
    if _key_usable(acc.get("api_key")):
        api_key = str(acc["api_key"]).strip()
    elif host_is_this and _key_usable(host.get("api_key")):
        api_key = str(host["api_key"]).strip()

    api_base: str | None = None
    if isinstance(acc.get("api_base"), str) and acc["api_base"].strip():
        api_base = acc["api_base"].strip()
    elif host_is_this and isinstance(host.get("api_base"), str) and str(host["api_base"]).strip():
        api_base = str(host["api_base"]).strip()

    account_model = _account_model(acc) if acc else None
    if not account_model and host_is_this and isinstance(host.get("model"), str) and host["model"].strip():
        account_model = str(host["model"]).strip()

    return api_key, api_base, account_model


def _resolve_provider_source(
    *,
    instance: dict[str, Any] | None,
    role_block: dict[str, Any],
    used_host: bool,
) -> str | None:
    if instance and _normalize_str(instance.get("provider")):
        return "instance"
    if _normalize_str(role_block.get("provider")):
        return "role"
    if used_host:
        return "host"
    return None


def resolve_agent_auth(
    config: dict[str, Any],
    *,
    role_kind: str,
    instance_id: str | None = None,
) -> dict[str, Any]:
    """Resolve executor / provider / model / credentials for a role instance.

    Priority: ``agents.instances[id]`` → role block → ``host`` text fallback.
    """
    agent_key = ROLE_KIND_TO_AGENT_KEY.get(role_kind)
    if not agent_key:
        return {
            "provider": None,
            "model": None,
            "api_key": None,
            "env_key": None,
            "api_base": None,
            "executor": None,
            "use_third_party": False,
            "source": None,
            "role_kind": role_kind,
            "instance_id": instance_id,
            "error": f"Unsupported role_kind: {role_kind}",
        }

    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    role_block = agents.get(agent_key) if isinstance(agents.get(agent_key), dict) else {}

    instance: dict[str, Any] | None = None
    if instance_id:
        instances = agents.get("instances") if isinstance(agents.get("instances"), dict) else {}
        raw = instances.get(instance_id)
        if isinstance(raw, dict):
            instance = raw

    merged = merge_instance_overlay(role_block, instance)

    executor = _normalize_str(merged.get("executor"))
    use_third_party = bool(merged.get("use_third_party", False))

    provider = _normalize_str(merged.get("provider"))
    if provider:
        provider = provider.lower()

    model = _normalize_str(merged.get("model"))

    host = config.get("host") if isinstance(config.get("host"), dict) else {}
    used_host = False
    if not provider:
        host_provider = _normalize_str(host.get("provider"))
        if host_provider:
            provider = host_provider.lower()
            used_host = True
        if not model:
            model = _normalize_str(host.get("model"))

    source = _resolve_provider_source(instance=instance, role_block=role_block, used_host=used_host)

    api_key: str | None = None
    api_base: str | None = None
    env_key: str | None = None
    error: str | None = None

    if provider:
        api_key, api_base, account_model = _lookup_credentials(config, provider)
        env_key = _provider_env_key(provider)
        if not model:
            model = account_model or _default_model(provider)
    else:
        error = "未配置 Provider（实例 / 工种 / 生文均未指定）"

    if provider and not api_key:
        error = f"未找到可用 API Key（provider_accounts.{provider} 或 host）"

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "env_key": env_key,
        "api_base": api_base,
        "executor": executor,
        "use_third_party": use_third_party,
        "source": source,
        "role_kind": role_kind,
        "instance_id": instance_id,
        "error": error,
    }
