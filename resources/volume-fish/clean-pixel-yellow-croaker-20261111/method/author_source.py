"""Update the original material images while preserving Blender's authored objects."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
SCRIPTS = ROOT/"resources/scripts/volume-fish"
sys.path[:0] = [str(SCRIPTS),str(SCRIPTS/"portable")]
from export_ordinary_source_owned import export_source
from restore_fin_source_normals import geometry_signature, normal_attribute_signature
from source_snapshot import rig_action_snapshot

CHARTS = {
    "Anal_native_source": 0,
    "Caudal_native_source": 1,
    "Yellow croaker native clean side skin": 2,
    "Front skin source chart": 3,
    "Front mouth oral chart": 3,
    "Current canonical posterior shoulder chart": 4,
    "Current posterior internal body chart": 5,
    "Dorsal_native_source": 6,
    "Pectoral_left_native_source": 7,
    "Pectoral_right_native_source": 7,
    "Pelvic_left_native_source": 8,
    "Pelvic_right_native_source": 8,
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def signature():
    result = []
    for obj in sorted(bpy.data.objects,key=lambda obj:obj.name):
        if obj.type != "MESH":
            continue
        uv = [(layer.name, [list(loop.uv) for loop in layer.data]) for layer in obj.data.uv_layers]
        weights = [[(group.group,group.weight) for group in v.groups] for v in obj.data.vertices]
        mats = [(slot.material.name, slot.material.get("foundry_export_contract_json"))
                for slot in obj.material_slots]
        result.append((obj.name,geometry_signature(obj),normal_attribute_signature(obj),uv,weights,mats))
    return result, rig_action_snapshot()

def main():
    parser = argparse.ArgumentParser()
    for arg in ["source","body","fins","output"]:
        parser.add_argument("--"+arg,type=Path,required=True)
    a = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    manifest = json.loads((WORK/"manifest.json").read_text())
    source = a.source.resolve()
    before_sha = sha(source)
    assert before_sha == manifest["baseline"]["source_sha256"]
    assert a.output.resolve().is_relative_to(WORK) and not a.output.exists()
    body_proof = json.loads((a.body/"bake.validation.json").read_text())
    fin_proof = json.loads((a.fins/"bake.validation.json").read_text())
    assert body_proof["ok"] and fin_proof["ok"] and fin_proof["body_frozen"]
    assert fin_proof["body_rgba"] == body_proof["body_rgba"]
    patches = body_proof["changed_images"] | fin_proof["changed_images"]
    assert set(patches) == {str(i) for i in CHARTS.values()}
    bpy.ops.wm.open_mainfile(filepath=str(source))
    before = signature()
    touched = {}
    for name, image_index in CHARTS.items():
        material = bpy.data.materials[name]
        nodes = [node for node in material.node_tree.nodes if node.type=="TEX_IMAGE" and node.image]
        assert len(nodes)==1
        image = nodes[0].image
        if image.name in touched:
            assert touched[image.name] == image_index
            continue
        patch = patches[str(image_index)]
        path = Path(patch["path"])
        assert sha(path) == patch["sha256"] and image.packed_file
        payload = path.read_bytes()
        image.pack(data=payload,data_len=len(payload))
        assert bytes(image.packed_file.data) == payload
        touched[image.name] = image_index
    assert signature() == before
    a.output.mkdir()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output/"fish.blend"))
    proof = export_source(a.output/"fish.glb")
    assert signature() == before and sha(source)==before_sha
    proof.update(source_sha256=sha(a.output/"fish.blend"), input_source_sha256=before_sha,
                 authored_image_ids=touched, source_static_rig_motion_exact=True)
    (a.output/"source-authoring.validation.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({"ok":True,"model_sha256":proof["model_sha256"]}))

if __name__ == "__main__":
    main()
