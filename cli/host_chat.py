"""Brief Tab host-chat — chat by default; commit-brief only on explicit 落实.

Sessions live at plans/conversations/brief/<session_id>.json.
Context: summary + recent messages; compress when over character budget.
"""

from __future__ import annotations

import json
import re
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
from prompt_craft import PromptCraftError, chat_text_completion
from shared_context import asset_to_dict, project_to_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOST_CHAT_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "host-chat.md"
_COMMIT_BRIEF_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "commit-brief.md"
_EXAMPLE_BRIEF = _REPO_ROOT / "resources" / "asset-brief.example.json"
_CONV_DIR = _REPO_ROOT / "plans" / "conversations" / "brief"

# Context budget (characters of conversation payload, not tokens).
_CHAR_BUDGET = 14_000
_RECENT_KEEP = 20

_COMMIT_BRIEF_RE = re.compile(
    r"(落实\s*(成)?\s*brief|写成\s*brief|导出\s*brief|定稿|生成\s*brief|"
    r"可以开项目|按这个开项目|开始做这个游戏|freeze\s*brief|commit\s*brief)",
    re.IGNORECASE,
)


class HostChatError(RuntimeError):
    """Raised when host-chat session or LLM step fails."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def conversations_dir() -> Path:
    return _CONV_DIR


def sanitize_session_id(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HostChatError("session_id is required.")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", s).strip("-")
    if not cleaned or cleaned in {".", ".."}:
        raise HostChatError(f"Invalid session_id: {raw!r}")
    return cleaned[:80]


def session_path_for_id(session_id: str, *, base_dir: Path | None = None) -> Path:
    sid = sanitize_session_id(session_id)
    root = base_dir or _CONV_DIR
    return root / f"{sid}.json"


def new_session(session_id: str | None = None) -> dict[str, Any]:
    sid = sanitize_session_id(session_id) if session_id else uuid.uuid4().hex[:12]
    now = _utc_now()
    return {
        "id": sid,
        "role": "brief",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "last_choices": [],
        "mode": "chat",
        "pending_mode": None,
        "intent_hint": "none",
        "summary": "",
        "draft_brief": None,
        "ready_to_export": False,
        "compressed_count": 0,
    }


def load_session(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise HostChatError(f"Session not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HostChatError("Session file must be a JSON object.")
    return data


def save_session(path: Path, session: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = _utc_now()
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_sessions(*, base_dir: Path | None = None) -> list[dict[str, Any]]:
    root = base_dir or _CONV_DIR
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        msgs = data.get("messages") or []
        title = ""
        for m in msgs:
            if isinstance(m, dict) and m.get("role") == "user":
                title = str(m.get("content") or "")[:36]
                break
        out.append(
            {
                "id": data.get("id") or path.stem,
                "path": str(path),
                "title": title or path.stem,
                "message_count": len(msgs) if isinstance(msgs, list) else 0,
                "ready_to_export": bool(data.get("ready_to_export")),
                "updated_at": data.get("updated_at") or "",
            }
        )
    return out


def _load_skill(path: Path, fallback: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return fallback


def _example_brief_snippet() -> str:
    if not _EXAMPLE_BRIEF.is_file():
        return "{}"
    data = json.loads(_EXAMPLE_BRIEF.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2)[:2500]


def _parse_llm_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HostChatError(f"Could not parse LLM JSON: {exc}\nRaw: {text[:500]}") from exc
    if not isinstance(parsed, dict):
        raise HostChatError("LLM JSON root must be an object.")
    return parsed


def user_requests_commit_brief(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    return bool(_COMMIT_BRIEF_RE.search(text.strip()))


def resolve_mode(session: dict[str, Any], user_message: str | None) -> str:
    pending = session.get("pending_mode")
    if pending == "commit_brief":
        return "commit_brief"
    if session.get("mode") == "commit_brief" and session.get("draft_brief"):
        # Stay in commit mode while refining an existing draft unless user clearly chats.
        if user_message and user_requests_commit_brief(user_message):
            return "commit_brief"
        if user_message and re.search(r"(继续落实|改一下 brief|更新 brief|导出)", user_message, re.I):
            return "commit_brief"
    if user_requests_commit_brief(user_message):
        return "commit_brief"
    if session.get("intent_hint") == "commit_brief" and user_message:
        # Previous turn signaled commit; this turn executes it if user confirms-ish.
        if re.search(r"^(好|行|可以|确认|嗯|ok|yes|落实)", user_message.strip(), re.I):
            return "commit_brief"
    return "chat"


def _messages_char_len(messages: list[dict[str, Any]], summary: str) -> int:
    n = len(summary or "")
    for m in messages:
        if isinstance(m, dict):
            n += len(str(m.get("content") or ""))
    return n


def _compress_prompt(existing_summary: str, old_messages: list[dict[str, Any]]) -> str:
    return (
        "你是对话摘要器。将下列「较早对话」压成一段中文摘要，供后续 Brief 创建助手使用。\n"
        "规则：\n"
        "- 保留已拍板设定、用户明确否定的选项、待定点、偏好。\n"
        "- 丢掉客套与重复脑暴。\n"
        "- 标明这些尚未落实为 brief，不是契约。\n"
        "- 只输出摘要正文，不要 JSON。\n\n"
        f"已有摘要：\n{existing_summary or '（无）'}\n\n"
        f"较早对话：\n{json.dumps(old_messages, ensure_ascii=False, indent=2)}"
    )


def maybe_compress_session(session: dict[str, Any], config: dict[str, Any]) -> bool:
    """If over budget, summarize older messages and keep recent ones. Returns True if compressed."""
    messages = list(session.get("messages") or [])
    summary = str(session.get("summary") or "")
    if _messages_char_len(messages, summary) <= _CHAR_BUDGET:
        return False
    if len(messages) <= _RECENT_KEEP:
        return False

    old = messages[: -_RECENT_KEEP]
    recent = messages[-_RECENT_KEEP :]
    api = resolve_host_api_settings(config)
    if not api.get("api_key"):
        # Fallback: hard trim without LLM summary.
        session["summary"] = (summary + "\n" if summary else "") + (
            f"（已截断较早 {len(old)} 条消息，摘要失败：无 API Key）"
        )
        session["messages"] = recent
        session["compressed_count"] = int(session.get("compressed_count") or 0) + len(old)
        return True

    try:
        raw = chat_text_completion(
            model=str(api["model"]),
            messages=[
                {"role": "system", "content": "You compress chat history. Reply with plain summary text only."},
                {"role": "user", "content": _compress_prompt(summary, old)},
            ],
            api_key=str(api["api_key"]),
            api_base=str(api["api_base"]),
            proxy=api.get("proxy"),
            timeout=90,
        )
        new_summary = (raw or "").strip()
        if not new_summary:
            raise HostChatError("empty compression")
        session["summary"] = new_summary
        session["messages"] = recent
        session["compressed_count"] = int(session.get("compressed_count") or 0) + len(old)
        return True
    except (HostChatError, PromptCraftError, OSError, ValueError):
        session["summary"] = (summary + "\n" if summary else "") + (
            f"（已截断较早 {len(old)} 条消息；自动摘要失败，仅保留近 {_RECENT_KEEP} 条原文）"
        )
        session["messages"] = recent
        session["compressed_count"] = int(session.get("compressed_count") or 0) + len(old)
        return True


def _system_prompt(mode: str) -> str:
    if mode == "commit_brief":
        skill = _load_skill(
            _COMMIT_BRIEF_SKILL,
            "Commit the conversation into a Foundry brief. Output JSON only.",
        )
        return (
            f"{skill}\n\n"
            f"## Example brief\n\n```json\n{_example_brief_snippet()}\n```\n\n"
            "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
        )
    skill = _load_skill(
        _HOST_CHAT_SKILL,
        "You are a Brief creation chat assistant. Output JSON only. Do not emit draft_brief.",
    )
    return (
        f"{skill}\n\n"
        "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
    )


def _build_user_payload(session: dict[str, Any], mode: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": mode,
        "conversation": session.get("messages") or [],
        "instruction": (
            "Synthesize draft_brief from the full conversation. Fill reasonable defaults."
            if mode == "commit_brief"
            else "Continue chatting. Do not output draft_brief. artifact must be null."
        ),
    }
    summary = str(session.get("summary") or "").strip()
    if summary:
        payload["conversation_summary"] = summary
        payload["summary_note"] = "Earlier turns were compressed; summary is not a frozen brief."
    if mode == "commit_brief" and session.get("draft_brief"):
        payload["current_draft_brief"] = session.get("draft_brief")
    return payload


def validate_brief_dict(data: dict[str, Any]) -> dict[str, Any]:
    project = ProjectContext.from_dict(data.get("project", {}))
    assets_raw = data.get("assets") or []
    if not assets_raw:
        raise HostChatError("Brief must contain at least one asset.")
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


def _extract_draft(parsed: dict[str, Any]) -> dict[str, Any] | None:
    artifact = parsed.get("artifact")
    if isinstance(artifact, dict):
        draft = artifact.get("draft_brief")
        if isinstance(draft, dict):
            return draft
    draft = parsed.get("draft_brief")
    if isinstance(draft, dict):
        return draft
    return None


def _call_llm(session: dict[str, Any], mode: str, config: dict[str, Any]) -> dict[str, Any]:
    api = resolve_host_api_settings(config)
    if not api.get("api_key"):
        raise HostChatError(
            "Host LLM API key missing. Configure config.host in ~/.gamefactory/config.json."
        )

    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt(mode)},
        {
            "role": "user",
            "content": json.dumps(_build_user_payload(session, mode), ensure_ascii=False, indent=2),
        },
    ]
    raw = chat_text_completion(
        model=str(api["model"]),
        messages=llm_messages,
        api_key=str(api["api_key"]),
        api_base=str(api["api_base"]),
        proxy=api.get("proxy"),
        timeout=120,
    )
    return _parse_llm_json(raw)


def _apply_parsed(session: dict[str, Any], parsed: dict[str, Any], mode: str) -> dict[str, Any]:
    assistant_message = str(parsed.get("assistant_message", "")).strip()
    if not assistant_message:
        raise HostChatError("LLM returned empty assistant_message.")

    choices = parsed.get("choices") or []
    if not isinstance(choices, list):
        choices = []
    choices = [str(c).strip() for c in choices if str(c).strip()][:6]

    intent = str(parsed.get("intent_hint") or "none").strip() or "none"
    ready = bool(parsed.get("ready_to_export"))
    draft: dict[str, Any] | None = None

    if mode == "chat":
        ready = False
        if intent == "commit_doc":
            assistant_message += "\n\n（commit_doc 尚未接线；请改说「落实成 brief」，或稍后再整理文档。）"
            intent = "none"
        session["mode"] = "chat"
        session["pending_mode"] = "commit_brief" if intent == "commit_brief" else None
    else:
        draft = _extract_draft(parsed)
        if draft is None:
            ready = False
            assistant_message += "\n\n（落实轮未返回 draft_brief，请再说明要冻结的玩法要点。）"
        else:
            if ready:
                try:
                    draft = validate_brief_dict(draft)
                except (HostChatError, ValueError) as exc:
                    ready = False
                    assistant_message += f"\n\n（草案尚未完整：{exc}，我们继续补几项。）"
            session["draft_brief"] = draft
            session["mode"] = "commit_brief"
        session["pending_mode"] = None

    messages = list(session.get("messages") or [])
    messages.append({"role": "assistant", "content": assistant_message})
    session["messages"] = messages
    session["last_choices"] = choices
    session["intent_hint"] = intent
    session["ready_to_export"] = ready

    return {
        "assistant_message": assistant_message,
        "choices": choices,
        "mode": session.get("mode") or mode,
        "intent_hint": intent,
        "draft_brief": session.get("draft_brief"),
        "ready_to_export": ready,
        "message_count": len(messages),
        "session_id": session.get("id"),
        "compressed_count": int(session.get("compressed_count") or 0),
    }


def run_turn(
    session: dict[str, Any],
    *,
    user_message: str | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Append user message, optionally compress, call host LLM (chat or commit)."""
    messages: list[dict[str, Any]] = list(session.get("messages") or [])
    if user_message and user_message.strip():
        messages.append({"role": "user", "content": user_message.strip()})
    elif not messages:
        messages.append({"role": "user", "content": "你好，想先随便聊聊游戏想法。"})
    session["messages"] = messages

    maybe_compress_session(session, config)

    mode = resolve_mode(session, user_message)
    if mode == "commit_brief":
        parsed = _call_llm(session, "commit_brief", config)
        return _apply_parsed(session, parsed, "commit_brief")

    parsed = _call_llm(session, "chat", config)
    intent = str(parsed.get("intent_hint") or "none").strip()
    if intent == "commit_brief":
        ack = str(parsed.get("assistant_message", "")).strip()
        if ack:
            msgs = list(session.get("messages") or [])
            msgs.append({"role": "assistant", "content": ack})
            session["messages"] = msgs
        session["pending_mode"] = "commit_brief"
        session["intent_hint"] = "commit_brief"
        parsed = _call_llm(session, "commit_brief", config)
        return _apply_parsed(session, parsed, "commit_brief")

    return _apply_parsed(session, parsed, "chat")


