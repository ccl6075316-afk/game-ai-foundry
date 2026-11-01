"""Replace an authored moving-fin footprint with a safe native donor patch.

The supplied source is never edited. Every changed RGB texel copies one native
source texel at a frozen translation; body alpha and all other texels are exact.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from build_surface_charts import raster
from freeze_surface_ownership import accessor, read_glb


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def polygons(shape, rows):
    mask = np.zeros(shape, np.uint8)
    for polygon in rows:
        cv2.fillPoly(mask, [np.asarray(polygon, np.int32)], 1)
    return mask > 0


def glb_uv_mask(gltf, binary, names, width, height):
    mask = np.zeros((height, width), np.uint8)
    found = []
    for node in gltf["nodes"]:
        name = node.get("name")
        if name not in names or "mesh" not in node:
            continue
        found.append(name)
        for part in gltf["meshes"][node["mesh"]]["primitives"]:
            uv = accessor(gltf, binary, part["attributes"]["TEXCOORD_0"])
            tri = accessor(gltf, binary, part["indices"]).reshape(-1, 3)
            mask = np.maximum(mask, raster(uv, tri, width, height))
    assert sorted(found) == sorted(names), (found, names)
    return mask > 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.plan.read_text())
    assert cfg["method"] == "single_translated_safe_native_donor"
    for path, expected in cfg["frozen_inputs"].items():
        assert sha(path) == expected, path
    source = np.asarray(Image.open(cfg["source"]).convert("RGBA"))
    current = np.asarray(Image.open(cfg["body_texture"]).convert("RGBA"))
    opaque = np.asarray(Image.open(cfg["opaque"]).convert("RGBA"))
    assert source.shape == current.shape == opaque.shape
    assert np.array_equal(current, source), "Current material texture differs from pinned original"
    height, width = source.shape[:2]
    gltf, binary = read_glb(Path(cfg["model"]))
    fin = glb_uv_mask(gltf, binary, cfg["fins"], width, height)
    fin |= polygons((height, width), cfg["painted_fin_polygons_px"])
    k = 2 * int(cfg["fin_margin_px"]) + 1
    excluded = cv2.dilate(fin.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
    body = glb_uv_mask(gltf, binary, [cfg["body_node"]], width, height)
    opaque_source = source[:, :, 3] >= 250
    k = 2 * int(cfg["outline_margin_px"]) + 1
    interior = cv2.erode(opaque_source.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
    head = np.indices((height, width))[1] >= round(float(cfg["head_start_u"]) * width)
    target = body & ~head & (excluded | ~interior)
    target &= polygons((height, width), cfg["repair_only_polygons_px"])
    protected = polygons((height, width), cfg["protected_body_marks_polygons_px"])
    target &= ~protected
    valid = body & ~excluded & interior & ~head & ~protected
    assert target.any() and not np.any(target & protected)
    dx, dy = map(int, cfg["donor_translation_px"])
    yy, xx = np.where(target)
    donor_x, donor_y = xx + dx, yy + dy
    assert donor_x.min() >= 0 and donor_x.max() < width
    assert donor_y.min() >= 0 and donor_y.max() < height
    assert np.all(valid[donor_y, donor_x]), "Translated donor touches an unsafe source pixel"
    output = current.copy()
    output[yy, xx, :3] = source[donor_y, donor_x, :3]
    assert np.array_equal(output[~target], current[~target])
    assert np.array_equal(output[:, :, 3], current[:, :, 3])
    assert np.array_equal(output[yy, xx, :3], source[donor_y, donor_x, :3])
    folder = Path(cfg["output"])
    folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output).save(folder / "skin-candidate.png")
    Image.fromarray(target.astype(np.uint8) * 255).save(folder / "repair-mask.png")
    Image.fromarray(valid.astype(np.uint8) * 255).save(folder / "safe-donors.png")
    crop = (1190, 345, 1590, 560)
    preview = Image.new("RGB", (400 * 3, 215), (25, 49, 63))
    for i, image in enumerate((current, output, np.dstack([target.astype(np.uint8) * 255] * 3))):
        preview.paste(Image.fromarray(image[:, :, :3]).crop(crop), (i * 400, 0))
    preview.save(folder / "pectoral-before-candidate-mask.png")
    report = {
        "schema_version": 1, "kind": "native_body_fin_footprint_candidate",
        "ok": True, "visual_acceptance": False, "species": cfg["species"],
        "plan_sha256": sha(args.plan), "builder_sha256": sha(__file__),
        "source_sha256": sha(cfg["source"]), "model_sha256": sha(cfg["model"]),
        "body_texture_sha256": sha(cfg["body_texture"]),
        "changed_pixels": int(target.sum()), "donor_translation_px": [dx, dy],
        "body_alpha_unchanged": True, "outside_target_rgba_unchanged": True,
        "protected_body_mark_pixels_changed": 0,
        "unsafe_donor_pixels": 0, "native_source_rgb_exact": True,
        "outputs": {name: sha(folder / name) for name in
                    ("skin-candidate.png", "repair-mask.png", "safe-donors.png",
                     "pectoral-before-candidate-mask.png")},
        "limits": "One translated native patch is an artistic reconstruction of hidden skin, not recovered source anatomy. Actual Godot hidden-fin and motion views must approve seams and retained base marks. Geometry/UV/skin are untouched.",
    }
    (folder / "repair.validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ok": True, "changed_pixels": report["changed_pixels"],
                      "candidate": str(folder / "skin-candidate.png")}))


if __name__ == "__main__":
    main()
