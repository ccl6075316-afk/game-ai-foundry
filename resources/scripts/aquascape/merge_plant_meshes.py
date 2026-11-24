"""Pack legacy plant art onto the verified V10 vertex-current geometry and weights."""

import argparse
import copy
import io
from itertools import combinations, permutations
from pathlib import Path
import json

import numpy as np
from PIL import Image

from build_from_art import Glb
from build_shader_plants import native_atlas
from optimize_scenery import budget_type, load, metrics, sha
from rig_plant_current import array, read_glb
from validate_shader_shells import points

CHANNELS = {"POSITION":"VEC3", "NORMAL":"VEC3", "TEXCOORD_0":"VEC2", "JOINTS_0":"VEC4", "WEIGHTS_0":"VEC4"}


def read_image(doc, binary, index):
    view = doc["bufferViews"][doc["images"][index]["bufferView"]]
    offset = view.get("byteOffset", 0)
    return Image.open(io.BytesIO(binary[offset:offset+view["byteLength"]])).convert("RGBA")


def source_parts(doc):
    if len(doc["skins"]) != 1:
        raise ValueError("Legacy merge needs a single shared skin")
    parts = []
    for index, node in enumerate(doc["nodes"]):
        if "mesh" not in node:
            continue
        if node.keys() != {"name", "mesh", "skin"} or node["skin"] != 0:
            raise ValueError(f"Cannot merge transformed or differently skinned mesh {node['name']}")
        for primitive in doc["meshes"][node["mesh"]]["primitives"]:
            if primitive.get("mode", 4) != 4 or "indices" in primitive or primitive["attributes"].keys() != CHANNELS.keys():
                raise ValueError(f"Unexpected geometry layout at {node['name']}")
            parts.append((index, primitive))
    return parts


def material_plan(doc, parts):
    per_primitive = []
    shared = None
    for _, primitive in parts:
        mat = copy.deepcopy(doc["materials"][primitive["material"]])
        mat.pop("name", None)
        texture = mat["pbrMetallicRoughness"]["baseColorTexture"]
        item = doc["textures"][texture.pop("index")]
        if texture or item.keys() != {"source","sampler"}:
            raise ValueError("Legacy atlas needs an untransformed base color texture")
        settings = (mat, doc["samplers"][item["sampler"]])
        if shared is not None and settings != shared:
            raise ValueError("Source materials differ in render settings")
        shared = settings
        per_primitive.append(item["source"])
    return shared, per_primitive


def compact_layout(images, pad):
    """Try all shelf orders for the small set of active plant textures."""
    sizes = [(image.width+2*pad,image.height+2*pad) for image in images]
    if len(sizes) > 4:
        raise ValueError("Legacy material requires more than four active atlas tiles")
    widths = {sum(w for w,_ in group) for n in range(1,len(sizes)+1) for group in combinations(sizes,n)}
    widest = max(w for w,_ in sizes)
    best = None
    result = None
    for order in permutations(range(len(sizes))):
        for capacity in sorted(w for w in widths if w >= widest):
            x = y = shelf_height = occupied_width = 0
            locations = [None]*len(sizes)
            for index in order:
                w,h = sizes[index]
                if x+w > capacity:
                    y += shelf_height
                    x = shelf_height = 0
                locations[index] = (x+pad,y+pad)
                x += w
                shelf_height = max(shelf_height,h)
                occupied_width = max(occupied_width,x)
            width = (occupied_width+3)//4*4
            height = (y+shelf_height+3)//4*4
            score = width*height, max(width,height)
            if best is None or score < best:
                best = score
                result = width,height,locations
    return result


def atlas_plan(doc, binary, per_primitive):
    indices = sorted(set(per_primitive))
    boards = {i:read_image(doc,binary,i) for i in indices}
    atlas, locations = native_atlas(list(boards.values()), compact_layout)
    rectangles = dict(zip(boards, locations))
    return atlas, boards, rectangles


VERTEX_CHANNELS = {"POSITION": "VEC3", "NORMAL": "VEC3", "TEXCOORD_1": "VEC2", "COLOR_0": "VEC4"}


def shader_payload(source_doc, source_bin, parts, reference_doc, reference_bin):
    primitive, = reference_doc["meshes"][0]["primitives"]
    assert len(reference_doc["meshes"]) == len(reference_doc["nodes"]) == 1
    assert not reference_doc.get("skins") and not reference_doc.get("animations")
    attributes = {
        key: array(reference_doc,reference_bin,primitive["attributes"][key])
        for key in VERTEX_CHANNELS
    }
    for key in ("POSITION", "NORMAL"):
        original = np.concatenate([array(source_doc,source_bin,p["attributes"][key]) for _,p in parts])
        assert np.array_equal(original,attributes[key]), f"V10 shader {key} differs from the source"
    return attributes


def atlas_uv(doc, binary, parts, images, boards, locations, size):
    result = []
    for (_, primitive), image in zip(parts, images):
        uv = array(doc,binary,primitive["attributes"]["TEXCOORD_0"])
        if not ((uv >= 0) & (uv <= 1)).all():
            raise ValueError("Drawing outside the donor rectangle would change clamp behavior")
        result.append((uv * boards[image].size + locations[image]) / size)
    return np.concatenate(result).astype(np.float32)


