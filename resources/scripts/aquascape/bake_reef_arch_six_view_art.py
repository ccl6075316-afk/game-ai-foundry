"""Bake the six concept views onto the current arch for material review."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from build_from_art import Glb
from build_reef_arch_from_material_views import axes
from rig_plant_current import read_glb, array
from validate_art_models import inspect


DIRECTIONS = {
    "front": (2, 1), "rear": (2, -1), "left": (0, -1),
    "right": (0, 1), "top": (1, 1), "bottom": (1, -1),
}
ATLAS_WIDTH = 1536


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_donors(folder, references):
    donors = {}
    for view, entry in references.items():
        art = folder / entry["path"]
        silhouette = folder / (view + "-outline.png")
        if sha(art) != entry["source_png_sha256"] or sha(silhouette) != entry["outline_sha256"]:
            raise ValueError(f"Changed {view} art or silhouette")
        with Image.open(art) as src, Image.open(silhouette) as stencil:
            rgb = np.asarray(src.convert("RGB"))
            mask = np.asarray(stencil.convert("1"))
        trusted = ndi.binary_erosion(mask, iterations=2)
        distances, edges = ndi.distance_transform_edt(~trusted, return_indices=True)
        donors[view] = rgb[edges[0], edges[1]], distances
    return donors


def project(view, points, spans, donor):
    w, h = spans[view]
    pix, distance = donor
    a, b = axes(np.moveaxis(points, -1, 0), view, spans)
    row = np.rint(b * (pix.shape[0] - 1) / h).astype(int)
    col = np.rint(a * (pix.shape[1] - 1) / w).astype(int)
    rr = np.clip(row, 0, pix.shape[0] - 1)
    cc = np.clip(col, 0, pix.shape[1] - 1)
    miss = np.hypot(rr - row, cc - col) + distance[rr, cc]
    return pix[rr, cc], np.exp(-miss / 9.0)


def texture_atlas(faces, positions, normals, inverse, donors, spans, ground_y, sharp):
    atlas_width = 2048 if sharp else ATLAS_WIDTH
    count = len(faces)
    grids = int(np.ceil(np.sqrt(count)))
    cell = atlas_width // grids
    border = 2
    axis = np.clip((np.arange(cell) - border) / (cell - 2 * border - 1), 0.0, 1.0)
    sx, sy = np.meshgrid(axis, axis)
    outside = np.maximum(sx + sy, 1.0)
    sx, sy = sx / outside, sy / outside
    bary = np.stack([1.0 - sx - sy, sx, sy], axis=-1)

    xyz = positions.reshape(-1, 3, 3).copy()
    # Match the gray model's original image-space registration.
    xyz[:, :, 1] += ground_y
    weighted = np.zeros((int(inverse.max()) + 1, 3), dtype=np.float32)
    cross = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
    for j in range(3):
        np.add.at(weighted, inverse.reshape(-1, 3)[:, j], cross)
    weighted /= np.maximum(np.linalg.norm(weighted, axis=1, keepdims=True), 1e-12)
    corner_normals = weighted[inverse].reshape(-1, 3, 3)
    shells = normals.reshape(-1, 3, 3)[:, 0]
    sums = {view: 0.0 for view in donors}
    atlas = np.zeros((atlas_width, atlas_width, 3), dtype=np.uint8)
    atlas_uv = np.empty((count, 3, 2), dtype=np.float32)
    for i, triangle in enumerate(xyz):
        samples = bary @ triangle
        smooth = bary @ corner_normals[i]
        direction = 0.65 * smooth + 0.35 * shells[i]
        weight_stack, colors_stack = [], []
        interior = (sx + sy) < 0.999
        for view, (component, sign) in DIRECTIONS.items():
            colors, trust = project(view, samples, spans, donors[view])
            faces_view = np.maximum(sign * direction[..., component], 0.0)
            priority = faces_view ** 3.7 + 0.0015
            weight_stack.append(priority * np.maximum(trust, 0.001))
            colors_stack.append(colors)
        weights = np.stack(weight_stack)
        colors = np.stack(colors_stack)
        if sharp:
            # One visible source texel per UV sample. Multi-view averaging
            # created ghost edges in the previous version.
            owner = weights.argmax(axis=0)
            rows, cols = np.indices(owner.shape)
            output = colors[owner, rows, cols]
            for index, view in enumerate(DIRECTIONS):
                sums[view] += float(np.count_nonzero((owner == index) & interior))
        else:
            output = np.rint((colors * weights[..., None]).sum(axis=0) / weights.sum(axis=0)[..., None])
            for index, view in enumerate(DIRECTIONS):
                sums[view] += float(weights[index][interior].sum())
        x = i % grids * cell
        y = i // grids * cell
        atlas[y:y + cell, x:x + cell] = output.astype(np.uint8)
        lo, hi = border + 0.5, cell - border - 0.5
        atlas_uv[i] = (np.array([[lo, lo], [hi, lo], [lo, hi]]) + [x, y]) / atlas_width
    contributions = {k: round(v / sum(sums.values()), 4) for k, v in sums.items()}
    return Image.fromarray(atlas).convert("RGBA"), atlas_uv.reshape(-1, 2), contributions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--shape-report", type=Path)
    p.add_argument("--sharp", action="store_true")
    args = p.parse_args()
    folder = args.source
    args.output.mkdir(parents=True, exist_ok=True)
    shape_report = args.shape_report or folder / "six-material-gray.validation.json"
    ground_truth = json.loads(shape_report.read_text())
    references = json.loads((folder / "material-source.handoff.json").read_text())["views"]
    model = shape_report.parent / Path(ground_truth["gray_model"]["path"]).name
    if sha(model) != ground_truth["gray_model"]["sha256"]:
        raise ValueError("Gray mesh hash does not match its verified handoff")
    doc, binary = read_glb(model)
    attrs = doc["meshes"][0]["primitives"][0]["attributes"]
    positions = array(doc, binary, attrs["POSITION"])
    normals = array(doc, binary, attrs["NORMAL"])
    vertices, inverse = np.unique(positions, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    spans = {view: row["span_m"] for view, row in ground_truth["projections"].items()}
    donors = read_donors(folder, references)
    paint, uv, ownership = texture_atlas(faces, positions, normals, inverse, donors, spans,
                                          ground_truth.get("source_ground_y_m", 0.112), args.sharp)
    glb = Glb()
    mat = glb.material(paint, "Limestone from six concept views")
    name = "reef_through_arch_relief_art.glb" if args.sharp else "reef_through_arch_six_view_material.glb"
    out = args.output / name
    glb.mesh(positions, np.arange(len(positions)).reshape(-1, 3), uv, mat, out.stem)
    glb.save(out)
    next_doc, next_bin = read_glb(out)
    next_attrs = next_doc["meshes"][0]["primitives"][0]["attributes"]
    same_position = np.array_equal(positions, array(next_doc, next_bin, next_attrs["POSITION"]))
    same_normals = np.array_equal(normals, array(next_doc, next_bin, next_attrs["NORMAL"]))
    payload = inspect(out)
    ok = same_position and same_normals and payload["ok"] and not payload["nonmanifold_edges"]
    report = {
        "stage": "six_view_material_preview", "ok": ok, "triangles": len(faces),
        "gray_sha256": sha(model), "model_sha256": sha(out), "atlas_size": list(paint.size),
        "source_view_weight_share": ownership, "position_stream_exact": same_position,
        "normal_stream_exact": same_normals, "material_passes": 1,
        "projected_texel_mode": "nearest_single_source" if args.sharp else "weighted_source_rgb",
        "gltf_texture_sampling": "nearest_no_mip",
        "embedded_texture_bytes": next_doc["bufferViews"][next_doc["images"][0]["bufferView"]]["byteLength"],
        "closed_geometry": payload["ok"] and not payload["nonmanifold_edges"],
        "limit": "Texture is baked albedo. Relief, recesses and cast shadows come from the gray mesh geometry. Source images infer interior color.",
    }
    np.savez_compressed(out.with_suffix(".npz"), vertices=vertices, faces=faces)
    (args.output / "material.validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return int(not ok)


if __name__ == "__main__":
    raise SystemExit(main())
