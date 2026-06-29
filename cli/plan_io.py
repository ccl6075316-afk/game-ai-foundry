"""Handoff artifacts between agents (prompt-crafter → image/video/godot generators)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roles import (
    GODOT_ASSEMBLER_ROLE,
    GODOT_DEVELOPER_ROLE,
    IMAGE_GENERATOR_ROLE,
    ORCHESTRATOR_ROLE,
    PROMPT_CRAFTER_ROLE,
    VIDEO_GENERATOR_ROLE,
)

HANDOFF_VERSION = 1


def build_handoff(
    plan: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
    consumer_role: str = IMAGE_GENERATOR_ROLE,
) -> dict[str, Any]:
    """Wrap a plan dict for a consumer agent."""
    return {
        "handoff_version": HANDOFF_VERSION,
        "producer_role": PROMPT_CRAFTER_ROLE,
        "consumer_role": consumer_role,
        "context": context or {},
        "plan": plan,
    }


def build_video_handoff(plan: dict[str, Any], *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_handoff(plan, context=context or {}, consumer_role=VIDEO_GENERATOR_ROLE)


def build_godot_handoff(plan: dict[str, Any], *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_handoff(plan, context=context or {}, consumer_role=GODOT_ASSEMBLER_ROLE)


def build_godot_dev_handoff(plan: dict[str, Any], *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "handoff_version": HANDOFF_VERSION,
        "producer_role": ORCHESTRATOR_ROLE,
        "consumer_role": GODOT_DEVELOPER_ROLE,
        "context": context or {},
        "plan": plan,
    }


def load_godot_dev_handoff(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("handoff_version") != HANDOFF_VERSION:
        raise ValueError(f"Unsupported handoff version in {path}")
    if data.get("consumer_role") != GODOT_DEVELOPER_ROLE:
        raise ValueError(f"Plan file {path} is not for godot-developer")
    plan = data.get("plan")
    if not isinstance(plan, dict) or not plan.get("project_path"):
        raise ValueError(f"Plan file {path} missing plan.project_path")
    return data


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


def load_godot_handoff(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("handoff_version") != HANDOFF_VERSION:
        raise ValueError(f"Unsupported handoff version in {path}")
    if data.get("consumer_role") != GODOT_ASSEMBLER_ROLE:
        raise ValueError(f"Plan file {path} is not for godot-assembler")
    plan = data.get("plan")
    if not isinstance(plan, dict):
        raise ValueError(f"Plan file {path} missing plan object")
    if not plan.get("project_path"):
        raise ValueError(f"Plan file {path} missing plan.project_path")
    return data


def prompt_from_handoff(handoff: dict[str, Any]) -> str:
    return str(handoff["plan"]["prompt"])


def validation_from_handoff(handoff: dict[str, Any]) -> dict[str, Any] | None:
    plan = handoff.get("plan", {})
    validation = plan.get("validation")
    return validation if isinstance(validation, dict) else None


def asset_type_from_handoff(handoff: dict[str, Any]) -> str:
    return str(handoff["plan"].get("asset_type", "character"))


def image_size_from_handoff(handoff: dict[str, Any]) -> str | None:
    """Generation size from plan (e.g. visual_target uses project.viewport)."""
    plan = handoff.get("plan", {})
    if not isinstance(plan, dict):
        return None
    raw = plan.get("image_size")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


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
