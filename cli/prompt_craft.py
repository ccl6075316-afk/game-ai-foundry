"""LLM prompt crafting for the prompt-crafter role.

Reads prompt-crafter skills only. Receives the same shared context as the
orchestrator (project + asset), not orchestrator skills.
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests

from image_model_route import effective_generate_tier, resolve_image_model_for_tier
from media_prompt_profile import (
    PromptCapabilityProfile,
    apply_video_prompt_profile,
    resolve_media_prompt_profile,
)
from seedance_api import resolve_model
from video_config import resolve_video_generate_settings
from proxy_utils import http_post
from roles import PROMPT_CRAFTER_ROLE
from skill_loader import (
    load_prompt_skills_for_asset,
    load_role_skill,
    load_role_skills,
)

DEFAULT_PROMPT_MODEL = "deepseek/deepseek-v4-flash"


class PromptCraftError(RuntimeError):
    """Raised when LLM prompt crafting fails."""


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_CJK_PROSE_PUNCT_RE = re.compile(r"[。！？.!?\n]")
_SHORT_CJK_LABEL_MAX = 12

_CJK_BRIEF_BLOCK_MSG = (
    "Chinese brief text cannot be used as the final image prompt; "
    "re-run prompt craft with LLM to secondary-generate English fields"
)


def contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _cjk_ok_as_short_label(text: str) -> bool:
    """Allow short CJK name/token; reject CJK prose (long or sentence-punctuated)."""
    s = (text or "").strip()
    if not s or not contains_cjk(s):
        return True
    if _CJK_PROSE_PUNCT_RE.search(s):
        return False
    return len(_CJK_RE.findall(s)) <= _SHORT_CJK_LABEL_MAX


def _raise_if_cjk_prompt_field(text: str, *, allow_short_label: bool = False) -> None:
    if not contains_cjk(text or ""):
        return
    if allow_short_label and _cjk_ok_as_short_label(text):
        return
    raise PromptCraftError(_CJK_BRIEF_BLOCK_MSG)


def chat_text_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    timeout: int = 90,
    temperature: float | None = None,
) -> str:
    endpoint = api_base.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
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


ASSET_STRUCTURED_KEYS = (
    "subject",
    "silhouette",
    "style_lock",
    "view",
    "technical",
    "negatives",
)

VIEW_LOCK_PHRASES: dict[str, str] = {
    "side": (
        "Side view, profile facing right, readable silhouette for side-scroller gameplay"
    ),
    "top_down": (
        "Top-down view, looking straight down, clear readable shapes from above"
    ),
    "three_quarter": (
        "Three-quarter view, slightly angled, readable game asset perspective"
    ),
}

GLOBAL_ASSET_NEGATIVES = (
    "No spritesheet; no multiple action frames in one image; "
    "never transparent background or checkerboard"
)

SOFT_STYLE_ALIGNMENT = (
    "Soft style alignment with art direction; prefer cohesive look over literal copy."
)

_ASSET_LABEL_ORDER: tuple[tuple[str, str], ...] = (
    ("Subject", "subject"),
    ("Silhouette", "silhouette"),
    ("Style lock", "style_lock"),
    ("View", "view"),
    ("Technical", "technical"),
    ("Negatives", "negatives"),
)


def _merge_prompt_text(existing: str, addition: str) -> str:
    """Prepend/merge token locks so empty LLM fields cannot wipe hard locks."""
    left = str(existing or "").strip()
    right = str(addition or "").strip()
    if not right:
        return left
    if not left:
        return right
    if right.lower() in left.lower():
        return left
    return f"{right}; {left}"


def _art_tokens_dict(project: dict[str, Any] | Any) -> dict[str, Any]:
    if isinstance(project, dict):
        tokens = project.get("art_tokens")
    else:
        tokens = getattr(project, "art_tokens", None)
    return tokens if isinstance(tokens, dict) else {}


def _resolve_content_class(spec: dict[str, Any] | Any) -> str:
    if isinstance(spec, dict):
        cc = str(spec.get("content_class") or "").strip()
        atype = str(spec.get("type") or "").strip().lower()
    else:
        cc = str(getattr(spec, "content_class", None) or "").strip()
        atype = str(getattr(spec, "type", None).value if getattr(spec, "type", None) else "").strip().lower()
    if cc:
        return cc
    if atype == "texture":
        return "floor_tile"
    if atype == "background":
        return "backdrop_full"
    if atype in ("character", "character_pose", "icon_kit"):
        return "prop_static"
    return ""


def _project_view_value(project: dict[str, Any] | Any) -> str:
    if isinstance(project, dict):
        return str(project.get("view") or "").strip()
    return str(getattr(project, "view", None) or "").strip()


def _technical_defaults_for_content_class(content_class: str) -> str:
    cc = (content_class or "").strip().lower()
    if cc.endswith("_tile") or cc in ("floor_tile", "wall_tile"):
        return (
            "Seamless tileable texture filling the frame; uniform lighting; "
            "no shadows; clean tile edges; not a white studio backdrop"
        )
    if cc in (
        "prop_static",
        "prop_interactable",
        "prop_stateful",
        "weapon",
        "tool",
        "decor",
    ):
        return (
            "Pure flat white background (#FFFFFF), uniform studio backdrop; "
            "single object centered; mattable still; no environment scenery"
        )
    if cc == "backdrop_sparse":
        return (
            "Environmental background with sparse focal elements; generous empty "
            "space for gameplay props; no white studio; no character sprites; no UI"
        )
    if cc == "backdrop_full":
        return (
            "Full environmental background scene; rich atmosphere; "
            "no white studio; no character sprites; no UI"
        )
    return ""


def _merge_art_tokens_into_fields(
    fields: dict[str, str],
    art_tokens: dict[str, Any],
) -> None:
    if not art_tokens:
        return

    silhouette = art_tokens.get("silhouette")
    if isinstance(silhouette, str) and silhouette.strip():
        fields["silhouette"] = _merge_prompt_text(
            fields.get("silhouette", ""),
            f"Silhouette lock: {silhouette.strip()}",
        )

    style_parts: list[str] = []
    line = art_tokens.get("line")
    if isinstance(line, str) and line.strip():
        style_parts.append(f"Line: {line.strip()}")
    palette = art_tokens.get("palette")
    if isinstance(palette, str) and palette.strip():
        style_parts.append(f"Palette: {palette.strip()}")
    elif isinstance(palette, list):
        items = [str(item).strip() for item in palette if str(item).strip()]
        if items:
            style_parts.append("Palette: " + ", ".join(items))
    if style_parts:
        fields["style_lock"] = _merge_prompt_text(
            fields.get("style_lock", ""),
            "; ".join(style_parts),
        )

    forbid = art_tokens.get("forbid")
    if isinstance(forbid, list):
        items = [str(item).strip() for item in forbid if str(item).strip()]
        if items:
            fields["negatives"] = _merge_prompt_text(
                fields.get("negatives", ""),
                "; ".join(items),
            )


def _ensure_view_lock(fields: dict[str, str], project: dict[str, Any] | Any) -> None:
    view_key = _project_view_value(project)
    phrase = VIEW_LOCK_PHRASES.get(view_key, "")
    if phrase:
        fields["view"] = _merge_prompt_text(fields.get("view", ""), phrase)


def _ensure_technical_lock(
    fields: dict[str, str],
    spec: dict[str, Any] | Any,
) -> None:
    defaults = _technical_defaults_for_content_class(_resolve_content_class(spec))
    if defaults:
        fields["technical"] = _merge_prompt_text(fields.get("technical", ""), defaults)


def _ensure_global_negatives(fields: dict[str, str]) -> None:
    fields["negatives"] = _merge_prompt_text(
        fields.get("negatives", ""),
        GLOBAL_ASSET_NEGATIVES,
    )


def _ensure_soft_style_sentence(style_lock: str) -> str:
    if SOFT_STYLE_ALIGNMENT.lower() in style_lock.lower():
        return style_lock
    return _merge_prompt_text(style_lock, SOFT_STYLE_ALIGNMENT)


def _merge_negatives_into_style_lock(fields: dict[str, str]) -> None:
    negatives = fields.pop("negatives", "").strip()
    if not negatives:
        return
    fields["style_lock"] = _merge_prompt_text(
        fields.get("style_lock", ""),
        f"Avoid: {negatives}",
    )


def _assemble_natural_prompt(
    cleaned: dict[str, str],
    *,
    include_negatives: bool,
) -> str:
    parts: list[str] = []
    for label, key in _ASSET_LABEL_ORDER:
        if key == "negatives" and not include_negatives:
            continue
        text = cleaned.get(key)
        if not text:
            continue
        parts.append(f"{label}: {text}")
    return "\n".join(parts)


def _assemble_tags_prompt(cleaned: dict[str, str]) -> str:
    fragments: list[str] = []
    for _label, key in _ASSET_LABEL_ORDER:
        text = cleaned.get(key)
        if not text:
            continue
        fragments.append(text)
    return ", ".join(fragments)


def assemble_asset_prompt(
    fields: dict[str, Any],
    *,
    project: dict[str, Any] | Any,
    spec: dict[str, Any] | Any,
    profile: PromptCapabilityProfile | None = None,
) -> str:
    """Assemble labeled asset prompt from structured fields + forced hard locks."""
    if profile is None:
        profile = resolve_media_prompt_profile("", modality="image")

    cleaned: dict[str, str] = {}
    for key in ASSET_STRUCTURED_KEYS:
        val = fields.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            cleaned[key] = text

    _merge_art_tokens_into_fields(cleaned, _art_tokens_dict(project))
    _ensure_view_lock(cleaned, project)
    _ensure_technical_lock(cleaned, spec)
    _ensure_global_negatives(cleaned)

    if not cleaned.get("subject"):
        if isinstance(spec, dict) and spec.get("description"):
            cleaned["subject"] = str(spec["description"]).strip()
        elif getattr(spec, "description", None):
            cleaned["subject"] = str(spec.description).strip()

    if not cleaned.get("style_lock"):
        if isinstance(project, dict) and project.get("art_direction"):
            cleaned["style_lock"] = str(project["art_direction"]).strip()
        else:
            art = getattr(project, "art_direction", None)
            if art:
                cleaned["style_lock"] = str(art).strip()

    if not cleaned.get("subject") and not cleaned.get("technical"):
        raise PromptCraftError(
            "Asset assemble needs at least 'subject' or injectable technical defaults"
        )

    # Prose / style fields: any CJK blocked. Name-like locks: short CJK labels only.
    for key in ("subject", "style_lock"):
        _raise_if_cjk_prompt_field(cleaned.get(key, ""))
    for key in ("silhouette", "view", "technical", "negatives"):
        _raise_if_cjk_prompt_field(cleaned.get(key, ""), allow_short_label=True)

    if not profile.negatives_effective:
        _merge_negatives_into_style_lock(cleaned)

    if profile.prefer_soft_style and cleaned.get("style_lock"):
        cleaned["style_lock"] = _ensure_soft_style_sentence(cleaned["style_lock"])

    if profile.prompt_dialect == "tags":
        return _assemble_tags_prompt(cleaned)
    return _assemble_natural_prompt(
        cleaned,
        include_negatives=profile.negatives_effective,
    )


def append_hard_locks(
    prompt: str,
    project: dict[str, Any] | Any,
    spec: dict[str, Any] | Any,
) -> str:
    """Legacy prose path: append forced view/tokens/technical tails."""
    base = str(prompt or "").strip()
    if not base:
        return base

    tail_fields: dict[str, str] = {}
    _merge_art_tokens_into_fields(tail_fields, _art_tokens_dict(project))
    _ensure_view_lock(tail_fields, project)
    _ensure_technical_lock(tail_fields, spec)
    _ensure_global_negatives(tail_fields)

    tails: list[str] = []
    for key in ("view", "technical", "style_lock", "silhouette", "negatives"):
        text = tail_fields.get(key, "").strip()
        if not text:
            continue
        if text.lower() in base.lower():
            continue
        tails.append(text)
    if not tails:
        return base
    return f"{base}\n\nHard locks: {'; '.join(tails)}"


def _asset_schema(kind: str) -> dict[str, str]:
    schema = {
        "subject": "main asset subject and readable description",
        "silhouette": "silhouette / shape readability cues",
        "style_lock": "line weight, palette, art style locks",
        "view": "camera / facing angle for this asset",
        "technical": "background, matting, tile, or scene technical requirements",
        "negatives": "forbidden elements and composition mistakes",
    }
    if kind == "animation":
        schema["video_prompt"] = "motion-focused video prompt for i2v"
    return schema


def _system_prompt(kind: str, context: dict[str, Any] | None = None) -> str:
    spec = None
    project = None
    if isinstance(context, dict):
        asset = context.get("asset")
        proj = context.get("project")
        if asset is not None:
            spec = asset
        if proj is not None:
            project = proj

    if spec is not None:
        skills = load_prompt_skills_for_asset(spec, project)
    else:
        skills = load_role_skills(PROMPT_CRAFTER_ROLE)

    schema = _asset_schema(kind)
    return (
        f"You are the **{PROMPT_CRAFTER_ROLE}** in Game AI Foundry. "
        "You receive shared project + asset context (same facts the orchestrator sees). "
        "You do NOT run the pipeline — you only write generation prompts.\n\n"
        f"{skills}\n\n"
        "Fill structured JSON fields; Python assembles the final image prompt — "
        "do not output a free-form `prompt` field unless legacy fallback.\n"
        "Respect project.view, project.art_tokens, and asset.content_class when present.\n\n"
        "Respond with ONLY valid JSON, no markdown fences, using exactly these keys:\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        "Craft visually specific English under 120 words total across fields."
    )


def _resolve_still_image_binding(
    config: dict[str, Any] | None,
    context: dict[str, Any],
) -> tuple[str, PromptCapabilityProfile]:
    asset = context.get("asset") if isinstance(context.get("asset"), dict) else {}
    generate_tier = str(asset.get("generate_tier") or "").strip() or None
    for_icon_kit = bool(str(asset.get("kit_item") or "").strip())
    tier = effective_generate_tier(
        generate_tier=generate_tier,
        for_icon_kit_item=for_icon_kit,
    )
    image_model = resolve_image_model_for_tier(config, tier)
    profile = resolve_media_prompt_profile(image_model or "", modality="image")
    return image_model, profile


def _attach_still_image_handoff(
    result: dict[str, Any],
    *,
    image_model: str,
    profile: PromptCapabilityProfile,
) -> None:
    if image_model:
        result["image_model"] = image_model
    result["prompt_profile_id"] = profile.profile_id


def _resolve_video_model_binding(
    config: dict[str, Any] | None,
    context: dict[str, Any],
) -> tuple[str, PromptCapabilityProfile]:
    asset = context.get("asset") if isinstance(context.get("asset"), dict) else {}
    overrides: dict[str, Any] = {}
    video_model_override = str(asset.get("video_model") or "").strip()
    if video_model_override:
        overrides["model"] = video_model_override
    from video_route import resolve_video_credentials

    creds = resolve_video_credentials(config or {})
    if creds.usable:
        overrides["backend"] = creds.backend
        if not overrides.get("model") and creds.model:
            overrides["model"] = creds.model
    video = resolve_video_generate_settings(config or {}, **overrides)
    video_model = resolve_model(str(video["model"]))
    profile = resolve_media_prompt_profile(video_model, modality="video")
    return video_model, profile


def _attach_animation_video_handoff(
    result: dict[str, Any],
    *,
    video_prompt: str,
    config: dict[str, Any] | None,
    context: dict[str, Any],
) -> None:
    video_model, video_profile = _resolve_video_model_binding(config, context)
    result["video_prompt"] = apply_video_prompt_profile(video_prompt, video_profile)
    result["video_model"] = video_model


def craft_asset_prompt(
    *,
    context: dict[str, Any],
    model: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    kind: str = "image",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """prompt-crafter role: structured fields → assembled generation prompt.

    Retries when the model dumps Chinese brief prose into final prompt fields
    (Host auto-fix reset+rerun alone cannot fix that flake).
    """
    last_cjk: PromptCraftError | None = None
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            return _craft_asset_prompt_once(
                context=context,
                model=model,
                api_key=api_key,
                api_base=api_base,
                proxy=proxy,
                kind=kind,
                config=config,
                english_only_retry=attempt > 0,
                retry_attempt=attempt,
            )
        except PromptCraftError as exc:
            if _CJK_BRIEF_BLOCK_MSG not in str(exc) or attempt >= max_attempts - 1:
                raise
            last_cjk = exc
    assert last_cjk is not None
    raise last_cjk


def _craft_asset_prompt_once(
    *,
    context: dict[str, Any],
    model: str,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    kind: str = "image",
    config: dict[str, Any] | None = None,
    english_only_retry: bool = False,
    retry_attempt: int = 0,
) -> dict[str, Any]:
    """Single LLM attempt for asset prompt craft."""
    user: dict[str, Any] = {
        "role": PROMPT_CRAFTER_ROLE,
        "task": f"Craft a {kind} generation prompt.",
        "context": context,
    }
    if english_only_retry:
        user["hard_constraint"] = (
            "CRITICAL retry: previous output was REJECTED. "
            "Every prompt / video_prompt / structured field value must be English prose only. "
            "Short CJK asset-name tokens are OK; do NOT paste Chinese brief description or art_direction. "
            f"(attempt {retry_attempt + 1})"
        )
        user["output_language"] = "en"

    raw = chat_text_completion(
        model=model,
        messages=[
            {"role": "system", "content": _system_prompt(kind, context)},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, indent=2)},
        ],
        api_key=api_key,
        api_base=api_base,
        proxy=proxy,
    )
    parsed = _parse_json_object(raw)
    project = context.get("project") if isinstance(context.get("project"), dict) else {}
    spec = context.get("asset") if isinstance(context.get("asset"), dict) else {}

    has_structured = any(
        str(parsed.get(k) or "").strip() for k in ASSET_STRUCTURED_KEYS
    )
    image_model, image_profile = _resolve_still_image_binding(config, context)

    if parsed.get("prompt") and not has_structured:
        prompt = str(parsed.get("prompt", "")).strip()
        if not prompt:
            raise PromptCraftError("LLM JSON missing non-empty 'prompt' field")
        prompt = append_hard_locks(prompt, project, spec)
        # Final prose must not be CJK brief dump (short name tokens OK).
        _raise_if_cjk_prompt_field(prompt, allow_short_label=True)
        result: dict[str, Any] = {"prompt": prompt, "prompt_source": "llm_prose"}
        _attach_still_image_handoff(
            result,
            image_model=image_model,
            profile=image_profile,
        )
        if kind == "animation":
            video_prompt = str(parsed.get("video_prompt", "")).strip()
            if not video_prompt:
                raise PromptCraftError(
                    "Animation craft requires non-empty 'video_prompt' in LLM JSON"
                )
            _raise_if_cjk_prompt_field(video_prompt, allow_short_label=True)
            _attach_animation_video_handoff(
                result,
                video_prompt=video_prompt,
                config=config,
                context=context,
            )
        return result

    fields = {k: parsed.get(k) for k in ASSET_STRUCTURED_KEYS}
    if not fields.get("style_lock") and project.get("art_direction"):
        fields["style_lock"] = str(project["art_direction"])

    prompt = assemble_asset_prompt(
        fields,
        project=project,
        spec=spec,
        profile=image_profile,
    )
    cleaned_fields = {
        k: str(v).strip()
        for k, v in fields.items()
        if v is not None and str(v).strip()
    }
    result = {
        "prompt": prompt,
        "prompt_source": "llm_structured",
        "prompt_fields": cleaned_fields,
    }
    _attach_still_image_handoff(
        result,
        image_model=image_model,
        profile=image_profile,
    )
    if kind == "animation":
        video_prompt = str(parsed.get("video_prompt", "")).strip()
        if not video_prompt:
            raise PromptCraftError(
                "Animation craft requires non-empty 'video_prompt' in LLM JSON"
            )
        _raise_if_cjk_prompt_field(video_prompt, allow_short_label=True)
        _attach_animation_video_handoff(
            result,
            video_prompt=video_prompt,
            config=config,
            context=context,
        )
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

    # Brief narrative may be Chinese; never inject Chinese prose into final VT prompt.
    # hero/hud may keep short CJK names (e.g. player_asset); long/punctuated CJK raises.
    for key in ("scene", "style_lock", "details", "gameplay_beat"):
        _raise_if_cjk_prompt_field(cleaned.get(key, ""))
    for key in ("hero", "hud"):
        _raise_if_cjk_prompt_field(cleaned.get(key, ""), allow_short_label=True)

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
    *,
    scene: dict[str, Any] | None = None,
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
    if isinstance(scene, dict) and scene:
        sid = str(scene.get("id") or "").strip()
        stitle = str(scene.get("title") or "").strip()
        scene_bits.insert(0, f"in-game screen: {stitle or sid}")
        summary = str(scene.get("summary") or "").strip()
        if summary:
            scene_bits.append(summary[:280])
        notes = str(scene.get("notes") or "").strip()
        if notes:
            scene_bits.append(notes[:200])
    details_bits = [
        cam_bits or "readable gameplay camera matching the genre",
        "clear silhouettes, cohesive lighting",
        f"variant focus: {variant.get('focus', '')}",
    ]
    beat = variant.get("focus") or loop or goal or "core gameplay action in progress"
    if isinstance(scene, dict) and str(scene.get("summary") or "").strip():
        beat = f"{str(scene.get('summary')).strip()[:160]}; {beat}"
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
        _raise_if_cjk_prompt_field(prompt, allow_short_label=True)
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
