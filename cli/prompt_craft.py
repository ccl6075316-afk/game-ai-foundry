"""LLM prompt crafting for the prompt-crafter role.

Reads prompt-crafter skills only. Receives the same shared context as the
orchestrator (project + asset), not orchestrator skills.
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests

from proxy_utils import http_post
from roles import PROMPT_CRAFTER_ROLE
from skill_loader import load_role_skill, load_role_skills

DEFAULT_PROMPT_MODEL = "google/gemini-2.5-flash"


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

    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content or not str(content).strip():
        raise PromptCraftError("Prompt LLM returned empty content")
    return str(content).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
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
        raise PromptCraftError(f"Could not parse LLM JSON: {exc}\nRaw: {text[:500]}") from exc
    if not isinstance(parsed, dict):
        raise PromptCraftError("LLM JSON root must be an object")
    return parsed


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


def _system_prompt_visual_target() -> str:
    base = load_role_skills(PROMPT_CRAFTER_ROLE)
    vt = load_role_skill(PROMPT_CRAFTER_ROLE, "visual-target")
    return (
        f"You are the **{PROMPT_CRAFTER_ROLE}** in Game AI Foundry. "
        "Craft a full-screen predicted gameplay screenshot prompt (Visual Target / north star).\n\n"
        f"{base}\n\n---\n\n{vt}\n\n"
        'Respond with ONLY valid JSON, no markdown fences:\n'
        '{"prompt": "<generation prompt>"}\n\n'
        "Craft visually specific English prompts under 120 words."
    )


def craft_visual_target_prompt(
    *,
    context: dict[str, Any],
    model: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
) -> dict[str, str]:
    """prompt-crafter: LLM writes a Visual Target (full-screen mock) prompt."""
    user = {
        "role": PROMPT_CRAFTER_ROLE,
        "task": "Craft a visual_target full-screen gameplay screenshot prompt.",
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
    )
    parsed = _parse_json_object(raw)
    prompt = str(parsed.get("prompt", "")).strip()
    if not prompt:
        raise PromptCraftError("LLM JSON missing non-empty 'prompt' field")
    return {"prompt": prompt}
