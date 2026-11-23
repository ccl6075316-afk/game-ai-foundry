"""Build the reef arch gray mesh from its six initial material concept outlines."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.measure import marching_cubes

from build_decor_ten import ray_hits
from build_from_art import Glb
from build_from_three_views import sample_sdf
from validate_art_models import inspect


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dimensions(mask, width, height):
    h, w = mask.shape
    if width is not None:
        return width, h * width / w
    return w * height / h, height


def blend_opposites(a, b):
    return 0.67 * np.minimum(a, b) + 0.33 * np.maximum(a, b)


def round_intersection(a, b, radius):
    transition = np.maximum(1 - np.abs(a - b) / radius, 0)
    return np.minimum(a, b) - (radius * 0.25) * transition ** 2


def axes(world, view, spans):
    x, y, z = world
    w, h = spans[view]
    if view in {"front", "rear"}:
        return x * (1 if view == "front" else -1) + w * 0.5, h - y
    if view in {"left", "right"}:
        return z * (1 if view == "left" else -1) + w * 0.5, h - y
    return x + w * 0.5, z * (1 if view == "top" else -1) + h * 0.5


def sampled_distance(mask, xyz, view, spans):
    a, b = axes(xyz, view, spans)
    w, h = spans[view]
    d = sample_sdf(mask, a / w, b / h, w / mask.shape[-1])
    # Keep padded samples outside each image crop in free space.
    edge = np.minimum(np.minimum(a, w - a), np.minimum(b, h - b))
    return np.where(edge < 0, np.minimum(d, edge), d)


def shape_patch(field, coordinates, spec, floor, add):
    _, location, radii, yaw, dip = spec
    center = np.asarray(location) + [0, floor, 0]
    radius = np.asarray(radii)
    extent = np.max(radius) * 1.55 + 0.12
    windows = tuple(slice(np.searchsorted(axis, c - extent), np.searchsorted(axis, c + extent))
                    for axis, c in zip(coordinates, center))
    x, y, z = np.ix_(*(axis[w] - c for axis, w, c in zip(coordinates, windows, center)))
    radians = np.radians([yaw, dip])
    cy, ct = np.cos(radians)
    sy, st = np.sin(radians)
    xz = cy * x - sy * z
    q = [(ct * xz + st * y) / radius[0], (ct * y - st * xz) / radius[1],
         (sy * x + cy * z) / radius[2]]
    # A local angular, shallow bed with two truncated corners; the broad
    # surface and the steep fracture wall survive reduction as geometry.
    core = 1.0 - (sum(abs(a) ** 3.8 for a in q)) ** (1.0 / 3.8)
    chamfer_a = 1.24 - (0.69 * q[0] + 0.39 * q[1] + 0.77 * q[2])
    chamfer_b = 1.20 - (-0.64 * q[0] + 0.71 * q[1] - 0.46 * q[2])
    rock = np.minimum(core, np.minimum(chamfer_a, chamfer_b)) * max(np.min(radius), 0.08)
    local = field[windows]
    if add:
        # Merge layers into the parent rock while retaining their ledge lips.
        transition = np.maximum(1.0 - abs(local - rock) / 0.045, 0.0)
        local[:] = np.maximum(local, rock) + 0.01125 * transition ** 2
    else:
        local[:] = round_intersection(local, -rock, 0.025)


def sculpt_hull(masks, spans, relief=None):
    width = spans["front"][0]
    height = max(spans[k][1] for k in ["front", "rear", "left", "right"])
    depth = max([spans[k][1] for k in ["top", "bottom"]] + [spans[k][0] for k in ["left", "right"]])
    step = width / (160 if relief else 120)
    pad = 0.36 if relief else 3 * step
    origin = np.array([-width * 0.5 - pad, -3 * step, -depth * 0.5 - pad])
    x = np.arange(origin[0], width * 0.5 + pad, step)
    y = np.arange(origin[1], height + pad, step)
    z = np.arange(origin[2], depth * 0.5 + pad, step)
    xyz = np.ix_(x, y, z)
    distances = {view: sampled_distance(mask, xyz, view, spans) for view, mask in masks.items()}
    front = blend_opposites(distances["front"], distances["rear"])
    ends = blend_opposites(distances["left"], distances["right"])
    plans = blend_opposites(distances["top"], distances["bottom"])
    field = round_intersection(round_intersection(front, ends, 0.16), plans, 0.13)
    field = ndi.gaussian_filter(field.astype(np.float32), sigma=1.35)
    # The underside material study shows two broad, planar contact pads.
    # Section off the irregular rolled pixels close to the drawn ground.
    floor = 0.112
    if relief:
        floor = relief["floor_y_from_reference_m"]
        for ledge in relief["ledges"]:
            shape_patch(field, (x, y, z), ledge, floor, add=True)
        for recess in relief["recesses"]:
            shape_patch(field, (x, y, z), recess, floor, add=False)
        field = ndi.gaussian_filter(field, sigma=0.58)
    field = np.minimum(field, np.broadcast_to(xyz[1] - floor, field.shape))
    labels, _ = ndi.label(field > 0)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    field[(labels > 0) & (labels != counts.argmax())] = -step
    field[[0, -1], :, :] = -step
    field[:, [0, -1], :] = -step
    field[:, :, [0, -1]] = -step
    vertices, faces, _, _ = marching_cubes(field, 0, spacing=(step,) * 3, allow_degenerate=False)
    vertices += origin
    return vertices, faces, float(vertices[:, 1].min())


def reduce_mesh(vertices, faces, blender, preferred):
    with tempfile.TemporaryDirectory(prefix="reef-six-views-") as temp:
        exchange = Path(temp) / "arch.npz"
        np.savez(exchange, vertices=vertices, faces=faces)
        command = [str(blender), "-b", "--python-exit-code", "1", "--python",
                   str(Path(__file__).with_name("blender_reef_mesh.py")), "--",
                   str(exchange), "--triangles", str(preferred)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout)
        with np.load(exchange) as mesh:
            return mesh["vertices"], mesh["faces"]


def projection_reports(vertices, faces, source_masks, spans, ground, dest):
    values = {}
    x, y, z = vertices.T
    for view, source in source_masks.items():
        mh, mw = source.shape
        px, py = axes((x, y + ground, z), view, spans)
        w, h = spans[view]
        uv = np.rint(np.column_stack([px / w * (mw - 1), py / h * (mh - 1)])).astype(int)
        raster = Image.new("1", (mw, mh))
        marker = ImageDraw.Draw(raster)
        for triangle in uv[faces]:
            marker.polygon([tuple(p) for p in triangle], fill=1)
        projected = np.asarray(raster)
        iou = np.count_nonzero(projected & source) / np.count_nonzero(projected | source)
        colors = np.full((mh, mw, 3), 244, dtype=np.uint8)
        colors[projected & source] = [107, 128, 125]
        colors[source & ~projected] = [216, 159, 88]
        colors[projected & ~source] = [88, 131, 177]
        Image.fromarray(colors).save(dest / (view + "-model-overlay.png"))
        values[view] = {"silhouette_iou": float(iou), "span_m": [float(w), float(h)]}
    return values


def passage(vertices, faces):
    # The paired front and back concepts have feet intruding into the lower
    # corridor (about x=-0.28 and +0.38 m at y=0.34 m). The span above the
    # ankle of the arch is visibly wider, so probe two separate cross-sections.
    sections = {
        "between_feet": ([-0.22, 0.30], [0.32, 0.50]),
        "above_feet": ([-0.43, 0.50], [0.62, 1.10]),
    }
    results = {}
    for name, (x_range, y_range) in sections.items():
        checks = []
        for direction in (-1, 1):
            for x in np.linspace(*x_range, 7):
                for y in np.linspace(*y_range, 4):
                    hits = ray_hits(vertices, faces, [x, y, direction * 2.5], [0, 0, -direction], 5.0)
                    checks.append(not hits)
        results[name] = {"clear_rays": sum(checks), "rays": len(checks),
                         "x_range_m": x_range, "y_range_m": y_range}
    flat = vertices[faces]
    flat = flat[np.max(np.abs(flat[:, :, 1]), axis=1) < 0.014]
    flat_area = abs(np.cross(flat[:, 1] - flat[:, 0], flat[:, 2] - flat[:, 0])[:, 1]) * 0.5
    x = flat[:, :, 0].mean(axis=1)
    floor = vertices[np.abs(vertices[:, 1]) <= 0.013, 0]
    return {"sections": results,
            "left_contact_area_m2": float(flat_area[x < -0.6].sum()),
            "right_contact_area_m2": float(flat_area[x > 0.6].sum()), "clear_rays": sum(r["clear_rays"] for r in results.values()),
            "rays": sum(r["rays"] for r in results.values()),
            "left_foot_contact_points": int((floor < -0.6).sum()),
            "right_foot_contact_points": int((floor > 0.6).sum())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_handoff", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--relief", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source_handoff.read_text())
    dirs = ("front", "rear", "left", "right", "top", "bottom")
    masks = {}
    for view in dirs:
        art = args.source_handoff.parent / source["views"][view]["path"]
        if digest(art) != source["views"][view]["source_png_sha256"]:
            raise ValueError(f"{view} concept art does not match its handoff")
        outline = art.with_name(view + "-outline.png")
        if digest(outline) != source["views"][view]["outline_sha256"]:
            raise ValueError(f"{view} silhouette does not match its handoff")
        with Image.open(outline) as image:
            masks[view] = np.asarray(image.convert("1"))
    width = source["reference_width_m"]
    spans = {view: dimensions(masks[view], width, None) for view in ("front", "rear", "top", "bottom")}
    y_anchor = np.mean([spans[k][1] for k in ("front", "rear")])
    spans.update({view: dimensions(masks[view], None, y_anchor) for view in ("left", "right")})

    args.output.mkdir(parents=True, exist_ok=True)
    policy_dir = Path(__file__).resolve().parents[2] / "aquascape"
    budget = json.loads((policy_dir / "geometry-budgets.json").read_text())["types"]["large_rock"]
    relief = json.loads(args.relief.read_text()) if args.relief else None
    target = relief["triangle_target"] if relief else budget["preferred"]
    if target > budget["hard_limit"]:
        raise ValueError("Target exceeds the large-rock budget")
    vertices, faces, _ = sculpt_hull(masks, spans, relief)
    vertices, faces = reduce_mesh(vertices, faces, args.blender, target)
    ground = vertices[:, 1].min()
    vertices[:, 1] -= ground
    if relief:
        # QEM may leave the two broad contact pads a few millimeters apart.
        # Reassert the shared ground plane only within the bottom 2.2 cm.
        vertices[vertices[:, 1] < 0.022, 1] = 0.0
    name = "reef_through_arch_relief_gray.glb" if relief else "reef_through_arch_six_material_gray.glb"
    path = args.output / name
    glb = Glb()
    material = glb.material(Image.new("RGBA", (4, 4), (157, 160, 162, 255)), "Neutral gray")
    texture_uv = np.clip(np.column_stack([vertices[:, 0] / width + 0.5, 1 - vertices[:, 1] / y_anchor]), 0, 1)
    glb.mesh(vertices, faces, texture_uv, material, path.stem)
    glb.save(path)
    np.savez_compressed(path.with_suffix(".npz"), vertices=vertices, faces=faces)
    overlaps = projection_reports(vertices, faces, masks, spans, ground, args.output)
    corridor = passage(vertices, faces)
    payload = inspect(path)
    ok = (payload["ok"] and not payload["nonmanifold_edges"] and glb.triangles <= budget["hard_limit"]
          and corridor["clear_rays"] == corridor["rays"]
          and corridor["left_contact_area_m2"] > 0.1 and corridor["right_contact_area_m2"] > 0.1)
    report = {
        "ok": bool(ok), "stage": "six_source_gray_shape", "source_handoff_sha256": digest(args.source_handoff),
        "user_acceptance": "pending", "gray_model": payload, "triangle_count": glb.triangles,
        "source_ground_y_m": float(ground),
        "relief_configuration": digest(args.relief) if relief else None,
        "dimensions_xyz_m": np.ptp(vertices, axis=0).tolist(), "projections": overlaps, "passage": corridor,
    }
    (args.output / "six-material-gray.validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ["ok", "triangle_count", "dimensions_xyz_m", "projections", "passage"]}))
    return int(not ok)


if __name__ == "__main__":
    raise SystemExit(main())
