"""Topic multi-persona brainstorm for host-chat brief sessions (generate then apply)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from host_chat import (
    HostChatError,
    _parse_llm_json,
    _utc_now,
    apply_draft_replacement,
)
from llm_config import resolve_host_api_settings
from prompt_craft import PromptCraftError, chat_text_completion

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PERSONA_SKILL = (
    _REPO_ROOT / "resources" / "skills" / "orchestrator" / "topic-brainstorm-persona.md"
)

DEFAULT_PERSONAS = (
    "systems",
    "ui_presentation",
    "feel_feedback",
    "devil_advocate",
)


def _load_persona_skill() -> str:
    if _PERSONA_SKILL.is_file():
        return _PERSONA_SKILL.read_text(encoding="utf-8")
    return (
        "You are a brainstorm persona. Reply JSON only: "
        '{"title":"...","bullets":["..."]}.'
    )


def _persona_system(role: str) -> str:
    return f"{_load_persona_skill()}\n\nYour role id for this call is: {role}."


def _one_persona_proposal(
    *,
    role: str,
    topic: str,
    constraints: str | None,
    draft: dict[str, Any],
    api: dict[str, Any],
    temperature: float,
    model: str | None = None,
) -> dict[str, Any]:
    use_model = str(model or api["model"])
    payload = {
        "role": role,
        "topic": topic,
        "constraints": constraints or "",
        "draft_brief": draft,
    }
    try:
        raw = chat_text_completion(
            model=use_model,
            messages=[
                {"role": "system", "content": _persona_system(role)},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, indent=2),
                },
            ],
            api_key=str(api["api_key"]),
            api_base=str(api["api_base"]),
            proxy=api.get("proxy"),
            timeout=180,
            temperature=temperature,
        )
    except PromptCraftError as exc:
        raise HostChatError(f"Brainstorm persona {role} failed: {exc}") from exc

    parsed = _parse_llm_json(raw or "")
    title = str(parsed.get("title") or "").strip() or f"{role} proposal"
    bullets_raw = parsed.get("bullets")
    bullets: list[str] = []
    if isinstance(bullets_raw, list):
        for b in bullets_raw:
            s = str(b).strip()
            if s:
                bullets.append(s)
    if not bullets:
        bullets = [title]
    return {
        "role": role,
        "title": title,
        "bullets": bullets,
        "model": use_model if model else None,
    }


def _extra_models_from_config(config: dict[str, Any]) -> list[str]:
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    extra = agents.get("brainstorm_models")
    if isinstance(extra, list):
        return [str(m).strip() for m in extra if str(m).strip()]
    return []


def run_topic_brainstorm(
    session: dict[str, Any],
    topic: str,
    *,
    constraints: str | None = None,
    multi_model: bool = False,
    temperature: float = 0.85,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parallel persona proposals; writes brainstorm_result only (not draft)."""
    topic_s = str(topic or "").strip()
    if not topic_s:
        raise HostChatError("Brainstorm requires a non-empty --topic.")

    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief yet. Chat about the game first, then brainstorm.")

    cfg = config or {}
    api = resolve_host_api_settings(cfg)
    if not api.get("api_key"):
        raise HostChatError("Brainstorm unavailable: configure API key (OpenRouter/host).")

    mode = "personas"
    jobs: list[tuple[str, str | None]] = [(role, None) for role in DEFAULT_PERSONAS]
    if multi_model:
        extras = _extra_models_from_config(cfg)
        if extras:
            mode = "personas+models"
            for i, model in enumerate(extras[:4]):
                role = DEFAULT_PERSONAS[i % len(DEFAULT_PERSONAS)]
                jobs.append((f"{role}__m{i}", model))

    proposals: list[dict[str, Any]] = []
    errors: list[str] = []

    def _run(job: tuple[str, str | None]) -> dict[str, Any]:
        role_key, model = job
        base_role = role_key.split("__", 1)[0]
        return _one_persona_proposal(
            role=base_role,
            topic=topic_s,
            constraints=constraints,
            draft=draft,
            api=api,
            temperature=temperature,
            model=model,
        )

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(jobs)))) as pool:
        futures = {pool.submit(_run, job): job for job in jobs}
        for fut in as_completed(futures):
            job = futures[fut]
            try:
                proposals.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{job[0]}: {exc}")

    if len(proposals) < 3:
        detail = "; ".join(errors) if errors else "unknown"
        raise HostChatError(
            f"Brainstorm produced fewer than 3 proposals ({len(proposals)}). {detail}"
        )

    proposals.sort(key=lambda p: (str(p.get("role") or ""), str(p.get("title") or "")))
    for i, prop in enumerate(proposals, start=1):
        prop["id"] = f"p{i}"

    result = {
        "topic": topic_s,
        "constraints": constraints or "",
        "mode": mode,
        "created_at": _utc_now(),
        "proposals": proposals,
        "errors": errors,
    }
    session["brainstorm_result"] = result

    titles = "；".join(f"{p['id']} {p['title']}" for p in proposals[:6])
    assistant_message = (
        f"议题头脑风暴完成（{mode}）：{len(proposals)} 个方案。{titles}。"
        "请选用方案后执行 brainstorm-apply。"
    )
    if multi_model and mode == "personas":
        assistant_message += " （未配置 agents.brainstorm_models，已降级为多角色。）"

    return {
        "ok": True,
        "brainstorm_result": result,
        "proposal_count": len(proposals),
        "mode": mode,
        "assistant_message": assistant_message,
        "session_id": session.get("id"),
    }


