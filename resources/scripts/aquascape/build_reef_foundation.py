"""Build source-art reef candidates with editable topology and baked nearest-color atlas."""

import argparse
import hashlib
import json
from pathlib import Path

import subprocess
import tempfile
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.measure import marching_cubes

from build_decor_ten import ray_hits
from build_from_art import Glb
from build_from_three_views import sample_sdf, silhouette


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_view(path):
    crop, mask, _ = silhouette(path)
    pixels = np.asarray(crop)
    trusted = ndi.binary_erosion(mask & (pixels.min(axis=-1) < 215), iterations=2)
    closest = ndi.distance_transform_edt(~trusted, return_distances=False, return_indices=True)
    colors = pixels[closest[0], closest[1]]
    return colors, mask


def rounded_intersection(a, b, radius):
    blend = np.maximum(radius - abs(a - b), 0) / radius
    return np.minimum(a, b) - blend ** 2 * radius * 0.25


def surface(record, masks, target, blender):
    asset = record["id"]
    width, height, depth = record["nominal_size_xyz_m"]
    step = max(width, height, depth) / 103
    x = np.arange(-width / 2 - 3 * step, width / 2 + 4 * step, step)
    y = np.arange(-3 * step, height + 4 * step, step)
    z = np.arange(-depth / 2 - 3 * step, depth / 2 + 4 * step, step)
    X, Y, Z = np.ix_(x, y, z)
    front = sample_sdf(masks["front"], X / width + 0.5, 1 - Y / height, height / masks["front"].shape[0])
    front = np.minimum(front, np.minimum(width / 2 - abs(X), height - Y))
    x_frac = X / width
    y_frac = Y / height
    z_frac = Z / depth
    # Aux drawings of the arch repeat the front. Its passage is the front negative
    # space continued through rounded transverse rock sections, with asymmetric feet.
    if asset == "reef_through_arch":
        center = 0.065 * np.sin(x_frac * np.pi * 2) + 0.03 * y_frac
        half_depth = 0.45 - 0.09 * y_frac + 0.033 * np.cos(8 * x_frac + 2.5 * y_frac)
        span = 1.08 - 0.17 * (np.abs(z_frac - center) / 0.45) ** 2
        lip = sample_sdf(masks["front"], x_frac / span + 0.5, 1 - y_frac, height / masks["front"].shape[0])
        field = rounded_intersection(lip, (half_depth - abs(z_frac - center)) * depth, depth * 0.075)
        # Preserve a useful uninterrupted clearance at the irregular lower lip.
        clear = 1 - ((X - 0.14) / 0.83) ** 2 - (np.maximum(Y - 0.29, 0) / 1.08) ** 2
        field = np.minimum(field, -clear * 0.3)
    elif asset == "reef_blind_grotto":
        center = -0.11 * y_frac + 0.09 * x_frac
        half_depth = 0.48 - 0.105 * y_frac + 0.042 * np.sin(8 * x_frac + 5 * y_frac)
        slab = (half_depth - np.abs(z_frac - center)) * depth
        field = rounded_intersection(front, slab, depth * 0.11)
        # Keep an explicit rear wall, floor, and roof. The opening narrows as it
        # recedes, preserving the forward shelter under the front source's lip.
        opening_radius = np.clip(0.31 + 0.16 * z_frac, 0.255, 0.39)
        arch = 1 - ((x_frac + 0.055) / opening_radius) ** 2 - ((y_frac - 0.065) / 0.47) ** 2
        void = np.minimum(np.minimum(arch * height * 0.3, (y_frac - 0.043) * height), (z_frac + 0.225) * depth)
        floor = np.minimum(np.minimum(0.092 * height - Y, Y + step),
                           (1 - ((x_frac + 0.05) / 0.37) ** 2 - ((z_frac + 0.03) / 0.45) ** 2) * depth * 0.2)
        field = np.minimum(np.maximum(field, floor), -void)
    elif asset == "reef_pinnacle":
        center = -0.14 * y_frac + 0.12 * x_frac
        half_depth = 0.49 - 0.27 * y_frac + 0.061 * np.sin(11 * y_frac + 3 * x_frac)
        field = rounded_intersection(front, (half_depth - abs(z_frac - center)) * depth, depth * 0.145)
    else:
        right = sample_sdf(masks["right"], 0.5 - z_frac, 1 - y_frac, height / masks["right"].shape[0])
        # For the rock ramp and terrace these views are approximate end/plan
        # references. Their bounds shape thickness without cutting the front ridge.
        top = sample_sdf(masks["top"], x_frac + 0.5, z_frac + 0.5, width / masks["top"].shape[1])
        field = np.minimum(front, np.minimum(right + depth * 0.11, top + depth * 0.075))
    field = np.minimum(field, depth / 2 - abs(Z))
    field = ndi.gaussian_filter(field.astype(np.float32), sigma=1.1)
    # Preserve a grounded finite foot and choose the coherent rock body only.
    field = np.minimum(field, np.broadcast_to(Y + 0.0097, field.shape))
    field[[0, -1], :, :] = -step
    field[:, [0, -1], :] = -step
    field[:, :, [0, -1]] = -step
    labels, _ = ndi.label(field > 0)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    field[(labels > 0) & (labels != counts.argmax())] = -step
    vertices, faces, _, _ = marching_cubes(field, level=0, spacing=(step,) * 3, allow_degenerate=False)
    vertices += np.array([x[0], y[0], z[0]])
    tri = vertices[faces]
    signed_volume = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()
    if signed_volume < 0:
        faces = faces[:, [0, 2, 1]]
    with tempfile.TemporaryDirectory(prefix="reef-decimate-") as temp:
        candidate = Path(temp) / (asset + ".npz")
        np.savez(candidate, vertices=vertices, faces=faces)
        script = Path(__file__).with_name("blender_reef_mesh.py")
        command = [str(blender), "-b", "--python-exit-code", "1", "--python", str(script), "--",
                   str(candidate), "--triangles", str(target)]
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(result.stdout)
        mesh = np.load(candidate)
        vertices, faces = mesh["vertices"], mesh["faces"]
    vertices[:, 1] -= vertices[:, 1].min()
    return vertices.astype(np.float32), faces


