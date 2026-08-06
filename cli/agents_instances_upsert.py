"""Upsert agents.instances[id] fields (IT toolbox — NL config for colleagues)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pi_runtime import normalize_thinking_level
from provider_upsert import BUILTIN_PROVIDERS, _load_config, _save_config

_KNOWN_ROLE_KINDS = frozenset({"brief", "it", "advisor", "product_host", "programmer"})
_KNOWN_EXECUTORS = frozenset({"pi", "hermes", "codex", "cursor"})
_IT_EXECUTORS = frozenset({"pi", "codex", "cursor"})
_PI_LOCKED = frozenset({"brief", "advisor"})


def upsert_agent_instance(
    *,
    instance_id: str,
    provider: str | None = None,
    model: str | None = None,
    thinking_level: str | None = None,
    executor: str | None = None,
    use_third_party: bool | None = None,
    i_confirm: bool = False,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Patch ``agents.instances[instance_id]``. Never stores API keys."""
    iid = str(instance_id or "").strip()
    if not iid:
        return {"ok": False, "instance_id": None, "error": "缺少 --instance-id"}
    if not i_confirm:
        return {
            "ok": False,
            "instance_id": iid,
            "error": "需要用户确认后带 --i-confirm 才能写入",
        }

    provider_id = str(provider or "").strip().lower() or None
    if provider_id and provider_id not in BUILTIN_PROVIDERS:
        return {
            "ok": False,
            "instance_id": iid,
            "error": f"未知 provider id: {provider_id}（仅支持内置: {', '.join(BUILTIN_PROVIDERS)}）",
        }

    exec_id = str(executor or "").strip().lower() or None
    if exec_id and exec_id not in _KNOWN_EXECUTORS:
        return {
            "ok": False,
            "instance_id": iid,
            "error": f"未知 executor: {exec_id}（支持: {', '.join(sorted(_KNOWN_EXECUTORS))}）",
        }

    cfg = _load_config(config_path)
    agents = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    instances = agents.get("instances") if isinstance(agents.get("instances"), dict) else {}
    existing = instances.get(iid)
    if not isinstance(existing, dict):
        return {
            "ok": False,
            "instance_id": iid,
            "error": f"实例不存在: {iid}（请先在 GUI 花名册使用该同事，或雇人创建）",
        }

    entry = dict(existing)
    role = str(entry.get("role_kind") or "").strip()
    if role and role not in _KNOWN_ROLE_KINDS:
        return {
            "ok": False,
            "instance_id": iid,
            "error": f"实例 role_kind 无效: {role}",
        }

    if exec_id:
        if role in _PI_LOCKED and exec_id != "pi":
            return {
                "ok": False,
                "instance_id": iid,
                "error": f"策划固定使用内置 Pi，不能改成 {exec_id}",
            }
        if role == "it" and exec_id not in _IT_EXECUTORS:
            return {
                "ok": False,
                "instance_id": iid,
                "error": "IT 不支持 Hermes；请选择 pi、codex 或 cursor",
            }
        entry["executor"] = exec_id

    if provider_id:
        entry["provider"] = provider_id
    if model is not None:
        text = str(model).strip()
        if text:
            from agent_auth_resolve import normalize_llm_model

            entry["model"] = normalize_llm_model(text) or text
        else:
            entry.pop("model", None)

    if thinking_level is not None:
        level = normalize_thinking_level(thinking_level)
        # normalize maps unknown → off; accept only explicit four levels from CLI choice
        raw = str(thinking_level).strip().lower()
        if raw not in ("off", "low", "medium", "high"):
            return {
                "ok": False,
                "instance_id": iid,
                "error": "thinking_level 须为 off|low|medium|high",
            }
        entry["thinking_level"] = level

    if use_third_party is not None and str(entry.get("executor") or exec_id or "") == "codex":
        entry["use_third_party"] = bool(use_third_party)

    instances = {**instances, iid: entry}
    agents = {**agents, "instances": instances}
    cfg["agents"] = agents
    _save_config(cfg, config_path)

    return {
        "ok": True,
        "instance_id": iid,
        "role_kind": entry.get("role_kind"),
        "executor": entry.get("executor"),
        "provider": entry.get("provider"),
        "model": entry.get("model"),
        "thinking_level": entry.get("thinking_level"),
        "use_third_party": entry.get("use_third_party"),
        "error": None,
    }
