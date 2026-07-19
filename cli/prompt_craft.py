"""LLM prompt crafting for the prompt-crafter role.

Reads prompt-crafter skills only. Receives the same shared context as the
orchestrator (project + asset), not orchestrator skills.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from proxy_utils import http_post
from roles import PROMPT_CRAFTER_ROLE
from skill_loader import load_role_skill, load_role_skills

DEFAULT_PROMPT_MODEL = "deepseek/deepseek-chat"


class PromptCraftError(RuntimeError):
    """Raised when LLM prompt crafting fails."""


def chat_text_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    timeout: int = 90,
) -> str:
    endpoint = api_base.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages}
    try:
        response = http_post(
            proxy,
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise PromptCraftError(f"Prompt LLM request failed: {exc}") from exc

    if response.status_code != 200:
        detail = response.text.strip()
        try:
            detail = response.json().get("error", {}).get("message", detail)
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        raise PromptCraftError(f"Prompt LLM error (HTTP {response.status_code}): {detail}")

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise PromptCraftError(f"Invalid JSON from prompt LLM: {exc}") from exc

    content = _extract_message_content(data)
    if not content or not str(content).strip():
        raise PromptCraftError("Prompt LLM returned empty content")
    return str(content).strip()


def _extract_message_content(data: dict[str, Any]) -> str:
    """Normalize OpenAI-style content (string or multipart list)."""
    choices = data.get("choices") or []
    if not choices or not isinstance(choices, list):
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        content = "".join(parts)
    if content is None or content == "":
        # Some reasoner models put visible text elsewhere
        for key in ("reasoning_content", "reasoning"):
            alt = message.get(key)
            if isinstance(alt, str) and alt.strip():
                return alt.strip()
    return str(content).strip() if content is not None else ""


def _parse_json_object(text: str) -> dict[str, Any]:
    from llm_json import LlmJsonError, parse_llm_json_object

    try:
        return parse_llm_json_object(text)
    except LlmJsonError as exc:
        raise PromptCraftError(str(exc)) from exc


def _system_prompt(kind: str) -> str:
    skills = load_role_skills(PROMPT_CRAFTER_ROLE)
    schema = '{"prompt": "<generation prompt>"'
    if kind == "animation":
        schema += ', "video_prompt": "<motion-focused video prompt>"'
    schema += "}"

    return (
        f"You are the **{PROMPT_CRAFTER_ROLE}** in Game AI Foundry. "
        "You receive shared project + asset context (same facts the orchestrator sees). "
        "You do NOT run the pipeline — you only write generation prompts.\n\n"
        f"{skills}\n\n"
        "Respond with ONLY valid JSON, no markdown fences:\n"
        f"{schema}\n\n"
        "Craft visually specific English prompts under 120 words."
    )


def craft_asset_prompt(
    *,
    context: dict[str, Any],
    model: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    kind: str = "image",
) -> dict[str, str]:
    """prompt-crafter role: LLM writes the generation prompt from shared context."""
    user = {
        "role": PROMPT_CRAFTER_ROLE,
        "task": f"Craft a {kind} generation prompt.",
        "context": context,
    }

    raw = chat_text_completion(
        model=model,
        messages=[
            {"role": "system", "content": _system_prompt(kind)},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, indent=2)},
        ],
        api_key=api_key,
        api_base=api_base,
        proxy=proxy,
    )
    parsed = _parse_json_object(raw)
    prompt = str(parsed.get("prompt", "")).strip()
    if not prompt:
        raise PromptCraftError("LLM JSON missing non-empty 'prompt' field")

    result = {"prompt": prompt}
    if kind == "animation":
        video_prompt = str(parsed.get("video_prompt", "")).strip()
        if not video_prompt:
            raise PromptCraftError(
                "Animation craft requires non-empty 'video_prompt' in LLM JSON"
            )
        result["video_prompt"] = video_prompt
    return result


VT_DEFAULT_USE_CASE = (
    "in-engine 16:9 gameplay screenshot / framebuffer capture, "
    "looks like a real game runtime frame not concept art or store key art"
)

VT_DEFAULT_CONSTRAINTS = (
    "no poster borders, no letterbox bars, no watermark, no pure-white studio background, "
    "no character isolate on white, no outer app chrome, no title card typography"
)

VT_STRUCTURED_KEYS = (
    "use_case",
    "scene",
    "hero",
    "gameplay_beat",
    "details",
    "hud",
    "style_lock",
    "constraints",
)


def assemble_visual_target_prompt(
    fields: dict[str, Any],
    *,
    extra_constraints: list[str] | None = None,
) -> str:
    """Assemble GPT-Image-style wide→narrow labeled prompt from structured fields."""
    cleaned: dict[str, str] = {}
    for key in VT_STRUCTURED_KEYS:
        val = fields.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            cleaned[key] = text

    if not cleaned.get("use_case"):
        cleaned["use_case"] = VT_DEFAULT_USE_CASE
    if not cleaned.get("constraints"):
        cleaned["constraints"] = VT_DEFAULT_CONSTRAINTS
    elif VT_DEFAULT_CONSTRAINTS.split(",")[0] not in cleaned["constraints"].lower():
        cleaned["constraints"] = f"{cleaned['constraints']}; {VT_DEFAULT_CONSTRAINTS}"

    if extra_constraints:
        extras = "; ".join(c.strip() for c in extra_constraints if c and str(c).strip())
        if extras:
            cleaned["constraints"] = f"{cleaned['constraints']}; {extras}"

    # Prefer hero+beat presence for quality; allow scaffold with fewer keys.
    if not cleaned.get("scene") and not cleaned.get("hero"):
        raise PromptCraftError(
            "Visual target assemble needs at least 'scene' or 'hero' field"
        )

    labels = [
        ("Use case", "use_case"),
        ("Scene", "scene"),
        ("Subject", "hero"),
        ("Gameplay beat", "gameplay_beat"),
        ("Important details", "details"),
        ("HUD", "hud"),
        ("Style lock", "style_lock"),
        ("Constraints", "constraints"),
    ]
    parts: list[str] = []
    for label, key in labels:
        text = cleaned.get(key)
        if not text:
            continue
        parts.append(f"{label}: {text}")
    return "\n".join(parts)


def structured_fields_from_project_scaffold(
    project: Any,
    variant: dict[str, str],
) -> dict[str, str]:
    """Rule-based structured fields when LLM craft is off."""
    dim = str(getattr(project, "dimension", None) or "2d").lower()
    player = str(getattr(project, "player_asset", None) or "player character").strip()
    art = str(getattr(project, "art_direction", None) or "").strip()
    genre = str(getattr(project, "genre", None) or "").strip()
    loop = str(getattr(project, "gameplay_loop", None) or "").strip()
    goal = str(getattr(project, "session_goal", None) or "").strip()
    desc = str(getattr(project, "description", None) or "").strip()
    title = str(getattr(project, "title", None) or "").strip()
    camera = getattr(project, "camera", None)
    cam_bits = ""
    if isinstance(camera, dict) and camera:
        mode = camera.get("mode") or camera.get("type")
        scope = camera.get("scope")
        cam_bits = ", ".join(
            str(x) for x in (mode, scope) if x
        )

    scene_bits = [
        f"{dim} game world for {title}" if title else f"{dim} game world",
        f"genre {genre}" if genre else "",
        desc[:220] if desc else "",
    ]
    details_bits = [
        cam_bits or "readable gameplay camera matching the genre",
        "clear silhouettes, cohesive lighting",
        f"variant focus: {variant.get('focus', '')}",
    ]
    beat = variant.get("focus") or loop or goal or "core gameplay action in progress"
    return {
        "use_case": VT_DEFAULT_USE_CASE,
        "scene": ". ".join(b for b in scene_bits if b),
        "hero": f"{player}, clearly readable focal character, about 15-20% of screen height",
        "gameplay_beat": str(beat),
        "details": ". ".join(b for b in details_bits if b),
        "hud": "",
        "style_lock": art or "cohesive game art style matching the brief",
        "constraints": VT_DEFAULT_CONSTRAINTS,
    }


def _system_prompt_visual_target() -> str:
    # VT-only: do NOT load asset-planner / asset-gen (white-studio rules pollute screenshots).
    vt = load_role_skill(PROMPT_CRAFTER_ROLE, "visual-target")
    schema = {
        "use_case": "in-engine 16:9 gameplay screenshot / framebuffer capture",
        "scene": "...",
        "hero": "...",
        "gameplay_beat": "...",
        "details": "...",
        "hud": "...",
        "style_lock": "...",
        "constraints": "...",
    }
    return (
        f"You are the **{PROMPT_CRAFTER_ROLE}** in Game AI Foundry. "
        "Fill structured fields for a Visual Target (north-star gameplay screenshot). "
        "Python will assemble the final image prompt — do not output a free-form `prompt` field.\n\n"
        f"{vt}\n\n"
        "Respond with ONLY valid JSON, no markdown fences, using exactly these keys:\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n"
    )


def craft_visual_target_prompt(
    *,
    context: dict[str, Any],
    model: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
) -> dict[str, Any]:
    """prompt-crafter: structured VT fields → assembled image prompt."""
    user = {
        "role": PROMPT_CRAFTER_ROLE,
        "task": (
            "Fill visual_target structured fields for a full-screen gameplay screenshot. "
            "Do not return a single prose prompt field."
        ),
        "context": context,
    }
    raw = chat_text_completion(
        model=model,
        messages=[
            {"role": "system", "content": _system_prompt_visual_target()},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, indent=2)},
        ],
        api_key=api_key,
        api_base=api_base,
        proxy=proxy,
        timeout=120,
    )
    parsed = _parse_json_object(raw)

    # Backward compat: if model still returns only {"prompt": "..."} use it.
    if parsed.get("prompt") and not any(
        parsed.get(k) for k in ("scene", "hero", "gameplay_beat")
    ):
        prompt = str(parsed.get("prompt", "")).strip()
        if not prompt:
            raise PromptCraftError("LLM JSON missing non-empty 'prompt' field")
        return {"prompt": prompt, "prompt_source": "llm_prose"}

    fields = {k: parsed.get(k) for k in VT_STRUCTURED_KEYS}
    # Soft fill from nested project if LLM omitted hero
    project = context.get("project") if isinstance(context.get("project"), dict) else {}
    if not fields.get("hero") and project.get("player_asset"):
        fields["hero"] = (
            f"{project['player_asset']}, focal player character, "
            "about 15-20% of screen height"
        )
    if not fields.get("style_lock") and project.get("art_direction"):
        fields["style_lock"] = str(project["art_direction"])

    prompt = assemble_visual_target_prompt(fields)
    return {"prompt": prompt, "prompt_source": "llm_structured", "fields": fields}
