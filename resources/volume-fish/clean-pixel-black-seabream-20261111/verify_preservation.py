"""Compare the final source export against the original and the frozen body."""
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

work = Path(__file__).resolve().parent
root = work.parents[1]
sys.path.insert(0, str(root / "resources/scripts/volume-fish/portable"))
from glb_io import arrays, read_glb

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rgba(document, binary):
    view = document["bufferViews"][document["images"][0]["bufferView"]]
    offset = view.get("byteOffset", 0)
    return np.array(Image.open(io.BytesIO(binary[offset:offset+view["byteLength"]])).convert("RGBA"))

baseline = Path(json.loads((work / "baseline.plan.json").read_text())["model"])
final = work / "source-r1" / "fish.glb"
original_doc, original_blob = read_glb(baseline)
new_doc, new_blob = read_glb(final)
for key in ("meshes", "nodes", "skins", "animations", "materials", "textures", "samplers", "accessors"):
    assert original_doc.get(key) == new_doc.get(key), key
for index in range(len(original_doc["accessors"])):
    original = arrays(original_doc, original_blob, index)
    current = arrays(new_doc, new_blob, index)
    assert np.array_equal(original, current) and np.isfinite(current).all(), index
original_atlas, new_atlas = rgba(original_doc, original_blob), rgba(new_doc, new_blob)
assert np.array_equal(original_atlas[:, :, 3], new_atlas[:, :, 3])
baked_atlas = np.array(Image.open(work / "fins-r1" / "atlas.png").convert("RGBA"))
assert np.array_equal(new_atlas, baked_atlas)
owned = np.load(work / "body-r1" / "body-ownership.npz")["owned"]
body_atlas = np.array(Image.open(work / "body-r1" / "atlas.png").convert("RGBA"))
assert np.array_equal(new_atlas[owned], body_atlas[owned])
result = {
    "ok": True, "model_sha256": sha(final), "baseline_sha256": sha(baseline),
    "nonimage_accessors_exact": len(original_doc["accessors"]),
    "original_alpha_exact": True, "source_export_rgba_equals_bake": True,
    "frozen_body_texels": int(owned.sum()), "frozen_body_rgba_exact": True,
}
output = work / "source-r1" / "preservation.validation.json"
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
