"""Build low-poly reef rocks from checked six-view sources and named relief landmarks."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from skimage.measure import euler_number, marching_cubes

from bake_reef_arch_six_view_art import read_donors, texture_atlas
from build_decor_ten import ray_hits
from build_from_art import Glb
from build_reef_arch_from_material_views import (
    blend_opposites, digest, dimensions, projection_reports, reduce_mesh, round_intersection,
    sampled_distance, shape_patch,
)
from validate_art_models import inspect


def source_geometry(source, folder):
    donors = read_donors(folder, source["views"])
    masks = {}
    for view in donors:
        with Image.open(folder / (view + "-outline.png")) as image:
            masks[view] = np.asarray(image.convert("1"))
    width, height, _ = source["nominal_xyz_m"]
    if source["id"] == "reef_pinnacle":
        # Keep the spire's placement height; its authored foot is broad.
        spans = {view: dimensions(masks[view], None, height) for view in ("front", "rear", "left", "right")}
        width = np.mean([spans[view][0] for view in ("front", "rear")])
    else:
        spans = {view: dimensions(masks[view], width, None) for view in ("front", "rear")}
        height = np.mean([spans[view][1] for view in ("front", "rear")])
        spans.update({view: dimensions(masks[view], None, height) for view in ("left", "right")})
    spans.update({view: dimensions(masks[view], width, None) for view in ("top", "bottom")})
    return donors, masks, spans, width, height


def surface_anchor(base, coords, view, u, v, width, height, depth, ground):
    # u uses world X on the broad views and world Z on the end views.
    # v is height above the bed, except in plan where it is world Z.
    if view in {"front", "rear"}:
        point = [u * width, ground + v * height, 0]
        free, positive = 2, view == "front"
    elif view in {"left", "right"}:
        point = [0, ground + v * height, u * depth]
        free, positive = 0, view == "right"
    else:
        point = [u * width, 0, v * depth]
        free, positive = 1, True
    line = []
    for axis, (coordinate, value) in enumerate(zip(coords, point)):
        line.append(slice(None) if axis == free else int(np.argmin(abs(coordinate - value))))
    rock = np.flatnonzero(base[tuple(line)] > 0)
    if not len(rock):
        return None
    point[free] = coords[free][rock[-1] if positive else rock[0]]
    point[1] -= ground
    return np.asarray(point), free, (1 if positive else -1)


def leading_volume(field):
    labels, _ = ndi.label(field > 0)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    return labels == counts.argmax(), float(counts.max() / counts.sum())


def has_through_hole(field):
    body, _ = leading_volume(field)
    if euler_number(body, connectivity=3) != 1:
        return True
    # These natural solid modules need a single external shell, including rooms
    # whose mouth joins the outside. Enclosed bubbles are treated as defects.
    return bool(np.any(ndi.binary_fill_holes(body) != body))


def blind_cavity(field, xyz, width, height, depth, floor, room):
    x, y, z = xyz
    center = room["x_fraction"] * width
    back = room["rear_depth_fraction"] * depth
    clear_y = y - floor
    widen = np.clip((z - back) / depth, 0.0, 1.0)
    half = (0.78 + widen * 0.32) * room["half_width_fraction"] * width
    y0 = room["floor_fraction"] * height
    tall = room["roof_height_fraction"] * height - y0
    arch = (1.0 - ((x - center) / half) ** 2 - ((clear_y - y0) / tall) ** 2) * tall * 0.55
    void = np.minimum(arch, np.minimum(clear_y - y0, z - back))
    return round_intersection(field, -void, 0.065)


def build_volumes(masks, spans, width, height, config):
    plan_depth = np.mean([spans[view][1] for view in ("top", "bottom")])
    depth_extent = max(plan_depth, *(spans[view][0] for view in ("left", "right")))
    step = max(width, height) / 147
    pad = 0.33
    origin = np.array([-width * 0.5 - pad, -3 * step, -depth_extent * 0.5 - pad])
    coords = [np.arange(origin[0], width * 0.5 + pad, step),
              np.arange(origin[1], height + pad, step),
              np.arange(origin[2], depth_extent * 0.5 + pad, step)]
    xyz = np.ix_(*coords)
    # White pixels enclosed by a painted rock face or highlight are not geology.
    # The grotto opening and shallow pits are explicit 3D cuts below.
    distance = {v: sampled_distance(ndi.binary_fill_holes(mask), xyz, v, spans) for v, mask in masks.items()}
    broad = blend_opposites(distance["front"], distance["rear"])
    side = blend_opposites(distance["left"], distance["right"])
    plan = blend_opposites(distance["top"], distance["bottom"])
    field = round_intersection(round_intersection(broad, side, step * 4.4), plan, step * 3.8)
    field = ndi.gaussian_filter(field.astype(np.float32), sigma=1.1)
    base = field.copy()
    floor = height * config.get("floor_fraction", 0.045)
    landmarks = []
    ordered = sorted(config["features"], key=lambda item: item[1] != "ledge")
    geometry_floor = np.broadcast_to(xyz[1] - floor, field.shape)
    for item in ordered:
        label, kind, view, u, v, extent, offset, yaw, dip = item
        hit = surface_anchor(base, coords, view, u, v, width, height, plan_depth, floor)
        if hit is None:
            landmarks.append({"name": label, "applied": False})
            continue
        center, free, sign = hit
        anchor = center.copy()
        center[free] += offset * sign
        if kind == "ledge":
            shape_patch(field, coords, [label, center, extent, yaw, dip], floor, add=True)
        else:
            for depth_factor in (1.0, 0.72, 0.48):
                candidate = field.copy()
                shallow = list(extent)
                shallow[free] *= depth_factor
                shape_patch(candidate, coords, [label, center, shallow, yaw, dip], floor, add=False)
                if not has_through_hole(np.minimum(candidate, geometry_floor)):
                    field = candidate
                    break
            else:
                landmarks.append({"name": label, "applied": False, "reason": "cut would pierce parent rock"})
                continue
        landmarks.append({"name": label, "applied": True, "form": kind, "view": view,
                          "surface_anchor_xyz_m": anchor.tolist(), "center_xyz_m": center.tolist()})
    if room := config.get("blind_cavity"):
        field = blind_cavity(field, xyz, width, height, plan_depth, floor, room)
    field = ndi.gaussian_filter(field, sigma=0.5)
    field = np.minimum(field, np.broadcast_to(xyz[1] - floor, field.shape))
    body, retained = leading_volume(field)
    field[(field > 0) & ~body] = -step
    field[[0, -1], :, :] = -step
    field[:, [0, -1], :] = -step
    field[:, :, [0, -1]] = -step
    vertices, faces, _, _ = marching_cubes(field, 0, spacing=(step,) * 3, allow_degenerate=False)
    vertices += origin
    return vertices, faces, landmarks, retained


def topology(vertices, faces):
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    graph = coo_matrix((np.ones(len(e)), (e[:,0], e[:,1])), shape=(len(vertices), len(vertices))).tocsr()
    unique = np.unique(np.sort(e, axis=1), axis=0)
    return int(connected_components(graph, directed=False, return_labels=False)), len(vertices)-len(unique)+len(faces)


def prove_cavity(vertices, faces, room, width, height):
    center = room["x_fraction"] * width
    y0 = room["floor_fraction"] * height
    result = []
    for x in [center - .27, center, center + .27]:
        y = y0 + .45
        front = ray_hits(vertices, faces, [x,y,3.5], [0,0,-1], 7)
        rear = ray_hits(vertices, faces, [x,y,-3.5], [0,0,1], 7)
        floor = ray_hits(vertices, faces, [x,y,.10], [0,-1,0], y+.04)
        roof = ray_hits(vertices, faces, [x,y,.10], [0,1,0], height)
        thickness = front[-1] - front[0] if len(front)==2 else 0.0
        # First view ray passes through the mouth until it strikes the interior rear wall.
        # Its two hits are both on the intact rear half, which has measurable thickness.
        result.append({"x":x,"y":y,"front_hits":front,"rear_hits":rear,"floor_hits":floor,"roof_hits":roof,
                       "rear_wall_thickness_m":thickness,
                       "mouth_open_and_back_closed": len(front)==len(rear)==2 and front[0]>3.63
                       and thickness>0.21 and bool(floor) and bool(roof)})
    return result


def relief_probes(vertices, faces, landmarks):
    directions = {
        "front":(2,1), "rear":(2,-1), "left":(0,-1), "right":(0,1), "top":(1,1),
    }
    results=[]
    for site in landmarks:
        if not site["applied"]:
            continue
        axis, side = directions[site["view"]]
        anchor=np.array(site["surface_anchor_xyz_m"])
        origin=anchor.copy()
        origin[axis]+=3.0*side
        beam=np.zeros(3)
        beam[axis]=-side
        hits=ray_hits(vertices,faces,origin,beam,6.0)
        if hits:
            results.append({"feature":site["name"],"form":site["form"],"signed_offset_m":3.0-hits[0]})
    return results


def run_asset(folder, output, blender, budget, config):
    source = json.loads((folder/"material-source.handoff.json").read_text())
    profile = budget[source["geometry_budget"]]
    if config["target_triangles"] > profile["hard_limit"]:
        raise ValueError("Configured target exceeds complete-instance budget")
    donors, masks, spans, width, height = source_geometry(source, folder)
    high, faces, landmarks, retained = build_volumes(masks, spans, width, height, config)
    vertices, faces = reduce_mesh(high, faces, blender, config["target_triangles"])
    ground = float(vertices[:,1].min())
    vertices[:,1]-=ground
    vertices[vertices[:,1]<min(.022,height*.029),1]=0
    gray = Glb()
    gmat = gray.material(Image.new("RGBA",(4,4),(153,159,160,255)),"Neutral")
    uv = np.zeros((len(vertices),2),dtype=np.float32)
    gray.mesh(vertices,faces,uv,gmat,source["id"])
    if gray.triangles != len(faces):
        raise ValueError("A degenerate triangle was dropped after ground snap")
    output.mkdir(parents=True,exist_ok=True)
    gray_path = output/(source["id"]+"-gray.glb")
    gray.save(gray_path)
    position = vertices[faces].reshape(-1, 3)
    triplets = vertices[faces]
    cross = np.cross(triplets[:,1]-triplets[:,0],triplets[:,2]-triplets[:,0])
    normal = np.repeat(cross / np.linalg.norm(cross, axis=1, keepdims=True),3,axis=0)
    atlas, atlas_uv, shares = texture_atlas(faces, position, normal, faces.ravel(), donors, spans, ground, True)
    art = Glb()
    mat=art.material(atlas,source["id"]+" · six-axis limestone")
    art.mesh(position,np.arange(len(position)).reshape(-1,3),atlas_uv,mat,source["id"])
    material_path=output/(source["id"]+".glb")
    art.save(material_path)
    np.savez_compressed(material_path.with_suffix(".npz"),vertices=vertices,faces=faces)
    review = inspect(material_path)
    outlines = projection_reports(vertices,faces,masks,spans,ground,output)
    cavity = prove_cavity(vertices,faces,config["blind_cavity"],width,height) if "blind_cavity" in config else []
    probe = relief_probes(vertices,faces,landmarks)
    samples = [x for x in probe if abs(x["signed_offset_m"])>.04]
    connected, euler = topology(vertices,faces)
    ok = bool(review["ok"] and review["nonmanifold_edges"]==0 and connected==1 and euler==2 and
              retained>.975 and art.triangles<=profile["hard_limit"] and
              all(sample["mouth_open_and_back_closed"] for sample in cavity) and
              any(row["signed_offset_m"]<-.04 for row in samples) and any(row["signed_offset_m"]>.04 for row in samples))
    report = {"id":source["id"],"ok":ok,"triangles":art.triangles,"budget":profile,
              "gray":str(gray_path),"gray_sha256":digest(gray_path),"glb":str(material_path),"glb_sha256":digest(material_path),
              "geometry_components":connected,"surface_euler_characteristic":euler,"open_edges":review["open_edges"],"nonmanifold_edges":review["nonmanifold_edges"],
              "vertex_bounds_xyz_m":np.ptp(vertices,axis=0).tolist(),"nominal_xyz_m":source["nominal_xyz_m"],
              "source":str(folder/"material-source.handoff.json"),"source_sha256":digest(folder/"material-source.handoff.json"),
              "finished_alpha":"opaque","material_passes":1,"atlas_size":list(atlas.size),"sampler":"nearest",
              "source_texel_shares":shares,"component_volume_fraction":retained,"outlines":outlines,
              "cavity":cavity,"landmarks":landmarks,"relief_probes":probe}
    (output/"geometry-and-material.validation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(source["id"],ok,art.triangles,len(samples),"relief probes", flush=True)
    return ok


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root",type=Path)
    parser.add_argument("output_root",type=Path)
    parser.add_argument("--blender",type=Path,required=True)
    parser.add_argument("--id",action="append")
    args=parser.parse_args()
    config=json.loads((args.source_root/"rock-shapes.json").read_text())
    budget=json.loads((Path(__file__).resolve().parents[2]/"aquascape/geometry-budgets.json").read_text())["types"]
    keys=args.id if args.id else config
    results=[run_asset(args.source_root/id,args.output_root/id,args.blender,budget,config[id]) for id in keys]
    return int(not all(results))


if __name__=="__main__":
    raise SystemExit(main())
