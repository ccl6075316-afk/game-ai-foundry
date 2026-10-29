"""Bounded Nile whole-fish reduction probe; never installs a game asset.

This tests whether the saved B-fin candidate can fit a complete fish budget.
The dense body is reduced only as a visual comparator; a production B body
must be reconstructed from accepted contours and measured sections.
This diagnostic deviated from the user's selected B route and was rejected.
"""

import bpy
import bmesh
import hashlib
import json
import sys
from pathlib import Path

if "--reproduce-rejected-A-route" not in sys.argv:
    raise SystemExit("Rejected A-route diagnostic; continue the selected B route instead.")


repo = Path(__file__).resolve().parents[3]
game = repo / "projects" / "fishing-2d"
trial = game / "experiments" / "nile-dorsal-route-trial"
source = trial / "round2" / "fins-candidate.blend"
output = trial / "round3-whole-budget-probe"
assert source.is_file() and output.parent.is_dir()
assert hashlib.sha256(source.read_bytes()).hexdigest() == (
    "e5d5364e8768487765baac4c7df4a2ba9e2b035e9e7b5aba035dcb8050406bc4"
)

targets = {
    "Closed_body": 920,
    "Dorsal": 150,
    "Anal": 80,
    "Caudal": 110,
    "Pectoral_left": 45,
    "Pectoral_right": 45,
    "Pelvic_left": 35,
    "Pelvic_right": 35,
}
assert sum(targets.values()) == 1420
output.mkdir(exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.preferences.filepaths.save_version = 0
original = {o.name: len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH"}
assert set(original) == set(targets) | {
    "Eye_relief112_-1_0", "Eye_relief112_1_0"
}

# Original source artwork already carries flat eye pixels. Remove only the
# raised eye geometry for this probe; face color continuity remains for review.
for name in ("Eye_relief112_-1_0", "Eye_relief112_1_0"):
    bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

counts = {}
checks = {}
for name, target in targets.items():
    obj = bpy.data.objects[name]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new("budget-probe", "DECIMATE")
    modifier.ratio = min(1.0, target / len(obj.data.polygons))
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = obj.data
    mesh.calc_loop_triangles()
    counts[name] = len(mesh.loop_triangles)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    checks[name] = {
        "vertices": len(mesh.vertices),
        "triangles": counts[name],
        "nonmanifold_edges": sum(not edge.is_manifold for edge in bm.edges),
        "zero_area_faces": sum(face.calc_area() <= 1e-13 for face in bm.faces),
        "uv_layers": len(mesh.uv_layers),
        "weighted_vertices": sum(
            bool(vertex.groups) for vertex in mesh.vertices
        ),
    }
    bm.free()

total = sum(counts.values())
assert total <= 1500, (total, counts)
blend_path = output / "whole-1500-probe.blend"
glb_path = output / "whole-1500-probe.glb"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=str(glb_path),
    export_format="GLB",
    use_selection=True,
    export_skins=True,
    export_animations=True,
)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = {
    "kind": "nile_whole_budget_probe",
    "ok": checks["Closed_body"]["nonmanifold_edges"] == 0
    and all(row["zero_area_faces"] == 0 for row in checks.values()),
    "formal_acceptance": False,
    "installed": False,
    "method": "Existing B fins reduced; old body collapse is a budget and visual comparator, not final B construction.",
    "source_blend": str(source.relative_to(game)).replace("\\", "/"),
    "source_sha256": sha(source),
    "original_counts": original,
    "target_counts": targets,
    "actual_counts": counts,
    "actual_whole_fish_triangles": total,
    "flat_eyes": True,
    "checks": checks,
    "outputs": {
        "blend": {"path": blend_path.name, "sha256": sha(blend_path)},
        "glb": {"path": glb_path.name, "sha256": sha(glb_path)},
    },
    "pending": [
        "B-route body source construction",
        "source silhouette and all-view review",
        "fin root and free membrane motion gates",
        "static texture and shader migration",
        "Godot cold load and complete SOP gate",
    ],
}
(output / "whole-1500-probe.validation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
)
print(json.dumps(report, ensure_ascii=False))
if not report["ok"]:
    raise SystemExit(1)
