"""Extract Seedance params for video-generator CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roles import IMAGE_GENERATOR_ROLE, PROMPT_CRAFTER_ROLE, VIDEO_GENERATOR_ROLE

HANDOFF_VERSION = 1


def build_handoff(
    plan: dict[str, Any],
    *,
    context: dict[str, Any],
    consumer_role: str = IMAGE_GENERATOR_ROLE,
) -> dict[str, Any]:
    """Wrap a PromptPlan dict for image-generator or video-generator."""
    return {
        "handoff_version": HANDOFF_VERSION,
        "producer_role": PROMPT_CRAFTER_ROLE,
        "consumer_role": consumer_role,
        "context": context,
        "plan": plan,
    }


def build_video_handoff(plan: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    return build_handoff(plan, context=context, consumer_role=VIDEO_GENERATOR_ROLE)


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


def load_video_handoff(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("handoff_version") != HANDOFF_VERSION:
        raise ValueError(f"Unsupported handoff version in {path}")
    if data.get("consumer_role") != VIDEO_GENERATOR_ROLE:
        raise ValueError(f"Plan file {path} is not for video-generator")
    plan = data.get("plan")
    if not isinstance(plan, dict) or not plan.get("video_prompt"):
        raise ValueError(f"Plan file {path} missing plan.video_prompt")
    return data


def prompt_from_handoff(handoff: dict[str, Any]) -> str:
    return str(handoff["plan"]["prompt"])


def validation_from_handoff(handoff: dict[str, Any]) -> dict[str, Any] | None:
    plan = handoff.get("plan", {})
    validation = plan.get("validation")
    return validation if isinstance(validation, dict) else None


def asset_type_from_handoff(handoff: dict[str, Any]) -> str:
    return str(handoff["plan"].get("asset_type", "character"))


def video_params_from_handoff(handoff: dict[str, Any]) -> dict[str, Any]:
    """Extract Seedance params for video-generator CLI."""
    plan = handoff["plan"]
    params: dict[str, Any] = {
        "prompt": str(plan["video_prompt"]),
        "model": plan.get("video_model"),
        "duration": plan.get("video_duration"),
        "resolution": plan.get("video_resolution"),
        "ratio": plan.get("video_ratio"),
        "generate_audio": plan.get("video_generate_audio"),
        "watermark": plan.get("video_watermark"),
        "reference_image": plan.get("reference_image"),
    }
    for step in plan.get("pipeline") or []:
        if isinstance(step, dict) and step.get("step") == "video_generate":
            if step.get("model"):
                params["model"] = step["model"]
            if step.get("duration") is not None:
                params["duration"] = int(step["duration"])
            if step.get("resolution"):
                params["resolution"] = step["resolution"]
            if step.get("ratio"):
                params["ratio"] = step["ratio"]
            if "generate_audio" in step:
                params["generate_audio"] = bool(step["generate_audio"])
            if "watermark" in step:
                params["watermark"] = bool(step["watermark"])
            break
    if params.get("duration") is not None:
        params["duration"] = int(params["duration"])
    return params
