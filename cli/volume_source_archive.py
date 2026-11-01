"""Reuse reviewed Foundry source pixels without inheriting an old model review.

Historical generation metadata stays historical. No missing raw/Brief is created,
and the new model always starts with an empty production checklist.
"""
from pathlib import Path
import copy


def snapshot(archive, profile, output):
    import volume_fish as v
    spec = v.read_json(archive)
    required = {"historical_handoff", "historical_profile", "source", "reference"}
    v.keys(spec, required, required, "reviewed source archive")
    files = {k: v.resolve_file(value, archive.parent) for k, value in spec.items()}
    old = v.read_json(files["historical_handoff"])
    v.require(old.get("kind") == "fish_volume_handoff", "Historical source handoff required")
    source, review = old.get("source", {}), old.get("source_review", {})
    v.require(review.get("status") == "accepted" and review.get("source") == "pipeline",
              "Historical Foundry asset acceptance required; model review is not source acceptance")
    v.require(source.get("generation_stage") == "image.raw" and source.get("generation_command") == "image.generate"
              and source.get("generation_task_id") and source.get("raw_sha256") and old.get("brief", {}).get("sha256"),
              "Historical generation/Brief metadata missing")
    info = v.image_info(files["source"], transparent=True)
    v.require(all(source.get(k) == info[k] for k in ("sha256", "width", "height")), "Historical source pixels changed")
    style = old.get("style_contract", {})
    ref_hash = v.sha(files["reference"])
    v.image_info(files["reference"])
    v.require(style.get("pixel_art") is True and style.get("texture_filter") == "nearest"
              and style.get("roughness") == 1 and style.get("source_sha256") == info["sha256"]
              and style.get("style_reference_sha256") == ref_hash, "Historical style reference mismatch")
    if source.get("generation_reference_required"):
        proof = source.get("generation_reference_evidence", {})
        v.require(source.get("generation_reference_sha256") == ref_hash
                  and proof.get("kind") == "pipeline_task" and proof.get("task_id") == source["generation_task_id"]
                  and proof.get("command_sha256"), "Historical generation reference missing")
    p, reference = v.validate_profile(v.read_json(profile), profile)
    import hashlib
    archived_profile = files["historical_profile"]
    profile_hashes = {v.sha(archived_profile), hashlib.sha256(archived_profile.read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
    v.require(old.get("profile_snapshot", {}).get("sha256") in profile_hashes, "Historical profile changed")
    identity = v.read_json(archived_profile)
    v.require(source.get("asset") == old.get("asset") and p["species"] == identity["species"], "Source species mismatch")
    v.require(p["real_length_cm"] == old["real_length_cm"] and reference["sha256"] == ref_hash,
              "Source length/style contract changed")
    v.require(abs(p["source_aspect_ratio"] / (info["width"] / info["height"]) - 1) <= .02,
              "Source/profile aspect mismatch")
    v.require(not any(k in p for k in ("head_projection", "dorsal_projection", "ventral_projection", "rest_shape_revision")),
              "Source-only reconstruction requires independently reviewed auxiliary inputs before projections/revisions")
    inputs = set(files.values()) | {archive, profile}
    v.require(output not in inputs and not any(Path(x) in inputs for x in v.expected_outputs(output).values()),
              "Outputs must not overwrite source archive inputs")
    relocated_source = {**copy.deepcopy(source), "path": str(files["source"])}
    if source.get("generation_reference_required"):
        relocated_source["generation_reference_image"] = str(files["reference"])
    return {"schema_version": 1, "kind": "fish_volume_handoff", "status": "pending", "next_action": "run",
            "asset": old["asset"], "source": relocated_source,
            "source_image": str(files["source"]), "source_review": copy.deepcopy(review),
            "brief": copy.deepcopy(old["brief"]), "profile": str(profile),
            "profile_snapshot": {"path": str(profile), "sha256": v.sha(profile)},
            "real_length_cm": p["real_length_cm"], "outputs": v.expected_outputs(output),
            "style_contract": {**copy.deepcopy(style), "style_reference_image": str(files["reference"])},
            "style_visual_review": "pending", "failures": [],
            "accepted_source_archive": {"path": str(archive), "sha256": v.sha(archive),
                "fingerprint": {k: v.sha(path) for k, path in files.items()},
                "scope": "Existing accepted source pixels only. No old geometry/model acceptance inherited; missing upstream files remain historical."}}


def plan_source_archive(archive, profile, output):
    import volume_fish as v
    from volume_sop import start_production
    archive, profile, output = (Path(p).resolve() for p in (archive, profile, output))
    v.require(not output.exists(), "Choose a fresh handoff output")
    data = snapshot(archive, profile, output)
    data["production"] = start_production(output, v.read_json(profile)["species"], "rebuild",
        {"source_image": data["source_image"], "species_profile": profile})
    v.write_json(output, data)
    return data


def fresh_source_archive(data, path):
    import volume_fish as v
    receipt = data["accepted_source_archive"]
    archive = v.resolve_file(receipt["path"], path.parent)
    v.require(v.sha(archive) == receipt["sha256"], "Reviewed source mapping changed after plan")
    expected = snapshot(archive, v.resolve_file(data["profile"], path.parent), path)
    for key, value in expected.items():
        if key not in {"status", "next_action", "style_visual_review", "failures"}:
            v.require(data.get(key) == value, "Reviewed source input changed after plan: " + key)
    return data
