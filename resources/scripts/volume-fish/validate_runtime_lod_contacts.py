"""Check the complete frozen root band and both sides of each posed fin membrane."""

from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
import hashlib
from itertools import product
import json
from pathlib import Path
import sys

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_fin_membrane_collision import basal_edge_distance
from check_runtime_lod_contacts import Fish

BODY = "body"
AUX = "aux"
RAY_DIRECTION = Vector((0.231, 0.371, 0.899)).normalized()
MEMBRANE_BARYCENTRIC = np.array(
    [
        [1 / 3, 1 / 3, 1 / 3],
        [0.6, 0.2, 0.2],
        [0.2, 0.6, 0.2],
        [0.2, 0.2, 0.6],
    ]
)
ROOT_FRACTIONS = np.arange(1, 8) / 8
MEMBRANE_FRACTIONS = [0.25, 0.5, 0.75]


def edge_points(vertices, edges, fractions):
    corners = vertices[edges]
    ratios = np.asarray(fractions)[None, :, None]
    return (corners[:, 0:1] * (1 - ratios) + corners[:, 1:2] * ratios).reshape(-1, 3)


class Patch:
    def __init__(self, faces, roots=()):
        self.faces = np.asarray(faces, dtype=int).reshape(-1, 3)
        if not len(self.faces):
            raise ValueError("Empty surface")
        self.key = self.faces.tobytes()
        self.vertices = np.unique(self.faces)
        self.root_vertices = np.intersect1d(self.vertices, roots).astype(int)
        self.edges = np.unique(
            np.sort(
                np.concatenate(
                    [
                        self.faces[:, [0, 1]],
                        self.faces[:, [1, 2]],
                        self.faces[:, [0, 2]],
                    ]
                ),
                axis=1,
            ),
            axis=0,
        )
        self.root_edges = self.edges[np.all(np.isin(self.edges, self.root_vertices), axis=1)]
        self.root_faces = self.faces[np.all(np.isin(self.faces, self.root_vertices), axis=1)]

    def root_samples(self, vertices):
        return np.concatenate(
            [
                vertices[self.root_vertices],
                edge_points(vertices, self.root_edges, ROOT_FRACTIONS),
            ]
        ).tolist()

    def membrane_samples(self, vertices):
        return np.concatenate(
            [
                vertices[self.vertices],
                (MEMBRANE_BARYCENTRIC @ vertices[self.faces]).reshape(-1, 3),
                edge_points(vertices, self.edges, MEMBRANE_FRACTIONS),
            ]
        ).tolist()

    def root_support(self, vertices):
        points = KDTree(len(self.root_vertices))
        for index, vertex in enumerate(self.root_vertices):
            points.insert(vertices[vertex], index)
        points.balance()
        faces = (
            BVHTree.FromPolygons(vertices, self.root_faces.tolist(), all_triangles=True)
            if len(self.root_faces)
            else None
        )
        edges = [(vertices[a], vertices[b]) for a, b in self.root_edges]
        return points, faces, edges


