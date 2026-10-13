"""Bounded motion artifacts for four existing, reviewed volume fish.

No model rebuilding or image provenance fabrication: pin the reviewed GLB,
reuse receipt, calibrated motion profile and fixed Godot controller instead.
"""
from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import struct
import tempfile

from PIL import Image

from volume_fish import REPO_ROOT, glb_document, keys, number, point, read_json, require, resolve_file, sha, validate_volume

SPECIES = {"blacktip_reef_shark", "silver_arowana", "piranha", "hairtail"}
RUNTIME = REPO_ROOT / "resources/runtime/godot/VolumeFishMotion.gd"


def record(path: Path) -> dict:
    return {"path":str(path),"sha256":sha(path)}


def reuse_receipt(path: Path, species: str, model: Path) -> dict:
    receipt = read_json(path)
    fields = {"schema_version","kind","species","model_sha256","review_status","reviewer","note","evidence"}
    contract = {"command","stage","status","ok","next_action","inputs","outputs","summary","failures"}
    keys(receipt, fields | {"reviewed_at"} | contract, fields, "model reuse receipt")
    require(receipt["schema_version"] == 1 and receipt["kind"] == "existing_volume_model_review", "Unknown model reuse receipt")
    require(receipt["species"] == species and receipt["model_sha256"] == sha(model), "Reviewed model identity changed")
    require(receipt["review_status"] == "accepted" and receipt["reviewer"] == "command_operator", "Explicit operator model reuse review required")
    require(receipt.get("ok",True) is True and receipt.get("status","done") == "done", "Model reuse validation did not pass")
    require(isinstance(receipt["note"],str) and 1 <= len(receipt["note"].strip()) <= 4000, "Model reuse review needs a concrete note")
    require(isinstance(receipt["evidence"],list) and 1 <= len(receipt["evidence"]) <= 8, "Model reuse needs 1–8 existing review evidence files")
    evidence = []
    for value in receipt["evidence"]:
        source = resolve_file(value,path.parent)
        require(source.stat().st_size <= 32*1024*1024, "Review evidence exceeds 32 MiB")
        if source.suffix.lower() == ".json":
            content = read_json(source)
            require(content and content.get("status") not in {"failed","blocked"}, "Review evidence records failure")
            if content.get("kind") == "fish_volume_handoff":
                validated, _ = validate_volume(source)
                require(validated.get("style_visual_review") == "accepted", "Existing volume handoff is not visually accepted")
                require(sha(Path(validated["outputs"]["glb"])) == sha(model), "Accepted volume handoff refers to another GLB")
        else:
            require(source.suffix.lower() in {".png",".jpg",".jpeg"}, "Reuse evidence must be a JSON report or review image")
            with Image.open(source) as image:
                image.verify()
        evidence.append(record(source))
    return {**record(path),"evidence":evidence,"reviewer":"command_operator","note":receipt["note"]}


def output_paths(handoff: Path) -> dict:
    directory = handoff.parent / (handoff.stem + "-artifacts")
    return {"runtime":str(directory/"FoundryFishMotion.gd"),"config":str(directory/"motion.json"),
            "validation_report":str(directory/"validation.json")}


def safe_output(path: Path, base: Path) -> None:
    require(path.is_absolute() and path.is_relative_to(base) and ".." not in path.parts, "Motion artifact escapes its handoff directory")
    current = path
    while current != base:
        require(not current.is_symlink(), "Motion output cannot be a symlink")
        current = current.parent
    require(path.resolve().is_relative_to(base), "Motion output resolves outside its directory")


