"""Handoff artifacts between agents (prompt-crafter → image-generator)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roles import IMAGE_GENERATOR_ROLE, PROMPT_CRAFTER_ROLE

HANDOFF_VERSION = 1


def build_handoff(
    plan: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Wrap a PromptPlan dict for the image-generator agent."""
    return {
        "handoff_version": HANDOFF_VERSION,
        "producer_role": PROMPT_CRAFTER_ROLE,
        "consumer_role": IMAGE_GENERATOR_ROLE,
        "context": context,
        "plan": plan,
    }


def save_handoff(path: Path, handoff: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_handoff(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("handoff_version") != HANDOFF_VERSION:
        raise ValueError(f"Unsupported handoff version in {path}")
    if data.get("consumer_role") != IMAGE_GENERATOR_ROLE:
        raise ValueError(f"Plan file {path} is not for image-generator")
    plan = data.get("plan")
    if not isinstance(plan, dict) or not plan.get("prompt"):
        raise ValueError(f"Plan file {path} missing plan.prompt")
    return data


def prompt_from_handoff(handoff: dict[str, Any]) -> str:
    return str(handoff["plan"]["prompt"])


def validation_from_handoff(handoff: dict[str, Any]) -> dict[str, Any] | None:
    plan = handoff.get("plan", {})
    validation = plan.get("validation")
    return validation if isinstance(validation, dict) else None


def asset_type_from_handoff(handoff: dict[str, Any]) -> str:
    return str(handoff["plan"].get("asset_type", "character"))
