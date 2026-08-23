"""Fingerprint generation-relevant brief/spec inputs for pipeline staleness checks."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from asset_sizing import resolve_effective_display_size, resolve_generation_image_size
from brief import AssetSpec, IconKitItem, ProjectContext, resolve_asset_file_key

_GENERATION_ASSET_KEYS = frozenset(
    {
        "id",
        "name",
        "type",
        "description",
        "usage",
        "usage_description",
        "generate_method",
        "aspect_ratio",
        "real_length_cm",
        "real_length_max_cm",
        "size_source",
        "reference_asset",
        "action",
        "animation_method",
        "duration_seconds",
        "sprite_frames",
        "video_model",
        "video_resolution",
        "video_ratio",
        "generate_audio",
        "watermark",
        "animation_name",
        "animation_loop",
        "style_group",
        "style_anchor_kind",
        "style_anchor",
        "identity_anchor",
        "use_style_img2img",
        "generate_tier",
        "content_class",
        "states",
        "state",
        "grid",
        "display_size",
        "generation_size",
    }
)

_KIT_ITEM_KEYS = frozenset({"id", "label", "usage", "usage_description"})


def _normalize_size(raw: Any) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    try:
        w = int(raw.get("width") or 0)
        h = int(raw.get("height") or 0)
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return {"width": w, "height": h}


def _normalize_baseline(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = {}
    ref = str(raw.get("asset_id") or raw.get("reference_asset_id") or "").strip()
    if ref:
        out["asset_id"] = ref
    try:
        cm = float(raw.get("real_length_cm") or raw.get("reference_real_length_cm") or 0)
    except (TypeError, ValueError):
        cm = 0.0
    if cm > 0:
        out["real_length_cm"] = cm
    ds = _normalize_size(raw.get("display_size") or raw.get("reference_display_size"))
    if ds:
        out["display_size"] = ds
    return out or None


def _pick_keys(data: dict[str, Any], keys: frozenset[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in keys:
        if key not in data:
            continue
        val = data[key]
        if val is None:
            continue
        if isinstance(val, str):
            text = val.strip()
            if not text:
                continue
            out[key] = text
        elif isinstance(val, bool):
            out[key] = val
        elif isinstance(val, (int, float)) and key.endswith("_cm"):
            if float(val) > 0:
                out[key] = float(val)
        elif isinstance(val, (int, float)) and key in ("duration_seconds", "sprite_frames", "parallax_order", "scroll_factor"):
            out[key] = val
        elif isinstance(val, list) and val:
            out[key] = val
        elif key in ("display_size", "generation_size"):
            norm = _normalize_size(val)
            if norm:
                out[key] = norm
        else:
            out[key] = val
    return out


def generation_input_from_spec_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a spec dict / handoff context.asset slice for comparison."""
    return _pick_keys(data, _GENERATION_ASSET_KEYS)


def _kit_item_dict(item: IconKitItem) -> dict[str, Any]:
    raw = {
        "id": item.id,
        "label": item.label,
        "usage": item.usage,
        "usage_description": item.usage_description,
    }
    return _pick_keys(raw, _KIT_ITEM_KEYS)