def label_levels(fish, domain):
    rest = np.concatenate([s.positions for s in fish.surfaces])
    low, high = rest[:, 0].min(), rest[:, 0].max()
    mixed, lost_mouth_faces, labels = [], [], []
    for surface, record in zip(fish.surfaces, domain["surfaces"], strict=True):
        if (surface.name, surface.index) != (record["mesh"], record["surface"]):
            raise ValueError("Contact domain surface order changed")
        owners = dict(zip(map(tuple, surface.levels[0]), record["parts"], strict=True))
        vertex_owners = defaultdict(set)
        for face, part in owners.items():
            for vertex in face:
                vertex_owners[vertex].add(part)

        x = (surface.positions[:, 0] - low) / (high - low)
        mouth = x < 0.16 if fish.input["species"] == "whale_shark" else x > 0.74
        joints = fish.input["mesh"][surface.mesh_index]["bindings"]
        oral = np.array(
            [any(word in name.lower() for word in ("jaw", "oral", "feeding_head")) for name in joints]
        )
        if oral.size and surface.weights.shape[1]:
            mouth |= np.any(oral[surface.joints] & (surface.weights > 0), axis=1)
        if surface.morphs.size:
            mouth |= np.any(surface.morphs.reshape(len(surface.morphs), -1, 3) != 0, axis=(0, 2))
        held = {
            face for face, part in owners.items() if part in (BODY, AUX) and np.any(mouth[np.asarray(face)])
        }
        level_labels = [record["parts"]]
        for index, tier in enumerate(surface.levels[1:], 1):
            removed = held.difference(map(tuple, tier))
            if removed:
                lost_mouth_faces.append([surface.name, surface.index, index, len(removed)])
            tier_labels = []
            for face in tier:
                owner = owners.get(tuple(face))
                if owner is None:
                    candidates = set.intersection(*(vertex_owners[v] for v in face))
                    if len(candidates) != 1:
                        mixed.append([surface.name, surface.index, index, face.tolist()])
                    owner = next(iter(candidates)) if len(candidates) == 1 else BODY
                tier_labels.append(owner)
            level_labels.append(tier_labels)
        labels.append(level_labels)
    return labels, mixed, lost_mouth_faces


def make_stages(fish, labels, roots):
    stages = []
    thresholds = sorted({step for surface in fish.surfaces for step in surface.thresholds})
    for threshold in thresholds:
        parts = defaultdict(list)
        for surface, owners in zip(fish.surfaces, labels, strict=True):
            index = max(i for i, step in enumerate(surface.thresholds) if step <= threshold)
            for face, part in zip(surface.levels[index] + surface.offset, owners[index], strict=True):
                parts[part].append(face)
        body = Patch(parts.pop(BODY))
        parts.pop(AUX, None)
        if set(parts) != set(roots):
            raise ValueError("Incomplete fin inventory after simplification")
        fins = {name: Patch(faces, roots[name]["points"]) for name, faces in parts.items()}
        if any(not len(patch.root_vertices) for patch in fins.values()):
            raise ValueError("A tier removed an entire basal band")
        stages.append((body, fins))
    return thresholds, stages


def body_probe_plan(fish, domain):
    labels, mixed, _ = label_levels(fish, domain)
    if mixed:
        raise ValueError("Cannot make a body GPU probe for mixed-part faces")
    thresholds = sorted({step for surface in fish.surfaces for step in surface.thresholds})
    variants = []
    for threshold in thresholds:
        nodes = defaultdict(dict)
        for surface, levels in zip(fish.surfaces, labels, strict=True):
            index = max(i for i, step in enumerate(surface.thresholds) if step <= threshold)
            mask = np.asarray(levels[index]) == BODY
            faces = surface.levels[index][mask]
            if len(faces):
                width = fish.input["mesh"][surface.mesh_index]["surfaces"][surface.index]["index_width"]
                data = faces.astype("<u2" if width == 2 else "<u4").tobytes()
                nodes[surface.name][surface.index] = base64.b64encode(data).decode()
        if nodes not in variants:
            variants.append(nodes)
    return {
        "model_sha256": fish.input["model_sha256"],
        "lod_sha256": fish.input["lod_sha256"],
        "variants": variants,
    }


def make_jobs(stages, independent):
    # Different MeshInstances can use different projected-distance thresholds.
    # Each body/fin pair is sufficient because the check measures fin vs body.
    jobs = {}
    tested = defaultdict(set)
    for index, (body, fins) in enumerate(stages):
        jobs.setdefault(body.key, (body, []))
        for name, fin in fins.items():
            pair = (body.key, fin.key)
            if pair not in tested[name]:
                jobs[body.key][1].append((str(index), name, fin))
                tested[name].add(pair)

    if independent:
        body_options = {body.key: i for i, (body, _) in reversed(list(enumerate(stages)))}
        for name in stages[0][1]:
            options = {fins[name].key: (i, fins[name]) for i, (_, fins) in reversed(list(enumerate(stages)))}
            for (body_key, body_stage), (fin_key, (fin_stage, fin)) in product(
                body_options.items(), options.items()
            ):
                if (body_key, fin_key) not in tested[name]:
                    jobs[body_key][1].append((f"body{body_stage}-fin{fin_stage}", name, fin))
    return list(jobs.values())


