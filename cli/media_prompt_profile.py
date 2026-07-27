"""Model id → PromptCapabilityProfile registry for media prompt assembly."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

PromptDialect = Literal["natural", "tags"]
MediaModality = Literal["image", "video"]


@dataclass(frozen=True)
class PromptCapabilityProfile:
    profile_id: str
    prompt_dialect: PromptDialect
    negatives_effective: bool
    prefer_soft_style: bool
    modality: MediaModality


GPT_IMAGE = PromptCapabilityProfile(
    profile_id="gpt_image",
    prompt_dialect="natural",
    negatives_effective=True,
    prefer_soft_style=True,
    modality="image",
)
GEMINI_IMAGE = PromptCapabilityProfile(
    profile_id="gemini_image",
    prompt_dialect="natural",
    negatives_effective=False,
    prefer_soft_style=True,
    modality="image",
)
VOLC_IMAGE = PromptCapabilityProfile(
    profile_id="volc_image",
    prompt_dialect="natural",
    negatives_effective=True,
    prefer_soft_style=True,
    modality="image",
)
VOLC_VIDEO = PromptCapabilityProfile(
    profile_id="volc_video",
    prompt_dialect="natural",
    negatives_effective=False,
    prefer_soft_style=True,
    modality="video",
)
GROK_IMAGE = PromptCapabilityProfile(
    profile_id="grok_image",
    prompt_dialect="natural",
    negatives_effective=True,
    prefer_soft_style=True,
    modality="image",
)
DEFAULT_IMAGE = PromptCapabilityProfile(
    profile_id="default",
    prompt_dialect="natural",
    negatives_effective=False,
    prefer_soft_style=True,
    modality="image",
)
DEFAULT_VIDEO = PromptCapabilityProfile(
    profile_id="default",
    prompt_dialect="natural",
    negatives_effective=False,
    prefer_soft_style=True,
    modality="video",
)

_SPACE_RE = re.compile(r"\s+")
_NEGATIVE_LINE_RE = re.compile(r"(?i)^\s*(?:negative(?:s)?)\s*:\s*(.*)$")

SOFT_STYLE_ALIGNMENT = (
    "Soft style alignment with art direction; prefer cohesive look over literal copy."
)


def _append_prompt_fragment(body: str, addition: str) -> str:
    left = str(body or "").strip()
    right = str(addition or "").strip()
    if not right:
        return left
    if right.lower() in left.lower():
        return left
    if not left:
        return right
    return f"{left}\n\n{right}"


def apply_video_prompt_profile(text: str, profile: PromptCapabilityProfile) -> str:
    """Post-process LLM video motion prose for target model capabilities."""
    body = str(text or "").strip()
    if not body:
        return body

    if not profile.negatives_effective:
        kept_lines: list[str] = []
        avoid_parts: list[str] = []
        for line in body.splitlines():
            match = _NEGATIVE_LINE_RE.match(line)
            if match:
                chunk = match.group(1).strip()
                if chunk:
                    avoid_parts.append(chunk)
                continue
            kept_lines.append(line)
        body = "\n".join(kept_lines).strip()
        if avoid_parts:
            avoid_clause = f"Avoid: {'; '.join(avoid_parts)}"
            if "avoid:" in body.lower():
                existing_tail = avoid_clause.split(":", 1)[1].strip()
                if existing_tail.lower() not in body.lower():
                    body = f"{body}; {existing_tail}".strip()
            else:
                body = _append_prompt_fragment(body, avoid_clause)

    if profile.prompt_dialect == "tags":
        body = re.sub(r"\s*\n+\s*", ", ", body)
        body = _SPACE_RE.sub(" ", body).strip()

    if profile.prefer_soft_style:
        body = _append_prompt_fragment(body, SOFT_STYLE_ALIGNMENT)

    return body


def normalize_media_model_id(model: str) -> str:
    return _SPACE_RE.sub(" ", model.lower().strip())


def _default_for(modality: MediaModality) -> PromptCapabilityProfile:
    if modality == "video":
        return DEFAULT_VIDEO
    return DEFAULT_IMAGE


def resolve_media_prompt_profile(
    model: str,
    *,
    modality: MediaModality,
) -> PromptCapabilityProfile:
    normalized = normalize_media_model_id(model or "")

    if modality == "image":
        if "gpt-image" in normalized or "gptimage" in normalized:
            return GPT_IMAGE
        if "gemini" in normalized and "image" in normalized:
            return GEMINI_IMAGE
        if "seedream" in normalized:
            return VOLC_IMAGE
        if "grok" in normalized:
            return GROK_IMAGE

    if modality == "video" and "seedance" in normalized:
        return VOLC_VIDEO

    return _default_for(modality)
