"""Check protected face identity and boundaries in the installed Godot LOD data."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

import numpy as np

from build_runtime_lod import face_set, protect_geometry, topology


def model_points(surfaces):
    return np.concatenate([np.asarray(s["model_positions"]).reshape(-1, 3) for s in surfaces])


def verify_fish(entry):
    meshes = entry["meshes"]
    by_mesh = {key: model_points(surfaces) for key, surfaces in meshes.items()}
    combined = np.concatenate(list(by_mesh.values()))
    extent = (combined[:, 0].min(), combined[:, 0].max())
    body = max(meshes, key=lambda name: sum(len(s["indices"]) for s in meshes[name]))
    separate_points = [p for name, p in by_mesh.items() if name != body]
    attachments = np.concatenate(separate_points) if separate_points else np.empty((0, 3))
    surfaces_checked = levels_checked = protected_checks = 0
    for name, surfaces in meshes.items():
        for surface in surfaces:
            levels = surface["installed_lods"]
            if not levels:
                continue
            positions = np.asarray(surface["positions"], dtype=np.float32).reshape(-1, 3)
            indices = np.asarray(surface["indices"], dtype=np.uint32)
            is_fin = name != body
            protected = protect_geometry(
                surface, positions, indices, extent, by_mesh[body] if is_fin else attachments, is_fin,
            )
            protected = face_set(protected.ravel())
            _, welded = np.unique(positions, axis=0, return_inverse=True)
            original_boundary = {edge: count for edge, count in topology(indices, welded).items() if count != 2}
            previous_count = len(indices)
            for packed in levels:
                lod = np.frombuffer(base64.b64decode(packed, validate=True), "<u2" if surface["index_width"] == 2 else "<u4")
                label = f"{name}/{surfaces_checked}/{levels_checked}"
                if lod.size == 0 or lod.size % 3 or lod.size >= previous_count or lod.max() >= len(positions):
                    raise ValueError(f"{label}: invalid simplified indices")
                if not protected.issubset(face_set(lod)):
                    raise ValueError(f"{label}: protected triangle changed")
                boundary = {edge: count for edge, count in topology(lod, welded).items() if count != 2}
                if boundary != original_boundary:
                    raise ValueError(f"{label}: welded boundary changed")
                previous_count = len(lod)
                levels_checked += 1
                protected_checks += len(protected)
            surfaces_checked += 1
    if levels_checked < 2:
        raise ValueError("Expected at least two installed simplification levels")
    return {"surfaces": surfaces_checked, "levels": levels_checked, "protected_triangle_checks": protected_checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installed_input", type=Path)
    parser.add_argument("lod_resource", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    results = {}
    for species, entry in json.loads(args.installed_input.read_text()).items():
        results[species] = {"model_sha256": entry["sha256"], **verify_fish(entry)}
    if len(results) != 28:
        raise ValueError(f"Expected 28 current fish, got {len(results)}")
    report = {
        "ok": True,
        "scope": "Exact index identity of the protected head, mouth, morph, and fin contact triangles selected by the builder, and equality of welded boundaries. Unchanged index and vertex data imply these protected faces deform identically under the same bone/morph pose. This does not measure distances or collisions against changed triangles.",
        "lod_resource_sha256": hashlib.sha256(args.lod_resource.read_bytes()).hexdigest(),
        "fish": results,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
