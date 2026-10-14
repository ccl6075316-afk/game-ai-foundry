"""Diagnostic graft of the accepted model's front face overlay onto a new mesh."""

import sys
from pathlib import Path

import bpy


new_glb, accepted_glb, target_glb = [Path(v).resolve() for v in sys.argv[sys.argv.index("--") + 1:]]
target_glb.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(accepted_glb))
bpy.context.scene.frame_set(0)
depsgraph = bpy.context.evaluated_depsgraph_get()
source = bpy.data.objects["Frontal_head_overlay"]
evaluated = source.evaluated_get(depsgraph)
overlay_data = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
overlay_data.transform(evaluated.matrix_world)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(new_glb))
overlay = bpy.data.objects.new("Accepted_front_overlay_probe", overlay_data)
bpy.context.collection.objects.link(overlay)
bpy.ops.export_scene.gltf(filepath=str(target_glb), export_format="GLB", export_animations=False)
