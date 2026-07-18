"""Multi-turn brief brainstorming — orchestrator-style requirement refinement."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brief import (
    AssetSpec,
    ProjectContext,
    animation_graph_to_dict,
    audit_brief_for_export,
    finalize_brief_export,
    parse_animation_graphs,
    validate_brief_for_export,
)
from llm_config import resolve_host_api_settings
from llm_json import LlmJsonError, parse_llm_json_object
from prompt_craft import PromptCraftError, chat_text_completion
from shared_context import asset_to_dict, project_to_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILL_PATH = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "brief-brainstorm.md"
_EXAMPLE_BRIEF = _REPO_ROOT / "resources" / "asset-brief.example.json"


class BriefBrainstormError(RuntimeError):
    """Raised when brainstorm session or LLM step fails."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_skill() -> str:
    if _SKILL_PATH.is_file():
        return _SKILL_PATH.read_text(encoding="utf-8")
    return "You are a game brief brainstorming assistant. Output JSON only."


def _example_brief_snippet() -> str:
    if not _EXAMPLE_BRIEF.is_file():
        return "{}"
    data = json.loads(_EXAMPLE_BRIEF.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2)[:2500]


def new_session() -> dict[str, Any]:
    draft: dict[str, Any] = {"project": {}, "assets": []}
    return {
        "id": uuid.uuid4().hex[:12],
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "messages": [],
        "last_choices": [],
        "draft_brief": draft,
        "ready_to_export": False,
    }


def load_session(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BriefBrainstormError(f"Session not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise BriefBrainstormError("Session file must be a JSON object.")
    return data


def save_session(path: Path, session: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = _utc_now()
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_llm_json(text: str) -> dict[str, Any]:
    try:
        return parse_llm_json_object(text, soft_prose_fallback=True)
    except LlmJsonError as exc:
        raise BriefBrainstormError(str(exc)) from exc


def _merge_draft(existing: dict[str, Any], incoming: dict[str, Any] | None) -> dict[str, Any]:
    if not incoming or not isinstance(incoming, dict):
        return existing
    out = {
        "project": dict(existing.get("project") or {}),
        "assets": list(existing.get("assets") or []),
    }
    proj = incoming.get("project")
    if isinstance(proj, dict):
        out["project"].update({k: v for k, v in proj.items() if v not in (None, "")})
    assets = incoming.get("assets")
    if isinstance(assets, list):
        by_name = {str(a.get("name")): a for a in out["assets"] if isinstance(a, dict) and a.get("name")}
        for item in assets:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            name = str(item["name"])
            merged = {**by_name.get(name, {}), **item}
            by_name[name] = merged
        out["assets"] = list(by_name.values())
    return out


def validate_brief_dict(data: dict[str, Any]) -> dict[str, Any]:
    project = ProjectContext.from_dict(data.get("project", {}))
    assets_raw = data.get("assets") or []
    if not assets_raw:
        raise BriefBrainstormError("Brief must contain at least one asset.")
    assets = [AssetSpec.from_dict(item) for item in assets_raw]
    graphs = parse_animation_graphs(data)
    validate_brief_for_export(project, assets, animation_graphs=graphs)
    out: dict[str, Any] = {
        "project": project_to_dict(project),
        "assets": [asset_to_dict(a) for a in assets],
    }
    if graphs:
        out["animation_graphs"] = [animation_graph_to_dict(g) for g in graphs]
    return out


def _system_prompt() -> str:
    return (
        f"{_load_skill()}\n\n"
        f"## Example brief\n\n```json\n{_example_brief_snippet()}\n```\n\n"
        "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
    )


def run_turn(
    session: dict[str, Any],
    *,
    user_message: str | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Append user message (if any), call host LLM, update session draft."""
    api = resolve_host_api_settings(config)
    if not api.get("api_key"):
        raise BriefBrainstormError(
            "Host LLM API key missing. Configure config.host in ~/.gamefactory/config.json."
        )

    messages: list[dict[str, str]] = list(session.get("messages") or [])
    if user_message and user_message.strip():
        messages.append({"role": "user", "content": user_message.strip()})
    elif not messages:
        messages.append({"role": "user", "content": "我想做一个新游戏，请帮我理清需求。"})

    llm_messages: list[dict[str, Any]] = [{"role": "system", "content": _system_prompt()}]
    draft = session.get("draft_brief") or {"project": {}, "assets": []}
    llm_messages.append(
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_draft_brief": draft,
                    "conversation": messages,
                    "instruction": "Continue brainstorming. Ask ONE next question or finalize.",
                },
                ensure_ascii=False,
                indent=2,
            ),
        }
    )

    raw = chat_text_completion(
        model=str(api["model"]),
        messages=llm_messages,
        api_key=str(api["api_key"]),
        api_base=str(api["api_base"]),
        proxy=api.get("proxy"),
        timeout=120,
    )
    parsed = _parse_llm_json(raw)

    assistant_message = str(parsed.get("assistant_message", "")).strip()
    if not assistant_message:
        raise BriefBrainstormError("LLM returned empty assistant_message.")

    choices = parsed.get("choices") or []
    if not isinstance(choices, list):
        choices = []
    choices = [str(c).strip() for c in choices if str(c).strip()][:6]

    draft_in = parsed.get("draft_brief")
    merged_draft = _merge_draft(draft, draft_in if isinstance(draft_in, dict) else None)
    ready = bool(parsed.get("ready_to_export"))

    if ready:
        try:
            merged_draft = validate_brief_dict(merged_draft)
        except (BriefBrainstormError, ValueError) as exc:
            ready = False
            assistant_message += f"\n\n（草案尚未完整：{exc}，我们继续补几项。）"

    messages.append({"role": "assistant", "content": assistant_message})
    session["messages"] = messages
    session["last_choices"] = choices
    session["draft_brief"] = merged_draft
    session["ready_to_export"] = ready

    return {
        "assistant_message": assistant_message,
        "choices": choices,
        "draft_brief": merged_draft,
        "ready_to_export": ready,
        "message_count": len(messages),
    }


def export_brief(session: dict[str, Any]) -> dict[str, Any]:
    draft = session.get("draft_brief") or {}
    return finalize_brief_export(draft, source="brainstorm")


def session_status(session: dict[str, Any]) -> dict[str, Any]:
    draft = session.get("draft_brief") or {}
    assets_raw = draft.get("assets") or []
    project_raw = draft.get("project") or {}
    gaps: list[str] = []
    try:
        project = ProjectContext.from_dict(project_raw)
        assets = [AssetSpec.from_dict(item) for item in assets_raw if isinstance(item, dict)]
        graphs = parse_animation_graphs(draft if isinstance(draft, dict) else {})
        gaps = audit_brief_for_export(project, assets, animation_graphs=graphs)
    except (ValueError, KeyError) as exc:
        gaps = [str(exc)]

    return {
        "id": session.get("id"),
        "ready_to_export": bool(session.get("ready_to_export")),
        "message_count": len(session.get("messages") or []),
        "title": project_raw.get("title") or "",
        "asset_count": len(assets_raw) if isinstance(assets_raw, list) else 0,
        "last_choices": session.get("last_choices") or [],
        "gaps": gaps,
        "contract_complete": not gaps,
    }
