"""
Universal Single-Material PBR Fish Upgrade Pipeline (Blender 5.x).
Produces 1-Mesh, 1-Material (Draw Call = 1), alphaMode=MASK (cutoff=0.5),
super-sampled pixel-locked Normal + ORM GLB assets ready for large-scale
Zhuhai-Chimelong-style multi-species aquariums.

Usage:
  # Tier 1: 100% automatic fast PBR conversion (works on ANY accepted fish.blend, zero species config!)
  Blender -b <fish.blend> --python upgrade_fish_pbr.py -- \
    --species black_seabream --mode fast_pbr --tier small \
    --out-glb /path/to/out.glb [--out-blend /path/to/out.blend]

  # Tier 2: Parameterized 3D eyeball + head/operculum sculpting (driven by species JSON config)
  Blender -b <fish.blend> --python upgrade_fish_pbr.py -- \
    --species red_seabream --mode sculpt_pbr --config configs/red_seabream.json --tier large \
    --out-glb /path/to/out.glb [--out-blend /path/to/out.blend]
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


# =========================== Math & Image Utilities ===========================

def smoothstep(edge0, edge1, x):
    """Exact Hermite smoothstep supporting both ascending (edge0 < edge1) and descending (edge0 > edge1) ramps."""
    diff = edge1 - edge0
    if isinstance(diff, (int, float)) and abs(diff) < 1e-12:
        return np.zeros_like(x, dtype=np.float32) if isinstance(x, np.ndarray) else 0.0
    t = np.clip((x - edge0) / diff, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def box_blur_2d(arr, radius):
    if radius <= 0:
        return arr.copy()
    k = 2 * radius + 1
    p = np.pad(arr, ((radius, radius), (0, 0)) + ((0, 0),) * (arr.ndim - 2), mode="edge")
    cs = np.cumsum(p, axis=0, dtype=np.float64)
    cs = np.concatenate([np.zeros((1,) + p.shape[1:], dtype=np.float64), cs], axis=0)
    tmp = (cs[k:] - cs[:-k]) / k
    p2 = np.pad(tmp, ((0, 0), (radius, radius)) + ((0, 0),) * (arr.ndim - 2), mode="edge")
    cs2 = np.cumsum(p2, axis=1, dtype=np.float64)
    cs2 = np.concatenate([np.zeros((p2.shape[0], 1) + p2.shape[2:], dtype=np.float64), cs2], axis=1)
    return ((cs2[:, k:] - cs2[:, :-k]) / k).astype(np.float32)


def gaussian_approx_2d(arr, radius):
    out = box_blur_2d(arr, radius)
    out = box_blur_2d(out, radius)
    return box_blur_2d(out, max(1, radius // 2))


def downsample_2x(arr, is_normal=False):
    """Super-sampled 2x2 box-filter downsample with tangent-space renormalization for normal maps."""
    h, w, c = arr.shape
    h2 = (h // 2) * 2
    w2 = (w // 2) * 2
    out = arr[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2, c).mean(axis=(1, 3)).astype(np.float32)
    if is_normal:
        n = out[:, :, :3] * 2.0 - 1.0
        inv = 1.0 / np.sqrt(np.sum(n * n, axis=2, keepdims=True) + 1e-12)
        out[:, :, :3] = np.clip(n * inv * 0.5 + 0.5, 0.0, 1.0)
        out[:, :, 3] = 1.0
    return out


def resample_bilinear(src_hw4, dst_h, dst_w):
    sh, sw, _ = src_hw4.shape
    if sh == dst_h and sw == dst_w:
        return src_hw4.copy()
    ys = (np.arange(dst_h, dtype=np.float32) + 0.5) * (sh / float(dst_h)) - 0.5
    xs = (np.arange(dst_w, dtype=np.float32) + 0.5) * (sw / float(dst_w)) - 0.5
    ys = np.clip(ys, 0.0, sh - 1.001)
    xs = np.clip(xs, 0.0, sw - 1.001)
    y0 = np.floor(ys).astype(np.int32)
    x0 = np.floor(xs).astype(np.int32)
    ty = (ys - y0)[:, None, None]
    tx = (xs - x0)[None, :, None]
    c00 = src_hw4[y0[:, None], x0[None, :]]
    c10 = src_hw4[y0[:, None], x0[None, :] + 1]
    c01 = src_hw4[y0[:, None] + 1, x0[None, :]]
    c11 = src_hw4[y0[:, None] + 1, x0[None, :] + 1]
    return ((c00 * (1.0 - tx) + c10 * tx) * (1.0 - ty) + (c01 * (1.0 - tx) + c11 * tx) * ty).astype(np.float32)


def dilate_alpha_rgb(rgba_hw4, alpha_thresh=0.45, passes=8):
    """Dilate opaque RGB outward into transparent pixels so bilinear/mipmap filtering never bleeds black/white."""
    out = rgba_hw4.copy()
    rgb_dil = out[:, :, :3].copy()
    mask_op = (out[:, :, 3] > alpha_thresh).astype(np.float32)
    for _ in range(passes):
        num = box_blur_2d(rgb_dil * mask_op[:, :, None], 1)
        den = box_blur_2d(mask_op, 1)
        fill = num / np.maximum(den[:, :, None], 1e-5)
        upd = (mask_op < 0.5) & (den > 0.05)
        rgb_dil = np.where(upd[:, :, None], fill, rgb_dil)
        mask_op = np.where(upd, 1.0, mask_op)
    out[:, :, :3] = np.clip(rgb_dil, 0.0, 1.0)
    return out


def height_to_normal(height_hw, strength=2.6):
    p = np.pad(height_hw.astype(np.float32), 1, mode="edge")
    gx = (
        (p[0:-2, 2:] + 2.0 * p[1:-1, 2:] + p[2:, 2:]) -
        (p[0:-2, :-2] + 2.0 * p[1:-1, :-2] + p[2:, :-2])
    ) * 0.25 * strength
    gy = (
        (p[2:, 0:-2] + 2.0 * p[2:, 1:-1] + p[2:, 2:]) -
        (p[:-2, 0:-2] + 2.0 * p[:-2, 1:-1] + p[:-2, 2:])
    ) * 0.25 * strength
    nx = -gx
    ny = -gy
    nz = np.ones_like(nx)
    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-12)
    out = np.empty((height_hw.shape[0], height_hw.shape[1], 4), dtype=np.float32)
    out[:, :, 0] = nx * inv_len * 0.5 + 0.5
    out[:, :, 1] = ny * inv_len * 0.5 + 0.5
    out[:, :, 2] = nz * inv_len * 0.5 + 0.5
    out[:, :, 3] = 1.0
    return out


def create_packed_image(name, rgba_hw4, filepath, colorspace="sRGB", has_alpha=True):
    h, w, _ = rgba_hw4.shape
    img = bpy.data.images.new(name, width=w, height=h, alpha=has_alpha, float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.clip(rgba_hw4, 0.0, 1.0).astype(np.float32).ravel())
    if filepath is not None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        img.filepath_raw = str(filepath)
        img.file_format = "PNG"
        if not has_alpha:
            img.alpha_mode = "NONE"
        img.save()
        img.pack()
    else:
        img.pack()
    return img


def make_single_pbr_material(name, img_alb, img_nrm, img_orm, alpha_cutoff=0.5, double_sided=True, normal_strength=0.93):
    """
    Create a single unified glTF 2.0 PBR material with hardware-depth-tested alphaMode=MASK.
    IMPORTANT: Blender 5 glTF exporter REQUIRES a ShaderNodeMath(GREATER_THAN) on Alpha to emit alphaMode='MASK'
    (without it, Blender 5 silently exports alphaMode='BLEND' which disables depth writes and breaks fin depth order!).
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    t_alb = nt.nodes.new("ShaderNodeTexImage")
    t_alb.image = img_alb
    nt.links.new(t_alb.outputs["Color"], bsdf.inputs["Base Color"])

    math_gt = nt.nodes.new("ShaderNodeMath")
    math_gt.operation = "GREATER_THAN"
    math_gt.inputs[1].default_value = float(alpha_cutoff)
    nt.links.new(t_alb.outputs["Alpha"], math_gt.inputs[0])
    nt.links.new(math_gt.outputs["Value"], bsdf.inputs["Alpha"])

    t_orm = nt.nodes.new("ShaderNodeTexImage")
    t_orm.image = img_orm
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t_orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

    gltf_ao_ng = bpy.data.node_groups.get("glTF Material Output")
    if gltf_ao_ng is None:
        gltf_ao_ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        gltf_ao_ng.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    ao_node = nt.nodes.new("ShaderNodeGroup")
    ao_node.node_tree = gltf_ao_ng
    nt.links.new(sep.outputs["Red"], ao_node.inputs["Occlusion"])

    t_nrm = nt.nodes.new("ShaderNodeTexImage")
    t_nrm.image = img_nrm
    nrm_node = nt.nodes.new("ShaderNodeNormalMap")
    nrm_node.inputs["Strength"].default_value = float(normal_strength)
    nt.links.new(t_nrm.outputs["Color"], nrm_node.inputs["Color"])
    nt.links.new(nrm_node.outputs["Normal"], bsdf.inputs["Normal"])

    mat.use_backface_culling = not double_sided
    if hasattr(mat, "blend_method"):
        mat.blend_method = "CLIP"
    if hasattr(mat, "alpha_threshold"):
        mat.alpha_threshold = float(alpha_cutoff)
    return mat


