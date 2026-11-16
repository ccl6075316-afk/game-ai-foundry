"""Export the released editable fish without an original GLB or a static builder."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "resources/scripts/volume-fish"
EXACT_SKIN = ROOT / "resources/volume-fish/top-body-repair-20261105/group-c"
THREE_METHODS = ROOT / "resources/volume-fish/clean-pixel-three-20261112/methods"
sys.path[:0] = list(map(str, [
    TOOLS, TOOLS / "portable", TOOLS / "hairtail_20261104", EXACT_SKIN, THREE_METHODS,
]))

from glb_io import arrays, sha
from patch_existing_fin_meshes import read, write
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE, geometry_signature, normal_attribute_signature

PACKED = {"rainbow_trout", "atlantic_salmon", "red_emperor", "nile_tilapia"}
RETAINED_SAMPLERS = {"mahi_mahi", "african_catfish"}


def guarded_meshes(objects):
    guarded = {}
    for obj in objects:
        assert EXACT_NORMAL_ATTRIBUTE in obj.data.attributes, obj.name
        geometry = geometry_signature(obj)
        normals = normal_attribute_signature(obj)
        assert geometry == obj.data["foundry_normal_geometry_sha256"], obj.name
        assert normals == obj.data["foundry_exact_normal_sha256"], obj.name
        guarded[obj.name] = {"geometry": geometry, "normal": normals}
    assert guarded
    return guarded


def restore_normals(document, binary, guarded):
    restored = set()
    for node in document["nodes"]:
        if "mesh" not in node or node["name"] not in guarded:
            continue
        for surface in document["meshes"][node["mesh"]]["primitives"]:
            attributes = surface["attributes"]
            owned = attributes.pop(EXACT_NORMAL_ATTRIBUTE)
            assert document["accessors"][owned]["count"] == document["accessors"][attributes["POSITION"]]["count"]
            normals = arrays(document, binary, owned)
            assert np.isfinite(normals).all() and np.max(abs(np.linalg.norm(normals, axis=1) - 1)) < 1e-4
            attributes["NORMAL"] = owned
        restored.add(node["name"])
    assert restored == guarded.keys()


def export_sailfish(output):
    guarded = guarded_meshes([bpy.data.objects["Closed_body"]])
    bpy.ops.export_scene.gltf(
        filepath=str(output), export_format="GLB", export_animations=True, export_yup=True,
        export_skins=True, export_attributes=True,
    )
    document, binary = read(output)
    restore_normals(document, binary, guarded)
    write(output, document, binary)
    return {"guarded_mesh_owners": guarded}


def export_retained_sampling(output, profile):
    from zander_source_exact_skin import export as export_exact_skin

    guarded = guarded_meshes([obj for obj in bpy.data.objects if obj.type == "MESH"])
    skin = export_exact_skin(output, json.loads(profile.read_text())["base_clip"])
    document, binary = read(output)
    restore_normals(document, binary, guarded)

    for material in document["materials"]:
        owner = bpy.data.materials[material["name"]]
        if "foundry_native_alpha_mode_explicit" in owner:
            alpha = owner["foundry_native_alpha_mode"]
            assert material.get("alphaMode", "OPAQUE") == alpha
            if owner["foundry_native_alpha_mode_explicit"]:
                material["alphaMode"] = alpha
            else:
                assert alpha == "OPAQUE"
                material.pop("alphaMode", None)
            double_sided = not owner.use_backface_culling
            if owner["foundry_native_double_sided_explicit"]:
                material["doubleSided"] = double_sided
            else:
                assert not double_sided
                material.pop("doubleSided", None)

    samplers = []
    texture_samplers = {}
    for material in document["materials"]:
        owner = bpy.data.materials[material["name"]]
        contract = json.loads(owner["foundry_frozen_gltf_sampler_json"])
        slots = {
            "base": material["pbrMetallicRoughness"].get("baseColorTexture"),
            "emission": material.get("emissiveTexture"),
        }
        assert set(contract) == {key for key, texture in slots.items() if texture is not None}
        for role, sampler in contract.items():
            if sampler not in samplers:
                samplers.append(sampler)
            sampler_index = samplers.index(sampler)
            texture_index = slots[role]["index"]
            assert texture_samplers.setdefault(texture_index, sampler_index) == sampler_index
            document["textures"][texture_index]["sampler"] = sampler_index
    assert set(texture_samplers) == set(range(len(document["textures"])))
    document["samplers"] = samplers
    write(output, document, binary)
    return {"guarded_mesh_owners": guarded, "source_owned_skin": skin, "samplers": samplers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species", required=True, choices=sorted(PACKED | RETAINED_SAMPLERS | {
        "atlantic_sailfish", "silver_arowana", "hairtail",
    }))
    for key in ("blend", "profile", "output", "report"):
        parser.add_argument(f"--{key}", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    blend, output, report = (path.resolve() for path in (args.blend, args.output, args.report))
    assert blend.is_file() and not output.exists() and not report.exists()
    before = sha(blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    if args.species in PACKED:
        from export_packed_fish_source import export_packed_source
        proof = export_packed_source(output)
    elif args.species in RETAINED_SAMPLERS:
        proof = export_retained_sampling(output, args.profile)
    elif args.species == "atlantic_sailfish":
        proof = export_sailfish(output)
    elif args.species == "silver_arowana":
        from author_three import native_export
        proof = native_export(output)
    else:
        from export_contract import export_current
        proof = export_current(output)

    assert sha(blend) == before
    result = {
        "ok": True, "kind": "formal_source_cold_export", "species": args.species,
        "source_sha256": before, "model_sha256": sha(output), "exporter_sha256": sha(__file__),
        "fresh_process": True, "candidate_glb_read": False, "runtime_static_builder_calls": 0,
    }
    if isinstance(proof, dict):
        result["export_proof"] = proof
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
