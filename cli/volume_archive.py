"""Replan unchanged accepted source pixels from a relocated, hash-bound archive.

This route verifies historical acceptance, not missing upstream generation files.
It creates new pending outputs and never edits the historical acceptance receipt.
"""
from pathlib import Path
import copy
import hashlib


def archive_inputs(path):
    import volume_fish as v
    path = Path(path).resolve()
    spec = v.read_json(path)
    required = {"accepted_handoff", "profile", "blend", "glb", "source", "reference", "review_images"}
    v.keys(spec, required | {"front_source", "top_source", "bottom_source"}, required, "accepted archive")
    files = {k: v.resolve_file(value, path.parent) for k, value in spec.items() if k != "review_images"}
    old = v.read_json(files["accepted_handoff"])
    v.require(old.get("kind") == "fish_volume_handoff" and old.get("status") == "done"
              and old.get("style_visual_review") == "accepted", "Archive requires an accepted historical volume handoff")
    review = old.get("style_review", {})
    v.require(review.get("reviewer") == "command_operator" and review.get("note", "").strip(), "Archive visual review missing")
    hashes = review.get("hashes", {})
    for key in ("blend", "glb", "source", "reference", "profile", "front_source", "top_source", "bottom_source"):
        expected = hashes.get(key + "_sha256")
        v.require(bool(expected) == (key in files), "Archive acceptance/input mismatch: " + key)
        if key not in files:
            continue
        actual = v.sha(files[key])
        # Git text checkout may change only line endings; binary evidence is exact.
        normalized = hashlib.sha256(files[key].read_bytes().replace(b"\r\n", b"\n")).hexdigest() if key == "profile" else actual
        v.require(expected in (actual, normalized), "Archive differs from accepted hash: " + key)
    reviews = spec["review_images"]
    v.require(isinstance(reviews, dict) and set(reviews) == set(hashes.get("review_images", {}))
              and {"side", "front", "oblique", "style_comparison"} <= set(reviews), "Archive must retain all accepted review images")
    image_paths = {k: v.resolve_file(value, path.parent) for k, value in reviews.items()}
    for key, image in image_paths.items():
        v.image_info(image)
        v.require(v.sha(image) == hashes["review_images"][key], "Archive review image changed: " + key)
    original_profile = v.read_json(files["profile"])
    style = old.get("style_contract", {})
    v.require(style.get("pixel_art") is True and style.get("texture_filter") == "nearest"
              and style.get("roughness") == 1, "Archive pixel style contract missing")
    for key in ("source", "front_source", "top_source", "bottom_source"):
        if key not in files:
            continue
        info = v.image_info(files[key], transparent=True)
        source = old.get(key, {})
        v.require(source.get("sha256") == info["sha256"] and source.get("width") == info["width"]
                  and source.get("height") == info["height"], "Archive source identity mismatch: " + key)
        acceptance = old.get("source_review" if key == "source" else key + "_review", {})
        v.require(acceptance.get("status") == "accepted" and acceptance.get("source") != "local_file"
                  and source.get("generation_stage") == "image.raw" and source.get("generation_task_id")
                  and source.get("raw_sha256"), "Archive historical generation/asset acceptance missing: " + key)
    v.require(style.get("source_sha256") == hashes["source_sha256"]
              and style.get("style_reference_sha256") == hashes["reference_sha256"], "Archive style hashes mismatch")
    v.require(old.get("brief", {}).get("sha256"), "Archive frozen Brief hash missing")
    fingerprint = {k: v.sha(p) for k, p in files.items()}
    fingerprint["review_images"] = {k: v.sha(p) for k, p in image_paths.items()}
    return old, original_profile, files, fingerprint


def snapshot(archive, profile, output):
    import volume_fish as v
    old, original, files, fingerprint = archive_inputs(archive)
    p, reference = v.validate_profile(v.read_json(profile), profile)
    v.require(p["species"] == original["species"] and p["real_length_cm"] == old["real_length_cm"],
              "Archive replan must retain species and representative length")
    v.require(reference["sha256"] == old["style_contract"]["style_reference_sha256"], "Archive style reference changed")
    v.require(abs(p["source_aspect_ratio"] / (old["source"]["width"] / old["source"]["height"]) - 1) <= .02,
              "Archive source aspect ratio mismatch")
    for key, projection in (("front_source", "head_projection"), ("top_source", "dorsal_projection"), ("bottom_source", "ventral_projection")):
        v.require((key in files) == (projection in p), "Archive source/projection mismatch: " + key)
    h = {"schema_version": 1, "kind": "fish_volume_handoff", "status": "pending", "next_action": "run",
         "asset": old["asset"], "brief": copy.deepcopy(old["brief"]),
         "profile": str(profile), "profile_snapshot": {"path": str(profile), "sha256": v.sha(profile)},
         "real_length_cm": p["real_length_cm"], "outputs": v.expected_outputs(output),
         "style_contract": {**old["style_contract"], "style_reference_image": str(files["reference"])},
         "style_visual_review": "pending", "failures": [],
         "accepted_archive": {"path": str(archive), "sha256": v.sha(archive), "fingerprint": fingerprint,
                              "scope": "Reuse accepted source pixels and historical acceptance; upstream raw/Brief files are historical, not revalidated or regenerated."}}
    for key in ("source", "front_source", "top_source", "bottom_source"):
        if key in files:
            h[key] = {**copy.deepcopy(old[key]), "path": str(files[key])}
            h["source_image" if key == "source" else key + "_image"] = str(files[key])
            review_key = "source_review" if key == "source" else key + "_review"
            h[review_key] = copy.deepcopy(old[review_key])
    input_paths = set(files.values()) | {archive, profile}
    input_paths.update(v.resolve_file(value, archive.parent) for value in v.read_json(archive)["review_images"].values())
    v.require(not any(Path(value) in input_paths for value in h["outputs"].values()), "Archive outputs must not overwrite inputs")
    if "rest_shape_revision" in p:
        v.revision_source(p["rest_shape_revision"], profile.parent, h)
    return h


def plan_archive(archive, profile, output):
    import volume_fish as v
    archive, profile, output = (Path(p).expanduser().resolve() for p in (archive, profile, output))
    v.require(not output.exists() and output not in (archive, profile), "Choose a new handoff output")
    h = snapshot(archive, profile, output)
    v.require(output not in {v.resolve_file(value, archive.parent) for key, value in v.read_json(archive).items() if key != "review_images"}, "Handoff must not overwrite archive inputs")
    v.write_json(output, h)
    return h


def fresh_archive(h, path):
    import volume_fish as v
    receipt = h["accepted_archive"]
    archive = v.resolve_file(receipt["path"], path.parent)
    v.require(v.sha(archive) == receipt["sha256"], "Archive input map changed after plan")
    expected = snapshot(archive, v.resolve_file(h["profile"], path.parent), path)
    for key, value in expected.items():
        if key not in {"status", "next_action", "style_visual_review", "failures"}:
            v.require(h.get(key) == value, "Archive inputs changed after plan: " + key)
    return h