def export_brief(session: dict[str, Any]) -> dict[str, Any]:
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief in session. Ask to 落实成 brief first.")
    if not session.get("ready_to_export"):
        # Still allow export attempt; finalize will validate.
        pass
    return finalize_brief_export(draft, source="host-chat")


def session_status(session: dict[str, Any]) -> dict[str, Any]:
    draft = session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else {}
    assets_raw = (draft or {}).get("assets") or []
    project_raw = (draft or {}).get("project") or {}
    gaps: list[str] = []
    if draft:
        try:
            project = ProjectContext.from_dict(project_raw)
            assets = [AssetSpec.from_dict(item) for item in assets_raw if isinstance(item, dict)]
            graphs = parse_animation_graphs(draft)
            gaps = audit_brief_for_export(project, assets, animation_graphs=graphs)
        except (ValueError, KeyError) as exc:
            gaps = [str(exc)]

    return {
        "id": session.get("id"),
        "exists": True,
        "mode": session.get("mode") or "chat",
        "intent_hint": session.get("intent_hint") or "none",
        "ready_to_export": bool(session.get("ready_to_export")),
        "message_count": len(session.get("messages") or []),
        "title": (project_raw.get("title") if isinstance(project_raw, dict) else None) or "",
        "asset_count": len(assets_raw) if isinstance(assets_raw, list) else 0,
        "last_choices": session.get("last_choices") or [],
        "gaps": gaps,
        "contract_complete": bool(draft) and not gaps,
        "has_summary": bool(str(session.get("summary") or "").strip()),
        "compressed_count": int(session.get("compressed_count") or 0),
    }