def save(path: Path, content: bytes, base: Path) -> None:
    safe_output(path,base)
    path.parent.mkdir(parents=True,exist_ok=True)
    # Never follow a predictable temporary-file symlink beside a handoff.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=".motion-",delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        safe_output(path,base)
        os.replace(temporary,path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def save_json(path: Path, content: dict, base: Path) -> None:
    save(path,(json.dumps(content,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode(),base)


def inspect_model(path: Path, clip_name: str) -> dict:
    require(path.stat().st_size <= 64 * 1024 * 1024, "Motion GLB exceeds 64 MiB")
    doc, blob = glb_document(path)
    nodes, skins = doc.get("nodes", []), doc.get("skins", [])
    require(doc.get("meshes") and skins, "Motion model needs real meshes and a skin")
    joints = {j for skin in skins for j in skin.get("joints", [])}
    require(joints and all(type(j) is int and 0 <= j < len(nodes) for j in joints), "Invalid model joints")
    names = [nodes[j].get("name") for j in sorted(joints)]
    require(all(isinstance(n, str) and n for n in names) and len(set(names)) == len(names), "Model bone names must be unique")
    cache = {}

    def view(index):
        item = doc["bufferViews"][index]
        offset, size = item.get("byteOffset", 0), item["byteLength"]
        require(item.get("buffer", 0) == 0 and type(offset) is int and type(size) is int
                and 0 <= offset <= offset + size <= len(blob), "Invalid embedded model buffer")
        return blob[offset:offset + size]

    def values(index):
        if index in cache:
            return cache[index]
        item = doc["accessors"][index]
        formats = {5120:("b",1),5121:("B",1),5122:("h",2),5123:("H",2),5125:("I",4),5126:("f",4)}
        widths = {"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}
        require("sparse" not in item and item["componentType"] in formats and item["type"] in widths, "Unsupported motion model accessor")
        fmt, size = formats[item["componentType"]]
        width, count = widths[item["type"]], item["count"]
        buf = view(item["bufferView"])
        offset = item.get("byteOffset", 0)
        stride = doc["bufferViews"][item["bufferView"]].get("byteStride", width * size)
        require(type(count) is int and 0 < count <= 500000 and type(offset) is int and type(stride) is int
                and offset >= 0 and stride >= width * size and offset + (count - 1) * stride + width * size <= len(buf), "Model accessor exceeds bounds/budget")
        rows = [struct.unpack_from("<" + fmt * width, buf, offset + i * stride) for i in range(count)]
        if item.get("normalized") and item["componentType"] != 5126:
            maximum = {5120:127,5121:255,5122:32767,5123:65535,5125:4294967295}[item["componentType"]]
            rows = [tuple(max(-1, v / maximum) for v in row) for row in rows]
        require(all(math.isfinite(v) for row in rows for v in row), "Nonfinite model accessor")
        cache[index] = rows
        return rows

    parents = {child:i for i,n in enumerate(nodes) for child in n.get("children", [])}
    points, vertex_count = [], 0
    for mesh_index, mesh in enumerate(doc["meshes"]):
        instances = [i for i,n in enumerate(nodes) if n.get("mesh") == mesh_index]
        require(instances, "Uninstanced fish mesh")
        for i in instances:
            require(type(nodes[i].get("skin")) is int and 0 <= nodes[i]["skin"] < len(skins), "Unskinned fish mesh")
            # The four accepted meshes are exported in common model coordinates.
            # Reject other layouts rather than misreporting their tank envelope.
            seen = set()
            while i is not None:
                require(i not in seen, "Cyclic model node hierarchy")
                seen.add(i)
                node = nodes[i]
                for key, identity in {"translation":[0,0,0],"rotation":[0,0,0,1],"scale":[1,1,1],
                                      "matrix":[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}.items():
                    require(node.get(key, identity) == identity, "Motion reuse requires identity mesh transforms")
                i = parents.get(i)
        for primitive in mesh.get("primitives", []):
            require(primitive.get("mode", 4) == 4, "Motion fish must contain triangles")
            attrs = primitive["attributes"]
            require({"POSITION","JOINTS_0","WEIGHTS_0"} <= set(attrs), "Motion fish needs skinned vertices")
            pos, weights, bone_indices = values(attrs["POSITION"]), values(attrs["WEIGHTS_0"]), values(attrs["JOINTS_0"])
            require(doc["accessors"][attrs["JOINTS_0"]]["componentType"] in {5121,5123},"Skin joint indices must use unsigned integers")
            require(all(len(row) == 3 for row in pos) and len(pos) == len(weights) == len(bone_indices), "Invalid skinned vertex layout")
            require(all(len(w) == 4 and min(w) >= 0 and abs(sum(w)-1) <= .001 for w in weights), "Unnormalized skin weights")
            limit = min(len(skins[nodes[i]["skin"]]["joints"]) for i in instances)
            require(all(len(row) == 4 and all(type(j) is int and 0 <= j < limit for j in row) for row in bone_indices), "Unknown vertex bone mapping")
            indices = [row[0] for row in values(primitive["indices"])] if "indices" in primitive else list(range(len(pos)))
            require(len(indices) >= 3 and len(indices) % 3 == 0 and all(type(j) is int and 0 <= j < len(pos) for j in indices), "Invalid fish triangles")
            points.extend(pos)
            vertex_count += len(pos)
    require(points and vertex_count <= 500000, "Empty or over-budget motion fish")
    clips = [a for a in doc.get("animations", []) if a.get("name") == clip_name]
    require(len(clips) == 1 and clips[0].get("channels"), "Requested base swim clip missing or ambiguous")
    changing, duration = set(), 0.0
    for channel in clips[0]["channels"]:
        sampler = clips[0]["samplers"][channel["sampler"]]
        require(sampler.get("interpolation", "LINEAR") in {"LINEAR","STEP"}, "Unsupported swim interpolation")
        times, rows = values(sampler["input"]), values(sampler["output"])
        require(len(times) == len(rows) >= 2 and all(len(t) == 1 for t in times)
                and all(times[i][0] < times[i+1][0] for i in range(len(times)-1)), "Invalid swim timeline")
        node, prop = channel["target"].get("node"), channel["target"].get("path")
        require(node in joints and prop in {"translation","rotation","scale"}, "Swim must animate bones, not the model carrier")
        require(all(len(row) == (4 if prop == "rotation" else 3) for row in rows), "Invalid swim keyframe width")
        seam = max(abs(a-b) for a,b in zip(rows[0],rows[-1]))
        if prop == "rotation":
            seam = min(seam,max(abs(a+b) for a,b in zip(rows[0],rows[-1])))
            require(all(abs(sum(v*v for v in row)-1) < .003 for row in rows),"Invalid bone rotation quaternion")
        require(seam <= .0001, "Base swim must actually loop")
        def delta(row):
            result=max(abs(a-b) for a,b in zip(rows[0],row))
            return min(result,max(abs(a+b) for a,b in zip(rows[0],row))) if prop == "rotation" else result
        if any(delta(row) > .00001 for row in rows[1:]):
            require(prop == "rotation","Reuse motion supports rotational base swim; animated translation/scale needs a new envelope review")
            changing.add(nodes[node]["name"])
        duration = max(duration,times[-1][0]-times[0][0])
    require(changing and .1 <= duration <= 10, "Base swim missing real motion or outside duration budget")
    texture_sizes = []
    for image in doc.get("images", []):
        require("uri" not in image and "bufferView" in image, "Existing texture must remain embedded")
        with Image.open(io.BytesIO(view(image["bufferView"]))) as texture:
            texture_sizes.append(list(texture.size))
    require(texture_sizes, "Reviewed fish must retain embedded source textures")
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    require(high[0] > low[0], "Model longitudinal size is zero")
    bone_parents = {}
    for joint in joints:
        parent, seen = parents.get(joint), {joint}
        while parent is not None and parent not in joints:
            require(parent not in seen, "Cyclic bone hierarchy")
            seen.add(parent)
            parent = parents.get(parent)
        bone_parents[nodes[joint]["name"]] = nodes[parent]["name"] if parent is not None else None
    return {"bones":names,"bone_parents":bone_parents,"animated_bones":sorted(changing),"clip":clip_name,"loop_seconds":duration,
            "meshes":len(doc["meshes"]),"vertices":vertex_count,"bounds_min":low,"bounds_max":high,
            "texture_sizes":texture_sizes}


def validate_motion_profile(data: dict, model: dict) -> dict:
    fields = {"schema_version","species","real_length_cm","head_sign","base_clip","body_bones","tank_size_m",
              "path_radii_m","vertical_amplitude_m","envelope_radius_m","period_seconds","transition_seconds",
              "body_delay_seconds","base_body_gain","actions","notes"}
    keys(data,fields,fields,"motion profile")
    require(data["schema_version"] == 1 and data["species"] in SPECIES,"Unknown motion profile species/schema")
    require(type(data["head_sign"]) is int and data["head_sign"] in {-1,1},"head_sign must be -1 or 1")
    require(data["base_clip"] == "Animation" and data["base_clip"] == model["clip"],"Unsupported base swim clip")
    for field,low,high in [("real_length_cm",.1,1000),("vertical_amplitude_m",0,20),("envelope_radius_m",.01,50),
                           ("period_seconds",4,60),("transition_seconds",.2,3),("body_delay_seconds",0,2),("base_body_gain",0,1)]:
        number(data[field],low,high,field)
    point(data["tank_size_m"],3,.1,100,"tank size")
    point(data["path_radii_m"],2,.01,50,"path radii")
    bones = data["body_bones"]
    require(isinstance(bones,list) and 4 <= len(bones) <= 32 and all(isinstance(b,str) for b in bones)
            and len(set(bones)) == len(bones) and set(bones) <= set(model["bones"]),"Body mapping needs 4–32 unique existing skin bones")
    for previous,current in zip(bones,bones[1:]):
        parent,seen = model["bone_parents"].get(current), {current}
        while parent != previous and parent is not None:
            require(parent not in seen,"Cyclic mapped body chain")
            seen.add(parent)
            parent = model["bone_parents"].get(parent)
        require(parent == previous,"Body bones must follow the real head-to-tail hierarchy")
    actions = keys(data["actions"],{"Swim","Turn","Ascend","Dive"},{"Swim","Turn","Ascend","Dive"},"motion actions")
    for name,action in actions.items():
        fields = {"radius_scale","bend_radians","vertical_sign","clip_speed"}
        keys(action,fields,fields,"motion action")
        number(action["radius_scale"],.3,1,"radius scale")
        number(action["bend_radians"],0,1,"total body bend")
        number(action["clip_speed"],.2,2,"clip speed")
        expected = {"Swim":0,"Turn":0,"Ascend":1,"Dive":-1}[name]
        require(type(action["vertical_sign"]) is int and action["vertical_sign"] == expected,"Action vertical direction mismatch")
    require(actions["Swim"]["radius_scale"] == 1,"Swim uses the full calibrated path")
    require(actions["Turn"]["radius_scale"] <= .8 and actions["Turn"]["bend_radians"] >= actions["Swim"]["bend_radians"]+.1,
            "Turn must use a smaller path and visibly greater body bend")
    require(isinstance(data["notes"],list) and len(data["notes"]) <= 16
            and all(isinstance(note,str) and len(note) <= 2000 for note in data["notes"]),"Motion notes exceed budget")
    length,extent = data["real_length_cm"]/100,data["envelope_radius_m"]
    require(extent >= 2*length,"Motion envelope must be at least twice real fish length")
    required = [data["path_radii_m"][0]+extent+.02*length,
                data["vertical_amplitude_m"]+extent+.02*length,
                data["path_radii_m"][1]+extent+.02*length]
    require(all(size/2 >= bound for size,bound in zip(data["tank_size_m"],required)),"Motion path/posed envelope exceeds tank safety bounds")
    return {"required_half_extents_m":required,"configured_envelope_radius_m":extent,
            "runtime_pose_envelope_check":"Required again from actual Godot skeleton rest/skin data at setup"}


def _canonical_handoff(path: Path) -> Path:
    require(not path.is_symlink(),"Motion handoff cannot be a symlink")
    return path.expanduser().absolute().parent.resolve()/path.name


def plan_motion(profiles: tuple[Path, ...], models_dir: Path, reviews_dir: Path, output: Path) -> tuple[dict,dict]:
    require(len(profiles) == 4,"Motion plan needs exactly four species profiles")
    require(RUNTIME.is_file() and not RUNTIME.is_symlink(),"Bundled motion runtime is missing or symlinked")
    handoff = _canonical_handoff(output)
    require(not handoff.exists(),"Motion handoff already exists; use a new output to preserve its review")
    entries,used = [],set()
    for path in profiles:
        path = path.expanduser().resolve()
        data = read_json(path)
        species = data.get("species")
        require(isinstance(species,str) and species in SPECIES and species not in used,"Four distinct supported species are required")
        used.add(species)
        model_path = resolve_file(str(models_dir.expanduser().resolve()/(species+".glb")),handoff.parent)
        receipt_path = resolve_file(str(reviews_dir.expanduser().resolve()/(species+".validation.json")),handoff.parent)
        model = inspect_model(model_path,data.get("base_clip",""))
        bounds = validate_motion_profile(data,model)
        entries.append({"species":species,"profile":record(path),"model":record(model_path),
                        "review":reuse_receipt(receipt_path,species,model_path),"model_checks":model,"bounds":bounds})
    outputs = output_paths(handoff)
    for value in outputs.values():
        safe_output(Path(value),handoff.parent)
    document = {"schema_version":1,"kind":"fish_volume_motion_handoff","status":"pending","next_action":"run",
                "scope":"Swim/Turn/Ascend/Dive for four existing reviewed models; no asset regeneration",
                "runtime":record(RUNTIME.resolve()),"models":sorted(entries,key=lambda e:e["species"]),"outputs":outputs,
                "motion_visual_review":"pending","failures":[]}
    save_json(handoff,document,handoff.parent)
    return document,{"handoff":str(handoff),"species":sorted(used),"motion_visual_review":"pending"}


def fresh_motion(path: Path) -> tuple[Path,dict,dict]:
    path = _canonical_handoff(path)
    data = read_json(path)
    require(data.get("kind") == "fish_volume_motion_handoff" and data.get("schema_version") == 1,"Unknown motion handoff")
    require(data.get("runtime") == record(RUNTIME.resolve()) and not RUNTIME.is_symlink(),"Bundled motion runtime changed; replan")
    require(data.get("outputs") == output_paths(path),"Motion output paths changed")
    for value in data["outputs"].values():
        safe_output(Path(value),path.parent)
    require(isinstance(data.get("models"),list) and len(data["models"]) == 4,"Motion handoff must contain four fish")
    profiles = {}
    for entry in data["models"]:
        species = entry.get("species")
        require(species in SPECIES and species not in profiles,"Duplicate/unknown handoff species")
        for key in ("profile","model"):
            require(entry[key] == record(Path(entry[key]["path"])),f"Motion {key} changed; replan")
        profile = read_json(Path(entry["profile"]["path"]))
        require(profile.get("species") == species,"Profile species identity changed")
        model_path = Path(entry["model"]["path"])
        require(entry["review"] == reuse_receipt(Path(entry["review"]["path"]),species,model_path),"Source/model review receipt or evidence changed")
        model = inspect_model(model_path,profile.get("base_clip",""))
        bounds = validate_motion_profile(profile,model)
        require(model == entry["model_checks"] and bounds == entry["bounds"],"Pinned model checks or tank bounds changed")
        profiles[species] = profile
    return path,data,{"schema_version":1,"profiles":profiles}


def build_motion(path: Path) -> tuple[dict,dict]:
    path,data,config = fresh_motion(path)
    outputs = data["outputs"]
    save(Path(outputs["runtime"]),RUNTIME.read_bytes(),path.parent)
    save_json(Path(outputs["config"]),config,path.parent)
    report = {"schema_version":1,"command":"volume.motion-build","stage":"assets","ok":True,"status":"done",
              "next_action":"human_review","motion_visual_review":"pending",
              "inputs":{"runtime":data["runtime"],"models":data["models"]},
              "outputs":{"runtime":record(Path(outputs["runtime"])),"config":record(Path(outputs["config"]))},
              "checks":{"four_models_reviewed":True,"actual_skin_loop_bone_mapping":True,"bounded_profiles":True,
                        "tank_envelopes":True,"native_models_unchanged":True},
              "remaining_review":"Actual Godot setup must validate posed envelope; inspect all 16 species/actions and GUI, then bind final operator report to these model/config/helper hashes.","failures":[]}
    save_json(Path(outputs["validation_report"]),report,path.parent)
    data.update(status="done",next_action="human_review",motion_visual_review="pending",failures=[],
                artifact_hashes={key:sha(Path(value)) for key,value in outputs.items()})
    save_json(path,data,path.parent)
    return data,{"validation_report":outputs["validation_report"],"motion_visual_review":"pending","artifact_hashes":data["artifact_hashes"]}


def validate_motion(path: Path) -> tuple[dict,dict]:
    _,data,config = fresh_motion(path)
    require(data.get("status") == "done" and data.get("artifact_hashes"),"Motion artifacts have not been built")
    for key,value in data["outputs"].items():
        require(Path(value).is_file() and sha(Path(value)) == data["artifact_hashes"].get(key),"Motion artifact changed or missing")
    require(Path(data["outputs"]["runtime"]).read_bytes() == RUNTIME.read_bytes(),"Output runtime is not the fixed bundled helper")
    require(read_json(Path(data["outputs"]["config"])) == config,"Runtime configuration no longer matches calibrated profiles")
    report = read_json(Path(data["outputs"]["validation_report"]))
    require(report.get("ok") is True and report.get("motion_visual_review") == "pending","Technical motion report cannot approve animation quality")
    return data,{"checks":report["checks"],"motion_visual_review":"pending","artifact_hashes":data["artifact_hashes"]}
