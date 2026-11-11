"""Bind the current bream source, model, motion, and complete root domains."""
import hashlib
import json
from pathlib import Path

work = Path(__file__).resolve().parent
root = work.parents[1]
candidate = work / "tail-r3"
portable = root / "resources/scripts/volume-fish/portable"

def read(path):
    return json.loads(path.read_text())

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

state = read(work / "manifest.json")
root_domain = root / read(work / "manifest.json")["root_domain"]["path"]
domains = read(root_domain)
assert sha(root_domain) == state["root_domain"]["sha256"]
assert domains["model"]["sha256"] == state["model_sha256"]
assert domains["editable_source"]["sha256"] == state["source_sha256"]
review = read(candidate / "review.plan.json")
profile = read(Path(review["motion_profile"]))
manifest = read(Path(review["packed_parts_manifest"]))
source = candidate / "fish.blend"
bindings = {str(path): sha(path) for path in (
    Path(review["model"]), source, Path(review["packed_parts_manifest"]), root_domain,
    Path(review["motion_profile"]), Path(review["motion_runtime"]),
    portable / "PackedFishParts.gd", portable / "parts.py",
)}
assert set(review["fins"]) == set(domains["current_export_domains"])
fin_roots = {
    name: {
        "source_baseline": domain["source_baseline"],
        "rest_points_gltf": domain["rest_points_gltf"],
        "root_ids": domain["ids"],
        "root_band": domain["root_band"],
        "original_complete_root_count": len(domain["ids"]),
    }
    for name, domain in domains["current_export_domains"].items()
}
length = profile["real_length_cm"]
fin_plan = {key: review[key] for key in (
    "species", "model", "model_sha256", "body", "motion_profile", "motion_profile_sha256",
    "motion_runtime", "motion_runtime_sha256", "packed_parts_manifest", "packed_parts_manifest_sha256"
)}
fin_plan.update(
    fins=fin_roots, body_bones=profile["body_bones"],
    length_native=length/(review["model_scale"]*100), scale_cm=review["model_scale"]*100,
    controller_script=review["motion_runtime"], packed_helper_script=str(portable/"PackedFishParts.gd"),
    packed_canonicalizer=str(portable/"parts.py"), frozen_inputs=bindings,
    attachment_limits={"outer_gap_mm":1.0,"max_embedding_mm":6.0},
    membrane_clearance={"root_collar_mm":0.5,"penetration_tolerance_mm":0.02},
    scope="Exact current bream geometry and complete anatomical root domains. Isolated material candidate.",
)
write(candidate/"fin.plan.json", {"kind":"current_material_only_candidate_fin_validation","items":[fin_plan]})
body = review | {"frozen_inputs":bindings,"expected_triangles":state["baseline_inventory"]["static"]["triangles"],
                 "expected_body_surfaces":3,"maximum_amplitude":2.5,"pose_time":1.17}
write(candidate/"body.plan.json",body)
write(candidate/"viewer.json",{
    "mode":"interactive", "species":state["species"], "model":review["model"],
    "model_sha256":review["model_sha256"], "model_role":"isolated_material_candidate",
    "output":str(candidate), "model_scale":[review["model_scale"]]*3,
    "inventory":{"mesh_count":manifest["expected"]["mesh_count"],
                 "surface_count":manifest["expected"]["surface_count"]},
    "controller":{"runtime":review["motion_runtime"],"profile":review["motion_profile"],"action":"Swim"},
    "camera":{"yaw_degrees":0,"pitch_degrees":0,"distance_scale":.88},
    "focuses":{}, "captures":[],
})