def sample_art(pixels, u, v):
    row = np.clip(np.rint(v * (pixels.shape[0] - 1)), 0, pixels.shape[0] - 1).astype(int)
    col = np.clip(np.rint(u * (pixels.shape[1] - 1)), 0, pixels.shape[1] - 1).astype(int)
    return pixels[row, col]


def mirror_tile(coord):
    return 1 - abs(coord % 2 - 1)


def atlas_mesh(record, vertices, faces, art, neutral, path):
    """Pack each triangle with a padded UV chart and bake the art from three axes."""
    width, height, depth = record["nominal_size_xyz_m"]
    atlas_size = 1536 if record["budget_class"] == "large_rock" else 1024
    columns = int(np.ceil(np.sqrt(len(faces))))
    cell = atlas_size // columns
    margin = 2
    axis = np.arange(cell, dtype=float)
    us, vs = np.meshgrid(axis, axis)
    us = np.clip((us - margin) / (cell - margin * 2 - 1), 0, 1)
    vs = np.clip((vs - margin) / (cell - margin * 2 - 1), 0, 1)
    outside = np.maximum(us + vs, 1.0)
    us, vs = us / outside, vs / outside
    atlas = np.zeros((atlas_size, atlas_size, 3), dtype=np.uint8)
    uvs = []
    triangles = vertices[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-15)
    for index, tri in enumerate(triangles):
        normal = normals[index]
        pts = tri[0] + us[:, :, None] * (tri[1] - tri[0]) + vs[:, :, None] * (tri[2] - tri[0])
        px, py, pz = np.moveaxis(pts, 2, 0)
        # A neutral donor covers inferred back/underside surfaces. The art's
        # apparent openings must never be copied to a closed rear or roof.
        factor = 1.0 / min(width, depth)
        neutral_a = sample_art(neutral, mirror_tile(pz * factor + 0.26), mirror_tile(py * factor + 0.15))
        neutral_b = sample_art(neutral, mirror_tile(px * factor + 0.54), mirror_tile(pz * factor + 0.33))
        neutral_c = sample_art(neutral, mirror_tile(px * factor + 0.12), mirror_tile(py * factor + 0.49))
        use_aux = record["id"] in {"reef_backwall", "reef_shelf_terrace", "reef_rubble_apron"}
        right = neutral_a
        top = neutral_b
        if use_aux and normal[0] > 0.0:
            right = 0.48 * sample_art(art["right"], 0.5 - pz / depth, 1 - py / height) + 0.52 * neutral_a
        if use_aux and normal[1] > 0.0:
            top = 0.45 * sample_art(art["top"], 0.5 + px / width, 0.5 + pz / depth) + 0.55 * neutral_b
        front = sample_art(art["front"], 0.5 + px / width, 1 - py / height) if normal[2] >= 0.0 else neutral_c
        paints = [right, top, front]
        weights = abs(normal) ** 4
        weights /= weights.sum()
        offset_x, offset_y = (index % columns) * cell, (index // columns) * cell
        atlas[offset_y:offset_y + cell, offset_x:offset_x + cell] = sum(
            paint * weight for paint, weight in zip(paints, weights)
        ).astype(np.uint8)
        low, high = margin + 0.5, cell - margin - 0.5
        uvs.extend(
            [[(offset_x + x) / atlas_size, (offset_y + y) / atlas_size] for x, y in
             [(low, low), (high, low), (low, high)]]
        )
    glb = Glb()
    material = glb.material(Image.fromarray(atlas).convert("RGBA"), record["id"] + "_baked_art")
    glb.mesh(triangles.reshape(-1, 3), np.arange(len(faces) * 3).reshape(-1, 3), uvs, material, record["id"])
    glb.save(path)
    return atlas_size


def cavity_checks(record, vertices, faces):
    width, height, depth = record["nominal_size_xyz_m"]
    probes = []
    if record["id"] == "reef_through_arch":
        for x in [-0.105, 0.032, 0.169]:
            for y in [0.09, 0.22, 0.36]:
                hits = ray_hits(vertices, faces, [x * width, y * height, depth], [0, 0, -1], depth * 2)
                probes.append({"type": "open_z", "x_m": x * width, "y_m": y * height, "hits_m": hits, "ok": not hits})
    elif record["id"] == "reef_blind_grotto":
        for x in [-0.13, -0.055, 0.02]:
            hits = ray_hits(vertices, faces, [x * width, height * 0.20, depth], [0, 0, -1], depth * 2)
            probes.append({"type": "rear_wall", "x_m": x * width, "hits_m": hits,
                           "ok": len(hits) == 2 and hits[0] >= depth * 0.94})
        for axis, direction in [("floor", [0, -1, 0]), ("roof", [0, 1, 0])]:
            hits = ray_hits(vertices, faces, [-width * 0.055, height * 0.22, 0], direction, height)
            probes.append({"type": axis, "hits_m": hits, "ok": bool(hits)})
    return probes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--neutral-donor", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    game = root / "projects/fishing-2d/game"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads((root / "resources/aquascape/reef-expansion-20261123/front-art.handoff.json").read_text())
    policy = json.loads((root / "resources/aquascape/geometry-budgets.json").read_text())["types"]
    rows, reports = [], []
    for record in config["outputs"]:
        key = record["id"]
        path = output / (key + ".glb")
        views = root / f"projects/aquascape-{key}-views-20261123/output"
        inputs = {
            "front": root / record["front_r2"]["path"],
            **{v: views / f"{key}_{v}_raw.png" for v in ("right", "top")},
        }
        views_data = {view: read_view(source) for view, source in inputs.items()}
        art = {view: data[0] for view, data in views_data.items()}
        masks = {view: data[1] for view, data in views_data.items()}
        donor = args.neutral_donor.resolve()
        with Image.open(donor) as image:
            neutral = np.array(image.convert("RGB"))
        if key in {"reef_blind_grotto", "reef_pinnacle", "reef_rubble_apron"}:
            neutral = (neutral * np.array([1.0, 0.93, 0.83])).astype(np.uint8)
        inputs["neutral_surface"] = donor
        budget = policy[record["budget_class"]]
        vertices, faces = surface(record, masks, budget["preferred"], args.blender)
        atlas_size = atlas_mesh(record, vertices, faces, art, neutral, path)
        cavity = cavity_checks(record, vertices, faces)
        # Preserve positions, topology with shared vertices, and baked corner UVs
        # for the Blender editing source, even when the GLB splits UV seams.
        np.savez_compressed(output / (key + ".npz"), vertices=vertices, faces=faces)
        rows.append({
            "id": key, "name_zh": record["name_zh"], "category": "rock", "budget_type": record["budget_class"],
            "model": "res://" + path.relative_to(game).as_posix(), "animated": False,
            "placement_size_m": max(record["nominal_size_xyz_m"]),
            "geometry_budget": {**budget, "type": record["budget_class"]},
        })
        reports.append({
            "id": key, "triangles": len(faces), "bounds_xyz_m": np.ptp(vertices, axis=0).tolist(),
            "model_sha256": digest(path), "materials": 1, "atlas_size": [atlas_size, atlas_size],
            "inputs": {view: {"path": str(source.relative_to(root)), "sha256": digest(source)}
                       for view, source in inputs.items()},
            "cavity_checks": cavity, "ok": len(faces) <= budget["hard_limit"] and all(p["ok"] for p in cavity),
        })
        print(key, len(faces), "triangles", "cavity", all(p["ok"] for p in cavity), flush=True)
    (output / "catalog.json").write_text(json.dumps({"assets": rows}, ensure_ascii=False, indent=2) + "\n")
    result = {"command": "aquascape.reef-foundation-build", "status": "candidate", "user_acceptance": "pending",
              "ok": all(row["ok"] for row in reports), "outputs": reports}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return int(not result["ok"])


if __name__ == "__main__":
    raise SystemExit(main())
