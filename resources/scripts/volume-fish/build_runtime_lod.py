"""Build index-only fish LOD tables from the production ArrayMesh export.

Requires NumPy, SciPy and meshoptimizer v0.25 built as a shared library. The library
is a build-time tool. The game reads only the reviewed index tables.
"""
from __future__ import annotations

import argparse
import base64
import ctypes as c
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

FIN = re.compile(r"^(anal|dorsal|firstdorsal|seconddorsal|pectoral|pelvic|caudal|hairtail_continuous_dorsal)", re.IGNORECASE)
BODY_OR_HEAD = re.compile(r"body|ribbon", re.IGNORECASE)
ARTICULATED_FEATURE = re.compile(r"jaw|oral|fin|pectoral|pelvic|anal|dorsal|caudal|adipose|tail|auxp|feeding_head", re.IGNORECASE)
MEDIUM = (0.68, 0.008, 170)
FAR = (0.38, 0.019, 75)
LOCK_VERTEX = 1
PROTECT_UV_SEAM = 2


class Simplifier:
    def __init__(self, library):
        self.library = c.CDLL(str(library))
        self.simplify = self.library.meshopt_simplifyWithAttributes
        self.simplify.argtypes = [
            c.c_void_p, c.c_void_p, c.c_size_t, c.c_void_p, c.c_size_t,
            c.c_size_t, c.c_void_p, c.c_size_t, c.c_void_p, c.c_size_t,
            c.c_void_p, c.c_size_t, c.c_float, c.c_uint, c.POINTER(c.c_float),
        ]
        self.simplify.restype = c.c_size_t

    def run(self, indices, positions, attributes, weights, locks, target, error):
        result = np.empty_like(indices)
        actual_error = c.c_float()
        # Lock geometric borders and allow compatible wedges to collapse.
        flags = (1 << 0) | (1 << 2) | (1 << 5)
        count = self.simplify(
            result.ctypes.data, indices.ctypes.data, indices.size,
            positions.ctypes.data, len(positions), positions.strides[0],
            attributes.ctypes.data, attributes.strides[0], weights.ctypes.data,
            weights.size, locks.ctypes.data, target, error, flags,
            c.byref(actual_error),
        )
        return result[:count].copy(), float(actual_error.value)


def topology(index, welded):
    triangles = welded[index.reshape(-1, 3)]
    edges = Counter()
    for a, b, d in triangles:
        if a == b or b == d or d == a:
            continue
        for u, v in ((a, b), (b, d), (d, a)):
            edges[tuple(sorted((u, v)))] += 1
    return edges


def face_set(index):
    return {tuple(row) for row in index.reshape(-1, 3)}


def protect_geometry(surface, positions, indices, extent, attachment_positions, is_fin):
    model_positions = np.asarray(surface["model_positions"]).reshape(-1, 3)
    length = extent[1] - extent[0]
    x = (model_positions[:, 0] - extent[0]) / length
    protected = np.asarray(surface["morph"], dtype=bool)
    if not is_fin:
        protected |= (x > 0.74) | (x < 0.075)
    if not is_fin and surface["skin_joints"] and surface["weights"]:
        joint_mask = np.array([bool(ARTICULATED_FEATURE.search(name)) for name in surface["skin_joints"]])
        joint_indices = np.asarray(surface["joints"], dtype=int).reshape(len(positions), -1)
        joint_weights = np.asarray(surface["weights"]).reshape(joint_indices.shape)
        protected |= np.any(joint_mask[joint_indices] & (joint_weights > 0.015), axis=1)

    if len(attachment_positions):
        # Keep the actual body triangles within the near-contact strip of separate fins.
        radius = length * (0.012 if is_fin else 0.003)
        distance, _ = cKDTree(attachment_positions).query(model_positions, distance_upper_bound=radius)
        protected |= np.isfinite(distance)

    triplets = indices.reshape(-1, 3)
    held_faces = triplets[np.any(protected[triplets], axis=1)]
    return held_faces


