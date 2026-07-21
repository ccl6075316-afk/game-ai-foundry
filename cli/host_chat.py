"""Brief Tab host-chat — progressive draft while chatting; freeze on 落实/export.

Sessions live at plans/conversations/brief/<session_id>.json.
Context: summary + recent messages; compress when over character budget.
"""

from __future__ import annotations

import copy
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
    apply_deterministic_brief_fixes,
    audit_brief_for_export,
    character_clip_names,
    characters_requiring_animation_graph,
    finalize_brief_export,
    parse_animation_graphs,
    validate_brief_for_export,
)
from llm_config import resolve_host_api_settings
from llm_json import LlmJsonError, parse_llm_json_object
from prompt_craft import PromptCraftError, chat_text_completion
from shared_context import asset_to_dict, project_to_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOST_CHAT_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "host-chat.md"
_COMMIT_BRIEF_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "commit-brief.md"
_ANIM_GRAPH_SKILL = (
    _REPO_ROOT / "resources" / "skills" / "orchestrator" / "brief-animation-graphs.md"
)
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
_COMMIT_DOC_RE = re.compile(
    r"(整理成.{0,12}(文档|markdown|md|设计说明|方案书|纪要)|"
    r"写成.{0,12}(文档|markdown|md|设计说明)|"
    r"输出.{0,8}(文档|说明|纪要)|"
    r"commit\s*doc|save\s*(as\s*)?(doc|markdown))",
    re.IGNORECASE,
)
_COMMIT_DOC_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "commit-doc.md"


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
        "draft_document": None,
        "ready_to_export": False,
        "gaps": [],
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
        draft = data.get("draft_brief") if isinstance(data.get("draft_brief"), dict) else {}
        project = draft.get("project") if isinstance(draft.get("project"), dict) else {}
        if project.get("title"):
            title = str(project["title"])[:36]
        else:
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
                "has_draft": bool(draft),
                "updated_at": data.get("updated_at") or "",
            }
        )
    return out


