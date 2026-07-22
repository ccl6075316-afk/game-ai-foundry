"""Asset prompt planning and image validation for Game AI Foundry.

Godogen-style split:
- Markdown skills (resources/skills/) — constraints and cheatsheets
- LLM — crafts the actual generation prompt (prompt_craft.py)
- Python — pipeline metadata, validation heuristics, CLI only
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from asset_sizing import resolve_generation_image_size
from brief import (
    ANIMATION_METHOD_IMG2IMG,
    ANIMATION_METHOD_VIDEO,
    AssetSpec,
    AssetType,
    ProjectContext,
    find_asset,
    load_brief,
    should_use_style_img2img,
)
from prompt_craft import DEFAULT_PROMPT_MODEL, PromptCraftError, craft_asset_prompt
from roles import PROMPT_CRAFTER_ROLE
from shared_context import build_role_context
from skill_loader import ROLE_SKILLS


@dataclass
class PromptPlan:
    asset_name: str
    asset_type: str
    prompt: str | None
    negative_hints: list[str]
    validation: dict[str, Any]
    pipeline: list[dict[str, Any]]
    requires_reference_image: bool = False
    requires_background_removal: bool = False
    animation_method: str | None = None
    prompt_source: str = "pending"  # llm | pending | scaffold_only
    role: str = PROMPT_CRAFTER_ROLE
    skill_refs: list[str] = field(
        default_factory=lambda: list(ROLE_SKILLS[PROMPT_CRAFTER_ROLE])
    )
    video_prompt: str | None = None
    video_model: str | None = None
    video_duration: int | None = None
    video_resolution: str | None = None
    video_ratio: str | None = None
    video_generate_audio: bool | None = None
    video_watermark: bool | None = None
    reference_image: str | None = None
    image_size: str | None = None
    display_size: dict[str, int] | None = None
    anchor: str = "bottom_center"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PURE_WHITE_BG_RETRY_HINTS = [
    "Append: pure flat white background (#FFFFFF), uniform studio backdrop only.",
    "Append: no border, no frame, no vignette, no gradient, no textured paper.",
    "Append: no cast shadow on ground, no environmental scenery behind character.",
    "Strengthen: single character centered on solid white canvas, square composition.",
]

PURE_WHITE_THRESHOLD = 240
PURE_WHITE_EDGE_MIN_RATIO = 0.88
PURE_WHITE_EDGE_MAX_DARK_RATIO = 0.04
PURE_WHITE_CORNER_MAX_STD = 22.0


@dataclass
class ValidationResult:
    ok: bool
    asset_type: str
    checks: list[dict[str, Any]]
    message: str
    next_action: str | None = None
    retry_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _apply_style_img2img_to_meta(
    meta: dict[str, Any],
    project: ProjectContext,
    spec: AssetSpec,
    assets: list[AssetSpec] | None,
) -> dict[str, Any]:
    """Mark still plans that require style-group ``--reference-image`` (not pose/video)."""
    if not assets or spec.type == AssetType.CHARACTER_POSE:
        return meta
    if not should_use_style_img2img(spec, project=project, assets=assets):
        return meta
    out = dict(meta)
    out["requires_reference_image"] = True
    return out


def _plan_metadata(
    project: ProjectContext,
    spec: AssetSpec,
    *,
    assets: list[AssetSpec] | None = None,
) -> dict[str, Any]:
    """Pipeline, validation, and flags — always deterministic."""
    if spec.type == AssetType.CHARACTER:
        return _apply_style_img2img_to_meta(
            {
            "negative_hints": [
                "Do not prompt for transparent background or checkerboard.",
                "Do not include multiple characters or action frames.",
                "Do not include borders, frames, vignettes, gradients, or textured backdrops.",
                "Character sprite only — not a prison scene, not environmental background, not item icon.",
                "No prison walls, bars, cells, floors, or scenery behind the character.",
            ],
            "validation": _validation_spec(spec.type),
            "pipeline": [
                {"step": "generate_image"},
                {"step": "validate"},
                {"step": "trim"},
                {"step": "remove_bg", "mode": "color"},
                {"step": "validate_matting"},
            ],
            "requires_background_removal": True,
            "requires_reference_image": False,
            "animation_method": None,
            },
            project,
            spec,
            assets,
        )
    if spec.type == AssetType.ICON_KIT:
        if not spec.items:
            raise ValueError(f"icon_kit '{spec.name}' requires an 'items' list.")
        # Per-item singles are planned in pipeline_manifest; scaffold describes one item.
        return {
            "negative_hints": [
                "Single object only — never a grid or multiple icons in one image.",
            ],
            "validation": _validation_spec(AssetType.CHARACTER),  # single subject on white
            "pipeline": [
                {"step": "generate_image"},
                {"step": "validate"},
                {"step": "trim"},
                {"step": "remove_bg", "mode": "color"},
                {"step": "validate_matting"},
            ],
            "requires_background_removal": True,
            "requires_reference_image": False,
            "animation_method": None,
            "expand_items": True,
        }
    if spec.type == AssetType.TEXTURE:
        return _apply_style_img2img_to_meta(
            {
            "negative_hints": ["Do not remove background — the full image is the texture."],
            "validation": _validation_spec(spec.type),
            "pipeline": [{"step": "generate_image"}, {"step": "validate"}],
            "requires_background_removal": False,
            "requires_reference_image": False,
            "animation_method": None,
            },
            project,
            spec,
            assets,
        )
    if spec.type == AssetType.BACKGROUND:
        return _apply_style_img2img_to_meta(
            {
            "negative_hints": ["Do not use a flat white studio background."],
            "validation": _validation_spec(spec.type, aspect_ratio=spec.aspect_ratio),
            "pipeline": [{"step": "generate_image"}, {"step": "validate"}],
            "requires_background_removal": False,
            "requires_reference_image": False,
            "animation_method": None,
            },
            project,
            spec,
            assets,
        )
    if spec.type == AssetType.CHARACTER_POSE:
        if not spec.action.strip():
            raise ValueError(f"character_pose '{spec.name}' requires an 'action' field.")
        if not spec.reference_asset.strip():
            raise ValueError(
                f"character_pose '{spec.name}' requires 'reference_asset'."
            )
        return {
            "negative_hints": [
                "Image-to-image: describe only the pose change.",
                "Never request multiple frames or animation sheet in one image.",
            ],
            "validation": _validation_spec(AssetType.CHARACTER),
            "pipeline": [
                {"step": "generate_image", "reference_asset": spec.reference_asset},
                {"step": "validate"},
                {"step": "trim"},
                {"step": "remove_bg", "mode": "color"},
                {"step": "validate_matting"},
            ],
            "requires_background_removal": True,
            "requires_reference_image": True,
            "animation_method": ANIMATION_METHOD_IMG2IMG,
        }
    raise ValueError(f"Unhandled asset type: {spec.type}")


def _anchor_for_usage(spec: AssetSpec) -> str:
    usage = (spec.usage or "").strip()
    if usage in ("item_icon", "ui_element", "vfx") or spec.type == AssetType.ICON_KIT:
        return "center"
    if spec.type in (AssetType.CHARACTER, AssetType.CHARACTER_POSE):
        return "bottom_center"
    if spec.type == AssetType.BACKGROUND:
        return "top_left"
    return "center"


def build_prompt_scaffold(
    project: ProjectContext,
    spec: AssetSpec,
    *,
    assets: list[AssetSpec] | None = None,
) -> PromptPlan:
    """Pipeline + validation metadata only. Prompt is null until LLM crafts it."""
    meta = _plan_metadata(project, spec, assets=assets)
    ds = None if spec.display_size.is_empty() else spec.display_size.to_dict()
    return PromptPlan(
        asset_name=spec.name,
        asset_type=spec.type.value,
        prompt=None,
        prompt_source="scaffold_only",
        skill_refs=list(ROLE_SKILLS[PROMPT_CRAFTER_ROLE]),
        image_size=resolve_generation_image_size(spec, project),
        display_size=ds,
        anchor=_anchor_for_usage(spec),
        **meta,
    )


def build_prompt(
    project: ProjectContext,
    spec: AssetSpec,
    *,
    craft: bool = True,
    prompt_model: str = DEFAULT_PROMPT_MODEL,
    api_key: str | None = None,
    api_base: str | None = None,
    proxy: str | None = None,
    assets: list[AssetSpec] | None = None,
    kit_item: str | None = None,
    kit_item_slug: str | None = None,
) -> PromptPlan:
    """Craft generation prompt via LLM reading skill docs (Godogen model)."""
    plan = build_prompt_scaffold(project, spec, assets=assets)
    if kit_item is not None:
        plan.validation = _validation_spec(AssetType.CHARACTER)
        plan.negative_hints = [
            "Single object only — never a grid or multiple icons in one image.",
            *(plan.negative_hints or []),
        ]

    if not craft:
        return plan

    if not api_key or not api_base:
        raise PromptCraftError(
            "Prompt crafting requires an API key (config.host, config.prompt, or config.image). "
            "Godogen uses its orchestrator LLM the same way — there is no hardcoded prompt."
        )

    crafted = craft_asset_prompt(
        context=build_role_context(
            project,
            spec,
            kit_item=kit_item,
            kit_item_slug=kit_item_slug,
        ),
        model=prompt_model,
        api_key=api_key,
        api_base=api_base,
        proxy=proxy,
        kind="image",
    )
    plan.prompt = crafted["prompt"]
    plan.prompt_source = "llm"
    return plan


def _load_gamefactory_config() -> dict[str, Any]:
    config_path = Path.home() / ".gamefactory" / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def build_animation_pipeline(
    project: ProjectContext,
    spec: AssetSpec,
    assets: list[AssetSpec],
    *,
    craft: bool = True,
    prompt_model: str = DEFAULT_PROMPT_MODEL,
    api_key: str | None = None,
    api_base: str | None = None,
    proxy: str | None = None,
    config: dict[str, Any] | None = None,
) -> PromptPlan:
    """Plan animation workflow: video first, img2img as fallback."""
    if spec.type != AssetType.CHARACTER or not spec.action:
        raise ValueError(
            "Animation planning requires a character asset with an 'action' field."
        )

    method = spec.animation_method
    if method not in (ANIMATION_METHOD_VIDEO, ANIMATION_METHOD_IMG2IMG):
        raise ValueError(
            f"animation_method must be '{ANIMATION_METHOD_VIDEO}' or "
            f"'{ANIMATION_METHOD_IMG2IMG}', got '{method}'."
        )

    ref_name = spec.reference_asset or spec.name
    ref_spec = find_asset(assets, ref_name) if ref_name != spec.name else spec
    if ref_spec.type != AssetType.CHARACTER:
        raise ValueError(f"Animation reference '{ref_name}' must be type 'character'.")

    action = spec.action.strip() or "smooth walk cycle to the right"

    if craft:
        if not api_key or not api_base:
            raise PromptCraftError(
                "Animation prompt crafting requires an API key. "
                "See resources/skills/asset-planner.md for the workflow."
            )
        anim_context = build_role_context(project, spec)
        anim_context["asset"]["action"] = action
        crafted = craft_asset_prompt(
            context=anim_context,
            model=prompt_model,
            api_key=api_key,
            api_base=api_base,
            proxy=proxy,
            kind="animation",
        )
        video_prompt = crafted["video_prompt"]
        prompt_source = "llm"
    else:
        video_prompt = None
        prompt_source = "scaffold_only"

    if method == ANIMATION_METHOD_VIDEO:
        from video_config import video_settings_from_asset_spec

        cfg = config if config is not None else _load_gamefactory_config()
        video = video_settings_from_asset_spec(cfg, spec)
        sprite_frames = spec.sprite_frames if spec.sprite_frames > 0 else 8
        duration = video["duration"]
        return PromptPlan(
            asset_name=spec.name,
            asset_type="character_animation",
            prompt=None,
            prompt_source=prompt_source,
            skill_refs=list(ROLE_SKILLS[PROMPT_CRAFTER_ROLE]),
            video_prompt=video_prompt,
            video_model=video["model"],
            video_duration=duration,
            video_resolution=video["resolution"],
            video_ratio=video["ratio"],
            video_generate_audio=video["generate_audio"],
            video_watermark=video["watermark"],
            reference_image=ref_name,
            negative_hints=[
                "Never generate a multi-frame spritesheet from one image prompt.",
                "Preferred path: reference still → video → split frames → video matte-frames (AI).",
            ],
            validation={"forbidden_patterns": ["spritesheet", "multiple_action_frames"]},
            pipeline=[
                {
                    "step": "generate_image",
                    "asset": ref_name,
                    "note": "character reference still (must pass pure-white validate); save as raw — do NOT trim",
                    "output_suffix": "_raw",
                },
                {
                    "step": "video_generate",
                    "model": video["model"],
                    "prompt": video_prompt,
                    "duration": duration,
                    "resolution": video["resolution"],
                    "ratio": video["ratio"],
                    "generate_audio": video["generate_audio"],
                    "watermark": video["watermark"],
                    "reference_asset": ref_name,
                    "reference_use_raw": True,
                    "note": "Pass image-generate raw PNG to Seedance — never trim/crop before i2v",
                },
                {"step": "video_split_frames", "frames": sprite_frames, "skip_lead_ratio": 0.25},
                {"step": "video_matte_frames", "engine": "ai", "trim": False, "batch": True},
            ],
            requires_reference_image=True,
            requires_background_removal=True,
            animation_method=ANIMATION_METHOD_VIDEO,
        )

    pose_spec = AssetSpec(
        name=spec.name,
        id=spec.id or "",
        type=AssetType.CHARACTER_POSE,
        action=action,
        reference_asset=ref_name,
    )
    plan = build_prompt(
        project,
        pose_spec,
        craft=craft,
        prompt_model=prompt_model,
        api_key=api_key,
        api_base=api_base,
        proxy=proxy,
    )
    plan.animation_method = ANIMATION_METHOD_IMG2IMG
    plan.pipeline = [
        {"step": "generate_image", "asset": ref_name},
        {"step": "generate_image", "asset": spec.name, "method": "img2img"},
        {"step": "validate"},
        {"step": "remove_bg", "mode": "color"},
    ]
    return plan


def _validation_spec(asset_type: AssetType, **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"asset_type": asset_type.value, **extra}
    if asset_type in (AssetType.CHARACTER, AssetType.CHARACTER_POSE):
        base.update(
            {
                "require_pure_white_background": True,
                "max_subject_regions": 1,
                "forbid_spritesheet_layout": True,
            }
        )
    elif asset_type == AssetType.ICON_KIT:
        base.update(
            {
                "require_pure_white_background": True,
                "max_subject_regions": 1,
                "forbid_spritesheet_layout": True,
            }
        )
    elif asset_type == AssetType.BACKGROUND:
        base.update(
            {
                "require_light_background": False,
                "forbid_uniform_white_studio": True,
                "min_color_variance": 20.0,
            }
        )
    elif asset_type == AssetType.TEXTURE:
        base.update({"require_light_background": False})
    return base


def _parse_grid(grid: str) -> tuple[int, int]:
    from brief import parse_icon_grid

    return parse_icon_grid(grid)


def _corner_mean_rgb(img: np.ndarray, margin: int = 8) -> np.ndarray:
    h, w = img.shape[:2]
    m = min(margin, h // 4, w // 4)
    corners = [
        img[:m, :m],
        img[:m, -m:],
        img[-m:, :m],
        img[-m:, -m:],
    ]
    pixels = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
    return pixels.mean(axis=0)


def _count_subject_regions(gray: np.ndarray, min_area: int = 200) -> int:
    _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return sum(1 for c in contours if cv2.contourArea(c) >= min_area)


def _edge_strip_pixels(gray: np.ndarray, margin: int) -> np.ndarray:
    h, w = gray.shape[:2]
    m = max(1, min(margin, h // 2, w // 2))
    strips = [
        gray[:m, :].ravel(),
        gray[-m:, :].ravel(),
        gray[:, :m].ravel(),
        gray[:, -m:].ravel(),
    ]
    return np.concatenate(strips)


def _corner_pixels(gray: np.ndarray, margin: int = 8) -> np.ndarray:
    h, w = gray.shape[:2]
    m = min(margin, h // 4, w // 4)
    corners = [
        gray[:m, :m],
        gray[:m, -m:],
        gray[-m:, :m],
        gray[-m:, -m:],
    ]
    return np.concatenate([c.ravel() for c in corners])


PURE_WHITE_BACKDROP_PROBE_MIN = 240


def _backdrop_probe_points(h: int, w: int) -> list[tuple[int, int]]:
    """Relative probe coords — corners and edge midpoints, never image center."""
    coords = [
        (0.10, 0.10),
        (0.50, 0.08),
        (0.90, 0.10),
        (0.08, 0.50),
        (0.92, 0.50),
        (0.10, 0.90),
        (0.50, 0.92),
        (0.90, 0.90),
    ]
    return [(int(w * xf), int(h * yf)) for xf, yf in coords]


def _subject_mask(gray: np.ndarray, *, threshold: int = 245, min_area: int = 200) -> np.ndarray:
    """Binary mask of foreground subject blobs (for background QA)."""
    _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(gray, dtype=np.uint8)
    for contour in contours:
        if cv2.contourArea(contour) >= min_area:
            cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)
    if mask.any():
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def _check_pure_white_background(
    img: np.ndarray,
    *,
    white_threshold: int = PURE_WHITE_THRESHOLD,
    edge_min_white_ratio: float = PURE_WHITE_EDGE_MIN_RATIO,
    edge_max_dark_ratio: float = PURE_WHITE_EDGE_MAX_DARK_RATIO,
    corner_max_std: float = PURE_WHITE_CORNER_MAX_STD,
    background_min_white_ratio: float = 0.90,
    background_mean_min: float = 238.0,
) -> tuple[bool, list[dict[str, Any]]]:
    """Heuristic: studio matting requires near-uniform pure white backdrop."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    margin = max(8, min(h, w) // 30)

    corner_rgb = _corner_mean_rgb(img)
    corner_brightness = float(corner_rgb.mean())
    corner_pixels = _corner_pixels(gray, margin=margin)
    corner_std = float(np.std(corner_pixels))

    edge_pixels = _edge_strip_pixels(gray, margin)
    edge_white_ratio = float(np.mean(edge_pixels >= white_threshold))
    edge_dark_ratio = float(np.mean(edge_pixels < 220))

    subject = _subject_mask(gray)
    probes = _backdrop_probe_points(h, w)
    probe_values = [
        int(gray[y, x]) for x, y in probes if subject[y, x] == 0
    ]
    if len(probe_values) < 3:
        probe_values = [
            int(gray[y, x])
            for x, y in probes
        ]
    background_pixels = gray[subject == 0]
    if background_pixels.size == 0:
        background_white_ratio = 0.0
        background_mean = 0.0
        background_dark_ratio = 1.0
    else:
        background_white_ratio = float(np.mean(background_pixels >= white_threshold))
        background_mean = float(background_pixels.mean())
        background_dark_ratio = float(np.mean(background_pixels < 220))

    probe_white_ratio = (
        float(np.mean(np.array(probe_values) >= white_threshold))
        if probe_values
        else 0.0
    )
    probe_dark_hits = sum(1 for v in probe_values if v < 200)

    corner_white = corner_brightness >= white_threshold
    edge_white = edge_white_ratio >= edge_min_white_ratio
    no_dark_frame = (
        edge_dark_ratio <= edge_max_dark_ratio
        and background_dark_ratio <= edge_max_dark_ratio
        and probe_dark_hits <= 2
    )
    uniform_corners = corner_std <= corner_max_std
    backdrop_white = (
        background_white_ratio >= background_min_white_ratio
        and background_mean >= background_mean_min
        and probe_white_ratio >= 0.80
    )

    checks = [
        {"check": "corner_brightness", "value": corner_brightness, "min": white_threshold},
        {"check": "corner_uniformity_std", "value": corner_std, "max": corner_max_std},
        {"check": "edge_white_ratio", "value": edge_white_ratio, "min": edge_min_white_ratio},
        {"check": "edge_dark_ratio", "value": edge_dark_ratio, "max": edge_max_dark_ratio},
        {
            "check": "background_white_ratio",
            "value": background_white_ratio,
            "min": background_min_white_ratio,
        },
        {"check": "background_mean_brightness", "value": background_mean, "min": background_mean_min},
        {"check": "background_dark_ratio", "value": background_dark_ratio, "max": edge_max_dark_ratio},
        {
            "check": "backdrop_probe_brightness",
            "values": probe_values,
            "min": white_threshold,
            "white_ratio": probe_white_ratio,
        },
        {
            "check": "require_pure_white_background",
            "passed": (
                corner_white
                and edge_white
                and no_dark_frame
                and uniform_corners
                and backdrop_white
            ),
        },
    ]
    passed = bool(checks[-1]["passed"])
    return passed, checks