def exceptional_edges(fish, body):
    # Compare the complete oriented welded incidence against the approved near mesh.
    rest = np.concatenate([s.positions for s in fish.surfaces])
    _, weld = np.unique(np.round(rest, 7), axis=0, return_inverse=True)
    counts = Counter()
    for a, b, c in weld[body.faces]:
        counts.update(((a, b), (b, c), (c, a)))
    return {edge: val for edge, val in counts.items() if val != 1 or counts[edge[::-1]] != 1}


def root_distance(samples, body, gap, embedding):
    low, high = float("inf"), float("-inf")
    failures = 0
    witnesses = set()
    for xyz in samples:
        point = Vector(xyz)
        near, normal, face, distance = body.find_nearest(point)
        signed = distance if (point - near).dot(normal) >= 0 else -distance
        low, high = min(low, signed), max(high, signed)
        if signed < -embedding or signed > gap:
            failures += 1
            witnesses.add(face)
    return failures, low, high, witnesses


def membrane_distance(samples, bounds, body, support, collar, penetration):
    root_points, root_faces, root_edges = support
    low, high = bounds
    failures, worst = 0, 0.0
    witnesses = set()
    for xyz in samples:
        x, y, z = xyz
        if x < low[0] or x > high[0] or y < low[1] or y > high[1] or z < low[2] or z > high[2]:
            continue
        point = Vector(xyz)
        hit, normal, ray_face, _ = body.ray_cast(point, RAY_DIRECTION)
        if hit is None or normal.dot(RAY_DIRECTION) <= 0:
            continue
        _, _, near_face, distance = body.find_nearest(point)
        if distance <= penetration:
            continue
        if distance <= collar:
            if root_points.find(point)[2] <= collar:
                continue
            if root_faces and root_faces.find_nearest(point, collar)[0] is not None:
                continue
            if basal_edge_distance(point, root_edges) <= collar:
                continue
        failures += 1
        worst = min(worst, -distance)
        witnesses.update((near_face, ray_face))
    return failures, worst, witnesses


def accumulate(summary, key, count, distance, index, pose):
    row = summary.setdefault(key, {"fail_samples": 0, "fail_poses": 0, "minimum_m": 0.0, "example_poses": []})
    row["minimum_m"] = min(row["minimum_m"], float(distance))
    if count:
        row["fail_samples"] += count
        row["fail_poses"] += 1
        if len(row["example_poses"]) < 3:
            row["example_poses"].append([index, *pose])
    return row


