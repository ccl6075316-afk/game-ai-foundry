"""Blender numeric audit of newly intersecting triangle pairs in actual Godot LOD poses."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from mathutils.bvhtree import BVHTree
import numpy as np


class Surface:
    def __init__(self, row, name, index, vertex_offset, mesh_index):
        self.name = name
        self.index = index
        self.mesh_index = mesh_index
        self.offset = vertex_offset
        self.positions = np.asarray(row["positions"], dtype=np.float32).reshape(-1, 3)
        self.weights = np.asarray(row["weights"], dtype=np.float32).reshape(len(self.positions), -1)
        self.joints = np.asarray(row["joints"], dtype=int).reshape(self.weights.shape)
        self.morphs = np.asarray(row["morphs"], dtype=np.float32).reshape(-1, len(self.positions) * 3)
        self.levels = [np.asarray(row["triangles"], dtype=int).reshape(-1, 3)]
        self.thresholds = [0.0]
        for threshold, packed in row["tiers"]:
            data = np.frombuffer(
                base64.b64decode(packed, validate=True), "<u2" if row["index_width"] == 2 else "<u4"
            )
            self.levels.append(data.astype(int).reshape(-1, 3))
            self.thresholds.append(threshold)
        if any(t.min() < 0 or t.max() >= len(self.positions) for t in self.levels):
            raise ValueError(f"Invalid surface indices: {name}/{index}")
        self.homogeneous = np.ones((len(self.positions), 4), dtype=np.float32)
        self.homogeneous[:, :3] = self.positions

    def skin(self, palette, morph):
        positions = self.homogeneous
        if len(morph):
            positions = positions.copy()
            positions[:, :3] += np.einsum("m,mv->v", morph, self.morphs).reshape(-1, 3)
        if self.weights.shape[1] == 0:
            return positions @ palette[0].T
        out = np.zeros_like(self.positions)
        for lane in range(self.weights.shape[1]):
            weights = self.weights[:, lane]
            use = weights > 0
            matrix = palette[self.joints[use, lane]]
            out[use] += np.einsum("vij,vj->vi", matrix, positions[use]) * weights[use, np.newaxis]
        return out


class Fish:
    def __init__(self, path):
        self.input = json.loads(path.read_text())
        self.poses = self.input["poses"]
        self.surfaces = []
        self.palette_spans = []
        offset = vertex_offset = 0
        for i, mesh in enumerate(self.input["mesh"]):
            binds = max(1, len(mesh["bindings"]))
            end = offset + binds * 12
            morph_end = end + mesh["morph_count"]
            self.palette_spans.append((offset, end, morph_end))
            offset = morph_end
            for si, data in enumerate(mesh["surfaces"]):
                surface = Surface(data, mesh["name"], si, vertex_offset, i)
                self.surfaces.append(surface)
                vertex_offset += len(surface.positions)
        self.palette = np.memmap(
            path.with_suffix(".f32"), dtype="<f4", mode="r", shape=(len(self.poses), offset)
        )
        if self.palette.nbytes != path.with_suffix(".f32").stat().st_size:
            raise ValueError("Unexpected pose stream size")
        if not np.all(np.isfinite(self.palette)):
            raise ValueError("Non-finite entries in the native pose stream")

    def posed(self, index):
        row = self.palette[index]
        mats = [(row[a:b].reshape(-1, 3, 4), row[b:c]) for a, b, c in self.palette_spans]
        return np.concatenate([s.skin(*mats[s.mesh_index]) for s in self.surfaces])


def collect_tiers(fish):
    # Unique active combinations at every stored threshold in addition to full detail.
    thresholds = sorted({step for surface in fish.surfaces for step in surface.thresholds})
    for threshold in thresholds[1:]:
        all_faces, new_faces, origin = [], [], []
        for surface in fish.surfaces:
            level = max(i for i, step in enumerate(surface.thresholds) if step <= threshold)
            faces = surface.levels[level]
            base = {tuple(row) for row in surface.levels[0]}
            added = np.array([tuple(row) not in base for row in faces])
            all_faces.extend((faces + surface.offset).tolist())
            new_faces.extend(added.tolist())
            origin.extend((surface.name, surface.index, tuple(row)) for row in faces)
        yield threshold, np.asarray(all_faces), np.asarray(new_faces), origin


def audit(fish, stride):
    # Also compare each surface's new faces against all faces from the original
    # level and all available lower levels of every other surface. Godot
    # evaluates surface-node distance independently.
    unified = {}
    for surface in fish.surfaces:
        base = {tuple(row) for row in surface.levels[0]}
        for level in surface.levels:
            for row in level:
                key = tuple(row + surface.offset)
                unified[key] = (tuple(row) not in base, surface.name, surface.index, tuple(row))
    faces = np.asarray(list(unified))
    face_rows = list(unified.values())
    added_ids = [i for i, row in enumerate(face_rows) if row[0]]
    added_faces = faces[added_ids].tolist()
    all_faces = faces.tolist()
    hit_count = Counter()
    example = {}
    overlap_poses = 0
    cache = {}
    tiers = list(collect_tiers(fish))
    global_ids = {key: i for i, key in enumerate(unified)}
    changed_surfaces = {row[1:3] for row in face_rows if row[0]}
    for index in range(0, len(fish.poses), stride):
        points = fish.posed(index)
        key = hashlib.sha256(points.tobytes()).digest()
        if key not in cache:
            xy = points.tolist()
            whole = BVHTree.FromPolygons(xy, all_faces, all_triangles=True)
            replacement = BVHTree.FromPolygons(xy, added_faces, all_triangles=True)
            hits = set()
            for new_at, other in replacement.overlap(whole):
                i = added_ids[new_at]
                lhs, rhs = face_rows[i], face_rows[other]
                if i == other:
                    continue
                # Same-surface alternatives never coexist. Their complement
                # is checked against the actual selected topology below.
                if lhs[1:3] == rhs[1:3]:
                    continue
                if any(
                    np.linalg.norm(points[a] - points[b]) <= 0.000002 for a in faces[i] for b in faces[other]
                ):
                    continue
                hits.add(i)
                if rhs[0]:
                    hits.add(other)
            for threshold, selected, changed, origin in tiers:
                equivalent = [j for j in np.where(changed)[0] if origin[j][:2] in changed_surfaces]
                if not equivalent:
                    continue
                body = BVHTree.FromPolygons(xy, selected.tolist(), all_triangles=True)
                delta = BVHTree.FromPolygons(xy, selected[equivalent].tolist(), all_triangles=True)
                for new_at, j in delta.overlap(body):
                    i = equivalent[new_at]
                    if origin[i][:2] != origin[j][:2] or i == j:
                        continue
                    if any(
                        np.linalg.norm(points[a] - points[b]) <= 0.000002
                        for a in selected[i]
                        for b in selected[j]
                    ):
                        continue
                    hits.add(global_ids[tuple(selected[i])])
                    if changed[j]:
                        hits.add(global_ids[tuple(selected[j])])
            cache[key] = hits
        hits = cache[key]
        overlap_poses += bool(hits)
        for face in hits:
            hit_count[face] += 1
            example.setdefault(face, (*fish.poses[index], index))
    unsafe_faces = []
    for face, count in hit_count.most_common():
        row = face_rows[face]
        unsafe_faces.append(
            {
                "mesh": row[1],
                "surface": row[2],
                "face": [int(x) for x in row[3]],
                "poses": count,
                "example": example[face],
            }
        )
    return {
        "samples": len(range(0, len(fish.poses), stride)),
        "distinct_poses": len(cache),
        "added_triangles": len(added_ids),
        "affected_poses": overlap_poses,
        "introduced_intersection_faces": unsafe_faces,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stride", type=int, default=1)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fish = Fish(args.input)
    data = audit(fish, args.stride)
    result = {
        "ok": not data["introduced_intersection_faces"],
        "species": fish.input["species"],
        "model_sha256": fish.input["model_sha256"],
        "lod_sha256": fish.input["lod_sha256"],
        "controller_sha256": fish.input["controller_sha256"],
        **data,
        "scope": "New triangles tested for BVH triangle intersection in actual Godot-skinned and morphed shapes. Pairs meeting at an existing welded vertex are excluded. This gate measures intersections. Root signed-distance and membrane sampling are separate.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        result["species"],
        result["samples"],
        result["affected_poses"],
        len(result["introduced_intersection_faces"]),
    )


if __name__ == "__main__":
    main()
