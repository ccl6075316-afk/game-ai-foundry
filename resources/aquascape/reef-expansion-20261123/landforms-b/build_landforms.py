"""Build budgeted closed geology from audited six-direction artwork and physical landmarks."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.measure import marching_cubes

directory = Path(__file__).resolve().parent
root = directory.parents[3]
sys.path.insert(0, str(root / "resources/scripts/aquascape"))
from bake_reef_arch_six_view_art import read_donors, texture_atlas
from build_decor_ten import ray_hits
from build_from_art import Glb
from build_reef_arch_from_material_views import (
    blend_opposites, digest, projection_reports, reduce_mesh, round_intersection,
    sampled_distance, shape_patch,
)
from build_reef_relief_set import has_through_hole, leading_volume, relief_probes, surface_anchor, topology
from validate_art_models import inspect


def rounded_patch(field, coords, point, radii, yaw, dip, ground, additive):
    center = point + np.array([0, ground, 0])
    reach = max(radii) * 1.60
    windows = tuple(slice(np.searchsorted(axis, coordinate - reach),
                          np.searchsorted(axis, coordinate + reach))
                    for axis, coordinate in zip(coords, center))
    local = field[windows]
    x, y, z = np.ix_(*(axis[window] - location
                      for axis, window, location in zip(coords, windows, center)))
    angle, tilt = np.deg2rad([yaw, dip])
    u = x * np.cos(angle) - z * np.sin(angle)
    w = x * np.sin(angle) + z * np.cos(angle)
    axes = [(u * np.cos(tilt) + y * np.sin(tilt)) / radii[0],
            (y * np.cos(tilt) - u * np.sin(tilt)) / radii[1], w / radii[2]]
    uneven = 0.055 * np.cos(4.8 * axes[0] + 1.3 * axes[1]) * np.cos(4.0 * axes[2])
    clast = (1.0 + uneven - np.sqrt(sum(component ** 2 for component in axes))) * min(radii)
    if additive:
        local[:] = -round_intersection(-local, -clast, .032)
    else:
        local[:] = round_intersection(local, -clast, .026)


def geometry(masks, spans, size, config):
    width, height, depth = size
    step = max(size) / 145
    pad = 0.19
    origin = np.array([-width / 2 - pad, -3 * step, -depth / 2 - pad])
    end = [width / 2 + pad, height + pad, depth / 2 + pad]
    coords = [np.arange(lo, hi, step) for lo, hi in zip(origin, end)]
    xyz = np.ix_(*coords)
    x, y, z = xyz
    distance = {
        view: sampled_distance(ndi.binary_fill_holes(mask), xyz, view, spans)
        for view, mask in masks.items()
    }
    broad = blend_opposites(distance["front"], distance["rear"])
    side = blend_opposites(distance["left"], distance["right"])
    plan = blend_opposites(distance["top"], distance["bottom"])
    field = round_intersection(round_intersection(broad, side, step * 3.2), plan, step * 2.8)
    field = ndi.gaussian_filter(field.astype(np.float32), sigma=0.95)
    ground = config.get("ground_fraction", 0.043) * height
    for label, location, radii, yaw, dip in config.get("masses", []):
        point = np.asarray(location) * size
        shape_patch(field, coords, [label, point, radii, yaw, dip], ground, add=True)
    base = field.copy()
    landmarks = []
    for label, kind, view, u, v, radii, offset, yaw, dip in config["relief"]:
        hit = surface_anchor(base, coords, view, u, v, width, height, depth, ground)
        if hit is None:
            landmarks.append({"name": label, "applied": False, "view": view})
            continue
        center, axis, sign = hit
        anchor = center.copy()
        center[axis] += offset * sign
        if label in config.get("round_features", []):
            if kind == "ledge":
                rounded_patch(field, coords, center, radii, yaw, dip, ground, True)
            else:
                for factor in (1.0, 0.65, 0.37):
                    candidate = field.copy()
                    shallow = list(radii)
                    shallow[axis] *= factor
                    rounded_patch(candidate, coords, center, shallow, yaw, dip, ground, False)
                    if not has_through_hole(np.minimum(candidate, y - ground)):
                        field = candidate
                        break
                else:
                    landmarks.append({"name": label, "applied": False, "view": view,
                                      "reason": "no material to support this cut through all depths"})
                    continue
        else:
            shape_patch(field, coords, [label, center, radii, yaw, dip], ground, add=(kind == "ledge"))
        landmarks.append({"name": label, "applied": True, "form": kind, "view": view,
                          "surface_anchor_xyz_m": anchor.tolist(), "center_xyz_m": center.tolist()})
    shape = config.get("section", {})
    kind = shape.get("kind")
    nx, ny, nz = x / width, (y - ground) / height, z / depth
    if kind == "rift":
        # A sinuous open-floor corridor from front to rear with no stone roof.
        center = 0.095 * nz + 0.035 * np.sin(6 * nz)
        half = shape["half_width"] * (1 + 0.14 * np.sin(5 * nz + 1.2))
        room_y = shape["floor_y"] + 0.024 * np.cos(8 * nz + .7)
        void = np.minimum((half - abs(nx - center)) * width, (ny - room_y) * height)
        field = round_intersection(field, -void, 0.062)
    elif kind == "canopy":
        # The cantilever's free area ends at its real supporting rear heel.
        tympanum = ((nx - shape["center_x"]) / shape["half_width"]) ** 2
        stone_lip = .035 * np.sin(29 * nx - 10 * nz) * np.cos(16 * nz)
        rough_heel = .040 * np.cos(23 * ny + 9 * nx) + .031 * np.sin(28 * nx - 7 * ny)
        clear_height = shape["clear_height"] - 0.21 * tympanum + 0.09 * nz + stone_lip
        rear_limit = shape["rear_limit"] + 0.19 * tympanum + rough_heel
        void = round_intersection((clear_height - ny) * height, (nz - rear_limit) * depth, 0.10)
        field = round_intersection(field, -void, 0.070)
    elif kind == "pedestal":
        # Recess the end profiles on all sides between the cap and root heel.
        center_x = np.interp(ny.reshape(-1), [0, .24, .56, .8, 1], [.0, -.07, -.105, -.055, .0]).reshape(ny.shape)
        waist_x = np.interp(ny.reshape(-1), [0, .24, .48, .64, .78, 1], [.55, .40, .27, .29, .43, .59]).reshape(ny.shape)
        waist_z = np.interp(ny.reshape(-1), [0, .24, .48, .64, .78, 1], [.55, .43, .31, .30, .49, .62]).reshape(ny.shape)
        body_rule = 1.0 - (((nx - center_x) / waist_x) ** 4 + ((nz + .035) / waist_z) ** 4) ** .25
        field = round_intersection(field, 0.35 * body_rule, 0.032)
    elif kind == "encircling":
        # Ground-facing wall has a wide heel, dark pockets and projecting
        # shelves. Height-dependent section widths keep the inner wall rocky.
        cx = -.055 - .04 * np.sin(4.2 * nz)
        side_pits = .032 * np.sin(24 * nz - 7 * ny) * np.sin(19 * ny + 2 * np.sign(nx))
        half = .23 + .062 * np.sin(6 * nz + 1) + .048 * ny + side_pits
        rear_shelves = .031 * np.sin(24 * ny - 7 * nx) + .025 * np.cos(19 * nx + 11 * ny)
        rear_extent = -.277 + .49 * (nx - cx) ** 2 - .09 * ny + rear_shelves
        inner = round_intersection((half - np.abs(nx - cx)) * width, (nz - rear_extent) * depth, 0.19)
        field = round_intersection(field, -inner, 0.055)
    elif kind == "eye":
        # Real tapered off-axis tunnel under an intact roof and over the foot.
        cx = shape["center_x"] + .04 * nz
        cy = shape["center_y"] - .07 * nz
        rx = shape["half_width"] * (1 + .15 * np.sin(6.2 * nz + .64))
        ry = shape["half_height"] * (1 + .10 * np.cos(6.7 * nz))
        angle = np.arctan2((ny - cy) / ry, (nx - cx) / rx)
        ring = 1 + .07 * np.sin(3 * angle + 0.70) + .045 * np.cos(5 * angle - .31)
        void = ring - np.sqrt(((nx - cx) / rx) ** 2 + ((ny - cy) / ry) ** 2)
        field = round_intersection(field, -void * min(width * shape["half_width"], height * shape["half_height"]), 0.025)
    field = ndi.gaussian_filter(field, sigma=0.52)
    field = np.minimum(field, y - ground)
    body, retained = leading_volume(field)
    field[(field > 0) & ~body] = -step
    field[[0, -1], :, :] = field[:, [0, -1], :] = field[:, :, [0, -1]] = -step
    v, f, _, _ = marching_cubes(field, 0, spacing=(step,) * 3, allow_degenerate=False)
    v += origin
    return v, f, landmarks, retained, ground


def section_evidence(v, f, size, spec):
    width, height, depth = size
    kind = spec.get("kind")
    if kind == "rift":
        free = {
            str(z): ray_hits(v, f, [x * width, .45 * height, z * depth], [0, 1, 0], height)
            for z, x in [(-.62, -.058), (-.35, -.05), (0, 0), (.35, .06), (.62, .06)]
        }
        wall = [ray_hits(v, f, [X * width, .55 * height, 0], [sign, 0, 0], width)
                for X, sign in [(-0.02, -1), (.02, 1)]]
        floor = ray_hits(v, f, [0, .45 * height, 0], [0, -1, 0], height)
        return {"kind": kind, "no_roof_test": free, "side_walls": wall, "floor": floor,
                "passed": all(not x for x in free.values()) and all(wall) and bool(floor)}
    if kind == "canopy":
        location = [spec["center_x"] * width, .30 * height, .24 * depth]
        roof = ray_hits(v, f, location, [0, 1, 0], height)
        free = ray_hits(v, f, location, [0, 0, 1], depth)
        support = ray_hits(v, f, location, [0, 0, -1], depth)
        return {"kind": kind, "roof": roof, "forward_exit": free, "rear_heel": support,
                "passed": bool(roof) and not free and bool(support)}
    if kind == "pedestal":
        def span(y):
            hits = ray_hits(v, f, [-width, y * height, 0], [1, 0, 0], 2 * width)
            return (max(hits) - min(hits)) if len(hits) >= 2 else 0.0
        waist, cap, heel = span(.50), max(span(.80), span(.86)), span(.15)
        return {"kind": kind, "waist_m": waist, "cap_m": cap, "foot_m": heel,
                "passed": waist > .16 * width and cap > 1.20 * waist and heel > 1.12 * waist}
    if kind == "encircling":
        location = [0, .22 * height, .03 * depth]
        behind = ray_hits(v, f, location, [0, 0, -1], depth)
        forward = ray_hits(v, f, location, [0, 0, 1], depth)
        above = ray_hits(v, f, location, [0, 1, 0], height)
        sides = [ray_hits(v, f, location, [sign, 0, 0], width) for sign in (-1, 1)]
        return {"kind": kind, "rear": behind, "open_front": forward, "open_top": above,
                "arms": sides, "passed": bool(behind) and all(sides) and not forward and not above}
    if kind == "eye":
        x, y = spec["center_x"] * width, spec["center_y"] * height
        bore = [ray_hits(v, f, [x + u * width, y + w * height, depth], [0, 0, -1], 2 * depth)
                for u, w in [(0, 0), (-.024, 0), (.024, 0), (0, -.028), (0, .028)]]
        collar = [ray_hits(v, f, [x + u * width, y + w * height, depth], [0, 0, -1], 2 * depth)
                  for u, w in [(-.15, 0), (.14, 0), (0, -.24), (0, .20)]]
        return {"kind": kind, "open_full_depth": bore, "solid_collar": collar,
                "passed": all(not h for h in bore) and all(collar)}
    return {"kind": "solid", "passed": True}


def build(key, output, blender, config, budget):
    folder = directory / key
    source_path = folder / "material-source.handoff.json"
    source = json.loads(source_path.read_text())
    profile = budget[source["geometry_budget"]]
    goal = config["target_triangles"]
    if goal > profile["hard_limit"]:
        raise ValueError(key + ": configured triangles above whole instance budget")
    donors = read_donors(folder, source["views"])
    masks = {}
    for view in donors:
        with Image.open(folder / (view + "-outline.png")) as image:
            masks[view] = np.asarray(image.convert("1"))
    size = np.asarray(source["nominal_xyz_m"])
    width, height, depth = size
    spans = {"front": (width, height), "rear": (width, height),
             "left": (depth, height), "right": (depth, height),
             "top": (width, depth), "bottom": (width, depth)}
    v, f, landmarks, retained, ground = geometry(masks, spans, size, config)
    v, f = reduce_mesh(v, f, blender, goal)
    v[:, 1] -= ground
    v[v[:, 1] < min(.009, height * .012), 1] = 0
    output.mkdir(parents=True, exist_ok=True)
    gray = Glb()
    mat = gray.material(Image.new("RGBA", (4, 4), (153, 159, 160, 255)), "Neutral")
    gray.mesh(v, f, np.zeros((len(v), 2), dtype=np.float32), mat, key)
    gray_path = output / (key + "-gray.glb")
    gray.save(gray_path)
    if gray.triangles != len(f):
        raise ValueError(key + ": collapsed mesh faces at ground")
    pts = v[f]
    cross = np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0])
    normal = np.repeat(cross / np.linalg.norm(cross, axis=1, keepdims=True), 3, axis=0)
    atlas, uv, coverage = texture_atlas(f, pts.reshape(-1, 3), normal, f.ravel(), donors, spans, ground, True)
    # Nearest only; retain the original projected pixel values while shrinking
    # the mostly empty texture page at a normal rock's gameplay scale.
    texel_width = 1536 if source["geometry_budget"] == "large_rock" else 1024
    atlas = atlas.resize((texel_width, texel_width), Image.Resampling.NEAREST)
    art = Glb()
    mat = art.material(atlas, key + " · six-direction rock")
    art.mesh(pts.reshape(-1, 3), np.arange(pts.size // 3).reshape(-1, 3), uv, mat, key)
    result = output / (key + ".glb")
    art.save(result)
    np.savez_compressed(result.with_suffix(".npz"), vertices=v, faces=f)
    geometry_stats = inspect(result)
    outline_check = projection_reports(v, f, masks, spans, ground, output)
    form_check = section_evidence(v, f, size, config.get("section", {}))
    connected, euler = topology(v, f)
    expected_euler = 0 if form_check["kind"] == "eye" else 2
    probe = relief_probes(v, f, landmarks)
    offsets = [x["signed_offset_m"] for x in probe]
    ok = bool(geometry_stats["ok"] and geometry_stats["nonmanifold_edges"] == 0
              and connected == 1 and euler == expected_euler and retained > .97
              and art.triangles <= profile["hard_limit"] and form_check["passed"]
              and min(offsets, default=0) < -.025 and max(offsets, default=0) > .025
              and all(coverage[view] > .008 for view in spans))
    evidence = {
        "id": key, "ok": ok, "geometry": geometry_stats, "triangles": art.triangles,
        "budget": profile, "source_handoff": str(source_path), "source_sha256": digest(source_path),
        "nominal_xyz_m": size.tolist(), "bounds_xyz_m": np.ptp(v, axis=0).tolist(),
        "floor_y_m": float(v[:, 1].min()), "surface_euler": euler,
        "geometry_components": connected, "volume_fraction_retained": retained,
        "material_passes": 1, "texture_filter": "nearest", "atlas_size": list(atlas.size),
        "atlas_uncompressed_rgba_bytes": texel_width ** 2 * 4, "source_texel_shares": coverage,
        "gray": str(gray_path), "gray_sha256": digest(gray_path), "glb": str(result),
        "glb_sha256": digest(result), "geometry_section": form_check, "art_outlines": outline_check,
        "landmarks": landmarks, "relief_probes": probe,
    }
    (output / "geometry-and-material.validation.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(key, ok, art.triangles, form_check["kind"], euler, round(min(offsets, default=0), 3),
          round(max(offsets, default=0), 3), flush=True)
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("ids", nargs="+")
    args = parser.parse_args()
    shapes = json.loads((directory / "sculpt.json").read_text())
    budgets = json.loads((root / "resources/aquascape/geometry-budgets.json").read_text())["types"]
    results = [build(key, args.output / key, args.blender, shapes[key], budgets) for key in args.ids]
    raise SystemExit(not all(results))