def limit_top4_weights(obj):
    me = obj.data
    for v in me.vertices:
        gs = [(g.group, g.weight) for g in v.groups if g.weight > 1e-5]
        if len(gs) > 4:
            gs.sort(key=lambda kv: -kv[1])
            keep = gs[:4]
            tot = sum(w for _, w in keep)
            for gi, _ in gs[4:]:
                obj.vertex_groups[gi].remove([v.index])
            if tot > 1e-6:
                for gi, w in keep:
                    obj.vertex_groups[gi].add([v.index], w / tot, "REPLACE")


def find_primary_skinned_mesh_and_armature(mesh_hint=None, arm_hint=None):
    arm = bpy.data.objects.get(arm_hint) if arm_hint else None
    if arm is None:
        arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
        if not arms:
            raise RuntimeError("No ARMATURE object found in source .blend")
        arm = max(arms, key=lambda o: len(o.data.bones))

    mesh_obj = bpy.data.objects.get(mesh_hint) if mesh_hint else None
    if mesh_obj is None:
        candidates = [
            o for o in bpy.data.objects
            if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))
        ]
        if not candidates:
            candidates = [o for o in bpy.data.objects if o.type == "MESH"]
        mesh_obj = max(candidates, key=lambda o: len(o.data.polygons))
    return mesh_obj, arm


def load_atlas_image(img_hint=None):
    img = bpy.data.images.get(img_hint) if img_hint else None
    if img is None:
        imgs = [i for i in bpy.data.images if i.size[0] >= 256 and i.size[1] >= 256]
        if not imgs:
            raise RuntimeError("No source atlas image >= 256px found in .blend")
        img = max(imgs, key=lambda i: i.size[0] * i.size[1])
    w, h = img.size
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape((h, w, 4)), w, h, img.name


def apply_spatial_smooth_split_normals(mesh_obj, dot_threshold=0.35):
    """
    Compute smooth area-weighted split normals across spatially co-located vertices (even when triangles are
    unwelded split faces!), while keeping sharp creases / thin opposing fin sheets crisp (dot <= dot_threshold).
    Zero change to vertex count, vertex indices, UVs, skin weights, or upper-lip hook anchors!
    """
    me = mesh_obj.data
    pos_buckets = {}
    for p in me.polygons:
        n = p.normal.copy()
        a = max(p.area, 1e-8)
        for vi in p.vertices:
            co = me.vertices[vi].co
            key = (round(co.x * 5000), round(co.y * 5000), round(co.z * 5000))
            pos_buckets.setdefault(key, []).append((n, a))

    loop_normals = []
    for p in me.polygons:
        pn = p.normal
        p.use_smooth = True
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            co = me.vertices[vi].co
            key = (round(co.x * 5000), round(co.y * 5000), round(co.z * 5000))
            acc = Vector((0.0, 0.0, 0.0))
            for fn, fa in pos_buckets[key]:
                if pn.dot(fn) > dot_threshold:
                    acc += fn * fa
            if acc.length > 1e-8:
                acc.normalize()
            else:
                acc = pn.copy()
            loop_normals.append(acc)
    me.normals_split_custom_set(loop_normals)


# =========================== TIER 1: 100% Automatic fast_pbr ===========================

