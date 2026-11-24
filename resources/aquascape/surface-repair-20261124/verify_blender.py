"""Cold-read the editable masters and compare every face corner to the deployed GLB.

Run with Blender in background mode:
  blender -b --python-exit-code 1 -P verify_blender.py -- /path/to/blender.validation.json
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

RELEASE = Path(__file__).resolve().parent
ROOT = RELEASE.parents[2]


def glb_payload(path):
    raw = path.read_bytes()
    json_size = struct.unpack_from("<I", raw, 12)[0]
    return json.loads(raw[20:20 + json_size]), raw[28 + json_size:]


def stream(doc, binary, accessor, width):
    view = doc["bufferViews"][accessor["bufferView"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    assert view.get("byteStride", width * 4) == width * 4
    assert accessor["componentType"] == 5126
    return np.frombuffer(binary, "<f4", accessor["count"] * width, offset).reshape(-1, width)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def error(actual, expected):
    return float(np.max(np.abs(actual - expected)))


def verify(row, bind_normals):
    model = ROOT / "projects/fishing-2d/game" / row["model"].removeprefix("res://")
    source = ROOT / row["editable"]
    assert sha(model.read_bytes()) == row["after_sha256"], row["id"]
    doc, binary = glb_payload(model)
    primitive, = doc["meshes"][0]["primitives"]
    attrs = primitive["attributes"]
    position, normal, uv = (
        stream(doc, binary, doc["accessors"][attrs[key]], width)
        for key, width in (("POSITION", 3), ("NORMAL", 3), ("TEXCOORD_0", 2))
    )
    position = position[:, [0, 2, 1]].copy()
    normal = normal[:, [0, 2, 1]].copy()
    position[:, 1] *= -1
    normal[:, 1] *= -1
    uv = uv.copy()
    uv[:, 1] = 1 - uv[:, 1]
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj, = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    mesh = obj.data
    assert len(mesh.polygons) == row["triangles"]
    assert all(poly.loop_total == 3 for poly in mesh.polygons)
    positions = np.array([obj.matrix_world @ mesh.vertices[loop.vertex_index].co for loop in mesh.loops])
    uvs = np.array([corner.uv for corner in mesh.uv_layers.active.data])
    position_error = error(positions, position)
    uv_error = error(uvs, uv)
    assert max(position_error, uv_error) < 1e-6, (row["id"], position_error, uv_error)
    normals = np.array([corner.vector for corner in mesh.corner_normals])
    if bind_normals and error(normals, normal) > 0.005:
        for poly in mesh.polygons:
            poly.use_smooth = True
        mesh.normals_split_custom_set(normal.tolist())
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
        return verify(row, False)
    normal_error = error(normals, normal)
    assert normal_error < 0.005, (row["id"], normal_error)

    material, = mesh.materials
    tex, = [node for node in material.node_tree.nodes if node.type == "TEX_IMAGE"]
    assert tex.interpolation == "Closest"
    assert tex.image.packed_file
    image = doc["bufferViews"][doc["images"][0]["bufferView"]]
    offset = image.get("byteOffset", 0)
    atlas = binary[offset:offset + image["byteLength"]]
    assert tex.image.packed_file.data == atlas, row["id"]
    entry = {
        "id":row["id"], "blend_sha256":sha(source.read_bytes()), "model_sha256":row["after_sha256"],
        "packed_atlas_sha256":sha(atlas), "atlas_size_px":list(tex.image.size),
        "triangle_corners":len(positions), "max_position_error_m":position_error,
        "max_uv_error":uv_error, "max_normal_component_error":normal_error,
    }
    print(row["id"], "cold source matches", flush=True)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--release", type=Path, default=RELEASE / "release.json")
    parser.add_argument("--bind-normals", action="store_true",
                        help="Transfer deployed corner normals into a master if they differ")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    release = json.loads(args.release.read_text(encoding="utf-8"))
    rows = [verify(row, args.bind_normals) for row in release["items"]]
    args.report.write_text(json.dumps({"ok":True, "count":len(rows), "items":rows}, indent=2) + "\n")
    print(f"Cold Blender source matches deployed models for {len(rows)} items.")


if __name__ == "__main__":
    main()