def surface_levels(simplifier, surface, extent, attachments, is_fin=False, contact_lock=None):
    length = extent[1] - extent[0]
    positions = np.asarray(surface["positions"], dtype=np.float32).reshape(-1, 3)
    indices = np.asarray(surface["indices"], dtype=np.uint32)
    if indices.size < 180:
        return [], {}

    uv = np.asarray(surface["uv"], dtype=np.float32).reshape(-1, 2)
    normals = np.asarray(surface["normals"], dtype=np.float32).reshape(-1, 3)
    if not len(uv) or not len(normals):
        return [], {}
    attributes = np.ascontiguousarray(np.column_stack((uv, normals)), dtype=np.float32)
    weights = np.array([0.30, 0.30, 0.07, 0.07, 0.07], dtype=np.float32)

    _, welded = np.unique(positions, axis=0, return_inverse=True)
    base_edges = topology(indices, welded)
    held_faces = protect_geometry(surface, positions, indices, extent, attachments, is_fin)
    contact_lock = contact_lock or {}
    contact_faces = np.asarray(contact_lock.get("faces", []), dtype=int).reshape(-1, 3)
    if not face_set(contact_faces).issubset(face_set(indices)):
        raise ValueError("Contact support must match the original surface indices")
    held_faces = np.concatenate([held_faces, contact_faces])
    protected_faces = face_set(held_faces.ravel())
    locks = np.zeros(len(positions), dtype=np.uint8)
    held_vertices = np.concatenate([held_faces.ravel(), contact_lock.get("vertices", [])]).astype(int)
    if len(held_vertices) and (held_vertices.min() < 0 or held_vertices.max() >= len(positions)):
        raise ValueError("Contact vertex outside the original surface")
    locks[np.isin(welded, welded[held_vertices])] = LOCK_VERTEX
    base_boundary = {edge: count for edge, count in base_edges.items() if count != 2}
    boundary_vertices = np.array(list(base_boundary), dtype=int).ravel()
    locks[np.isin(welded, boundary_vertices)] = LOCK_VERTEX

    # Keep discontinuous UV wedges on their original side of the chart seam.
    lo = np.full((welded.max() + 1, 2), np.inf)
    hi = np.full_like(lo, -np.inf)
    np.minimum.at(lo, welded, uv)
    np.maximum.at(hi, welded, uv)
    locks[np.max(hi[welded] - lo[welded], axis=1) > 0.012] |= PROTECT_UV_SEAM

    def simplify(ratio, tolerance):
        target = max(3, int(indices.size * ratio / 3) * 3)
        for factor in (1.0, 0.75, 0.5, 0.25, 0.15, 0.08, 0.04):
            reduced, error = simplifier.run(
                indices, positions, attributes, weights, locks, target, tolerance * length * factor,
            )
            edges = topology(reduced, welded)
            boundary = {edge: count for edge, count in edges.items() if count != 2}
            if boundary == base_boundary and protected_faces.issubset(face_set(reduced)):
                return reduced, error
        return indices, 0.0

    far, far_error = simplify(*FAR[:2])
    if far.size >= indices.size:
        return [], {}
    medium, medium_error = simplify(*MEDIUM[:2])
    if medium.size <= far.size:
        # A wide safety margin can produce the same geometry at both limits.
        # Request a less aggressive first step when there is room for one.
        fraction = (indices.size + far.size) / (2 * indices.size)
        medium, medium_error = simplify(fraction, MEDIUM[1])

    tiers = [(far, far_error, FAR[2])]
    if far.size < medium.size < indices.size:
        tiers.insert(0, (medium, medium_error, MEDIUM[2]))
    levels, counts, errors = [], [], []
    for reduced, error, pixels in tiers:
        # Godot uses this geometric error in its projected size calculation.
        # Impose a floor so the transition stays outside inspection distance.
        data = reduced.astype("<u2" if surface["index_width"] == 2 else "<u4").tobytes()
        levels.append([max(length / pixels, error), base64.b64encode(data).decode()])
        counts.append(int(reduced.size // 3))
        errors.append(error)

    return levels, {
        "base": int(indices.size // 3), "protected": len(protected_faces),
        "triangles": counts, "maximum_quadric_errors": errors,
    }


def build(source, simplifier, contact_locks=None):
    contact_locks = contact_locks or {}
    result = {}
    for species, entry in sorted(source.items()):
        meshes = entry["meshes"]
        combined = np.concatenate([s["model_positions"][::3] for surfaces in meshes.values() for s in surfaces])
        extent = [combined.min(), combined.max()]
        body = max(meshes, key=lambda name: sum(len(s["indices"]) for s in meshes[name]))
        if len(meshes) > 1 and not BODY_OR_HEAD.search(body):
            raise ValueError(f"Verify body mesh for {species}: {body}")
        attachments = [
            np.asarray(surface["model_positions"]).reshape(-1, 3)
            for name, surfaces in meshes.items() if name != body
            for surface in surfaces
        ]
        attachments = np.concatenate(attachments) if attachments else np.empty((0, 3))

        rows = {}
        records = {}
        total = sum(len(s["indices"]) // 3 for surfaces in meshes.values() for s in surfaces)

        def add_mesh(name, near_points, is_fin=False):
            for index, surface in enumerate(meshes[name]):
                locked = contact_locks.get(species, {}).get(name, {}).get(str(index))
                levels, record = surface_levels(simplifier, surface, extent, near_points, is_fin, locked)
                if levels:
                    rows.setdefault(name, {})[str(index)] = {
                        "index_sha256": surface["index_sha256"],
                        "vertex_count": len(surface["positions"]) // 3, "levels": levels,
                    }
                    records.setdefault(name, {})[str(index)] = record

        add_mesh(body, attachments)
        removed = sum(r["base"] - r["triangles"][-1] for r in records.get(body, {}).values())
        if removed < total * 0.15:
            body_points = np.concatenate([np.asarray(s["model_positions"]).reshape(-1, 3) for s in meshes[body]])
            for name in meshes:
                if name != body and FIN.match(name):
                    add_mesh(name, body_points, is_fin=True)

        records_flat = [r for surfaces in records.values() for r in surfaces.values()]
        far = total - sum(r["base"] - r["triangles"][-1] for r in records_flat)
        if far >= total:
            raise ValueError(f"No valid simplified surface for {species}")
        result[species] = {
            "sha256": entry["sha256"], "meshes": rows,
            "base_triangles": total, "far_triangles": far, "surfaces": records,
        }
        print(f"{species:24} {total:5} -> {far:5}  {(total - far) / total:5.1%}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--contact-locks", type=Path, help="Additional per-surface vertices selected from posed contact checks")
    args = parser.parse_args()
    source = json.loads(args.input.read_text())
    locks = json.loads(args.contact_locks.read_text()) if args.contact_locks else None
    result = build(source, Simplifier(args.library), locks)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
