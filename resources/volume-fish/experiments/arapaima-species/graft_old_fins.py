"""Controlled comparison: new species body/head with fins from the accepted game mesh."""

import sys
from pathlib import Path

import bpy


new_glb, accepted_glb, output_dir = [Path(v).resolve() for v in sys.argv[sys.argv.index("--") + 1:]]
output_dir.mkdir(parents=True, exist_ok=True)
fin_names = {"Dorsal", "Anal", "Caudal", "Pectoral_left", "Pectoral_right", "Pelvic_left", "Pelvic_right"}

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(accepted_glb))
bpy.context.scene.frame_set(0)
depsgraph = bpy.context.evaluated_depsgraph_get()
fin_meshes = []
for name in sorted(fin_names):
    source = bpy.data.objects[name]
    evaluated = source.evaluated_get(depsgraph)
    data = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
    data.transform(evaluated.matrix_world)
    fin_meshes.append((name, data))

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(new_glb))
clay = bpy.data.materials.get("Neutral form study")
for name in fin_names:
    bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
for name, data in fin_meshes:
    fin = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(fin)
    data.materials.clear()
    data.materials.append(clay)

bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "arapaima-new-body-old-fins.blend"))
bpy.ops.export_scene.gltf(filepath=str(output_dir / "arapaima-new-body-old-fins.glb"),
                          export_format="GLB", export_animations=False)