def build_generation_input(
    spec: AssetSpec,
    project: ProjectContext,
    *,
    kit_item: IconKitItem | None = None,
    raw_shard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Current generation inputs derived from live brief/spec (not crafted prompt)."""
    shard = raw_shard if isinstance(raw_shard, dict) else {}
    base = generation_input_from_spec_dict(shard)
    if not base.get("id"):
        base["id"] = spec.id or resolve_asset_file_key(spec)
    if not base.get("name"):
        base["name"] = spec.name
    if not base.get("type"):
        base["type"] = spec.type.value
    if not base.get("description"):
        base["description"] = (spec.description or "").strip()
    for field_name in (
        "usage",
        "usage_description",
        "generate_method",
        "aspect_ratio",
        "size_source",
        "reference_asset",
        "action",
        "animation_method",
        "video_model",
        "video_resolution",
        "video_ratio",
        "animation_name",
        "style_group",
        "style_anchor_kind",
        "style_anchor",
        "identity_anchor",
        "content_class",
        "state",
        "generate_tier",
        "grid",
    ):
        val = getattr(spec, field_name, "")
        if val and field_name not in base:
            base[field_name] = str(val).strip()
    if spec.real_length_cm > 0 and "real_length_cm" not in base:
        base["real_length_cm"] = spec.real_length_cm
    if spec.real_length_max_cm > 0 and "real_length_max_cm" not in base:
        base["real_length_max_cm"] = spec.real_length_max_cm
    if spec.duration_seconds and "duration_seconds" not in base:
        base["duration_seconds"] = spec.duration_seconds
    if spec.sprite_frames and "sprite_frames" not in base:
        base["sprite_frames"] = spec.sprite_frames
    if spec.generate_audio is not None and "generate_audio" not in base:
        base["generate_audio"] = spec.generate_audio
    if spec.watermark is not None and "watermark" not in base:
        base["watermark"] = spec.watermark
    if spec.animation_loop is not None and "animation_loop" not in base:
        base["animation_loop"] = spec.animation_loop
    if spec.use_style_img2img is not None and "use_style_img2img" not in base:
        base["use_style_img2img"] = spec.use_style_img2img
    if spec.states and "states" not in base:
        base["states"] = list(spec.states)

    effective = resolve_effective_display_size(spec, project)
    if not effective.is_empty():
        base["display_size"] = effective.to_dict()
    if not spec.generation_size.is_empty():
        base["generation_size"] = spec.generation_size.to_dict()
    base["image_size"] = resolve_generation_image_size(spec, project)

    baseline = _normalize_baseline(project.size_baseline)
    if baseline:
        base["_project_size_baseline"] = baseline

    if kit_item is not None:
        base["kit_item"] = _kit_item_dict(kit_item)

    return base


def extract_generation_input_from_handoff(handoff: dict[str, Any]) -> dict[str, Any] | None:
    """Generation inputs snapshot stored inside a prompt-craft handoff."""
    if not isinstance(handoff, dict):
        return None
    ctx = handoff.get("context") if isinstance(handoff.get("context"), dict) else {}
    asset = ctx.get("asset") if isinstance(ctx.get("asset"), dict) else {}
    plan = handoff.get("plan") if isinstance(handoff.get("plan"), dict) else {}
    base = generation_input_from_spec_dict(asset)
    if plan.get("image_size"):
        base["image_size"] = str(plan["image_size"]).strip()
    ds = _normalize_size(plan.get("display_size"))
    if ds:
        base["display_size"] = ds
    if plan.get("reference_image"):
        base["reference_image"] = str(plan["reference_image"]).strip()
    project = ctx.get("project") if isinstance(ctx.get("project"), dict) else {}
    baseline = _normalize_baseline(project.get("size_baseline"))
    if baseline:
        base["_project_size_baseline"] = baseline
    kit = ctx.get("kit_item") if isinstance(ctx.get("kit_item"), dict) else None
    if kit:
        picked = _pick_keys(kit, _KIT_ITEM_KEYS)
        if picked:
            base["kit_item"] = picked
    return base or None


def generation_input_fingerprint(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def generation_inputs_match(current: dict[str, Any], stored: dict[str, Any]) -> bool:
    return generation_input_fingerprint(current) == generation_input_fingerprint(stored)


def embed_generation_fingerprint(
    plan_dict: dict[str, Any],
    *,
    spec: AssetSpec,
    project: ProjectContext,
    kit_item: IconKitItem | None = None,
    raw_shard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach fingerprint to plan dict before saving handoff."""
    out = dict(plan_dict)
    inp = build_generation_input(spec, project, kit_item=kit_item, raw_shard=raw_shard)
    out["generation_input_fingerprint"] = generation_input_fingerprint(inp)
    return out


def is_handoff_generation_stale(
    handoff: dict[str, Any],
    current_input: dict[str, Any],
) -> bool:
    plan = handoff.get("plan") if isinstance(handoff.get("plan"), dict) else {}
    stored_fp = str(plan.get("generation_input_fingerprint") or "").strip()
    current_fp = generation_input_fingerprint(current_input)
    if stored_fp:
        return stored_fp != current_fp
    stored_input = extract_generation_input_from_handoff(handoff)
    if not stored_input:
        return False
    return not generation_inputs_match(current_input, stored_input)