def run_fast_pbr(species, tier, alpha_cutoff, out_glb, out_blend, tex_dir):
    """
    100% deterministic, zero-species-config single-material PBR upgrade:
      - Preserves 100% of original vertex positions, topology, mouth/jaw articulation, upper-lip anchor & animations
      - Automatically re-bakes fragmented per-triangle legacy body UVs onto a continuous bilateral UV sheet
        (eliminating tangent-space discontinuities & triangle-border normal artifacts completely!)
      - Automatically packs all fin islands losslessly into the right half of the unified 2:1 atlas
      - Applies spatial normal-cone smooth split normals so split-face legacy meshes shade silky-smooth under PBR
      - Produces 1 Mesh, 1 Material (Draw Call = 1), alphaMode=MASK (cutoff=0.5):
          large -> 2048x1024 Albedo + 1024x512 Normal/ORM (16 MB raw / 4 MB BC7)
          small -> 1024x512  Albedo + 512x256  Normal/ORM ( 4 MB raw / 1 MB BC7)
    """
    orig_obj, armature = find_primary_skinned_mesh_and_armature()
    orig_me = orig_obj.data
    vg_names = [vg.name for vg in orig_obj.vertex_groups]
    atlas_arr, aw, ah, atlas_name = load_atlas_image()

    fin_keywords = ("dorsal", "caudal", "anal", "pectoral", "pelvic", "adipose", "tail")
    fin_vg_set = {n for n in vg_names if any(k in n.lower() for k in fin_keywords)}

    # 1) Automatically classify every polygon as Fin / Oral / Outer Body directly from bone weights & original UV
    uv_layer_orig = orig_me.uv_layers.active.data
    poly_fin_label = {}
    poly_is_oral = set()
    for p in orig_me.polygons:
        vg_sum = {}
        for vi in p.vertices:
            for g in orig_me.vertices[vi].groups:
                gn = vg_names[g.group]
                if gn in fin_vg_set:
                    vg_sum[gn] = vg_sum.get(gn, 0.0) + g.weight
        if vg_sum:
            best_fin, best_w = max(vg_sum.items(), key=lambda kv: kv[1])
            if best_w > 0.25:
                poly_fin_label[p.index] = best_fin
                continue
        u_avg = sum(uv_layer_orig[li].uv.x for li in p.loop_indices) / len(p.loop_indices)
        v_avg = sum(uv_layer_orig[li].uv.y for li in p.loop_indices) / len(p.loop_indices)
        if u_avg > 0.955 and v_avg < 0.025:
            poly_is_oral.add(p.index)

    # Also propagate fin label to adjacent fin-root collar triangles that have > 0.005 fin weight and lie inside that fin's UV bbox
    fin_uv_bounds = {}
    for pi, lbl in poly_fin_label.items():
        p = orig_me.polygons[pi]
        b = fin_uv_bounds.setdefault(lbl, [1e9, -1e9, 1e9, -1e9])
        for li in p.loop_indices:
            u, v = uv_layer_orig[li].uv.x, uv_layer_orig[li].uv.y
            b[0] = min(b[0], u); b[1] = max(b[1], u)
            b[2] = min(b[2], v); b[3] = max(b[3], v)
    for p in orig_me.polygons:
        if p.index in poly_fin_label or p.index in poly_is_oral:
            continue
        vg_sum = {}
        for vi in p.vertices:
            for g in orig_me.vertices[vi].groups:
                gn = vg_names[g.group]
                if gn in fin_uv_bounds:
                    vg_sum[gn] = vg_sum.get(gn, 0.0) + g.weight
        if not vg_sum:
            continue
        best_fin, best_w = max(vg_sum.items(), key=lambda kv: kv[1])
        if best_w > 0.04:
            u_avg = sum(uv_layer_orig[li].uv.x for li in p.loop_indices) / len(p.loop_indices)
            v_avg = sum(uv_layer_orig[li].uv.y for li in p.loop_indices) / len(p.loop_indices)
            b = fin_uv_bounds[best_fin]
            if b[0] - 0.001 <= u_avg <= b[1] + 0.001 and b[2] - 0.001 <= v_avg <= b[3] + 0.001:
                poly_fin_label[p.index] = best_fin

    # Recompute exact fin UV bounds after root-collar propagation
    fin_uv_bounds = {}
    for pi, lbl in poly_fin_label.items():
        p = orig_me.polygons[pi]
        b = fin_uv_bounds.setdefault(lbl, [1e9, -1e9, 1e9, -1e9])
        for li in p.loop_indices:
            u, v = uv_layer_orig[li].uv.x, uv_layer_orig[li].uv.y
            b[0] = min(b[0], u); b[1] = max(b[1], u)
            b[2] = min(b[2], v); b[3] = max(b[3], v)

    # 2) Build exact 3D BVH over outer body faces to sample original painted artwork cleanly
    b_verts, b_polys, b_vcos, b_uvs = [], [], [], []
    bx_min, bx_max, bz_min, bz_max = 1e9, -1e9, 1e9, -1e9
    oral_cols = []
    for p in orig_me.polygons:
        if p.index in poly_fin_label:
            continue
        if p.index in poly_is_oral:
            u_avg = sum(uv_layer_orig[li].uv.x for li in p.loop_indices) / len(p.loop_indices)
            v_avg = sum(uv_layer_orig[li].uv.y for li in p.loop_indices) / len(p.loop_indices)
            oral_cols.append(atlas_arr[min(ah - 1, max(0, int(v_avg * ah))), min(aw - 1, max(0, int(u_avg * aw))), :3])
            continue
        # Triangulate fan if polygon > 3 verts
        loops = list(p.loop_indices)
        for vi in p.vertices:
            co = orig_me.vertices[vi].co
            bx_min = min(bx_min, co.x); bx_max = max(bx_max, co.x)
            bz_min = min(bz_min, co.z); bz_max = max(bz_max, co.z)
        for ti in range(1, len(loops) - 1):
            tri_ls = [loops[0], loops[ti], loops[ti + 1]]
            base = len(b_verts)
            fv, fu = [], []
            for li in tri_ls:
                co = orig_me.vertices[orig_me.loops[li].vertex_index].co.copy()
                b_verts.append(co); fv.append(co)
                fu.append(uv_layer_orig[li].uv.copy())
            b_polys.append((base, base + 1, base + 2))
            b_vcos.append(fv); b_uvs.append(fu)
    body_bvh = BVHTree.FromPolygons(b_verts, b_polys)
    pad_x = max(0.01, (bx_max - bx_min) * 0.015)
    pad_z = max(0.01, (bz_max - bz_min) * 0.025)
    X_MIN, X_MAX = bx_min - pad_x, bx_max + pad_x
    Z_MIN, Z_MAX = bz_min - pad_z, bz_max + pad_z
    oral_rgb = np.median(np.array(oral_cols, dtype=np.float32), axis=0) if oral_cols else np.array([0.22, 0.13, 0.14], dtype=np.float32)

    def sample_body_rgb(pt):
        loc, _, idx, _ = body_bvh.find_nearest(pt)
        if idx is None:
            return np.array([0.5, 0.5, 0.5], dtype=np.float32)
        p0, p1, p2 = b_vcos[idx]
        u0, u1, u2 = b_uvs[idx]
        e0 = p1 - p0; e1 = p2 - p0; ep = loc - p0
        d00 = e0.dot(e0); d01 = e0.dot(e1); d11 = e1.dot(e1)
        d20 = ep.dot(e0); d21 = ep.dot(e1)
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-12:
            bw, bu, bv = 1.0, 0.0, 0.0
        else:
            bu = max(0.0, min(1.0, (d11 * d20 - d01 * d21) / denom))
            bv = max(0.0, min(1.0 - bu, (d00 * d21 - d01 * d20) / denom))
            bw = 1.0 - bu - bv
        uv = u0 * bw + u1 * bu + u2 * bv
        fx = max(0.0, min(aw - 1.001, uv.x * (aw - 1)))
        fy = max(0.0, min(ah - 1.001, uv.y * (ah - 1)))
        x0, y0 = int(fx), int(fy)
        tx, ty = fx - x0, fy - y0
        c00 = atlas_arr[y0, x0, :3]; c10 = atlas_arr[y0, x0 + 1, :3]
        c01 = atlas_arr[y0 + 1, x0, :3]; c11 = atlas_arr[y0 + 1, x0 + 1, :3]
        return ((c00 * (1.0 - tx) + c10 * tx) * (1.0 - ty) + (c01 * (1.0 - tx) + c11 * tx) * ty).astype(np.float32)

    # 3) Auto-pack detected fins cleanly into a tidy non-overlapping grid inside right half [0..1]x[0..1]
    fin_labels_sorted = sorted(fin_uv_bounds.keys())
    n_fins = max(1, len(fin_labels_sorted))
    cols = 3 if n_fins > 4 else 2
    rows = int(math.ceil(n_fins / float(cols)))
    cell_w = (1.0 - 0.02 * (cols + 1)) / cols
    cell_h = (1.0 - 0.02 * (rows + 1)) / rows
    fin_uv_maps = {}
    for idx_f, lbl in enumerate(fin_labels_sorted):
        b = fin_uv_bounds[lbl]
        pu = max(0.002, (b[1] - b[0]) * 0.02)
        pv = max(0.002, (b[3] - b[2]) * 0.02)
        r = idx_f // cols
        c = idx_f % cols
        du0 = 0.02 + c * (cell_w + 0.02)
        dv0 = 0.02 + r * (cell_h + 0.02)
        fin_uv_maps[lbl] = {
            "src": (max(0.0, b[0] - pu), min(1.0, b[1] + pu), max(0.0, b[2] - pv), min(1.0, b[3] + pv)),
            "dst": (du0, dv0, cell_w, cell_h),
        }

    # 4) Assign continuous bilateral UVs to Body, dedicated tile to Oral, and lossless packed UVs to Fins
    #    (while keeping 100% of original vertices, indices, positions, bone weights & upper-lip anchor untouched!)
    uv_body_verts, uv_body_polys, uv_body_3d = [], [], []
    for p in orig_me.polygons:
        if p.index in poly_fin_label:
            lbl = poly_fin_label[p.index]
            su0, su1, sv0, sv1 = fin_uv_maps[lbl]["src"]
            du0, dv0, dw, dh = fin_uv_maps[lbl]["dst"]
            for li in p.loop_indices:
                uv = uv_layer_orig[li].uv
                nu = du0 + dw * ((uv.x - su0) / max(su1 - su0, 1e-6))
                nv = dv0 + dh * ((uv.y - sv0) / max(sv1 - sv0, 1e-6))
                uv_layer_orig[li].uv = Vector((0.5 + nu * 0.5, nv))
        elif p.index in poly_is_oral:
            for li in p.loop_indices:
                uv_layer_orig[li].uv = Vector((0.46, 0.04))  # u=0.92 in left half -> dedicated oral corner!
        else:
            right_side = p.center.y >= 0.0
            loops = list(p.loop_indices)
            p_uvs, p_3d = [], []
            for li in loops:
                co = orig_me.vertices[orig_me.loops[li].vertex_index].co
                u_l = 0.03 + 0.94 * max(0.0, min(1.0, (co.x - X_MIN) / max(X_MAX - X_MIN, 1e-6)))
                vz = max(0.0, min(1.0, (co.z - Z_MIN) / max(Z_MAX - Z_MIN, 1e-6)))
                v_l = (0.53 + 0.44 * vz) if right_side else (0.03 + 0.44 * vz)
                uv_layer_orig[li].uv = Vector((u_l * 0.5, v_l))
                p_uvs.append(Vector((u_l, v_l, 0.0)))
                p_3d.append(co.copy())
            for ti in range(1, len(loops) - 1):
                base = len(uv_body_verts)
                uv_body_verts.extend([p_uvs[0], p_uvs[ti], p_uvs[ti + 1]])
                uv_body_polys.append((base, base + 1, base + 2))
                uv_body_3d.append([p_3d[0], p_3d[ti], p_3d[ti + 1]])

    # 5) Always bake at full 1024x1024 per half so fine scales & fin rays are extracted at full sharpness!
    #    For tier=small: Albedo=1024x512, Normal/ORM=1024x512 (8 MB raw / 2 MB BC7 — crisp scales, never blurry 256px!)
    #    For tier=large: Albedo=2048x1024, Normal/ORM=1024x512 (16 MB raw / 4 MB BC7)
    S = 1024
    uv_bvh = BVHTree.FromPolygons(uv_body_verts, uv_body_polys)
    b_alb = np.zeros((S, S, 4), dtype=np.float32)
    b_alb[:, :, 3] = 1.0
    valid = np.zeros((S, S), dtype=np.float32)
    for iy in range(S):
        v = (iy + 0.5) / S
        for ix in range(S):
            u = (ix + 0.5) / S
            loc, _, idx, dist = uv_bvh.find_nearest(Vector((u, v, 0.0)))
            if idx is None or dist > 0.05:
                continue
            v0, v1, v2 = uv_body_verts[idx * 3], uv_body_verts[idx * 3 + 1], uv_body_verts[idx * 3 + 2]
            e0 = v1 - v0; e1 = v2 - v0; ep = loc - v0
            d00 = e0.dot(e0); d01 = e0.dot(e1); d11 = e1.dot(e1)
            d20 = ep.dot(e0); d21 = ep.dot(e1)
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-12:
                bw, bu, bv = 1.0, 0.0, 0.0
            else:
                bu = max(0.0, min(1.0, (d11 * d20 - d01 * d21) / denom))
                bv = max(0.0, min(1.0 - bu, (d00 * d21 - d01 * d20) / denom))
                bw = 1.0 - bu - bv
            p0, p1, p2 = uv_body_3d[idx]
            b_alb[iy, ix, :3] = sample_body_rgb(p0 * bw + p1 * bu + p2 * bv)
            valid[iy, ix] = 1.0 if dist < 0.008 else 0.0

    # Dedicated oral tile corner in bottom-right of left half
    uu = (np.arange(S, dtype=np.float32) + 0.5) / S
    U, V = np.meshgrid(uu, uu)
    oral_tile = ((U > 0.855) & (V < 0.105)).astype(np.float32)
    b_alb[:, :, :3] = b_alb[:, :, :3] * (1.0 - oral_tile[:, :, None]) + oral_rgb[None, None, :] * oral_tile[:, :, None]

    # Pixel-locked crisp body Normal & ORM (matched to red_seabream tactile scale relief!)
    b_lum = 0.299 * b_alb[:, :, 0] + 0.587 * b_alb[:, :, 1] + 0.114 * b_alb[:, :, 2]
    v_soft = gaussian_approx_2d(valid, 3) * (1.0 - oral_tile)
    bh_s = np.clip((gaussian_approx_2d(b_lum, 2) - gaussian_approx_2d(b_lum, 9)) * 4.8, -0.68, 0.68) * v_soft
    bh_m = np.clip((gaussian_approx_2d(b_lum, 9) - gaussian_approx_2d(b_lum, 24)) * 2.8, -0.75, 0.75) * v_soft
    b_nrm = height_to_normal(bh_s * 0.78 + bh_m * 0.50, strength=3.6)
    b_sat = np.max(b_alb[:, :, :3], axis=2) - np.min(b_alb[:, :, :3], axis=2)
    b_silver = smoothstep(0.32, 0.72, b_lum) * (1.0 - smoothstep(0.18, 0.48, b_sat))
    b_orm = np.ones((S, S, 4), dtype=np.float32)
    b_orm[:, :, 0] = np.clip(1.0 - 0.26 * np.clip(-bh_s, 0.0, 1.0) - 0.28 * np.clip(-bh_m, 0.0, 1.0) - 0.35 * oral_tile, 0.34, 1.0)
    b_orm[:, :, 1] = np.clip(0.54 - 0.15 * bh_s - 0.10 * b_silver + 0.28 * oral_tile, 0.34, 0.90)
    b_orm[:, :, 2] = np.clip((0.15 * b_silver + 0.08 * np.clip(bh_s + 0.45, 0.0, 1.0)) * (1.0 - oral_tile), 0.0, 0.24)

    # Lossless Fin packing into 1024x1024 right half
    f_alb = np.zeros((S, S, 4), dtype=np.float32)
    for lbl, info in fin_uv_maps.items():
        su0, su1, sv0, sv1 = info["src"]
        du0, dv0, dw, dh = info["dst"]
        xs0, xs1 = max(0, int(math.floor(du0 * S))), min(S, int(math.ceil((du0 + dw) * S)))
        ys0, ys1 = max(0, int(math.floor(dv0 * S))), min(S, int(math.ceil((dv0 + dh) * S)))
        if xs1 <= xs0 or ys1 <= ys0:
            continue
        tu = np.clip(((np.arange(xs0, xs1, dtype=np.float32) + 0.5) / S - du0) / max(dw, 1e-6), 0.0, 1.0)
        tv = np.clip(((np.arange(ys0, ys1, dtype=np.float32) + 0.5) / S - dv0) / max(dh, 1e-6), 0.0, 1.0)
        fx = np.clip((su0 + tu * (su1 - su0)) * (aw - 1), 0.0, aw - 1.001)
        fy = np.clip((sv0 + tv * (sv1 - sv0)) * (ah - 1), 0.0, ah - 1.001)
        ix0, iy0 = np.floor(fx).astype(np.int32), np.floor(fy).astype(np.int32)
        tx, ty = (fx - ix0)[None, :, None], (fy - iy0)[:, None, None]
        f_alb[ys0:ys1, xs0:xs1] = (
            (atlas_arr[iy0[:, None], ix0[None, :]] * (1.0 - tx) + atlas_arr[iy0[:, None], ix0[None, :] + 1] * tx) * (1.0 - ty) +
            (atlas_arr[iy0[:, None] + 1, ix0[None, :]] * (1.0 - tx) + atlas_arr[iy0[:, None] + 1, ix0[None, :] + 1] * tx) * ty
        )
    f_alb = dilate_alpha_rgb(f_alb, alpha_thresh=alpha_cutoff, passes=8)
    f_lum = 0.299 * f_alb[:, :, 0] + 0.587 * f_alb[:, :, 1] + 0.114 * f_alb[:, :, 2]
    f_alpha = smoothstep(0.30, 0.75, f_alb[:, :, 3])
    ray_h = np.clip((gaussian_approx_2d(f_lum, 2) - gaussian_approx_2d(f_lum, 9)) * 5.0, -0.75, 0.85) * f_alpha
    f_nrm = height_to_normal(ray_h, strength=3.4)
    ray_01 = np.clip(ray_h * 0.65 + 0.5, 0.0, 1.0)
    f_orm = np.ones((S, S, 4), dtype=np.float32)
    f_orm[:, :, 0] = np.clip(0.86 + 0.14 * ray_01, 0.55, 1.0)
    f_orm[:, :, 1] = np.clip(0.72 - 0.24 * ray_01, 0.42, 0.80)
    f_orm[:, :, 2] = np.clip(0.05 * ray_01, 0.0, 0.07)

    atlas_alb_full = np.concatenate([b_alb, f_alb], axis=1)   # 1024 x 2048
    atlas_nrm = downsample_2x(np.concatenate([b_nrm, f_nrm], axis=1), is_normal=True)   # 512 x 1024 (crisp scales!)
    atlas_orm = downsample_2x(np.concatenate([b_orm, f_orm], axis=1), is_normal=False)  # 512 x 1024
    atlas_alb = downsample_2x(atlas_alb_full, is_normal=False) if tier == "small" else atlas_alb_full

    # 6) Smooth spatial normal-cone split normals + top-4 skin weights (zero vertex/index/anchor change!)
    orig_verts_before = len(orig_me.vertices)
    apply_spatial_smooth_split_normals(orig_obj, dot_threshold=0.35)
    limit_top4_weights(orig_obj)

    tag = "".join(p.capitalize() for p in species.split("_"))
    img_alb = create_packed_image(f"{tag}_PBR_Albedo", atlas_alb, (tex_dir / "fish_albedo.png") if tex_dir else None, "sRGB", has_alpha=True)
    img_nrm = create_packed_image(f"{tag}_PBR_Normal", atlas_nrm, (tex_dir / "fish_normal.png") if tex_dir else None, "Non-Color", has_alpha=False)
    img_orm = create_packed_image(f"{tag}_PBR_ORM", atlas_orm, (tex_dir / "fish_orm.png") if tex_dir else None, "Non-Color", has_alpha=False)

    mat = make_single_pbr_material(f"{tag}_PBR", img_alb, img_nrm, img_orm, alpha_cutoff=alpha_cutoff, double_sided=True, normal_strength=0.95)
    orig_me.materials.clear()
    orig_me.materials.append(mat)

    keep_imgs = {img_alb.name, img_nrm.name, img_orm.name}
    for img in list(bpy.data.images):
        if img.name not in keep_imgs and img.users == 0:
            bpy.data.images.remove(img)

    if out_blend:
        out_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))

    out_glb.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    orig_obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(out_glb),
        export_format="GLB",
        use_selection=True,
        export_texcoords=True,
        export_normals=True,
        export_tangents=True,
        export_materials="EXPORT",
        export_skins=True,
        export_animations=True,
        export_yup=True,
    )

    total_tris = sum(len(p.vertices) - 2 for p in orig_me.polygons)
    print("UPGRADE_FISH_PBR_OK " + json.dumps({
        "species": species,
        "mode": "fast_pbr",
        "tier": tier,
        "source_atlas": atlas_name,
        "detected_fins": fin_labels_sorted,
        "albedo_size": [atlas_alb.shape[1], atlas_alb.shape[0]],
        "normal_orm_size": [atlas_nrm.shape[1], atlas_nrm.shape[0]],
        "total_tris": total_tris,
        "verts_before": orig_verts_before,
        "verts_after": len(orig_me.vertices),
        "draw_calls": 1,
        "alpha_cutoff": alpha_cutoff,
        "glb_kb": out_glb.stat().st_size // 1024,
        "glb_path": str(out_glb),
    }))