def deep_merge_brief(
    base: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge incoming draft onto base. Lists (assets/graphs) replaced when provided."""
    if not incoming:
        return copy.deepcopy(base) if isinstance(base, dict) else None
    if not isinstance(base, dict) or not base:
        return copy.deepcopy(incoming)

    out = copy.deepcopy(base)
    for key, value in incoming.items():
        if value is None:
            continue
        if key in ("assets", "animation_graphs") and isinstance(value, list):
            out[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = copy.deepcopy(out[key])
            for sk, sv in value.items():
                if sv is None:
                    continue
                if isinstance(sv, dict) and isinstance(merged.get(sk), dict):
                    nested = copy.deepcopy(merged[sk])
                    nested.update(sv)
                    merged[sk] = nested
                else:
                    merged[sk] = copy.deepcopy(sv)
            out[key] = merged
        else:
            out[key] = copy.deepcopy(value)
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
    try:
        return parse_llm_json_object(text, soft_prose_fallback=True)
    except LlmJsonError as exc:
        raise HostChatError(str(exc)) from exc


def user_requests_commit_brief(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    return bool(_COMMIT_BRIEF_RE.search(text.strip()))


def user_requests_commit_doc(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    # Prefer brief freeze when both patterns could match.
    if user_requests_commit_brief(text):
        return False
    return bool(_COMMIT_DOC_RE.search(text.strip()))


def resolve_mode(session: dict[str, Any], user_message: str | None) -> str:
    pending = session.get("pending_mode")
    if pending == "commit_brief":
        return "commit_brief"
    if pending == "commit_doc":
        return "commit_doc"
    if session.get("mode") == "commit_brief" and session.get("draft_brief"):
        if user_message and user_requests_commit_brief(user_message):
            return "commit_brief"
        if user_message and re.search(r"(继续落实|改一下 brief|更新 brief|导出)", user_message, re.I):
            return "commit_brief"
    if session.get("mode") == "commit_doc" and session.get("draft_document"):
        if user_message and user_requests_commit_doc(user_message):
            return "commit_doc"
        if user_message and re.search(r"(继续整理|改一下文档|更新文档|保存文档)", user_message, re.I):
            return "commit_doc"
    if user_requests_commit_brief(user_message):
        return "commit_brief"
    if user_requests_commit_doc(user_message):
        return "commit_doc"
    if session.get("intent_hint") == "commit_brief" and user_message:
        if re.search(r"^(好|行|可以|确认|嗯|ok|yes|落实)", user_message.strip(), re.I):
            return "commit_brief"
    if session.get("intent_hint") == "commit_doc" and user_message:
        if re.search(r"^(好|行|可以|确认|嗯|ok|yes|整理)", user_message.strip(), re.I):
            return "commit_doc"
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


def _animation_graphs_skill_block() -> str:
    """Always inject clip-name contract for chat / commit_brief (autofix uses chat)."""
    body = _load_skill(
        _ANIM_GRAPH_SKILL,
        "animation_graphs: use Godot clip names from assets (suffix after character_), "
        "never states[], never asset full names in from/to/then.",
    )
    return f"\n\n---\n\n{body}\n"


def _system_prompt(mode: str) -> str:
    if mode == "commit_brief":
        skill = _load_skill(
            _COMMIT_BRIEF_SKILL,
            "Commit the conversation into a Foundry brief. Output JSON only.",
        )
        return (
            f"{skill}"
            f"{_animation_graphs_skill_block()}"
            f"## Example brief\n\n```json\n{_example_brief_snippet()}\n```\n\n"
            "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
        )
    if mode == "commit_doc":
        skill = _load_skill(
            _COMMIT_DOC_SKILL,
            "Commit the conversation into a markdown document. Output JSON only.",
        )
        return (
            f"{skill}\n\n"
            "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
        )
    skill = _load_skill(
        _HOST_CHAT_SKILL,
        "You are a Brief creation chat assistant. Output JSON only. "
        "When discussing a game, emit progressive draft_brief; ready_to_export false until freeze.",
    )
    return (
        f"{skill}"
        f"{_animation_graphs_skill_block()}"
        "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
    )


def _build_user_payload(session: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "commit_brief":
        instruction = (
            "Synthesize/refine draft_brief from the full conversation and current_draft_brief. "
            "Fill reasonable defaults. Set ready_to_export only if contract-complete."
        )
    elif mode == "commit_doc":
        instruction = (
            "Synthesize a complete markdown document from the conversation and current_draft_document. "
            "Put full body in artifact.body. ready_to_export true when content is savable."
        )
    else:
        instruction = (
            "Continue chatting. When the user discusses a game, output a FULL current "
            "draft_brief in artifact (expand/correct prior draft). "
            "When drafting a design note (not Foundry brief), you may also set "
            "artifact.draft_document {title, format, body}. ready_to_export must be false. "
            "Pure tech Q&A with no game design: artifact may be null."
        )
    payload: dict[str, Any] = {
        "mode": mode,
        "conversation": session.get("messages") or [],
        "instruction": instruction,
    }
    summary = str(session.get("summary") or "").strip()
    if summary:
        payload["conversation_summary"] = summary
        payload["summary_note"] = "Earlier turns were compressed; summary is not a frozen brief."
    if session.get("draft_brief"):
        payload["current_draft_brief"] = session.get("draft_brief")
    if session.get("draft_document"):
        payload["current_draft_document"] = session.get("draft_document")
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


def _normalize_document(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    body = str(raw.get("body") or "").strip()
    title = str(raw.get("title") or "").strip() or "未命名文档"
    if not body and not raw.get("title"):
        return None
    return {
        "title": title,
        "format": str(raw.get("format") or "markdown").strip() or "markdown",
        "body": body,
    }


def _extract_document(parsed: dict[str, Any]) -> dict[str, Any] | None:
    artifact = parsed.get("artifact")
    if isinstance(artifact, dict):
        if artifact.get("kind") == "document" or artifact.get("body"):
            doc = _normalize_document(
                {
                    "title": artifact.get("title"),
                    "format": artifact.get("format"),
                    "body": artifact.get("body"),
                }
            )
            if doc:
                return doc
        nested = artifact.get("draft_document")
        doc = _normalize_document(nested if isinstance(nested, dict) else None)
        if doc:
            return doc
    return _normalize_document(
        parsed.get("draft_document") if isinstance(parsed.get("draft_document"), dict) else None
    )


def _extract_gaps(parsed: dict[str, Any]) -> list[str]:
    raw = parsed.get("gaps")
    if not isinstance(raw, list):
        return []
    return [str(g).strip() for g in raw if str(g).strip()][:20]


def _call_llm(
    session: dict[str, Any],
    mode: str,
    config: dict[str, Any],
    *,
    instance_id: str | None = None,
) -> dict[str, Any]:
    system = _system_prompt(mode)
    user_text = json.dumps(_build_user_payload(session, mode), ensure_ascii=False, indent=2)

    raw: str | None = None
    backend = "host"
    try:
        from pi_runtime import (
            PiRuntimeError,
            resolve_brief_executor,
            run_pi_brief_turn_with_tools,
        )

        if resolve_brief_executor(config) == "pi":
            allow_export = mode == "commit_brief" and bool(session.get("ready_to_export"))
            try:
                sid = str(session.get("id") or "brief")
                # Persist mid-turn so export/status tools can read the session file.
                try:
                    save_session(session_path_for_id(sid), session)
                except (HostChatError, OSError):
                    pass
                raw = run_pi_brief_turn_with_tools(
                    system_prompt=system,
                    user_text=user_text,
                    session_id=sid,
                    config=config,
                    allow_export=allow_export,
                    timeout_sec=240.0,
                    instance_id=instance_id,
                )
                backend = "pi"
                session.pop("_brief_llm_pi_error", None)
            except PiRuntimeError as exc:
                # One Pi attempt only — fall back to Host (avoid double paid calls).
                session["_brief_llm_pi_error"] = str(exc)[:500]
                raw = None
                backend = "host"
    except ImportError:
        raw = None
        backend = "host"

    if raw is None:
        api = resolve_host_api_settings(config)
        if not api.get("api_key"):
            raise HostChatError(
                "Brief LLM unavailable: configure API key (OpenRouter/host) "
                "or embed Pi (`node scripts/prepare_embedded_pi.mjs`)."
            )
        try:
            raw = chat_text_completion(
                model=str(api["model"]),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ],
                api_key=str(api["api_key"]),
                api_base=str(api["api_base"]),
                proxy=api.get("proxy"),
                timeout=180,
            )
            backend = "host"
        except PromptCraftError as exc:
            raise HostChatError(str(exc)) from exc

    session["_brief_llm_backend"] = backend
    parsed = _parse_llm_json(raw)
    note = str(parsed.get("notes_for_host") or "")
    if note.startswith("recovered") and isinstance(raw, str):
        try:
            dump = _CONV_DIR / "_last_llm_raw.txt"
            dump.parent.mkdir(parents=True, exist_ok=True)
            dump.write_text(raw[:200_000], encoding="utf-8")
        except OSError:
            pass
    return parsed


def _infer_choices_from_message(text: str, *, max_n: int = 6) -> list[str]:
    """If LLM forgot JSON choices, recover option lines from assistant prose."""
    line_re = re.compile(
        r"^(?:[-*•]|\d+[.)、]|[A-Da-d][.)、]|选项\s*[A-Da-d\d])\s*(.+)$"
    )
    found: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = line_re.match(line)
        if not m:
            continue
        opt = m.group(1).strip().strip("*").rstrip("。；;")
        if len(opt) < 2 or len(opt) > 80:
            continue
        if opt not in found:
            found.append(opt)
        if len(found) >= max_n:
            break
    return found if len(found) >= 2 else []


def _apply_parsed(session: dict[str, Any], parsed: dict[str, Any], mode: str) -> dict[str, Any]:
    assistant_message = str(parsed.get("assistant_message", "")).strip()
    if not assistant_message:
        # Prefer keeping the turn alive over hard-failing the GUI.
        note = str(parsed.get("notes_for_host") or "").strip()
        assistant_message = (
            "（模型没有返回可读回复，草稿未改动。请再发一句，或说「再整理一遍」。）"
            + (f"\n\n_{note}_" if note else "")
        )

    choices = parsed.get("choices") or []
    if not isinstance(choices, list):
        choices = []
    choices = [str(c).strip() for c in choices if str(c).strip()][:6]
    if not choices:
        # Recover A/B/1/2 style lines from prose so GUI can render chips
        choices = _infer_choices_from_message(assistant_message)

    intent = str(parsed.get("intent_hint") or "none").strip() or "none"
    ready = bool(parsed.get("ready_to_export"))
    gaps = _extract_gaps(parsed)
    incoming = _extract_draft(parsed)
    incoming_doc = _extract_document(parsed)

    if mode == "chat":
        ready = False
        if incoming:
            session["draft_brief"] = deep_merge_brief(
                session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
                incoming,
            )
        if incoming_doc:
            session["draft_document"] = incoming_doc
        session["mode"] = "chat"
        if intent == "commit_brief":
            session["pending_mode"] = "commit_brief"
        elif intent == "commit_doc":
            session["pending_mode"] = "commit_doc"
        else:
            session["pending_mode"] = None
    elif mode == "commit_doc":
        if incoming_doc is None:
            ready = False
            assistant_message += "\n\n（整理文档轮未返回正文，请再说要写入文档的要点。）"
        else:
            session["draft_document"] = incoming_doc
            if ready and not incoming_doc.get("body"):
                ready = False
                assistant_message += "\n\n（文档正文为空，我们继续补全。）"
        session["mode"] = "commit_doc"
        session["pending_mode"] = None
    else:
        if incoming is None:
            ready = False
            assistant_message += "\n\n（落实轮未返回 draft_brief，请再说明要冻结的玩法要点。）"
        else:
            merged = deep_merge_brief(
                session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
                incoming,
            )
            draft = merged or incoming
            if ready:
                try:
                    draft = validate_brief_dict(draft)
                except (HostChatError, ValueError) as exc:
                    ready = False
                    assistant_message += f"\n\n（草案尚未完整：{exc}，我们继续补几项。）"
            session["draft_brief"] = draft
            session["mode"] = "commit_brief"
        if incoming_doc:
            session["draft_document"] = incoming_doc
        session["pending_mode"] = None

    # Prefer live audit of the merged draft over LLM-reported gaps (which go stale).
    live_gaps = _audit_draft_gaps(
        session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None
    )
    if live_gaps:
        session["gaps"] = live_gaps
    elif gaps:
        session["gaps"] = gaps
    elif mode in ("chat", "commit_brief", "commit_doc"):
        session["gaps"] = []

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
        "draft_document": session.get("draft_document"),
        "ready_to_export": ready,
        "gaps": session.get("gaps") or [],
        "message_count": len(messages),
        "session_id": session.get("id"),
        "compressed_count": int(session.get("compressed_count") or 0),
        "llm_backend": session.get("_brief_llm_backend"),
        "llm_pi_error": session.get("_brief_llm_pi_error"),
    }


def run_turn(
    session: dict[str, Any],
    *,
    user_message: str | None,
    config: dict[str, Any],
    instance_id: str | None = None,
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
        parsed = _call_llm(session, "commit_brief", config, instance_id=instance_id)
        return _apply_parsed(session, parsed, "commit_brief")
    if mode == "commit_doc":
        parsed = _call_llm(session, "commit_doc", config, instance_id=instance_id)
        return _apply_parsed(session, parsed, "commit_doc")

    parsed = _call_llm(session, "chat", config, instance_id=instance_id)
    intent = str(parsed.get("intent_hint") or "none").strip()
    if intent in ("commit_brief", "commit_doc"):
        ack = str(parsed.get("assistant_message", "")).strip()
        incoming = _extract_draft(parsed)
        if incoming:
            session["draft_brief"] = deep_merge_brief(
                session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
                incoming,
            )
        incoming_doc = _extract_document(parsed)
        if incoming_doc:
            session["draft_document"] = incoming_doc
        if ack:
            msgs = list(session.get("messages") or [])
            msgs.append({"role": "assistant", "content": ack})
            session["messages"] = msgs
        session["pending_mode"] = intent
        session["intent_hint"] = intent
        follow = "commit_brief" if intent == "commit_brief" else "commit_doc"
        parsed = _call_llm(session, follow, config, instance_id=instance_id)
        return _apply_parsed(session, parsed, follow)

    return _apply_parsed(session, parsed, "chat")


def export_brief(session: dict[str, Any]) -> dict[str, Any]:
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief in session. Chat about the game first, then 落实成 brief.")
    if not session.get("ready_to_export"):
        raise HostChatError(
            "Brief 尚未 ready_to_export。请先落实（契约完整）后再导出，或在 GUI 等「保存 Brief」可点时导出。"
        )
    return finalize_brief_export(draft, source="host-chat")


DEFAULT_AUTOFIX_MAX_ROUNDS = 5


def _clip_map_for_draft(draft: dict[str, Any] | None) -> dict[str, list[str]]:
    """character_asset → known Godot clip names (for autofix hints)."""
    if not isinstance(draft, dict):
        return {}
    try:
        assets_raw = draft.get("assets") or []
        assets = [AssetSpec.from_dict(item) for item in assets_raw if isinstance(item, dict)]
    except (ValueError, KeyError, TypeError):
        return {}

    out: dict[str, list[str]] = {}
    chars = set(characters_requiring_animation_graph(assets))
    # Also include any graph character even if not "required"
    for g in draft.get("animation_graphs") or []:
        if isinstance(g, dict) and g.get("character_asset"):
            chars.add(str(g["character_asset"]).strip())
    for char in sorted(chars):
        if not char:
            continue
        out[char] = sorted(character_clip_names(assets, char).keys())
    return out


def _asset_clip_lines(draft: dict[str, Any] | None) -> list[str]:
    """Human table: asset.name → Godot clip (what graphs must use)."""
    if not isinstance(draft, dict):
        return []
    lines: list[str] = []
    try:
        assets = [
            AssetSpec.from_dict(item)
            for item in (draft.get("assets") or [])
            if isinstance(item, dict)
        ]
    except (ValueError, KeyError, TypeError):
        return []
    for char in sorted(characters_requiring_animation_graph(assets)):
        clips = character_clip_names(assets, char)
        lines.append(f"角色 {char}:")
        for clip, spec in sorted(clips.items(), key=lambda kv: kv[0]):
            lines.append(f"  - assets.name={spec.name!r} → clip={clip!r}")
    return lines


def build_autofix_user_message(gaps: list[str], draft: dict[str, Any] | None) -> str:
    """Structured prompt so the model reads validator gaps without the user pasting them."""
    lines = [
        "【自动修 brief】下面是宿主对当前 draft_brief 的校验错误。"
        "请修正并输出完整的 artifact.draft_brief（在上一版上改，不要只给碎片）。"
        "ready_to_export 必须为 false。",
        "",
        "硬约束：",
        "- Foundry brief 没有 states[]；禁止输出 states / states[].id / states[].clip。",
        "- animation_graphs 的 from/to/then/default_clip 只能用下面「资产→clip」表里的 clip 列，"
        "不要用资产全名、不要用中文状态 id、不要自创 clip。",
        "- 例：资产 球员_普通_跑动 的 clip 是「跑动」，transition 必须写 to:\"跑动\" 而不是 \"球员_普通_跑动\"。",
        "- one-shot（animation_loop:false）作为 to 时必须有 then（通常指向 idle）。",
        "- 缺动画就补 assets[]（video + reference_asset）；有资产但图写错名就改 transitions。",
        "- 每个 usage=ui_element 必须在 project.hud[] 有一条 "
        '{"asset":"<同名>","anchor":"top_left|…","description":"…"}；'
        "必须写进 artifact.draft_brief.project.hud，不能只口头说改了。",
        "",
        "校验错误：",
    ]
    for i, g in enumerate(gaps, 1):
        lines.append(f"{i}. {g}")
    asset_lines = _asset_clip_lines(draft)
    if asset_lines:
        lines.append("")
        lines.append("资产 → Godot clip（from/to/then/default_clip 只能用 clip 列）：")
        lines.extend(asset_lines)
    clip_map = _clip_map_for_draft(draft)
    if clip_map:
        lines.append("")
        lines.append("各角色合法 clip 集合：")
        for char, clips in clip_map.items():
            lines.append(f"- {char}: {', '.join(clips) if clips else '（无）'}")
    lines.append("")
    lines.append("请直接改草稿并简短说明改了什么。")
    return "\n".join(lines)


def _apply_code_autofix(session: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Deterministic graph repair. Returns (gaps_before, gaps_after, notes)."""
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        return [], [], []
    gaps_before = _audit_draft_gaps(draft)
    fixed, notes = apply_deterministic_brief_fixes(draft)
    session["draft_brief"] = fixed
    gaps_after = _audit_draft_gaps(fixed)
    session["gaps"] = gaps_after
    return gaps_before, gaps_after, notes


def _autofix_success_payload(
    session: dict[str, Any],
    *,
    rounds_run: int,
    max_rounds: int,
    rounds: list[dict[str, Any]],
    assistant_message: str | None = None,
) -> dict[str, Any]:
    session["ready_to_export"] = True
    try:
        session["draft_brief"] = validate_brief_dict(session["draft_brief"])
    except (HostChatError, ValueError):
        session["ready_to_export"] = False
    out: dict[str, Any] = {
        "ok": True,
        "reason": "contract_complete",
        "rounds_run": rounds_run,
        "max_rounds": max_rounds,
        "gaps": [],
        "rounds": rounds,
        "draft_brief": session.get("draft_brief"),
        "ready_to_export": bool(session.get("ready_to_export")),
        "session_id": session.get("id"),
        "message_count": len(session.get("messages") or []),
    }
    if assistant_message:
        out["assistant_message"] = assistant_message
    return out


def run_autofix(
    session: dict[str, Any],
    *,
    config: dict[str, Any],
    max_rounds: int = DEFAULT_AUTOFIX_MAX_ROUNDS,
) -> dict[str, Any]:
    """Loop: deterministic graph fix → audit → LLM only if still broken."""
    if max_rounds < 1:
        raise HostChatError("max_rounds must be >= 1")
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief yet. Chat about the game first, then run autofix.")

    rounds: list[dict[str, Any]] = []
    prev_sig: tuple[str, ...] | None = None
    stuck_hits = 0

    # Round 0: code repairs clip mismatches (LLM often can't map 跑动 ↔ asset names).
    gaps_b, gaps_a, notes = _apply_code_autofix(session)
    if notes or gaps_a != gaps_b:
        rounds.append(
            {
                "round": 0,
                "kind": "deterministic",
                "gaps_before": gaps_b,
                "gaps_after": gaps_a,
                "notes": notes,
                "assistant_message": (
                    "代码已自动修补 brief（animation_graphs / project.hud 等）"
                    + (f"：{'; '.join(notes[:6])}" if notes else "。")
                ),
                "gap_count_before": len(gaps_b),
                "gap_count_after": len(gaps_a),
            }
        )
    if not gaps_a:
        return _autofix_success_payload(
            session,
            rounds_run=0,
            max_rounds=max_rounds,
            rounds=rounds,
            assistant_message=rounds[-1]["assistant_message"] if rounds else "草稿已通过校验。",
        )

    for round_i in range(1, max_rounds + 1):
        # Re-run code fix each round (LLM may reintroduce remappable wrong names).
        gaps_b, gaps_a, notes = _apply_code_autofix(session)
        if notes and gaps_a != gaps_b:
            rounds.append(
                {
                    "round": round_i,
                    "kind": "deterministic",
                    "gaps_before": gaps_b,
                    "gaps_after": gaps_a,
                    "notes": notes,
                    "assistant_message": "代码再次对齐 clip：" + "; ".join(notes[:8]),
                    "gap_count_before": len(gaps_b),
                    "gap_count_after": len(gaps_a),
                }
            )
        gaps = gaps_a
        session["gaps"] = gaps
        if not gaps:
            return _autofix_success_payload(
                session,
                rounds_run=round_i,
                max_rounds=max_rounds,
                rounds=rounds,
                assistant_message="校验已通过（代码修复）。",
            )

        sig = tuple(gaps)
        if sig == prev_sig:
            stuck_hits += 1
            if stuck_hits >= 2:
                return {
                    "ok": False,
                    "reason": "stuck",
                    "rounds_run": round_i - 1,
                    "max_rounds": max_rounds,
                    "gaps": gaps,
                    "rounds": rounds,
                    "draft_brief": session.get("draft_brief"),
                    "ready_to_export": False,
                    "session_id": session.get("id"),
                    "message_count": len(session.get("messages") or []),
                    "assistant_message": (
                        f"自动修 brief 连续 {stuck_hits} 轮错误未变化，已停止。"
                        "请人工改设定，或提高上限后再试。"
                    ),
                }
        else:
            stuck_hits = 0
        prev_sig = sig

        user_msg = build_autofix_user_message(
            gaps,
            session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
        )
        turn = run_turn(session, user_message=user_msg, config=config)
        gaps_after = _audit_draft_gaps(
            session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None
        )
        session["gaps"] = gaps_after
        rounds.append(
            {
                "round": round_i,
                "kind": "llm",
                "gaps_before": gaps,
                "gaps_after": gaps_after,
                "assistant_message": turn.get("assistant_message"),
                "gap_count_before": len(gaps),
                "gap_count_after": len(gaps_after),
            }
        )
        if not gaps_after:
            return _autofix_success_payload(
                session,
                rounds_run=round_i,
                max_rounds=max_rounds,
                rounds=rounds,
                assistant_message=turn.get("assistant_message"),
            )

    gaps = _audit_draft_gaps(
        session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None
    )
    session["gaps"] = gaps
    return {
        "ok": False,
        "reason": "max_rounds",
        "rounds_run": max_rounds,
        "max_rounds": max_rounds,
        "gaps": gaps,
        "rounds": rounds,
        "draft_brief": session.get("draft_brief"),
        "ready_to_export": False,
        "session_id": session.get("id"),
        "message_count": len(session.get("messages") or []),
        "assistant_message": (
            f"已跑满 {max_rounds} 轮自动修 brief，仍有 {len(gaps)} 条校验错误。"
            "可再点一次或提高 --max-rounds。"
        ),
    }


def _audit_draft_gaps(draft: dict[str, Any] | None) -> list[str]:
    """Live gaps from current draft — authoritative for status / after each merge."""
    if not isinstance(draft, dict) or not draft:
        return []
    try:
        project = ProjectContext.from_dict(draft.get("project") or {})
        assets_raw = draft.get("assets") or []
        assets = [AssetSpec.from_dict(item) for item in assets_raw if isinstance(item, dict)]
        graphs = parse_animation_graphs(draft)
        return audit_brief_for_export(project, assets, animation_graphs=graphs)
    except (ValueError, KeyError, TypeError) as exc:
        return [str(exc)]


def session_status(session: dict[str, Any]) -> dict[str, Any]:
    draft = session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else {}
    assets_raw = (draft or {}).get("assets") or []
    project_raw = (draft or {}).get("project") or {}
    # Always re-audit the current draft. Stale session["gaps"] from an older LLM
    # turn must not keep showing after the user already fixed the brief.
    gaps = _audit_draft_gaps(draft if draft else None)
    session["gaps"] = gaps

    genre = project_raw.get("genre") if isinstance(project_raw, dict) else None
    gameplay = project_raw.get("gameplay_loop") if isinstance(project_raw, dict) else None
    asset_summaries: list[dict[str, str]] = []
    if isinstance(assets_raw, list):
        for item in assets_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            asset_summaries.append(
                {
                    "name": name,
                    "type": str(item.get("type") or ""),
                    "usage": str(item.get("usage") or ""),
                }
            )

    doc = session.get("draft_document") if isinstance(session.get("draft_document"), dict) else None
    doc_title = str((doc or {}).get("title") or "") if doc else ""

    return {
        "id": session.get("id"),
        "exists": True,
        "mode": session.get("mode") or "chat",
        "intent_hint": session.get("intent_hint") or "none",
        "ready_to_export": bool(session.get("ready_to_export")),
        "llm_backend": session.get("_brief_llm_backend") or None,
        "message_count": len(session.get("messages") or []),
        "title": (project_raw.get("title") if isinstance(project_raw, dict) else None) or "",
        "genre": genre or "",
        "gameplay_loop": gameplay or "",
        "asset_count": len(assets_raw) if isinstance(assets_raw, list) else 0,
        "assets": asset_summaries,
        "draft_brief": draft or None,
        "draft_document": doc,
        "document_title": doc_title,
        "has_document": bool(doc and (doc.get("body") or doc.get("title"))),
        "last_choices": session.get("last_choices") or [],
        "gaps": gaps,
        "contract_complete": bool(draft) and not gaps,
        "has_summary": bool(str(session.get("summary") or "").strip()),
        "compressed_count": int(session.get("compressed_count") or 0),
    }
