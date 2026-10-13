"""Portable image-first fish-volume handoffs and deterministic verification.

Only handoffs, assets manifests and validation reports carry state. Profiles are
bounded declarative geometry; execution always uses the bundled Blender script.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import shlex
from datetime import datetime, timezone
import struct
import subprocess
import uuid
from collections import Counter
from dataclasses import asdict
from typing import Any

from PIL import Image

from asset_review import get_review, resolve_canonical_path
from assets_manifest import load_assets_manifest
from brief import find_asset, load_brief_full
from project_paths import default_paths_for_brief

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDER = REPO_ROOT / "resources/scripts/volume-fish/build_fish.py"
CHECKS = ("closed_mesh", "normalized_weights", "finite_glb", "animation_loop",
          "texture_original_resolution", "texture_nearest", "roughness_contract", "root_motion")


class VolumeError(ValueError):
    def __init__(self, message: str, *, code: str = "manifest_invalid", status: str = "blocked"):
        super().__init__(message)
        self.code, self.status = code, status


def require(condition: Any, message: str) -> None:
    if not condition:
        raise VolumeError(message)


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    require(isinstance(data, dict), f"JSON must be an object: {path}")
    return data


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def resolve_file(value: Any, base: Path) -> Path:
    require(isinstance(value, str) and bool(value.strip()), "An explicit file path is required")
    # Accept the running platform's absolute paths and either relative separator.
    # A Windows drive/UNC path cannot be silently reinterpreted on Unix.
    require(not (os.name != "nt" and PureWindowsPath(value).is_absolute()), "Windows absolute path requires a Windows host")
    if value.startswith("repo://"):
        value, base = value[len("repo://"):], REPO_ROOT
        require(not Path(value).is_absolute(), "repo:// requires a relative path")
    normalized = value.replace("\\", "/")
    path = Path(normalized).expanduser()
    if not path.is_absolute():
        require(".." not in path.parts, f"Relative path traversal is not allowed: {value}")
        path = base / path
    require(path.is_file(), f"File not found: {path}")
    return path.resolve()


def image_info(path: Path, *, transparent: bool = False) -> dict:
    with Image.open(path) as image:
        require(image.format == "PNG", f"Source/style image must be a PNG: {path}")
        image.load()
        if transparent:
            low, high = image.convert("RGBA").getchannel("A").getextrema()
            require(low < 255 and high > 0, "Canonical source must contain both visible pixels and transparency")
        return {"path": str(path), "sha256": sha(path), "width": image.width, "height": image.height}


def keys(obj: Any, allowed: set[str], required: set[str], label: str) -> dict:
    require(isinstance(obj, dict), f"{label} must be an object")
    require(not (set(obj) - allowed), f"Unknown {label} fields: {sorted(set(obj) - allowed)}")
    require(required <= set(obj), f"Missing {label} fields: {sorted(required - set(obj))}")
    return obj


def number(value: Any, low: float, high: float, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            and low <= value <= high, f"{label} must be finite in [{low}, {high}]")
    return float(value)


def point(value: Any, length: int, low: float, high: float, label: str) -> None:
    require(isinstance(value, list) and len(value) == length, f"{label} must have {length} coordinates")
    for v in value:
        number(v, low, high, label)


def validate_profile(data: dict, path: Path) -> tuple[dict, dict]:
    fields = {"schema_version", "species", "display_name", "coordinate_space", "source_aspect_ratio",
              "profile_review_status", "body", "rig", "fins", "eyes", "barbels", "animation", "notes", "style", "real_length_cm", "body_uv_patches", "head_projection", "dorsal_projection", "ventral_projection", "cephalofoil"}
    keys(data, fields, fields - {"eyes", "barbels", "notes", "body_uv_patches", "head_projection", "dorsal_projection", "ventral_projection", "cephalofoil"}, "profile")
    require(data["schema_version"] == 1, "Unsupported profile schema")
    require(isinstance(data["species"], str) and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", data["species"]), "Invalid species identifier")
    require(isinstance(data["display_name"], str) and 0 < len(data["display_name"]) <= 100, "display_name is required")
    require(data["coordinate_space"] == "normalized_source_top_left", "Unsupported profile coordinates")
    require(data["profile_review_status"] == "approved", "Profile geometry must be calibrated to the source image and approved")
    number(data["source_aspect_ratio"], .1, 20, "source_aspect_ratio")
    number(data["real_length_cm"], .1, 1000, "real_length_cm")
    body = keys(data["body"], {"sections", "rings", "radial"}, {"sections", "rings", "radial"}, "body")
    require(isinstance(body["sections"], list) and 4 <= len(body["sections"]) <= 128, "body requires 4–128 sections")
    previous = -1.0
    for section in body["sections"]:
        point(section, 4, 0, 1, "body section")
        require(section[0] > previous and section[1] < section[2], "Body sections need increasing u and top < bottom")
        number(section[3], .0001, .3, "body half depth")
        previous = section[0]
    for field, low, high in (("rings", 16, 256), ("radial", 12, 96)):
        number(body[field], low, high, field)
        require(type(body[field]) is int, f"{field} must be an integer")
    patches = data.get("body_uv_patches", [])
    if "cephalofoil" in data:
        head = keys(data["cephalofoil"], {"sections", "center_v", "mouth"}, {"sections", "center_v"}, "cephalofoil")
        if "mouth" in head:
            mouth = keys(head["mouth"], {"points", "width", "source_uv"}, {"points", "width", "source_uv"}, "mouth")
            require(3 <= len(mouth["points"]) <= 32, "Invalid mouth path")
            for p in mouth["points"]: point(p, 3, -.5, 1, "mouth point")
            number(mouth["width"], .0001, .005, "mouth width")
            point(mouth["source_uv"], 2, 0, 1, "mouth source UV")
        number(head["center_v"], 0, 1, "head center")
        require(5 <= len(head["sections"]) <= 64, "Head needs 5–64 lateral sections")
        previous = -.5
        for row in head["sections"]:
            point(row, 4, -.3, 1, "head section")
            require(previous < row[0] <= .3 and 0 <= row[1] < row[2] <= 1 and .001 <= row[3] <= .05, "Invalid lateral head section")
            previous = row[0]
    require(isinstance(patches, list) and len(patches) <= 16, "At most 16 body UV patches")
    for patch in patches:
        keys(patch, {"polygon", "offset"}, {"polygon", "offset"}, "UV patch")
        require(isinstance(patch["polygon"], list) and 3 <= len(patch["polygon"]) <= 128, "UV patch needs 3–128 points")
        for p in patch["polygon"]:
            point(p, 2, 0, 1, "UV patch point")
        point(patch["offset"], 2, -1, 1, "UV patch offset")
    if "head_projection" in data:
        fields = {"start_u", "end_u", "normal_threshold", "side_limit", "source_rect", "model_depth_range", "model_v_range", "uv_patches"}
        head = keys(data["head_projection"], fields, fields - {"uv_patches"}, "head projection")
        for key in ("start_u", "end_u"):
            number(head[key], 0, 1, key)
        require(head["start_u"] != head["end_u"], "Head projection u range must be nonzero")
        number(head["normal_threshold"], -1, .95, "head projection normal threshold")
        number(head["side_limit"], .1, 1, "head projection side limit")
        point(head["source_rect"], 4, 0, 1, "front source rect")
        rect = head["source_rect"]
        require(rect[0] < rect[2] and rect[1] < rect[3], "Front source rectangle must increase")
        for key, low, high in (("model_depth_range", -.5, .5), ("model_v_range", 0, 1)):
            point(head[key], 2, low, high, key)
            require(head[key][0] < head[key][1], f"{key} must increase")
        patches = head.get("uv_patches", [])
        require(isinstance(patches, list) and len(patches) <= 16, "At most 16 head UV patches")
        for patch in patches:
            keys(patch, {"polygon", "offset"}, {"polygon", "offset"}, "head UV patch")
            require(isinstance(patch["polygon"], list) and 3 <= len(patch["polygon"]) <= 128, "Head UV patch needs 3–128 points")
            point(patch["offset"], 2, -1, 1, "head UV patch offset")
            for p in patch["polygon"]:
                point(p, 2, 0, 1, "head UV patch point")
                point([p[i] + patch["offset"][i] for i in range(2)], 2, 0, 1, "head UV donor point")
    for projection_name in ("dorsal_projection", "ventral_projection"):
        if projection_name not in data:
            continue
        surface = keys(data[projection_name], {"start_u", "end_u", "normal_threshold", "source_rect", "model_depth_range", "head_source_rect", "sections"},
                       {"start_u", "end_u", "normal_threshold", "source_rect", "model_depth_range"}, projection_name.replace("_", " "))
        for key in ("start_u", "end_u"):
            number(surface[key], 0, 1, key)
        require(surface["start_u"] != surface["end_u"], f"{projection_name} u range must be nonzero")
        number(surface["normal_threshold"], 0, .95, f"{projection_name} normal threshold")
        point(surface["source_rect"], 4, 0, 1, f"{projection_name} source rect")
        rect = surface["source_rect"]
        require(rect[0] < rect[2] and rect[1] < rect[3], f"{projection_name} source rectangle must increase")
        if "head_source_rect" in surface:
            point(surface["head_source_rect"], 4, 0, 1, "head surface rect")
            r = surface["head_source_rect"]
            require(r[0] < r[2] and r[1] < r[3], "Head surface rectangle must increase")
        point(surface["model_depth_range"], 2, -.5, .5, f"{projection_name} model depth range")
        require(surface["model_depth_range"][0] < surface["model_depth_range"][1], f"{projection_name} model depth range must increase")
        if "sections" in surface:
            rows=surface["sections"]
            require(isinstance(rows,list) and 4 <= len(rows) <= 128, "Surface mapping needs 4–128 sections")
            previous=-1
            for row in rows:
                point(row,5,0,1,"surface mapping section")
                require(row[0]>previous and row[2]<row[3] and .0001<=row[4]<=.3,"Invalid surface mapping section")
                previous=row[0]
    rig = keys(data["rig"], {"spine"}, {"spine"}, "rig")
    require(isinstance(rig["spine"], list) and 4 <= len(rig["spine"]) <= 32, "rig requires 4–32 spine points")
    for p in rig["spine"]:
        point(p, 2, 0, 1, "spine")
    require(isinstance(data["fins"], list) and len(data["fins"]) <= 32, "At most 32 fins")
    names = set()
    for fin in data["fins"]:
        allowed = {"name", "polygon", "anchor", "tip", "paired", "root_depth", "tip_depth", "thickness", "amplitude", "phase", "axis", "vertical_scale", "opaque", "source_rect"}
        keys(fin, allowed, allowed - {"vertical_scale", "opaque", "source_rect"}, "fin")
        if "source_rect" in fin:
            point(fin["source_rect"], 4, 0, 1, "fin donor rectangle")
            r=fin["source_rect"]
            require(r[0]<r[2] and r[1]<r[3] and fin.get("opaque"), "Fin donor requires opaque and increasing rectangle")
        number(fin.get("vertical_scale", 1), 0, 1, "fin vertical scale")
        require(type(fin.get("opaque", False)) is bool, "Fin opaque must be boolean")
        require(isinstance(fin["name"], str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", fin["name"]) and fin["name"] not in names, "Fin names must be unique identifiers")
        names.add(fin["name"])
        require(isinstance(fin["polygon"], list) and 3 <= len(fin["polygon"]) <= 128, "Fin needs 3–128 polygon points")
        for p in fin["polygon"] + [fin["anchor"], fin["tip"]]:
            point(p, 2, 0, 1, "fin point")
        require(type(fin["paired"]) is bool, "paired must be boolean")
        for key, low, high in (("root_depth", 0, .3), ("tip_depth", 0, .5), ("thickness", .0001, .02), ("amplitude", 0, .5), ("phase", -20, 20)):
            number(fin[key], low, high, key)
        point(fin["axis"], 3, -1, 1, "fin axis")
        require(sum(v * v for v in fin["axis"]) > 0, "Fin axis must be nonzero")
    if data.get("eyes") is not None:
        base = {"center", "radius", "depth"}
        patch_fields = {"source_rect", "thickness", "surface_offset"}
        eyes = keys(data["eyes"], base | {"mode", "source_uv"} | patch_fields, base, "eyes")
        if "source_uv" in eyes: point(eyes["source_uv"], 2, 0, 1, "eye source UV")
        point(eyes["center"], 2, 0, 1, "eye center")
        number(eyes["radius"], .001, .05, "eye radius")
        number(eyes["depth"], .001, .2, "eye depth")
        if "mode" in eyes:
            require(eyes["mode"] == "surface_patch", "The only explicit eye mode is surface_patch; omit mode for existing behavior")
            require(patch_fields <= set(eyes), "Surface patch eyes require source_rect, thickness and surface_offset")
            point(eyes["source_rect"], 4, 0, 1, "eye source rectangle")
            rect = eyes["source_rect"]
            require(rect[0] < rect[2] and rect[1] < rect[3], "Eye source rectangle must increase")
            # The native crop's aspect controls geometry, not just UVs. Divide
            # its spans first so a subnormal width cannot underflow a denominator.
            half_height = (eyes["radius"] / data["source_aspect_ratio"]) * ((rect[3] - rect[1]) / (rect[2] - rect[0]))
            require(math.isfinite(half_height) and 0 < half_height <= .05, "Derived eye patch half height must be finite in (0, 0.05]")
            number(eyes["thickness"], .0001, .01, "eye patch thickness")
            number(eyes["surface_offset"], 0, .003, "eye patch surface offset")
        else:
            require(not (patch_fields & set(eyes)), "Eye patch fields require mode=surface_patch")
    barbels = data.get("barbels", [])
    require(isinstance(barbels, list) and len(barbels) <= 8, "At most 8 barbels")
    for barbel in barbels:
        keys(barbel, {"name", "path", "radius"}, {"name", "path", "radius"}, "barbel")
        require(isinstance(barbel["name"], str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", barbel["name"]), "Invalid barbel name")
        require(isinstance(barbel["path"], list) and 2 <= len(barbel["path"]) <= 128, "Barbel path needs 2–128 points")
        for p in barbel["path"]:
            point(p, 3, -.5, 1, "barbel point")
            number(p[0], 0, 1, "barbel u")
            number(p[1], 0, 1, "barbel v")
            number(p[2], -.5, .5, "barbel depth")
        number(barbel["radius"], .0001, .01, "barbel radius")
    anim = keys(data["animation"], {"fps", "period_seconds", "body_amplitudes", "phase_step"}, {"fps", "period_seconds", "body_amplitudes", "phase_step"}, "animation")
    number(anim["fps"], 12, 60, "fps")
    require(type(anim["fps"]) is int, "fps must be an integer")
    number(anim["period_seconds"], .5, 10, "period_seconds")
    number(anim["phase_step"], 0, 3, "phase_step")
    require(isinstance(anim["body_amplitudes"], list) and len(anim["body_amplitudes"]) == len(rig["spine"]), "One body amplitude per spine point is required")
    for amplitude in anim["body_amplitudes"]:
        number(amplitude, 0, .5, "body amplitude")
    require(isinstance(data.get("notes", []), list) and all(isinstance(x, str) for x in data.get("notes", [])), "notes must be strings")
    style = keys(data["style"], {"pixel_art", "reference_image", "texture_filter", "roughness"}, {"pixel_art", "reference_image", "texture_filter", "roughness"}, "style")
    require(style["pixel_art"] is True and style["texture_filter"] == "nearest" and style["roughness"] == 1.0, "Explicit pixel_art=true, nearest texture and roughness=1.0 contract required")
    reference = image_info(resolve_file(style["reference_image"], path.parent))
    return data, reference


def generation_path(value: str) -> Path:
    """Foundry command paths are relative to cli/, confined to the repository."""
    require(isinstance(value, str) and bool(value), "Generation reference path missing")
    candidate = Path(value.replace("\\", "/")).expanduser()
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / "cli" / candidate).resolve()
        require(candidate.is_relative_to(REPO_ROOT), "Generation path escapes repository")
    return resolve_file(str(candidate), REPO_ROOT)


def generation_reference(plan: Path | None, raw: Path, task_id: str, asset: str, brief: Path) -> dict:
    content = read_json(plan).get("plan", {}) if plan else {}
    require(isinstance(content, dict), "Generation plan must contain an object")
    required = content.get("requires_reference_image", False)
    require(type(required) is bool, "requires_reference_image must be boolean")
    value = content.get("reference_image")
    evidence = None
    if value:
        reference = generation_path(value)
        evidence = {"kind": "prompt_plan", "plan_path": str(plan)}
    elif required:
        ledger = Path(default_paths_for_brief(brief)["manifest"])
        pipeline = read_json(ledger)
        tasks = pipeline.get("tasks", [])
        require(isinstance(tasks, list), "Pipeline tasks must be a list")
        matching = [t for t in tasks if isinstance(t, dict) and t.get("id") == task_id]
        require(len(matching) == 1, "Required generation reference lacks matching pipeline task evidence")
        task = matching[0]
        require(task.get("asset") == asset and task.get("step") == "image.generate" and task.get("status") == "done"
                and task.get("result", {}).get("exit_code") == 0, "Generation reference task was not successfully completed for this asset")
        command = task.get("command")
        require(isinstance(command, str), "Generation command missing")
        lexer = shlex.shlex(command, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        # Foundry emits mixed-separator Windows paths. Backslashes are path
        # characters here, not shell escapes; provenance never executes them.
        if os.name == "nt": lexer.escape = ""
        argv = list(lexer)
        require("image" in argv and argv[argv.index("image") + 1:argv.index("image") + 2] == ["generate"], "Not an image generation command")
        def flag(name):
            require(argv.count(name) == 1 and argv.index(name) + 1 < len(argv), f"Generation command needs one {name}")
            return argv[argv.index(name) + 1]
        require(generation_path(flag("--plan-file")) == plan and generation_path(flag("--output")) == raw,
                "Generation command plan/raw output does not match source provenance")
        reference = generation_path(flag("--reference-image"))
        evidence = {"kind": "pipeline_task", "manifest_path": str(ledger.resolve()), "task_id": task_id,
                    "command_sha256": hashlib.sha256(command.encode()).hexdigest()}
    else:
        reference = None
    info = image_info(reference) if reference else None
    return {"generation_reference_required": required,
            "generation_reference_image": info["path"] if info else None,
            "generation_reference_sha256": info["sha256"] if info else None,
            "generation_reference_evidence": evidence}


def accepted_source(manifest_path: Path, asset: str, brief_path: Path) -> tuple[dict, dict, dict]:
    manifest = load_assets_manifest(manifest_path)
    require(resolve_file(manifest.get("brief"), REPO_ROOT) == brief_path.resolve(), "Assets manifest belongs to another Brief")
    entry = (manifest.get("assets") or {}).get(asset)
    require(isinstance(entry, dict), f"Unknown asset: {asset}")
    review = get_review(manifest, asset_name=asset)
    require(review["status"] == "accepted", "Source image requires accepted assets review")
    require(review["source"] != "local_file", "A local replacement is not proof of Foundry image generation")
    stages = [s for s in entry.get("stages", []) if isinstance(s, dict) and s.get("status") == "done"]
    raw_stages = [s for s in stages if s.get("stage") == "image.raw" and s.get("task_id")]
    require(raw_stages, "Foundry image.generate provenance missing: a completed image.raw stage is required")
    canonical = resolve_canonical_path({**entry, "stages": stages})
    require(canonical, "Accepted canonical image path is missing")
    canonical_stage = next(s for s in stages if s.get("path_repo") == canonical)
    require(canonical_stage.get("stage") in {"image.nobg", "image.plate_locked"}, "Canonical source must be an accepted transparent still, not an animation or raw draft")
    source = image_info(resolve_file(canonical, REPO_ROOT), transparent=True)
    raw = raw_stages[-1]
    raw_info = image_info(resolve_file(raw.get("path_repo"), REPO_ROOT))
    plans = [s for s in stages if s.get("stage") == "prompt.plan"]
    plan = resolve_file(plans[-1]["path_repo"], REPO_ROOT) if plans else None
    source.update({"asset": asset, "raw_path": raw_info["path"], "raw_sha256": raw_info["sha256"],
                   "generation_task_id": raw["task_id"], "generation_stage": "image.raw",
                   "generation_command": "image.generate", "plan_path": str(plan) if plan else None,
                   "plan_sha256": sha(plan) if plan else None})
    source.update(generation_reference(plan, Path(raw_info["path"]), raw["task_id"], asset, brief_path))
    return source, review, entry


def expected_outputs(handoff_path: Path) -> dict:
    directory = handoff_path.parent / (handoff_path.stem + "-artifacts")
    return {"directory": str(directory), "blend": str(directory / "fish.blend"),
            "glb": str(directory / "fish.glb"), "validation_report": str(directory / "validation.json"),
            "review_dir": str(directory / "review"), "render_report": str(directory / "render.json")}


def plan_volume(brief: Path, assets_manifest: Path, asset: str, profile: Path, output: Path,
                front_assets_manifest: Path | None = None, front_asset: str | None = None,
                top_assets_manifest: Path | None = None, top_asset: str | None = None,
                bottom_assets_manifest: Path | None = None, bottom_asset: str | None = None) -> dict:
    brief, assets_manifest, profile, output = (p.expanduser().resolve() for p in (brief, assets_manifest, profile, output))
    require(not output.exists(), "Handoff already exists; choose a new output instead of overwriting state")
    require(output not in {brief, assets_manifest, profile}, "Output must not overwrite an input")
    brief_data = read_json(brief)
    meta = brief_data.get("brief_meta", {})
    require(isinstance(meta, dict) and meta.get("contract_version") == 1 and bool(meta.get("frozen_at")), "A frozen Brief with brief_meta is required")
    project, specs, _ = load_brief_full(brief)
    spec = find_asset(specs, asset)
    asset = spec.name
    source, review, _ = accepted_source(assets_manifest, asset, brief)
    profile_data, reference = validate_profile(read_json(profile), profile)
    require(abs(profile_data["source_aspect_ratio"] / (source["width"] / source["height"]) - 1) <= .02,
            "Profile aspect ratio differs from canonical source; recalibrate geometry")
    if spec.real_length_cm:
        require(abs(spec.real_length_cm - profile_data["real_length_cm"]) <= .001,
                "Profile real_length_cm differs from Brief")
    require(bool(project.art_direction.strip()), "Brief art_direction is required")
    data = {"schema_version": 1, "kind": "fish_volume_handoff", "status": "pending", "next_action": "run",
            "asset": asset, "assets_manifest": str(assets_manifest), "source_image": source["path"],
            "source": source, "source_review": review,
            "brief": {"path": str(brief), "sha256": sha(brief), "art_direction": project.art_direction, "tokens": project.art_tokens,
                      "asset_spec_sha256": hashlib.sha256(json.dumps(asdict(spec), sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()},
            "profile": str(profile), "profile_snapshot": {"path": str(profile), "sha256": sha(profile)},
            "style_contract": {"pixel_art": True, "source_sha256": source["sha256"],
                "style_reference_image": reference["path"], "style_reference_sha256": reference["sha256"],
                "texture_filter": "nearest", "roughness": 1.0},
            "real_length_cm": profile_data["real_length_cm"], "outputs": expected_outputs(output),
            "style_visual_review": "pending", "failures": []}
    require(bool(front_assets_manifest) == bool(front_asset), "--front-assets-manifest and --front-asset must be paired")
    require(bool(front_assets_manifest) == ("head_projection" in profile_data), "head_projection requires a front source; front source requires head_projection")
    if front_assets_manifest:
        front_manifest = front_assets_manifest.expanduser().resolve()
        front_source, front_review, front_brief = frozen_front(front_manifest, front_asset)
        data.update(front_source=front_source, front_source_image=front_source["path"], front_source_review=front_review,
                    front_assets_manifest=str(front_manifest), front_brief=front_brief)
    for label, manifest, aux_asset, projection, view in (
            ("top", top_assets_manifest, top_asset, "dorsal_projection", "top_down"),
            ("bottom", bottom_assets_manifest, bottom_asset, "ventral_projection", "bottom_up")):
        require(bool(manifest) == bool(aux_asset), f"--{label}-assets-manifest and --{label}-asset must be paired")
        require(bool(manifest) == (projection in profile_data), f"{projection} requires a {label} source; {label} source requires {projection}")
        if manifest:
            resolved = manifest.expanduser().resolve()
            aux_source, aux_review, aux_brief = frozen_view(resolved, aux_asset, view, label.capitalize())
            data.update({f"{label}_source": aux_source, f"{label}_source_image": aux_source["path"],
                         f"{label}_source_review": aux_review, f"{label}_assets_manifest": str(resolved),
                         f"{label}_brief": aux_brief})
    write_json(output, data)
    return data


def frozen_front(manifest: Path, asset: str) -> tuple[dict, dict, dict]:
    return frozen_view(manifest, asset, "front", "Front")


def frozen_view(manifest: Path, asset: str, required_view: str, label: str) -> tuple[dict, dict, dict]:
    ledger = load_assets_manifest(manifest)
    brief = resolve_file(ledger.get("brief"), REPO_ROOT)
    meta = read_json(brief).get("brief_meta", {})
    require(isinstance(meta, dict) and meta.get("contract_version") == 1 and bool(meta.get("frozen_at")), f"{label} source requires a frozen Brief")
    project, specs, _ = load_brief_full(brief)
    require(project.view == required_view, f"{label} source Brief must declare project.view={required_view}")
    spec = find_asset(specs, asset)
    source, review, _ = accepted_source(manifest, spec.name, brief)
    return source, review, {"path": str(brief), "sha256": sha(brief), "art_direction": project.art_direction, "tokens": project.art_tokens,
                           "asset_spec_sha256": hashlib.sha256(json.dumps(asdict(spec), sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()}


def fresh_handoff(path: Path) -> dict:
    path = path.expanduser().resolve()
    data = read_json(path)
    require(data.get("schema_version") == 1 and data.get("kind") == "fish_volume_handoff", "Unsupported volume handoff")
    expected = expected_outputs(path)
    require(data.get("outputs") == expected, "Handoff output paths must remain within its fixed artifact directory")
    # Reject symlink redirection even when the textual path still matches the handoff.
    directory = Path(expected["directory"])
    require(directory.resolve() == directory, "Output directory may not redirect through a symlink")
    for key, value in expected.items():
        target = Path(value)
        require(target.resolve() == target, f"Output {key} may not redirect through a symlink")
    brief = resolve_file(data["brief"]["path"], path.parent)
    profile = resolve_file(data["profile"], path.parent)
    require(data["profile_snapshot"]["path"] == str(profile), "Profile pointer changed")
    require(sha(brief) == data["brief"]["sha256"], "Brief changed after plan; create a fresh handoff")
    require(sha(profile) == data["profile_snapshot"]["sha256"], "Profile changed after plan; create a fresh handoff")
    profile_data, reference = validate_profile(read_json(profile), profile)
    require(bool(data.get("front_source")) == ("head_projection" in profile_data), "Front source/projection contract changed")
    if data.get("front_source"):
        front_source, _, front_brief = frozen_front(resolve_file(data["front_assets_manifest"], path.parent), data["front_source"]["asset"])
        require(front_source == data["front_source"] and data.get("front_source_image") == front_source["path"] and data.get("front_brief") == front_brief,
                "Front source/provenance/Brief changed after plan")
    else:
        require(not any(key in data for key in ("front_source_image", "front_assets_manifest", "front_brief", "front_source_review")), "Unexpected front source metadata")
    for label, projection, view in (("top", "dorsal_projection", "top_down"), ("bottom", "ventral_projection", "bottom_up")):
        source_key = f"{label}_source"
        require(bool(data.get(source_key)) == (projection in profile_data), f"{label.capitalize()} source/projection contract changed")
        if data.get(source_key):
            aux_source, _, aux_brief = frozen_view(resolve_file(data[f"{label}_assets_manifest"], path.parent),
                                                    data[source_key]["asset"], view, label.capitalize())
            require(aux_source == data[source_key] and data.get(f"{label}_source_image") == aux_source["path"]
                    and data.get(f"{label}_brief") == aux_brief, f"{label.capitalize()} source/provenance/Brief changed after plan")
        else:
            require(not any(key in data for key in (f"{label}_source_image", f"{label}_assets_manifest", f"{label}_brief", f"{label}_source_review")),
                    f"Unexpected {label} source metadata")
    source, review, _ = accepted_source(resolve_file(data["assets_manifest"], path.parent), data["asset"], brief)
    require(source == data["source"] and data["source_image"] == source["path"], "Source/provenance changed after plan; create a fresh handoff")
    style = data["style_contract"]
    require(style == {"pixel_art": True, "source_sha256": source["sha256"], "style_reference_image": reference["path"],
                      "style_reference_sha256": reference["sha256"], "texture_filter": "nearest", "roughness": 1.0},
            "Style reference or contract changed after plan; create a fresh handoff")
    require(data["real_length_cm"] == profile_data["real_length_cm"], "Physical length contract changed")
    project, specs, _ = load_brief_full(brief)
    spec = find_asset(specs, data["asset"])
    spec_hash = hashlib.sha256(json.dumps(asdict(spec), sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    require(data["brief"].get("asset_spec_sha256") == spec_hash, "Resolved Brief asset/shard changed after plan")
    require(data["brief"].get("art_direction") == project.art_direction and data["brief"].get("tokens") == project.art_tokens, "Brief art contract metadata changed")
    return data


def glb_document(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    require(len(raw) >= 20, "GLB is truncated")
    magic, version, length = struct.unpack_from("<4sII", raw)
    require(magic == b"glTF" and version == 2 and length == len(raw), "Invalid GLB header")
    cursor, doc, blob = 12, None, None
    while cursor < len(raw):
        require(cursor + 8 <= len(raw), "Truncated GLB chunk")
        size, kind = struct.unpack_from("<I4s", raw, cursor)
        cursor += 8
        require(cursor + size <= len(raw), "GLB chunk exceeds file")
        chunk = raw[cursor:cursor + size]
        if kind == b"JSON":
            require(doc is None, "Duplicate GLB JSON")
            doc = json.loads(chunk.decode("utf-8").rstrip("\0 "), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        elif kind == b"BIN\0":
            require(blob is None, "Duplicate GLB binary")
            blob = chunk
        cursor += size
    require(isinstance(doc, dict) and blob is not None, "GLB needs JSON and embedded binary")
    require(len(doc.get("buffers", [])) == 1 and "uri" not in doc["buffers"][0], "Only self-contained GLB buffers are accepted")
    require(doc["buffers"][0]["byteLength"] <= len(blob), "GLB binary is truncated")
    return doc, blob


def glb_checks(path: Path, source_path: Path, front_source_path: Path | None = None,
               surface_source_paths: tuple[Path, ...] = ()) -> dict:
    doc, blob = glb_document(path)
    components = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
    widths = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    decoded = {}

    def view_bytes(index: int) -> bytes:
        view = doc["bufferViews"][index]
        require(view.get("buffer", 0) == 0, "External GLB buffer")
        offset, length = view.get("byteOffset", 0), view["byteLength"]
        require(isinstance(offset, int) and isinstance(length, int) and 0 <= offset <= offset + length <= len(blob), "GLB view out of bounds")
        return blob[offset:offset + length]

    def accessor(index: int) -> list[tuple]:
        if index in decoded:
            return decoded[index]
        a = doc["accessors"][index]
        require("sparse" not in a, "Sparse accessor unsupported by fish validator")
        require(a["componentType"] in components and a["type"] in widths, "Unsupported fish accessor")
        fmt, size = components[a["componentType"]]
        width = widths[a["type"]]
        buf = view_bytes(a["bufferView"])
        offset = a.get("byteOffset", 0)
        stride = doc["bufferViews"][a["bufferView"]].get("byteStride", width * size)
        count = a["count"]
        require(type(count) is int and count > 0 and stride >= size * width and offset >= 0,
                "Invalid GLB accessor layout")
        require(offset + (count - 1) * stride + width * size <= len(buf), "GLB accessor exceeds buffer")
        values = [struct.unpack_from("<" + fmt * width, buf, offset + i * stride) for i in range(count)]
        if a.get("normalized") and a["componentType"] != 5126:
            maximum = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535, 5125: 4294967295}[a["componentType"]]
            values = [tuple(max(-1.0, x / maximum) for x in row) for row in values]
        require(all(math.isfinite(x) for row in values for x in row), "GLB contains non-finite numeric data")
        decoded[index] = values
        return values

    for i in range(len(doc.get("accessors", []))):
        accessor(i)
    require(doc.get("meshes") and doc.get("skins") and doc.get("animations"), "GLB needs actual meshes, skin and animation")
    for skin in doc["skins"]:
        require(skin.get("joints") and all(type(j) is int and 0 <= j < len(doc.get("nodes", [])) for j in skin["joints"]), "Invalid skin joint node")
    for mesh_index, mesh in enumerate(doc["meshes"]):
        skin_indices = [node["skin"] for node in doc.get("nodes", []) if node.get("mesh") == mesh_index and "skin" in node]
        require(skin_indices and all(type(i) is int and 0 <= i < len(doc["skins"]) for i in skin_indices), "Mesh has no valid skin binding")
        max_joint = min(len(doc["skins"][i]["joints"]) for i in skin_indices)
        edges = Counter()
        for primitive in mesh["primitives"]:
            require(primitive.get("mode", 4) == 4, "Fish mesh must use triangles")
            attrs = primitive["attributes"]
            positions = accessor(attrs["POSITION"])
            indices = [x[0] for x in accessor(primitive["indices"])] if "indices" in primitive else list(range(len(positions)))
            require(len(indices) % 3 == 0, "Triangle index count invalid")
            welded = [tuple(round(v, 7) for v in p) for p in positions]
            for i in range(0, len(indices), 3):
                tri = [welded[int(j)] for j in indices[i:i + 3]]
                require(len(set(tri)) == 3, "Degenerate fish triangle")
                for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                    edges[tuple(sorted((a, b)))] += 1
            require("WEIGHTS_0" in attrs and "JOINTS_0" in attrs, "All fish surfaces must be skinned")
            joints = accessor(attrs["JOINTS_0"])
            require(doc["accessors"][attrs["JOINTS_0"]]["componentType"] in {5121, 5123}
                    and len(joints) == len(positions) and all(len(row) == 4 and all(0 <= j < max_joint for j in row) for row in joints),
                    "Vertex references an invalid skin joint")
            weights = accessor(attrs["WEIGHTS_0"])
            require(len(weights) == len(positions) and all(len(row) == 4 and all(0 <= x <= 1 for x in row) and abs(sum(row) - 1) < .001 for row in weights), "Skin weights are not normalized")
        require(edges and all(n == 2 for n in edges.values()), "Fish GLB mesh is not closed/manifold")
    joint_nodes = {j for skin in doc["skins"] for j in skin["joints"]}
    parents = {child: i for i, node in enumerate(doc.get("nodes", [])) for child in node.get("children", [])}
    roots = set()
    for joint in joint_nodes:
        parent, seen = parents.get(joint), {joint}
        while parent is not None and parent not in joint_nodes:
            require(parent not in seen, "Cyclic GLB node hierarchy")
            seen.add(parent)
            parent = parents.get(parent)
        if parent is None:
            roots.add(joint)
    channels, animated_motion = 0, False
    for animation in doc["animations"]:
        for channel in animation.get("channels", []):
            sampler = animation["samplers"][channel["sampler"]]
            require(sampler.get("interpolation", "LINEAR") in {"LINEAR", "STEP"}, "Unsupported animation interpolation")
            times, values = accessor(sampler["input"]), accessor(sampler["output"])
            require(len(times) == len(values) and len(times) >= 2 and all(times[i][0] < times[i + 1][0] for i in range(len(times) - 1)), "Animation timeline invalid")
            first, last = values[0], values[-1]
            changing = any(max(abs(a - b) for a, b in zip(first, row)) > .00001 for row in values[1:])
            node = channel.get("target", {}).get("node")
            require(node in joint_nodes and node not in roots or not changing,
                    "Root/model carrier animation must remain stationary")
            animated_motion = animated_motion or changing
            error = max(abs(a - b) for a, b in zip(first, last))
            if channel.get("target", {}).get("path") == "rotation":
                error = min(error, max(abs(a + b) for a, b in zip(first, last)))
            require(error <= .0001, "Animation actual first/last keyframes do not loop")
            channels += 1
    require(channels > 0 and animated_motion, "No actual changing animated channels")
    sources = [source_path] + ([front_source_path] if front_source_path else []) + list(surface_source_paths)
    matching_by_source = []
    for source_path in sources:
        with Image.open(source_path) as source:
            source_rgba = source.convert("RGBA")
            matches = set()
            for image_index, image in enumerate(doc.get("images", [])):
                require("uri" not in image, "Texture must be embedded in GLB")
                with Image.open(io.BytesIO(view_bytes(image["bufferView"]))) as embedded:
                    if embedded.size == source_rgba.size and embedded.convert("RGBA").tobytes() == source_rgba.tobytes():
                        matches.add(image_index)
            require(matches, "Original-resolution source pixels are not embedded in GLB")
            matching_by_source.append(matches)
    allowed_images = set().union(*matching_by_source)
    require(allowed_images == set(range(len(doc.get("images", [])))), "GLB contains an undeclared source image")
    used_images = set()
    used_materials = {primitive.get("material") for mesh in doc["meshes"] for primitive in mesh["primitives"]}
    for material_index, material in enumerate(doc.get("materials", [])):
        pbr = material.get("pbrMetallicRoughness", {})
        require(pbr.get("roughnessFactor", 1.0) == 1.0 and pbr.get("metallicFactor", 1.0) == 0.0, "Material roughness/nonmetal contract violated")
        if "baseColorTexture" in pbr:
            tex = doc["textures"][pbr["baseColorTexture"]["index"]]
            require(tex.get("source") in allowed_images, "Material does not use an original source image")
            sampler = doc["samplers"][tex["sampler"]]
            require(sampler.get("magFilter") == 9728 and sampler.get("minFilter") == 9728, "Pixel-art texture must use nearest without mipmap blur")
            if material_index in used_materials:
                used_images.add(tex["source"])
    require(used_images == allowed_images and all(matches & used_images for matches in matching_by_source),
            "Every declared source texture must be used by actual mesh materials")
    return {key: True for key in CHECKS}


def validate_volume(handoff_path: Path, *, require_run: bool = False, check_visual: bool = True) -> tuple[dict, dict]:
    data = fresh_handoff(handoff_path)
    report = read_json(Path(data["outputs"]["validation_report"]))
    require(report.get("ok") is True and report.get("status") == "done", "Builder did not report successful completion")
    require(not report.get("failures"), "Builder report contains failures")
    require(require_run or data.get("status") == "done", "Handoff has not completed a successful build")
    require(bool(data.get("build_run_id")) and report.get("run_id") == data["build_run_id"], "Builder report belongs to an older run")
    require(report.get("source_sha256") == data["source"]["sha256"] and report.get("profile_sha256") == data["profile_snapshot"]["sha256"]
            and report.get("style_reference_sha256") == data["style_contract"]["style_reference_sha256"], "Builder input hashes do not match handoff")
    require(report.get("blend_sha256") == sha(Path(data["outputs"]["blend"])), "Blend output changed after builder validation")
    glb = Path(data["outputs"]["glb"])
    require(report.get("glb_sha256") == sha(glb), "GLB output changed after builder validation")
    require(all(report.get("checks", {}).get(k) is True for k in CHECKS), "Builder mechanical validation is incomplete or failed")
    require(report.get("front_source_sha256") == data.get("front_source", {}).get("sha256"), "Builder front source hash mismatch")
    for label in ("top", "bottom"):
        require(report.get(f"{label}_source_sha256") == data.get(f"{label}_source", {}).get("sha256"),
                f"Builder {label} source hash mismatch")
    checks = glb_checks(glb, Path(data["source_image"]), Path(data["front_source_image"]) if data.get("front_source_image") else None,
                        tuple(Path(data[f"{label}_source_image"]) for label in ("top", "bottom") if data.get(f"{label}_source_image")))
    require(report.get("style_visual_review", "pending") == "pending", "Builder cannot automatically approve visual style")
    visual = data.get("style_visual_review", "pending")
    require(visual in {"pending", "accepted"}, "Unknown visual review status")
    if visual == "accepted" and check_visual:
        review = data.get("style_review", {})
        require(review.get("note", "").strip() and review.get("reviewer") == "command_operator", "Visual review record incomplete")
        require(review.get("hashes") == review_fingerprint(data), "Visual review is stale; render and review again")
    return data, {"checks": checks, "style_visual_review": visual, "validation_report": data["outputs"]["validation_report"]}


def run_builder(handoff_path: Path, blender: Path | None, *, render_only: bool = False) -> tuple[dict, dict]:
    handoff_path = handoff_path.expanduser().resolve()
    try:
        data = fresh_handoff(handoff_path)
    except Exception as exc:
        # A requested mutation must not leave an obsolete successful handoff state.
        existing = read_json(handoff_path)
        if existing.get("kind") == "fish_volume_handoff":
            existing.update(status="blocked", next_action="fix_input", failures=[{"code": "manifest_invalid", "kind": "validation", "message": str(exc)}])
            write_json(handoff_path, existing)
        raise
    require(data.get("status") != "running", "This handoff already has a running builder; wait for that run before starting another")
    if render_only:
        validate_volume(handoff_path, check_visual=False)
    executable = str(blender.expanduser().resolve()) if blender else shutil.which("blender")
    if not executable or not Path(executable).is_file():
        raise VolumeError("Blender executable missing; pass --blender <executable>", code="dependency_missing")
    require(BUILDER.is_file(), "Bundled volume builder is missing")
    data["run_id"] = uuid.uuid4().hex
    data["render_run_id" if render_only else "build_run_id"] = data["run_id"]
    data.pop("style_review", None)
    data.update(status="running", next_action="poll", style_visual_review="pending", failures=[])
    write_json(handoff_path, data)
    argv = [executable, "--background", "--python", str(BUILDER), "--", str(handoff_path)]
    if render_only:
        argv.append("--render-only")
    try:
        process = subprocess.run(argv, capture_output=True, text=True, timeout=600, check=False)
        if process.returncode:
            raise VolumeError(f"Blender exited with code {process.returncode}; inspect the validation report", code="run_failed", status="failed")
        data, summary = validate_volume(handoff_path, require_run=True)
        if render_only:
            summary["review"] = {key: value["path"] for key, value in validated_render(data).items()}
        data.update(status="done", next_action="human_review", style_visual_review="pending", failures=[])
        write_json(handoff_path, data)
        return data, summary
    except Exception as exc:
        status = exc.status if isinstance(exc, VolumeError) else "failed"
        code = exc.code if isinstance(exc, VolumeError) else "run_failed"
        data.update(status=status, next_action="fix_input", failures=[{"code": code, "kind": "validation" if code == "manifest_invalid" else "unknown", "message": str(exc)}])
        write_json(handoff_path, data)
        if isinstance(exc, VolumeError):
            raise
        raise VolumeError(str(exc), code="run_failed", status="failed") from exc


def validated_render(data: dict) -> dict:
    report = read_json(Path(data["outputs"]["render_report"]))
    require(report.get("ok") is True and report.get("status") == "done" and not report.get("failures"), "Render failed")
    require(report.get("run_id") == data["render_run_id"], "Render report is stale")
    require(report.get("glb_sha256") == sha(Path(data["outputs"]["glb"])) and report.get("blend_sha256") == sha(Path(data["outputs"]["blend"])), "Render used outdated model artifacts")
    require(report.get("source_sha256") == data["source"]["sha256"] and report.get("profile_sha256") == data["profile_snapshot"]["sha256"]
            and report.get("style_reference_sha256") == data["style_contract"]["style_reference_sha256"], "Render inputs changed")
    require(report.get("front_source_sha256") == data.get("front_source", {}).get("sha256"), "Render front source hash mismatch")
    for label in ("top", "bottom"):
        require(report.get(f"{label}_source_sha256") == data.get(f"{label}_source", {}).get("sha256"),
                f"Render {label} source hash mismatch")
    require(report.get("style_visual_review", "pending") == "pending", "Render cannot automatically approve style")
    review = report.get("review", {})
    require(isinstance(review, dict), "Render review artifact map missing")
    views = ["side", "front", "oblique", "style_comparison"]
    profile = read_json(Path(data["profile"]))
    if profile.get("cephalofoil"):
        views.extend(["clay_side", "clay_front", "clay_top", "clay_oblique"])
    if data.get("top_source"): views.append("top")
    if data.get("bottom_source"): views.append("bottom")
    if "master_comparison" in review: views.append("master_comparison")
    for view in views:
        require(isinstance(review.get(view), str) and bool(review[view]), f"Required review view missing: {view}")
        path = resolve_file(review.get(view), Path(data["outputs"]["review_dir"]))
        require(path.is_relative_to(Path(data["outputs"]["review_dir"])), "Render review path escapes output directory")
        image_info(path)
    return {view: image_info(resolve_file(value, Path(data["outputs"]["review_dir"]))) for view, value in review.items() if view in set(views)}


def review_fingerprint(data: dict) -> dict:
    return {"glb_sha256": sha(Path(data["outputs"]["glb"])), "blend_sha256": sha(Path(data["outputs"]["blend"])),
            "source_sha256": data["source"]["sha256"], "reference_sha256": data["style_contract"]["style_reference_sha256"],
            "profile_sha256": data["profile_snapshot"]["sha256"], "front_source_sha256": data.get("front_source", {}).get("sha256"),
            "top_source_sha256": data.get("top_source", {}).get("sha256"), "bottom_source_sha256": data.get("bottom_source", {}).get("sha256"),
            "review_images": {view: info["sha256"] for view, info in validated_render(data).items()}}


def accept_volume(handoff_path: Path, note: str) -> tuple[dict, dict]:
    require(isinstance(note, str) and bool(note.strip()), "A nonempty visual review note is required")
    data, summary = validate_volume(handoff_path)
    hashes = review_fingerprint(data)
    data.update(style_visual_review="accepted", next_action="none", style_review={
        "reviewer": "command_operator", "note": note.strip(), "updated_at": datetime.now(timezone.utc).isoformat(),
        "glb_sha256": hashes["glb_sha256"], "source_sha256": hashes["source_sha256"],
        "reference_sha256": hashes["reference_sha256"], "hashes": hashes})
    write_json(handoff_path, data)
    summary.update(style_visual_review="accepted", style_review=data["style_review"])
    return data, summary