# =========================== TIER 2: Parameterized sculpt_pbr ===========================

def run_sculpt_pbr(cfg, tier, alpha_cutoff, out_glb, out_blend, tex_dir):
    species = cfg["species"]
    orig_obj, armature = find_primary_skinned_mesh_and_armature(cfg.get("mesh_name"), cfg.get("armature_name"))
    vg_names = [vg.name for vg in orig_obj.vertex_groups]
    atlas_arr, aw, ah, _ = load_atlas_image(cfg.get("atlas_image_name"))

    eye_c = Vector(cfg["eye"]["center_right"])
    eye_r = float(cfg["eye"]["radius"])
    skin_rim_rgb = np.array(cfg["eye"]["skin_rim_rgb"], dtype=np.float32)
    bx = cfg["body_bounds_xz"]
    X_MIN, X_MAX, Z_MIN, Z_MAX = float(bx["x_min"]), float(bx["x_max"]), float(bx["z_min"]), float(bx["z_max"])
    oral_strip = cfg["mouth"]["oral_uv_strip"]
    no_subdiv = cfg["mouth"]["no_subdiv_box_xz"]
    fin_bones = set(cfg["fin_bones"])
    fin_src_boxes = cfg["fin_src_uv_boxes"]
    fin_dst_tiles = cfg["fin_dst_tiles"]
    op_cfg = cfg.get("operculum", {"enabled": False})
    nos_cfg = cfg.get("nostril", {"enabled": False})

    def op_curve_x(z):
        dz = z - float(op_cfg.get("curve_z_center", -0.02))
        return float(op_cfg.get("curve_base_x", 0.278)) + float(op_cfg.get("curve_quad_coeff", -0.95)) * (dz ** 2) + float(op_cfg.get("curve_lin_coeff", -0.14)) * dz

    def classify_fin_face(f, me, uv_layer):
        bone_w = {}
        for v in f.verts:
            for g in me.vertices[v.index].groups:
                gname = vg_names[g.group]
                if gname in fin_bones:
                    bone_w[gname] = bone_w.get(gname, 0.0) + g.weight
        if not bone_w:
            return None
        best_fin, best_w = max(bone_w.items(), key=lambda kv: kv[1])
        if best_w > 0.25:
            return best_fin
        u = sum(l[uv_layer].uv.x for l in f.loops) / len(f.loops)
        v = sum(l[uv_layer].uv.y for l in f.loops) / len(f.loops)
        if best_w > 0.005 and best_fin in fin_src_boxes:
            u0, u1, v0, v1 = fin_src_boxes[best_fin]
            if u0 <= u <= u1 and v0 <= v <= v1:
                return best_fin
        return None

    def is_orig_oral_face(f, uv_layer):
        n = len(f.loops)
        u = sum(l[uv_layer].uv.x for l in f.loops) / n
        v = sum(l[uv_layer].uv.y for l in f.loops) / n
        return u > float(oral_strip["u_min"]) and v < float(oral_strip["v_max"])

    # Outer-body-only BVH sampler (excludes fins & oral cavity so outer lips stay spotless!)
    orig_me = orig_obj.data
    bm_bvh = bmesh.new()
    bm_bvh.from_mesh(orig_me)
    bm_bvh.faces.ensure_lookup_table()
    uv_bvh_l = bm_bvh.loops.layers.uv.active
    b_verts, b_polys, b_vcos, b_uvs = [], [], [], []
    for f in bm_bvh.faces:
        if classify_fin_face(f, orig_me, uv_bvh_l) is not None or is_orig_oral_face(f, uv_bvh_l):
            continue
        base = len(b_verts)
        fv, fu = [], []
        for l in f.loops:
            b_verts.append(l.vert.co.copy())
            fv.append(l.vert.co.copy())
            fu.append(l[uv_bvh_l].uv.copy())
        b_polys.append((base, base + 1, base + 2))
        b_vcos.append(fv)
        b_uvs.append(fu)
    bvh = BVHTree.FromPolygons(b_verts, b_polys)
    bm_bvh.free()

    def sample_body_rgba(pt):
        loc, _, idx, _ = bvh.find_nearest(pt)
        if idx is None:
            return np.array([0.85, 0.72, 0.68, 1.0], dtype=np.float32)
        p0, p1, p2 = b_vcos[idx]
        u0, u1, u2 = b_uvs[idx]
        e0 = p1 - p0; e1 = p2 - p0; ep = loc - p0
        d00 = e0.dot(e0); d01 = e0.dot(e1); d11 = e1.dot(e1)
        d20 = ep.dot(e0); d21 = ep.dot(e1)
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-12:
            bw, bu, bv = 1.0, 0.0, 0.0
        else:
            bu = max(0.0, min(1.0, (d11 * d20 - d01 * d21) / denom))
            bv = max(0.0, min(1.0 - bu, (d00 * d21 - d01 * d20) / denom))
            bw = 1.0 - bu - bv
        uv = u0 * bw + u1 * bu + u2 * bv
        fx = max(0.0, min(aw - 1.001, uv.x * (aw - 1)))
        fy = max(0.0, min(ah - 1.001, uv.y * (ah - 1)))
        x0, y0 = int(fx), int(fy)
        tx, ty = fx - x0, fy - y0
        c00 = atlas_arr[y0, x0]; c10 = atlas_arr[y0, x0 + 1]
        c01 = atlas_arr[y0 + 1, x0]; c11 = atlas_arr[y0 + 1, x0 + 1]
        return ((c00 * (1.0 - tx) + c10 * tx) * (1.0 - ty) + (c01 * (1.0 - tx) + c11 * tx) * ty).astype(np.float32)

    # 1) Split Body & Fins while preserving exact deform weights, exact oral tags, and normal-cone fin welding
    bm_all = bmesh.new()
    bm_all.from_mesh(orig_me)
    bm_all.faces.ensure_lookup_table()
    uv_all = bm_all.loops.layers.uv.active
    dvert_all = bm_all.verts.layers.deform.verify()

    bm_body = bmesh.new()
    uv_body = bm_body.loops.layers.uv.new("UVMap")
    dvert_body = bm_body.verts.layers.deform.verify()
    oral_tag = bm_body.faces.layers.int.new("is_oral")

    bm_fins = bmesh.new()
    uv_fins = bm_fins.loops.layers.uv.new("UVMap")
    dvert_fins = bm_fins.verts.layers.deform.verify()
    fin_face_labels = []
    fin_vert_cache = {}

    for f in bm_all.faces:
        lbl = classify_fin_face(f, orig_me, uv_all)
        if lbl is not None:
            fn = f.normal
            ns = (round(fn.x * 2.0), round(fn.y * 2.0), round(fn.z * 2.0))
            new_vs = []
            for ol in f.loops:
                ov = ol.vert
                co = ov.co
                ouv = ol[uv_all].uv
                key = (lbl, round(co.x * 5000), round(co.y * 5000), round(co.z * 5000), round(ouv.x * 500), round(ouv.y * 500), ns)
                nv = fin_vert_cache.get(key)
                if nv is None:
                    nv = bm_fins.verts.new(co.copy())
                    for gi, gw in ov[dvert_all].items():
                        nv[dvert_fins][gi] = gw
                    fin_vert_cache[key] = nv
                new_vs.append(nv)
            if len(set(new_vs)) < 3:
                continue
            try:
                nf = bm_fins.faces.new(new_vs)
            except ValueError:
                continue
            nf.smooth = True
            for nl, ol in zip(nf.loops, f.loops):
                nl[uv_fins].uv = ol[uv_all].uv.copy()
            fin_face_labels.append(lbl)
        else:
            is_oral_orig = 1 if is_orig_oral_face(f, uv_all) else 0
            new_vs = []
            for ov in f.verts:
                nv = bm_body.verts.new(ov.co.copy())
                for gi, gw in ov[dvert_all].items():
                    nv[dvert_body][gi] = gw
                new_vs.append(nv)
            nf = bm_body.faces.new(new_vs)
            nf.smooth = True
            nf[oral_tag] = is_oral_orig
            for nl, ol in zip(nf.loops, f.loops):
                nl[uv_body].uv = ol[uv_all].uv.copy()
    bm_all.free()

    # 2) Weld & selectively subdivide body (keeping mouth rim & oral cavity untouched!)
    bmesh.ops.remove_doubles(bm_body, verts=bm_body.verts, dist=0.00015)
    bmesh.ops.recalc_face_normals(bm_body, faces=bm_body.faces)

    def in_no_subdiv(c):
        return c.x > float(no_subdiv["x_min"]) and float(no_subdiv["z_min"]) < c.z < float(no_subdiv["z_max"])

    non_mouth_faces = [f for f in bm_body.faces if f[oral_tag] == 0 and not in_no_subdiv(f.calc_center_median())]
    bmesh.ops.join_triangles(bm_body, faces=non_mouth_faces, angle_face_threshold=0.65, angle_shape_threshold=0.85)

    edges_to_subdiv = set()
    for f in bm_body.faces:
        if f[oral_tag] == 1 or in_no_subdiv(f.calc_center_median()):
            continue
        c = f.calc_center_median()
        if c.x > 0.25:
            for e in f.edges:
                if any(lf[oral_tag] == 1 or in_no_subdiv(lf.calc_center_median()) for lf in e.link_faces):
                    continue
                edges_to_subdiv.add(e)
        elif c.x > -0.26:
            for e in f.edges:
                if e.calc_length() > 0.125:
                    edges_to_subdiv.add(e)

    bmesh.ops.subdivide_edges(bm_body, edges=list(edges_to_subdiv), cuts=1, smooth=0.35, smooth_falloff="SMOOTH", use_grid_fill=True)
    bmesh.ops.triangulate(bm_body, faces=bm_body.faces, quad_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm_body, faces=bm_body.faces)

    # 3) 3D Anatomical Sculpting (Orbital socket, curved operculum, nostrils; never displaces upper-lip anchor or oral vertices!)
    upper_lip_anchor = Vector(cfg["upper_lip_anchor"])
    bm_body.verts.ensure_lookup_table()
    bm_body.normal_update()
    for v in bm_body.verts:
        p = v.co
        if (p - upper_lip_anchor).length < 0.004 or any(lf[oral_tag] == 1 for lf in v.link_faces):
            continue
        side = 1.0 if p.y >= 0.0 else -1.0
        ay = abs(p.y)

        de = math.hypot(p.x - eye_c.x, p.z - eye_c.z)
        if ay > 0.025 and de < eye_r * 1.48:
            if de < eye_r * 0.88:
                t = 1.0 - (de / (eye_r * 0.88)) ** 2
                p.y -= side * 0.0055 * t
            else:
                rim = math.exp(-((de - eye_r * 1.15) / 0.0070) ** 2)
                brow_boost = 1.35 if p.z > eye_c.z else 0.85
                p.y += side * 0.0024 * rim * brow_boost

        if op_cfg.get("enabled", False) and ay > 0.020 and -0.145 < p.z < 0.105 and 0.21 < p.x < 0.37:
            x_op = float(op_curve_x(p.z))
            gz = float(smoothstep(-0.145, -0.105, p.z) * (1.0 - smoothstep(0.068, 0.102, p.z)))
            dop = p.x - x_op
            if -0.014 < dop < 0.062:
                plate = float(smoothstep(-0.003, 0.011, dop) * (1.0 - smoothstep(0.022, 0.062, dop)))
                slit = math.exp(-((dop + 0.0045) / 0.0055) ** 2)
                p.y += side * (0.0038 * plate - 0.0034 * slit) * gz

        if p.x > 0.448 and p.x < 0.494 and ay > 0.004:
            ul = math.exp(-((p.z - (-0.027)) / 0.0085) ** 2)
            ll = math.exp(-((p.z - (-0.053)) / 0.0085) ** 2)
            lx = float(smoothstep(0.448, 0.470, p.x) * (1.0 - smoothstep(0.488, 0.495, p.x)))
            p.y += side * (0.0024 * ul + 0.0019 * ll) * lx
            p.x += (0.0013 * ul + 0.0010 * ll) * lx

        if nos_cfg.get("enabled", False):
            nx, nz = float(nos_cfg["pos_xz"][0]), float(nos_cfg["pos_xz"][1])
            dn = math.hypot(p.x - nx, p.z - nz)
            if ay > 0.015 and dn < 0.008:
                p.y -= side * 0.0016 * math.exp(-(dn / 0.0042) ** 2)

    relax_verts = [v for v in bm_body.verts if not v.is_boundary and -0.31 < v.co.x < 0.21 and abs(v.co.y) > 0.012]
    bmesh.ops.smooth_vert(bm_body, verts=relax_verts, factor=0.18, use_axis_x=False, use_axis_y=True, use_axis_z=False)

    # Bilateral Body UV (with exact hand-authored oral faces in bottom-right tile)
    uv_body = bm_body.loops.layers.uv["UVMap"]
    for f in bm_body.faces:
        f.smooth = True
        fc = f.calc_center_median()
        if f[oral_tag] == 1:
            for l in f.loops:
                p = l.vert.co
                uo = 0.87 + 0.10 * max(0.0, min(1.0, (p.x - 0.425) / 0.075))
                vo = 0.02 + 0.06 * max(0.0, min(1.0, (p.y + 0.05) / 0.10))
                l[uv_body].uv = Vector((uo, vo))
            continue
        right_side = fc.y >= 0.0
        for l in f.loops:
            p = l.vert.co
            u = 0.03 + 0.94 * max(0.0, min(1.0, (p.x - X_MIN) / (X_MAX - X_MIN)))
            vz = max(0.0, min(1.0, (p.z + 0.04 * abs(p.y) * (1.0 if p.z < -0.03 else -1.0) - Z_MIN) / (Z_MAX - Z_MIN)))
            v = (0.53 + 0.44 * vz) if right_side else (0.03 + 0.44 * vz)
            l[uv_body].uv = Vector((u, v))

    bmesh.ops.recalc_face_normals(bm_body, faces=bm_body.faces)
    body_me = bpy.data.meshes.new(f"{species}_Body_Mesh")
    bm_body.to_mesh(body_me)
    bm_body.free()
    body_obj = bpy.data.objects.new(f"{species}_Body", body_me)
    bpy.context.collection.objects.link(body_obj)
    for gn in vg_names:
        body_obj.vertex_groups.new(name=gn)
    limit_top4_weights(body_obj)

    # 4) Lossless 1:1 Fin UV packing
    bm_fins.faces.ensure_lookup_table()
    uv_fins = bm_fins.loops.layers.uv["UVMap"]
    src_boxes = {}
    for f, lbl in zip(bm_fins.faces, fin_face_labels):
        b = src_boxes.setdefault(lbl, [1e9, -1e9, 1e9, -1e9])
        for l in f.loops:
            uv = l[uv_fins].uv
            b[0] = min(b[0], uv.x); b[1] = max(b[1], uv.x)
            b[2] = min(b[2], uv.y); b[3] = max(b[3], uv.y)

    fin_uv_maps = {}
    for lbl, b in src_boxes.items():
        pad_u = (b[1] - b[0]) * 0.015
        pad_v = (b[3] - b[2]) * 0.015
        fin_uv_maps[lbl] = {
            "src": (max(0.0, b[0] - pad_u), min(1.0, b[1] + pad_u), max(0.0, b[2] - pad_v), min(1.0, b[3] + pad_v)),
            "dst": tuple(fin_dst_tiles[lbl]),
        }

    for f, lbl in zip(bm_fins.faces, fin_face_labels):
        su0, su1, sv0, sv1 = fin_uv_maps[lbl]["src"]
        du0, dv0, dw, dh = fin_uv_maps[lbl]["dst"]
        for l in f.loops:
            uv = l[uv_fins].uv
            l[uv_fins].uv = Vector((du0 + dw * ((uv.x - su0) / max(su1 - su0, 1e-6)), dv0 + dh * ((uv.y - sv0) / max(sv1 - sv0, 1e-6))))

    fin_me = bpy.data.meshes.new(f"{species}_Fins_Mesh")
    bm_fins.to_mesh(fin_me)
    bm_fins.free()
    fin_obj = bpy.data.objects.new(f"{species}_Fins", fin_me)
    bpy.context.collection.objects.link(fin_obj)
    for gn in vg_names:
        fin_obj.vertex_groups.new(name=gn)
    limit_top4_weights(fin_obj)

    # 5) 3D Protruding Eyeballs locked rigidly to orbital-socket rim bone weights
    bm_eye = bmesh.new()
    uv_eye = bm_eye.loops.layers.uv.new("UVMap")
    SEGS = 16
    thetas = [0.26, 0.56, 0.92, 1.32, 1.72]
    r_ball = eye_r * 1.08
    for side in [1.0, -1.0]:
        center = Vector((eye_c.x, side * (eye_c.y - 0.0040), eye_c.z))
        out_dir = Vector((0.23, side * 0.965, 0.08)).normalized()
        tan_x = Vector((0.0, 0.0, 1.0)).cross(out_dir).normalized()
        if side < 0:
            tan_x = -tan_x
        tan_z = out_dir.cross(tan_x).normalized()
        if tan_z.z < 0:
            tan_z = -tan_z
        v_apex = bm_eye.verts.new(center + out_dir * 0.0150)
        ring_verts = []
        for ti, th in enumerate(thetas):
            r_ring = r_ball * math.sin(th) * (0.94 if ti == len(thetas) - 1 else 1.0)
            depth = 0.0150 * math.cos(th)
            ring_verts.append([bm_eye.verts.new(center + out_dir * depth + tan_x * (math.cos(2 * math.pi * si / SEGS) * r_ring) + tan_z * (math.sin(2 * math.pi * si / SEGS) * r_ring)) for si in range(SEGS)])
        eye_faces = []
        for si in range(SEGS):
            sn = (si + 1) % SEGS
            f = bm_eye.faces.new([v_apex, ring_verts[0][si], ring_verts[0][sn]] if side > 0 else [v_apex, ring_verts[0][sn], ring_verts[0][si]])
            f.smooth = True
            eye_faces.append(f)
        for ri in range(len(ring_verts) - 1):
            r0, r1 = ring_verts[ri], ring_verts[ri + 1]
            for si in range(SEGS):
                sn = (si + 1) % SEGS
                f1 = bm_eye.faces.new([r0[si], r1[si], r1[sn]] if side > 0 else [r0[si], r1[sn], r1[si]])
                f2 = bm_eye.faces.new([r0[si], r1[sn], r0[sn]] if side > 0 else [r0[si], r0[sn], r1[sn]])
                f1.smooth = True; f2.smooth = True
                eye_faces.extend([f1, f2])
        for f in eye_faces:
            for l in f.loops:
                rel = l.vert.co - center
                u_loc = rel.dot(tan_x) / (eye_r * 1.04)
                v_loc = rel.dot(tan_z) / (eye_r * 1.04)
                l[uv_eye].uv = Vector((0.088 + u_loc * 0.076, 0.912 + v_loc * 0.076))
    bmesh.ops.recalc_face_normals(bm_eye, faces=bm_eye.faces)
    eye_me = bpy.data.meshes.new(f"{species}_Eyes_Mesh")
    bm_eye.to_mesh(eye_me)
    bm_eye.free()
    eye_obj = bpy.data.objects.new(f"{species}_Eyes", eye_me)
    bpy.context.collection.objects.link(eye_obj)
    for gn in vg_names:
        eye_obj.vertex_groups.new(name=gn)
    body_vgs = [g.name for g in body_obj.vertex_groups]
    for side in [1.0, -1.0]:
        side_vs = [v.index for v in eye_me.vertices if (v.co.y > 0 if side > 0 else v.co.y < 0)]
        acc = {}
        for bv in body_me.vertices:
            if (bv.co.y > 0.03 if side > 0 else bv.co.y < -0.03):
                d = math.hypot(bv.co.x - eye_c.x, bv.co.z - eye_c.z)
                if eye_r * 0.78 < d < eye_r * 1.28:
                    for g in bv.groups:
                        if g.weight > 1e-4:
                            gn = body_vgs[g.group]
                            acc[gn] = acc.get(gn, 0.0) + g.weight
        tot = sum(acc.values())
        if tot > 1e-6:
            top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
            top_tot = sum(w for _, w in top4)
            for gn, w in top4:
                eye_obj.vertex_groups[gn].add(side_vs, w / top_tot, "REPLACE")
        else:
            eye_obj.vertex_groups["body_00"].add(side_vs, 1.0, "REPLACE")

    # 6) Bake Body+Eye (1024x1024) + Fins (1024x1024) -> Single-Material 2:1 Atlas (large=2048x1024, small=1024x512)
    S = 1024
    bm_uv = bmesh.new()
    bm_uv.from_mesh(body_me)
    bm_uv.faces.ensure_lookup_table()
    uv_l = bm_uv.loops.layers.uv["UVMap"]
    uv_verts, uv_polys, tri_3d = [], [], []
    for f in bm_uv.faces:
        base = len(uv_verts)
        p3 = []
        for l in f.loops:
            uv = l[uv_l].uv
            uv_verts.append(Vector((uv.x, uv.y, 0.0)))
            p3.append(l.vert.co.copy())
        uv_polys.append((base, base + 1, base + 2))
        tri_3d.append(p3)
    uv_bvh = BVHTree.FromPolygons(uv_verts, uv_polys)
    bm_uv.free()

    b_alb = np.zeros((S, S, 3), dtype=np.float32)
    valid = np.zeros((S, S), dtype=np.float32)
    for iy in range(S):
        v = (iy + 0.5) / S
        for ix in range(S):
            u = (ix + 0.5) / S
            loc, _, idx, dist = uv_bvh.find_nearest(Vector((u, v, 0.0)))
            if idx is None or dist > 0.04:
                continue
            v0, v1, v2 = uv_verts[idx * 3], uv_verts[idx * 3 + 1], uv_verts[idx * 3 + 2]
            e0 = v1 - v0; e1 = v2 - v0; ep = loc - v0
            d00 = e0.dot(e0); d01 = e0.dot(e1); d11 = e1.dot(e1)
            d20 = ep.dot(e0); d21 = ep.dot(e1)
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-12:
                bw, bu, bv = 1.0, 0.0, 0.0
            else:
                bu = max(0.0, min(1.0, (d11 * d20 - d01 * d21) / denom))
                bv = max(0.0, min(1.0 - bu, (d00 * d21 - d01 * d20) / denom))
                bw = 1.0 - bu - bv
            p0, p1, p2 = tri_3d[idx]
            b_alb[iy, ix] = sample_body_rgba(p0 * bw + p1 * bu + p2 * bv)[:3]
            valid[iy, ix] = 1.0 if dist < 0.005 else 0.0

    orig_body_albedo = b_alb.copy()
    uu = (np.arange(S, dtype=np.float32) + 0.5) / S
    U, V = np.meshgrid(uu, uu)
    v_side = np.where(V >= 0.5, (V - 0.53) / 0.44, (V - 0.03) / 0.44)
    u_side = (U - 0.03) / 0.94
    X = X_MIN + u_side * (X_MAX - X_MIN)
    Z = Z_MIN + v_side * (Z_MAX - Z_MIN)

    d_eye = np.sqrt((X - eye_c.x) ** 2 + (Z - eye_c.z) ** 2)
    socket_inner = 1.0 - smoothstep(eye_r * 0.65, eye_r * 0.95, d_eye)
    socket_ring = smoothstep(eye_r * 0.80, eye_r * 1.06, d_eye) * (1.0 - smoothstep(eye_r * 1.06, eye_r * 1.42, d_eye))
    b_alb = b_alb * (1.0 - socket_inner[:, :, None]) + np.array([0.46, 0.25, 0.22], dtype=np.float32)[None, None, :] * socket_inner[:, :, None]
    b_alb = b_alb * (1.0 - socket_ring[:, :, None] * 0.35) + skin_rim_rgb[None, None, :] * (socket_ring[:, :, None] * 0.35)

    oral_tile_f = ((U > 0.855) & (V < 0.105)).astype(np.float32)
    b_smooth = gaussian_approx_2d(b_alb, 10)
    sat_orange = (b_alb[:, :, 0] - b_alb[:, :, 2] > 0.28) & (b_alb[:, :, 1] < 0.46)
    pec_box = (X > 0.08) & (X < 0.235) & (Z > -0.105) & (Z < -0.010)
    pel_box = (X > 0.06) & (X < 0.220) & (Z < -0.115)
    bleed_mask = np.clip(gaussian_approx_2d((sat_orange & (pec_box | pel_box)).astype(np.float32), 3) * 2.2, 0.0, 1.0)
    b_alb = b_alb * (1.0 - bleed_mask[:, :, None]) + b_smooth * bleed_mask[:, :, None]

    lip_zone_mask = smoothstep(0.428, 0.446, X) * smoothstep(-0.066, -0.056, Z) * (1.0 - smoothstep(-0.026, -0.016, Z)) * (1.0 - oral_tile_f)
    lum_pre = 0.299 * b_alb[:, :, 0] + 0.587 * b_alb[:, :, 1] + 0.114 * b_alb[:, :, 2]
    dark_lip_grime = smoothstep(0.56, 0.28, lum_pre) * lip_zone_mask
    is_ul = smoothstep(-0.044, -0.032, Z)
    ul_rgb = np.array(cfg["mouth"]["upper_lip_rgb"], dtype=np.float32)
    ll_rgb = np.array(cfg["mouth"]["lower_lip_rgb"], dtype=np.float32)
    clean_lip_col = ul_rgb[None, None, :] * is_ul[:, :, None] + ll_rgb[None, None, :] * (1.0 - is_ul[:, :, None])
    b_alb = b_alb * (1.0 - dark_lip_grime[:, :, None] * 0.92) + clean_lip_col * (dark_lip_grime[:, :, None] * 0.92)

    lip_clean_guard = 1.0 - 0.88 * lip_zone_mask
    lum = 0.299 * b_alb[:, :, 0] + 0.587 * b_alb[:, :, 1] + 0.114 * b_alb[:, :, 2]
    h_scales = np.clip((gaussian_approx_2d(lum, 2) - gaussian_approx_2d(lum, 9)) * 4.5, -0.65, 0.65)
    h_macro = np.clip((gaussian_approx_2d(lum, 9) - gaussian_approx_2d(lum, 24)) * 2.8, -0.75, 0.75)
    valid_soft = gaussian_approx_2d(valid, 3)
    h_scales *= valid_soft * (1.0 - socket_inner) * (1.0 - oral_tile_f) * lip_clean_guard
    h_macro *= valid_soft * (1.0 - socket_inner) * (1.0 - oral_tile_f) * lip_clean_guard

    h_op = np.zeros((S, S), dtype=np.float32)
    op_ao = np.ones((S, S), dtype=np.float32)
    if op_cfg.get("enabled", False):
        x_op = op_curve_x(Z)
        gill_z = smoothstep(-0.140, -0.100, Z) * (1.0 - smoothstep(0.068, 0.100, Z))
        dist_op = X - x_op
        h_op = (smoothstep(-0.005, 0.012, dist_op) * 0.55 - np.exp(-((dist_op + 0.004) / 0.0055) ** 2) * 0.45) * gill_z
        op_ao = 1.0 - 0.38 * np.exp(-((dist_op + 0.0035) / 0.006) ** 2) * gill_z

    h_orbit = np.exp(-((d_eye - eye_r * 1.18) / 0.0068) ** 2) * 0.42 - socket_inner * 0.55
    lip_x_mask = smoothstep(0.435, 0.458, X) * (1.0 - oral_tile_f)
    h_lip = (np.exp(-((Z - (-0.028)) / 0.008) ** 2) * 0.36 + np.exp(-((Z - (-0.053)) / 0.008) ** 2) * 0.30) * lip_x_mask
    b_nrm_arr = height_to_normal(h_scales * 0.72 + h_macro * 0.48 + h_op * 0.55 + h_orbit * 0.55 + h_lip * 0.50, strength=3.4)

    oral_col = np.array(cfg["mouth"]["oral_interior_rgb"], dtype=np.float32)
    b_alb = b_alb * (1.0 - oral_tile_f[:, :, None]) + oral_col[None, None, :] * oral_tile_f[:, :, None]
    b_alb *= (1.0 - 0.14 * np.exp(-((d_eye - eye_r * 1.04) / 0.0055) ** 2)[:, :, None])

    scale_ao = 1.0 - (0.24 * np.clip(-h_scales, 0.0, 1.0) + 0.28 * np.clip(-h_macro, 0.0, 1.0)) * lip_clean_guard
    orbit_ao = 1.0 - 0.40 * np.exp(-((d_eye - eye_r * 1.02) / 0.006) ** 2) - 0.28 * socket_inner
    ao = np.clip(scale_ao * op_ao * orbit_ao * (1.0 - oral_tile_f * 0.45), 0.32, 1.0)
    dorsal_f = smoothstep(0.015, 0.125, Z)
    belly_f = smoothstep(-0.045, -0.140, Z)
    flank_silver = (1.0 - dorsal_f * 0.75) * (1.0 - belly_f * 0.25)
    cobalt = smoothstep(0.01, 0.10, b_alb[:, :, 2] - b_alb[:, :, 1] * 0.92) * smoothstep(-0.02, 0.05, Z)
    snout_mask = 1.0 - smoothstep(0.365, 0.415, X)
    rough = 0.48 + 0.14 * dorsal_f + 0.04 * belly_f - 0.14 * h_scales
    snout_matte = smoothstep(0.355, 0.425, X)
    rough = rough * (1.0 - snout_matte) + np.maximum(rough, 0.72) * snout_matte
    rough = np.clip(rough * (1.0 - cobalt * 0.22) + 0.24 * oral_tile_f + 0.22 * (1.0 - op_ao), 0.34, 0.94)
    metal = np.clip((0.14 * flank_silver * np.clip(0.55 + 0.75 * h_scales, 0.0, 1.0) + 0.22 * cobalt) * snout_mask * op_ao * (1.0 - oral_tile_f) * (1.0 - socket_inner), 0.0, 0.28)

    b_alb_arr = np.ones((S, S, 4), dtype=np.float32)
    b_alb_arr[:, :, :3] = np.clip(b_alb, 0.0, 1.0)
    b_orm_arr = np.ones((S, S, 4), dtype=np.float32)
    b_orm_arr[:, :, 0] = ao; b_orm_arr[:, :, 1] = rough; b_orm_arr[:, :, 2] = metal

    # Stamp stylized pixel-art 3D eye into top-left empty UV tile
    ex0, ex1, ey0, ey1 = 8, 172, 852, 1016
    g = np.linspace(-1.0, 1.0, ex1 - ex0, dtype=np.float32)
    gx, gy = np.meshgrid(g, g)
    er = np.sqrt(gx * gx + gy * gy)
    u_eb = 0.03 + 0.94 * np.clip(((eye_c.x - gx * eye_r * 1.12) - X_MIN) / (X_MAX - X_MIN), 0.0, 1.0)
    v_eb = 0.53 + 0.44 * np.clip(((eye_c.z + gy * eye_r * 1.12) - Z_MIN) / (Z_MAX - Z_MIN), 0.0, 1.0)
    fx = np.clip(u_eb * (S - 1), 0.0, S - 1.001)
    fy = np.clip(v_eb * (S - 1), 0.0, S - 1.001)
    ix0, iy0 = np.floor(fx).astype(np.int32), np.floor(fy).astype(np.int32)
    tx, ty = (fx - ix0)[:, :, None], (fy - iy0)[:, :, None]
    e_smp = ((orig_body_albedo[iy0, ix0] * (1.0 - tx) + orig_body_albedo[iy0, ix0 + 1] * tx) * (1.0 - ty) +
             (orig_body_albedo[iy0 + 1, ix0] * (1.0 - tx) + orig_body_albedo[iy0 + 1, ix0 + 1] * tx) * ty)
    e_lum = 0.299 * e_smp[:, :, 0] + 0.587 * e_smp[:, :, 1] + 0.114 * e_smp[:, :, 2]
    e_pupil = smoothstep(0.24, 0.08, e_lum) * (1.0 - smoothstep(0.42, 0.58, er))
    e_outer = smoothstep(0.84, 0.96, er)
    e_iris = (1.0 - e_pupil) * (1.0 - e_outer)
    e_rgb = np.clip(e_smp * (1.0 + 0.05 * e_iris[:, :, None]), 0.0, 1.0)
    e_rgb = e_rgb * (1.0 - e_outer[:, :, None]) + skin_rim_rgb[None, None, :] * e_outer[:, :, None]
    b_alb_arr[ey0 - 4:ey1 + 4, ex0 - 4:ex1 + 4, :3] = skin_rim_rgb[None, None, :]
    b_alb_arr[ey0:ey1, ex0:ex1, :3] = np.clip(e_rgb, 0.0, 1.0)
    b_nrm_arr[ey0 - 4:ey1 + 4, ex0 - 4:ex1 + 4] = np.array([0.5, 0.5, 1.0, 1.0], dtype=np.float32)
    b_orm_arr[ey0 - 4:ey1 + 4, ex0 - 4:ex1 + 4, :3] = np.array([0.82, 0.62, 0.0], dtype=np.float32)
    b_orm_arr[ey0:ey1, ex0:ex1, 0] = np.clip(1.0 - 0.18 * e_outer, 0.72, 1.0)
    b_orm_arr[ey0:ey1, ex0:ex1, 1] = np.clip(0.22 * e_pupil + 0.32 * e_iris + 0.62 * e_outer, 0.20, 0.66)
    b_orm_arr[ey0:ey1, ex0:ex1, 2] = np.clip(0.05 * e_iris, 0.0, 0.06)

    # Fins 1024x1024 atlas
    f_alb_arr = np.zeros((S, S, 4), dtype=np.float32)
    for lbl, info in fin_uv_maps.items():
        su0, su1, sv0, sv1 = info["src"]
        du0, dv0, dw, dh = info["dst"]
        xs0, xs1 = max(0, int(math.floor(du0 * S))), min(S, int(math.ceil((du0 + dw) * S)))
        ys0, ys1 = max(0, int(math.floor(dv0 * S))), min(S, int(math.ceil((dv0 + dh) * S)))
        if xs1 <= xs0 or ys1 <= ys0:
            continue
        tu = np.clip(((np.arange(xs0, xs1, dtype=np.float32) + 0.5) / S - du0) / max(dw, 1e-6), 0.0, 1.0)
        tv = np.clip(((np.arange(ys0, ys1, dtype=np.float32) + 0.5) / S - dv0) / max(dh, 1e-6), 0.0, 1.0)
        fx = np.clip((su0 + tu * (su1 - su0)) * (aw - 1), 0.0, aw - 1.001)
        fy = np.clip((sv0 + tv * (sv1 - sv0)) * (ah - 1), 0.0, ah - 1.001)
        ix0, iy0 = np.floor(fx).astype(np.int32), np.floor(fy).astype(np.int32)
        tx, ty = (fx - ix0)[None, :, None], (fy - iy0)[:, None, None]
        f_alb_arr[ys0:ys1, xs0:xs1] = (
            (atlas_arr[iy0[:, None], ix0[None, :]] * (1.0 - tx) + atlas_arr[iy0[:, None], ix0[None, :] + 1] * tx) * (1.0 - ty) +
            (atlas_arr[iy0[:, None] + 1, ix0[None, :]] * (1.0 - tx) + atlas_arr[iy0[:, None] + 1, ix0[None, :] + 1] * tx) * ty
        )
    f_alb_arr = dilate_alpha_rgb(f_alb_arr, alpha_thresh=alpha_cutoff, passes=8)
    f_lum = 0.299 * f_alb_arr[:, :, 0] + 0.587 * f_alb_arr[:, :, 1] + 0.114 * f_alb_arr[:, :, 2]
    f_alpha = smoothstep(0.30, 0.75, f_alb_arr[:, :, 3])
    ray_relief = np.clip((gaussian_approx_2d(f_lum, 2) - gaussian_approx_2d(f_lum, 9)) * 5.0, -0.75, 0.85) * f_alpha
    f_nrm_arr = height_to_normal(ray_relief, strength=3.4)
    ray_01 = np.clip(ray_relief * 0.65 + 0.5, 0.0, 1.0)
    f_orm_arr = np.ones((S, S, 4), dtype=np.float32)
    f_orm_arr[:, :, 0] = np.clip(0.86 + 0.14 * ray_01, 0.55, 1.0)
    f_orm_arr[:, :, 1] = np.clip(0.72 - 0.24 * ray_01, 0.42, 0.80)
    f_orm_arr[:, :, 2] = np.clip(0.05 * ray_01, 0.0, 0.07)

    # Combine into unified single-material 2:1 atlas
    atlas_alb = np.concatenate([b_alb_arr, f_alb_arr], axis=1)   # 1024 x 2048
    atlas_nrm = np.concatenate([b_nrm_arr, f_nrm_arr], axis=1)
    atlas_orm = np.concatenate([b_orm_arr, f_orm_arr], axis=1)
    if tier == "small":
        atlas_alb = downsample_2x(atlas_alb, is_normal=False)    # 512 x 1024
        atlas_nrm = downsample_2x(downsample_2x(atlas_nrm, True), True)   # 256 x 512
        atlas_orm = downsample_2x(downsample_2x(atlas_orm, False), False) # 256 x 512
    else:
        atlas_nrm = downsample_2x(atlas_nrm, is_normal=True)     # 512 x 1024
        atlas_orm = downsample_2x(atlas_orm, is_normal=False)    # 512 x 1024

    tag = "".join(p.capitalize() for p in species.split("_"))
    img_alb = create_packed_image(f"{tag}_PBR_Albedo", atlas_alb, (tex_dir / "fish_albedo.png") if tex_dir else None, "sRGB", has_alpha=True)
    img_nrm = create_packed_image(f"{tag}_PBR_Normal", atlas_nrm, (tex_dir / "fish_normal.png") if tex_dir else None, "Non-Color", has_alpha=False)
    img_orm = create_packed_image(f"{tag}_PBR_ORM", atlas_orm, (tex_dir / "fish_orm.png") if tex_dir else None, "Non-Color", has_alpha=False)

    # Shift UVs into left (Body+Eye) and right (Fins) halves
    for obj_left in (body_obj, eye_obj):
        for l_uv in obj_left.data.uv_layers["UVMap"].data:
            l_uv.uv.x *= 0.5
    for l_uv in fin_obj.data.uv_layers["UVMap"].data:
        l_uv.uv.x = 0.5 + l_uv.uv.x * 0.5

    mat = make_single_pbr_material(f"{tag}_PBR", img_alb, img_nrm, img_orm, alpha_cutoff=alpha_cutoff, double_sided=True, normal_strength=0.93)
    body_obj.data.materials.append(mat)
    eye_obj.data.materials.append(mat)
    fin_obj.data.materials.append(mat)

    body_tris = sum(len(p.vertices) - 2 for p in body_obj.data.polygons)
    eye_tris = sum(len(p.vertices) - 2 for p in eye_obj.data.polygons)
    fin_tris = sum(len(p.vertices) - 2 for p in fin_obj.data.polygons)
    orig_mesh_name = orig_obj.name

    bpy.data.objects.remove(orig_obj, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    body_obj.select_set(True); eye_obj.select_set(True); fin_obj.select_set(True)
    bpy.context.view_layer.objects.active = body_obj
    bpy.ops.object.join()

    final_obj = bpy.context.view_layer.objects.active
    final_obj.name = orig_mesh_name
    final_obj.data.name = f"{tag}_PBR_Mesh"
    final_obj.parent = armature
    mod = final_obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = armature

    keep_imgs = {img_alb.name, img_nrm.name, img_orm.name}
    for img in list(bpy.data.images):
        if img.name not in keep_imgs and img.users == 0:
            bpy.data.images.remove(img)

    if out_blend:
        out_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))

    out_glb.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    final_obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(out_glb),
        export_format="GLB",
        use_selection=True,
        export_texcoords=True,
        export_normals=True,
        export_tangents=True,
        export_materials="EXPORT",
        export_skins=True,
        export_animations=True,
        export_yup=True,
    )

    print("UPGRADE_FISH_PBR_OK " + json.dumps({
        "species": species,
        "mode": "sculpt_pbr",
        "tier": tier,
        "albedo_size": [atlas_alb.shape[1], atlas_alb.shape[0]],
        "normal_orm_size": [atlas_nrm.shape[1], atlas_nrm.shape[0]],
        "body_tris": body_tris,
        "eye_tris": eye_tris,
        "fin_tris": fin_tris,
        "total_tris": body_tris + eye_tris + fin_tris,
        "verts": len(final_obj.data.vertices),
        "draw_calls": 1,
        "alpha_cutoff": alpha_cutoff,
        "glb_kb": out_glb.stat().st_size // 1024,
        "glb_path": str(out_glb),
    }))


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="Universal Single-Material PBR Fish Upgrade Pipeline")
    p.add_argument("--species", required=True)
    p.add_argument("--mode", choices=["fast_pbr", "sculpt_pbr"], default="fast_pbr")
    p.add_argument("--config", type=str, default=None, help="Species JSON config (required for sculpt_pbr)")
    p.add_argument("--tier", choices=["large", "small"], default="large")
    p.add_argument("--alpha-cutoff", type=float, default=0.5)
    p.add_argument("--out-glb", required=True)
    p.add_argument("--out-blend", default=None)
    p.add_argument("--tex-dir", default=None)
    return p.parse_args(argv)


def main():
    args = parse_args()
    out_glb = Path(args.out_glb).resolve()
    out_blend = Path(args.out_blend).resolve() if args.out_blend else None
    tex_dir = Path(args.tex_dir).resolve() if args.tex_dir else None
    if args.mode == "fast_pbr":
        run_fast_pbr(args.species, args.tier, args.alpha_cutoff, out_glb, out_blend, tex_dir)
    else:
        if not args.config:
            raise ValueError("--config <species.json> is required for --mode sculpt_pbr")
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        cutoff = float(cfg.get("alpha_cutoff", args.alpha_cutoff))
        run_sculpt_pbr(cfg, args.tier, cutoff, out_glb, out_blend, tex_dir)


if __name__ == "__main__":
    main()
