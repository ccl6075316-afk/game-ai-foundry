"""Upsert agents.executors presets (IT toolbox)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from provider_upsert import KNOWN_PROVIDERS, _load_config, _save_config

KNOWN_EXECUTORS = ("pi", "hermes", "codex", "cursor")


def upsert_agent_executor(
    *,
    executor: str,
    provider: str | None = None,
    model: str | None = None,
    use_third_party: bool | None = None,
    i_confirm: bool = False,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Write agents.executors[executor]. Never stores api keys."""
    exec_id = str(executor or "").strip().lower()
    if exec_id not in KNOWN_EXECUTORS:
        return {
            "ok": False,
            "executor": exec_id or None,
            "error": f"未知 executor: {exec_id}（支持: {', '.join(KNOWN_EXECUTORS)}）",
        }
    if not i_confirm:
        return {
            "ok": False,
            "executor": exec_id,
            "error": "需要用户确认后带 --i-confirm 才能写入",
        }

    provider_id = str(provider or "").strip().lower() or None
    if provider_id and provider_id not in KNOWN_PROVIDERS:
        return {
            "ok": False,
            "executor": exec_id,
            "error": f"未知 provider id: {provider_id}",
        }

    cfg = _load_config(config_path)
    agents = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    executors = agents.get("executors") if isinstance(agents.get("executors"), dict) else {}
    entry = dict(executors.get(exec_id) if isinstance(executors.get(exec_id), dict) else {})

    if provider_id:
        entry["provider"] = provider_id
    if model is not None:
        text = str(model).strip()
        if text:
            entry["model"] = text
        elif "model" in entry:
            del entry["model"]
    if exec_id == "codex" and use_third_party is not None:
        entry["use_third_party"] = bool(use_third_party)
    elif exec_id != "codex":
        entry.pop("use_third_party", None)

    executors = {**executors, exec_id: entry}
    agents = {**agents, "executors": executors}
    cfg["agents"] = agents
    _save_config(cfg, config_path)

    return {
        "ok": True,
        "executor": exec_id,
        "provider": entry.get("provider"),
        "model": entry.get("model"),
        "use_third_party": entry.get("use_third_party") if exec_id == "codex" else False,
        "error": None,
    }
