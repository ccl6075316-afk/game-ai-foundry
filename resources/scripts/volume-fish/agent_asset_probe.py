"""Read-only Blender fish asset summary for external agents."""

import json
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1 :]
if len(args) != 1:
    raise SystemExit("expected exactly one .blend or .glb path")
source = Path(args[0]).resolve()
if not source.is_file() or source.suffix.lower() not in {".blend", ".glb"}:
    raise SystemExit("missing or unsupported asset")

if source.suffix.lower() == ".blend":
    bpy.ops.wm.open_mainfile(filepath=str(source))
else:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))

meshes = []
for obj in sorted(bpy.data.objects, key=lambda x: x.name):
    if obj.type != "MESH":
        continue
    mesh = obj.data
    meshes.append(
        {
            "name": obj.name,
            "vertices": len(mesh.vertices),
            "faces": len(mesh.polygons),
            "uv_layers": len(mesh.uv_layers),
            "material_slots": len(obj.material_slots),
            "weighted_vertices": sum(bool(v.groups) for v in mesh.vertices),
            "armature_modifier": any(m.type == "ARMATURE" for m in obj.modifiers),
        }
    )

armatures = [
    {"name": obj.name, "bones": len(obj.data.bones)}
    for obj in sorted(bpy.data.objects, key=lambda x: x.name)
    if obj.type == "ARMATURE"
]
print(
    "AGENT_FISH_PROBE "
    + json.dumps(
        {
            "engine": "blender",
            "asset": str(source),
            "mesh_count": len(meshes),
            "meshes": meshes,
            "armatures": armatures,
            "actions": sorted(a.name for a in bpy.data.actions),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
)