def _looks_like_spritesheet(gray: np.ndarray, min_area: int = 200) -> bool:
    """Heuristic: several similar-width blobs in a horizontal row."""
    _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) >= min_area]
    if len(boxes) < 3:
        return False
    boxes.sort(key=lambda b: b[0])
    widths = [b[2] for b in boxes]
    if max(widths) - min(widths) > max(widths) * 0.5:
        return False
    ys = [b[1] for b in boxes]
    return max(ys) - min(ys) < gray.shape[0] * 0.15


def validate_image(
    image_path: Path,
    asset_type: AssetType | str,
    rules: dict[str, Any] | None = None,
) -> ValidationResult:
    """Run OpenCV heuristics for asset-type-specific QA."""
    if isinstance(asset_type, str):
        asset_type = AssetType(asset_type)

    rules = rules or _validation_spec(asset_type)
    img = cv2.imread(str(image_path))
    if img is None:
        return ValidationResult(
            ok=False,
            asset_type=asset_type.value,
            checks=[],
            message=f"Cannot read image: {image_path}",
        )

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    checks: list[dict[str, Any]] = []
    ok = True

    corner_rgb = _corner_mean_rgb(img)
    checks.append({"check": "corner_brightness", "value": float(corner_rgb.mean())})

    retry_hints: list[str] = []
    next_action: str | None = None

    if rules.get("require_pure_white_background"):
        passed, pure_checks = _check_pure_white_background(img)
        checks.extend(pure_checks)
        ok = ok and passed
        if not passed:
            retry_hints = list(PURE_WHITE_BG_RETRY_HINTS)
            next_action = "prompt_crafter_regenerate"

    elif rules.get("require_light_background"):
        corner_brightness = float(_corner_mean_rgb(img).mean())
        passed = corner_brightness >= 200
        checks.append({"check": "require_light_background", "passed": passed, "min": 200})
        ok = ok and passed

    if rules.get("forbid_uniform_white_studio"):
        passed = float(corner_rgb.mean()) < 245 or float(np.std(img)) > 25
        checks.append({"check": "forbid_uniform_white_studio", "passed": passed})
        ok = ok and passed

    regions = _count_subject_regions(gray)
    checks.append({"check": "subject_regions", "value": regions})

    if rules.get("max_subject_regions") is not None:
        passed = regions <= int(rules["max_subject_regions"])
        checks.append(
            {
                "check": "max_subject_regions",
                "passed": passed,
                "max": rules["max_subject_regions"],
            }
        )
        ok = ok and passed

    if rules.get("min_subject_regions") is not None:
        passed = regions >= int(rules["min_subject_regions"])
        checks.append(
            {
                "check": "min_subject_regions",
                "passed": passed,
                "min": rules["min_subject_regions"],
            }
        )
        ok = ok and passed

    if rules.get("forbid_spritesheet_layout"):
        sheet = _looks_like_spritesheet(gray)
        checks.append({"check": "forbid_spritesheet_layout", "passed": not sheet})
        if sheet:
            ok = False

    if rules.get("min_color_variance") is not None:
        variance = float(np.std(img))
        passed = variance >= float(rules["min_color_variance"])
        checks.append(
            {
                "check": "min_color_variance",
                "passed": passed,
                "value": variance,
                "min": rules["min_color_variance"],
            }
        )
        ok = ok and passed

    if not ok:
        if rules.get("require_pure_white_background") and next_action:
            msg = (
                "Background is not pure white — block matting pipeline. "
                "Do not run trim/remove-bg. Return to prompt-crafter, adjust prompt, regenerate."
            )
        elif rules.get("forbid_spritesheet_layout") and _looks_like_spritesheet(gray):
            msg = (
                "Image looks like a multi-frame spritesheet. "
                "Use video generation for actions, or img2img for a single pose frame."
            )
        else:
            msg = f"Validation failed for asset type '{asset_type.value}'."
    else:
        msg = f"Validation passed for asset type '{asset_type.value}'."

    return ValidationResult(
        ok=ok,
        asset_type=asset_type.value,
        checks=checks,
        message=msg,
        next_action=next_action,
        retry_hints=retry_hints,
    )


def plan_all(
    project: ProjectContext,
    assets: list[AssetSpec],
    *,
    craft: bool = True,
    prompt_model: str = DEFAULT_PROMPT_MODEL,
    api_key: str | None = None,
    api_base: str | None = None,
    proxy: str | None = None,
) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for spec in assets:
        if spec.action and spec.type == AssetType.CHARACTER:
            plans.append(
                build_animation_pipeline(
                    project,
                    spec,
                    assets,
                    craft=craft,
                    prompt_model=prompt_model,
                    api_key=api_key,
                    api_base=api_base,
                    proxy=proxy,
                ).to_dict()
            )
        else:
            plans.append(
                build_prompt(
                    project,
                    spec,
                    craft=craft,
                    prompt_model=prompt_model,
                    api_key=api_key,
                    api_base=api_base,
                    proxy=proxy,
                ).to_dict()
            )
    return plans