def build(source, reference, output):
    doc, binary = read_glb(source)
    parts = source_parts(doc)
    (material, sampler), images = material_plan(doc, parts)
    atlas, boards, locations = atlas_plan(doc, binary, images)
    current_doc, current_binary = read_glb(reference)
    values = shader_payload(doc,binary,parts,current_doc,current_binary)
    merged = Glb()
    merged.doc["samplers"] = [sampler]
    mat = merged.material(atlas, source.stem + "_combined_atlas")
    material["pbrMetallicRoughness"]["baseColorTexture"]["index"] = 0
    merged.doc["materials"][mat].update(material)
    attributes = {key:merged.accessor(data,VERTEX_CHANNELS[key]) for key,data in values.items()}
    attributes["TEXCOORD_0"] = merged.accessor(atlas_uv(doc,binary,parts,images,boards,locations,atlas.size),"VEC2")
    merged.doc["meshes"] = [{"name":source.stem,"primitives":[{"attributes":attributes,"material":mat,"mode":4}]}]
    merged.doc["nodes"] = [{"name":source.stem,"mesh":0}]
    merged.doc["scenes"] = [{"nodes":[0]}]
    output.parent.mkdir(parents=True,exist_ok=True)
    merged.save(output)


def validate_merge(source, reference, target, config):
    old, original = read_glb(source)
    new, binary = read_glb(target)
    ref_doc, ref_data = read_glb(reference)
    previous = source_parts(old)
    original_settings, images = material_plan(old, previous)
    atlas, boards, locations = atlas_plan(old, original, images)
    assert len(new["meshes"]) == len(new["nodes"]) == len(new["materials"]) == len(new["images"]) == 1
    assert not new.get("animations") and not new.get("skins")
    primitive, = new["meshes"][0]["primitives"]
    assert primitive["attributes"].keys() == VERTEX_CHANNELS.keys() | {"TEXCOORD_0"}
    expected = shader_payload(old,original,previous,ref_doc,ref_data)
    for key, values in expected.items():
        assert np.array_equal(values, array(new,binary,primitive["attributes"][key])), key
    assert np.array_equal(atlas_uv(old,original,previous,images,boards,locations,atlas.size),
                          array(new,binary,primitive["attributes"]["TEXCOORD_0"]))
    assert np.array_equal(atlas, read_image(new,binary,0)), "Atlas donor pixels changed"
    combined_settings, _ = material_plan(new, [(0, primitive)])
    assert original_settings == combined_settings, "Merged material render state changed"
    old_metrics, new_metrics = metrics(source), metrics(target)
    assert old_metrics["triangles"] == new_metrics["triangles"]

    pos, flow, color = (expected[key].astype(float) for key in ("POSITION", "TEXCOORD_1", "COLOR_0"))
    pinned = (flow[:,0] <= .08) | (color[:,3] == 0.0)
    tip = (flow[:,0] > .80) & (color[:,3] > 0)
    assert pinned.any() and tip.any()
    lo, size = (np.asarray(config[key],dtype=float) for key in ("anchor_min", "anchor_size"))
    amp = config["amplitude"]
    reference_pose = points(pos,flow,color,lo,size,0.,amplitude=amp)
    max_root = max_tip = 0.
    for time in np.linspace(0.,10.,81):
        moved = points(pos,flow,color,lo,size,time,amplitude=amp)
        max_root = max(max_root,float(np.linalg.norm(moved[pinned]-pos[pinned],axis=1).max()))
        max_tip = max(max_tip,float(np.linalg.norm(moved[tip]-reference_pose[tip],axis=1).max()))
    seam = float(np.linalg.norm(moved-reference_pose,axis=1).max())
    assert max_root < 1e-6 and seam < 1e-6 and max_tip > .0003
    return {
        "source_sha256":sha(source),"previous_shader_sha256":sha(reference),"sha256":sha(target),
        "source_surfaces":len(previous),"surfaces":1,
        "source_atlas_pixels":sum(im.width*im.height for im in boards.values()),
        "texture_px":list(atlas.size),"triangles":new_metrics["triangles"],
        "skeletons":0,"animation_clips":0,"shader_poses":81,"duration_s":10.0,
        "rooted_current":config,"max_pinned_motion_m":max_root,"loop_seam_m":seam,"max_tip_displacement_m":max_tip,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    game = args.root / "projects/fishing-2d/game"
    policy = load(args.root / "resources/aquascape/geometry-budgets.json")
    catalog = load(game / "assets/aquascape-v5/catalog.json")
    results = []
    for row in catalog["assets"]:
        if row.get("geometry_revision") != "consolidated-vertex-current-v10":
            continue
        source = game / row["merge_source_model"].removeprefix("res://")
        reference = game / row["shader_model"].removeprefix("res://")
        audit = load(game / row["shader_metadata"].removeprefix("res://"))
        proof = next(entry for entry in audit["outputs"] if entry["id"] == row["id"])
        assert proof["source_sha256"] == sha(source) and proof["sha256"] == sha(reference)
        current = {key:proof[key] for key in ("anchor_min","anchor_size")}
        current["amplitude"] = .18  # Same default as the V10/V11 shader plant tank.
        target = args.output / source.name
        assert target.resolve() not in (source.resolve(), reference.resolve())
        build(source,reference,target)
        check = validate_merge(source,reference,target,current)
        hard_limit = policy["types"][budget_type(row,policy)]["hard_limit"]
        if check["triangles"] > hard_limit:
            raise ValueError(f"{row['id']}: {check['triangles']} exceeds {hard_limit} triangles")
        results.append({"id":row["id"],"limit":hard_limit,**check})
        print(row["id"], check["source_surfaces"],"→ 1 surface, vertex current;",check["triangles"],"triangles",flush=True)
    if len(results) != 10:
        raise ValueError(f"Expected 10 legacy plants, got {len(results)}")
    args.report.write_text(json.dumps({"ok":True,"items":results},ensure_ascii=False,indent=2)+"\n")


if __name__ == "__main__":
    main()