def _apply_system() -> str:
    return (
        "You merge selected brainstorm proposals into draft_brief. "
        "Return JSON only: "
        '{"draft_brief": {...}, "asset_proposals": [...], "summary": "..."}. '
        "Thicken player-visible presentation for the topic; list needed parameter names "
        "without requiring fixed schema keys; propose related assets. "
        "Keep existing project intent; do not invent unrelated systems."
    )


def apply_brainstorm_proposals(
    session: dict[str, Any],
    proposal_ids: list[str],
    *,
    fuse: bool = False,
    temperature: float = 0.7,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply selected proposals into draft_brief via LLM merge + DraftMergeGuard."""
    ids = [str(x).strip() for x in proposal_ids if str(x).strip()]
    if not ids:
        raise HostChatError("brainstorm-apply requires at least one --proposal-id.")

    stored = session.get("brainstorm_result")
    if not isinstance(stored, dict) or not isinstance(stored.get("proposals"), list):
        raise HostChatError("No brainstorm_result on session. Run brainstorm first.")

    by_id = {
        str(p.get("id")): p
        for p in stored["proposals"]
        if isinstance(p, dict) and p.get("id")
    }
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise HostChatError(f"Unknown proposal id(s): {', '.join(missing)}")

    selected = [by_id[i] for i in ids]
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief in session.")

    cfg = config or {}
    api = resolve_host_api_settings(cfg)
    if not api.get("api_key"):
        raise HostChatError("Brainstorm apply unavailable: configure API key.")

    user_payload = {
        "fuse": bool(fuse),
        "topic": stored.get("topic"),
        "selected_proposals": selected,
        "draft_brief": draft,
    }
    try:
        raw = chat_text_completion(
            model=str(api["model"]),
            messages=[
                {"role": "system", "content": _apply_system()},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                },
            ],
            api_key=str(api["api_key"]),
            api_base=str(api["api_base"]),
            proxy=api.get("proxy"),
            timeout=180,
            temperature=temperature,
        )
    except PromptCraftError as exc:
        raise HostChatError(str(exc)) from exc

    parsed = _parse_llm_json(raw or "")
    candidate = parsed.get("draft_brief")
    if not isinstance(candidate, dict):
        raise HostChatError("Brainstorm apply LLM did not return draft_brief object.")
    proposals_raw = parsed.get("asset_proposals")
    asset_proposals = (
        [p for p in proposals_raw if isinstance(p, dict)]
        if isinstance(proposals_raw, list)
        else []
    )
    summary = str(parsed.get("summary") or "").strip() or "已采用头脑风暴方案并写回 draft。"

    merge = apply_draft_replacement(session, candidate, asset_proposals=asset_proposals)
    return {
        "ok": True,
        "summary": summary,
        "assistant_message": summary,
        "fingerprint": merge.get("fingerprint"),
        "asset_count": merge.get("asset_count"),
        "applied_ids": ids,
        "fuse": bool(fuse),
        "ready_to_export": bool(session.get("ready_to_export")),
        "session_id": session.get("id"),
    }