def validate(fish, domain, stride, gap, embedding, collar, penetration):
    labels, mixed, mouth = label_levels(fish, domain)
    thresholds, stages = make_stages(fish, labels, domain["roots"])
    original_body, original_fins = stages[0]
    incomplete_roots = []
    baseline_edges = exceptional_edges(fish, original_body)
    changed_boundaries = []
    for i, (body, fins) in enumerate(stages[1:], 1):
        if exceptional_edges(fish, body) != baseline_edges:
            changed_boundaries.append(i)
        for name, fin in fins.items():
            original = original_fins[name]
            for field in ("root_vertices", "root_edges"):
                if not np.array_equal(getattr(fin, field), getattr(original, field)):
                    incomplete_roots.append([i, name, field])
            if set(map(tuple, fin.root_faces)) != set(map(tuple, original.root_faces)):
                incomplete_roots.append([i, name, "root_faces"])
    jobs = make_jobs(stages, independent=len(fish.input["mesh"]) > 1)
    summary = defaultdict(dict)
    witness = defaultdict(set)
    pose_count = 0
    for index in range(0, len(fish.poses), stride):
        pose_count += 1
        vertices = fish.posed(index)
        vectors = [Vector(row) for row in vertices.tolist()]
        supports = {name: fin.root_support(vectors) for name, fin in original_fins.items()}
        for body, checks in jobs:
            coords = vertices[body.faces]
            volume = np.einsum("ij,ij->", coords[:, 0], np.cross(coords[:, 1], coords[:, 2])) / 6
            if abs(volume) < 1e-9:
                raise ValueError(f"Zero oriented body volume at pose {index}")
            faces = body.faces if volume > 0 else body.faces[:, ::-1]
            tree = BVHTree.FromPolygons(vectors, faces.tolist(), all_triangles=True)
            body_points = vertices[body.vertices]
            bounds = ((body_points.min(axis=0) - 1e-8).tolist(), (body_points.max(axis=0) + 1e-8).tolist())
            for stage, name, fin in checks:
                bad, low, high, r = root_distance(fin.root_samples(vertices), tree, gap, embedding)
                row = accumulate(summary[name], f"{stage}:root", bad, low, index, fish.poses[index])
                row["maximum_m"] = max(row.get("maximum_m", 0), float(high))
                bad, low, m = membrane_distance(
                    fin.membrane_samples(vertices), bounds, tree, supports[name], collar, penetration
                )
                accumulate(summary[name], f"{stage}:membrane", bad, low, index, fish.poses[index])
                if r or m:
                    witness[(stage, name)].update(tuple(map(int, f)) for f in body.faces[sorted(r | m)])
        if index % 100 == 0:
            print(fish.input["species"], index, flush=True)
    passed = not (mixed or mouth or incomplete_roots or changed_boundaries or witness)
    return {
        "ok": passed,
        "poses": pose_count,
        "thresholds": thresholds,
        "parts": summary,
        "topology_pair_checks_per_pose": sum(len(checks) for _, checks in jobs),
        "baseline_exceptional_body_directed_edges": len(baseline_edges),
        "changed_boundaries": changed_boundaries,
        "mixed_part_triangles": mixed,
        "lost_protected_mouth_faces": mouth,
        "changed_complete_root_support": incomplete_roots,
        "failed_body_face_witnesses": {str(key): sorted(faces) for key, faces in witness.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("posed", type=Path, help="Native Godot pose JSON with accompanying .f32 palette")
    parser.add_argument("domain", type=Path, help="Current resolved contact domains")
    parser.add_argument("output", type=Path)
    parser.add_argument("--stride", type=int, default=1, help="Diagnostic only. A release uses every pose.")
    parser.add_argument(
        "--body-probe",
        action="store_true",
        help="Export only the actual body arrays for the GPU coverage gate",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.stride < 1:
        parser.error("--stride must be positive")
    fish = Fish(args.posed)
    domain = json.loads(args.domain.read_text())
    if domain["unmapped"] or domain["model_sha256"] != fish.input["model_sha256"]:
        raise ValueError("Incomplete or stale contact domain")
    if args.body_probe:
        args.output.write_text(json.dumps(body_probe_plan(fish, domain)) + "\n")
        return 0
    species = fish.input["species"]
    gap_mm, embedding_mm = (0.5, 0.5) if species == "blacktip_reef_shark" else (1.0, 6.0)
    limits = (gap_mm, embedding_mm, 0.5, 0.02)
    result = validate(fish, domain, args.stride, *(x / 1000 for x in limits))
    result.update(
        species=species,
        model_sha256=fish.input["model_sha256"],
        lod_sha256=fish.input["lod_sha256"],
        controller_sha256=fish.input["controller_sha256"],
        exhibit_sha256=fish.input["exhibit_sha256"],
        domain_sha256=hashlib.sha256(args.domain.read_bytes()).hexdigest(),
        tolerance_mm=dict(zip(("root_gap", "root_embedding", "basal_collar", "membrane"), limits)),
        sampled_stride=args.stride,
        actions=sorted({pose[0] for pose in fish.poses}),
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(species, result["ok"], result["poses"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
