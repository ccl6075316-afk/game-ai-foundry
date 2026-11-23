"""Create the editable arch gray model after reviewing four orthographic drawings."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw
from shapely import Point, Polygon

from build_decor_ten import ray_hits
from build_from_art import Glb
from validate_art_models import inspect


VIEWS = ("left", "right", "top", "bottom")


def interior_cap_points(ring, advance):
    xy = ring[:, :2]
    polygon = Polygon(xy)
    depth = ring[:, 2]
    samples = []
    for i, y in enumerate(np.arange(0.17, xy[:, 1].max(), 0.32)):
        for x in np.arange(xy[:, 0].min() + 0.15 + (i % 2) * 0.155, xy[:, 0].max(), 0.32):
            point = np.array([x + 0.019 * np.cos(x * 13 + y), y + 0.021 * np.sin(y * 9 - x)])
            cursor = Point(point)
            if not polygon.contains(cursor) or polygon.boundary.distance(cursor) < 0.10:
                continue
            distances = np.linalg.norm(xy - point, axis=1)
            nearest = np.argsort(distances)[:5]
            weights = 1 / distances[nearest] ** 2
            z = np.average(depth[nearest], weights=weights)
            relief = 0.015 + 0.038 * np.sin(y * 7.3 + x * 1.65)
            samples.append([*point, z + relief * advance])
    return np.array(samples, dtype=float)


def triangulate_caps(rings, blender):
    with tempfile.TemporaryDirectory(prefix="reef-arch-caps-") as temp:
        path = Path(temp) / "cap-points.npz"
        interior = [interior_cap_points(ring, direction)
                    for ring, direction in ((rings[0], -1), (rings[-1], 1))]
        np.savez(path, rear=np.vstack([rings[0], interior[0]]),
                 front=np.vstack([rings[-1], interior[1]]), boundary_count=len(rings[0]))
        command = [str(blender), "-b", "--python-exit-code", "1", "--python",
                   str(Path(__file__).with_name("triangulate_reef_arch_caps.py")), "--", str(path)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        output = np.load(path)
        return interior, [output["rear"], output["front"]]


def loft(profile, blender):
    xy = profile[:, :2]
    signed_area = np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - xy[:, 1] * np.roll(xy[:, 0], -1))
    if signed_area < 0:
        profile = profile[::-1]
        xy = profile[:, :2]
    angles = np.roll(xy, -1, axis=0) - xy
    angles /= np.linalg.norm(angles, axis=1)[:, None]
    outward = np.column_stack([angles[:, 1], -angles[:, 0]])
    outward += np.roll(outward, 1, axis=0)
    outward /= np.maximum(np.linalg.norm(outward, axis=1, keepdims=True), 1e-12)
    count = len(profile)
    ground = xy[:, 1] == 0.0
    rings = []
    # Five depth bands keep the footing and opening open while breaking up the
    # silhouette corners. Depth limits come from the reviewed orthographic drawings.
    bands = [(0.0, 0.062), (0.17, 0.018), (0.48, 0.0), (0.82, 0.017), (1.0, 0.058)]
    for i, (depth, crease) in enumerate(bands):
        inset = crease * (1.05 + 0.30 * np.sin(xy[:, 0] * 3 + xy[:, 1] * 5 + i))
        ring_xy = xy - outward * inset[:, None]
        ring_xy[ground, 1] = 0.0
        ring_z = (1 - depth) * profile[:, 2] + depth * profile[:, 3]
        rings.append(np.column_stack([ring_xy, ring_z]))
    vertices = np.vstack(rings).tolist()
    faces = []
    for band in range(len(rings) - 1):
        for i in range(count):
            j = (i + 1) % count
            a = band * count + i
            b = band * count + j
            c = (band + 1) * count + j
            d = (band + 1) * count + i
            faces.extend([[a, b, c], [a, c, d]])
    interiors, caps = triangulate_caps(rings, blender)
    for index, (points, cap) in enumerate(zip(interiors, caps)):
        ring_index = 0 if index == 0 else len(rings) - 1
        added = len(vertices)
        vertices.extend(points.tolist())
        labels = np.concatenate([np.arange(count) + ring_index * count, np.arange(len(points)) + added])
        for face in cap:
            ids = labels[face]
            a, b, c = np.asarray(vertices)[ids]
            direction = np.cross(b - a, c - a)[2]
            if (direction > 0) == (index == 0):
                ids = ids[::-1]
            faces.append(ids.tolist())
    vertices = np.asarray(vertices, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.int32)
    triangles = vertices[faces]
    volume = np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum()
    if volume < 0:
        faces = faces[:, [0, 2, 1]]
    return vertices, faces


def draft_overlays(vertices, faces, views, output):
    x, y, z = vertices.T
    angles = {"left": (z, y, 645), "right": (-z, y, 645),
              "top": (x, -z, 419), "bottom": (x, z, 419)}
    facts = {}
    for key, (u, v, baseline) in angles.items():
        draft = Image.open(views / f"{key}-outline.png").convert("1")
        raster = Image.new("1", draft.size)
        pen = ImageDraw.Draw(raster)
        pixels = np.rint(np.column_stack([550 + 164 * u, baseline - 164 * v])).astype(int)
        for f in faces:
            pen.polygon([tuple(point) for point in pixels[f]], fill=1)
        sampled = np.asarray(raster)
        reference = np.asarray(draft)
        iou = float(np.count_nonzero(sampled & reference) / np.count_nonzero(sampled | reference))
        facts[key] = {"silhouette_iou": iou, "passed": iou >= 0.93}
        rgba = np.full((*reference.shape, 3), 243, dtype=np.uint8)
        rgba[sampled & reference] = [116, 142, 143]
        rgba[reference & ~sampled] = [220, 147, 68]
        rgba[sampled & ~reference] = [53, 118, 178]
        Image.fromarray(rgba).save(output / f"{key}-overlay.png")
    return facts


def aperture_checks(spec, vertices, faces):
    aperture = spec["clearance_check"]
    sampled = []
    for direction in (1, -1):
        for y in aperture["y_m"]:
            for x in aperture["x_m"]:
                origin = [x, y, direction * aperture["origin_z_m"]]
                hits = ray_hits(vertices, faces, origin, [0, 0, -direction], aperture["origin_z_m"] * 2)
                sampled.append({"x": x, "y": y, "from_front": bool(direction == 1), "clear": not hits})
    # Confirm solid rock just outside the proposed rectangular central clearance.
    outer_probes = {}
    for name, x, y in [("left_foot", -1.18, 0.36), ("right_foot", 1.47, 0.36), ("roof", 0.12, 1.73)]:
        outer_probes[name] = ray_hits(vertices, faces, [x, y, 2], [0, 0, -1], 4)
    return {"samples": sampled, "opposite_sides_clear": all(p["clear"] for p in sampled),
            "closed_rock_outside_opening": all(len(hits) >= 2 for hits in outer_probes.values()),
            "outer_hits": outer_probes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--blender", required=True, type=Path)
    args = parser.parse_args()
    views = args.design.parent
    args.output.mkdir(parents=True, exist_ok=True)
    spec = json.loads(args.design.read_text())
    reference_views = {k: views / (f"arch-{k}.png") for k in VIEWS}
    for file in reference_views.values():
        with Image.open(file) as im:
            im.verify()

    vertices, faces = loft(np.array(spec["profile"], dtype=float), args.blender)
    path = args.output / "reef_through_arch_gray.glb"
    glb = Glb()
    tone = Image.new("RGBA", (4, 4), (150, 157, 158, 255))
    material = glb.material(tone, "Neutral shape review")
    uv = np.column_stack([(vertices[:, 0] + 2.25) / 4.5, 1 - vertices[:, 1] / 2.8])
    glb.mesh(vertices, faces, uv, material, path.stem)
    glb.save(path)
    np.savez_compressed(path.with_suffix(".npz"), vertices=vertices, faces=faces)

    overlays = draft_overlays(vertices, faces, views, args.output)
    aperture = aperture_checks(spec, vertices, faces)
    payload = inspect(path)
    ground = vertices[np.abs(vertices[:, 1]) <= 1e-6]
    support = {"left_contact_vertices": int(np.count_nonzero(ground[:, 0] < -0.67)),
               "right_contact_vertices": int(np.count_nonzero(ground[:, 0] > 0.76)),
               "vertices_under_ground": int(np.count_nonzero(vertices[:, 1] < -1e-6))}
    policy = Path(__file__).resolve().parents[2] / "aquascape/geometry-budgets.json"
    faces_bound = json.loads(policy.read_text())["types"]["large_rock"]
    ok = (payload["ok"] and not payload["nonmanifold_edges"] and glb.triangles <= faces_bound["hard_limit"]
          and all(row["passed"] for row in overlays.values()) and aperture["closed_rock_outside_opening"]
          and aperture["opposite_sides_clear"] and support["left_contact_vertices"]
          and support["right_contact_vertices"] and not support["vertices_under_ground"])
    report = {
        "ok": bool(ok),
        "stage": "gray_geometry_review",
        "user_acceptance": "pending",
        "source_views": {view: {"path": str(f), "sha256": sha256(f.read_bytes()).hexdigest()}
                         for view, f in reference_views.items()},
        "gray_model": payload,
        "triangles": glb.triangles,
        "budget": faces_bound,
        "bounds_xyz_m": np.ptp(vertices, axis=0).tolist(),
        "overlays": overlays,
        "aperture": aperture,
        "ground": support,
    }
    (args.output / "geometry.validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("ok","triangles","bounds_xyz_m","overlays","ground")}))
    return int(not ok)


if __name__ == "__main__":
    raise SystemExit(main())
