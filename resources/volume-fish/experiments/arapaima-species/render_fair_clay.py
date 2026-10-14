"""Render six orthographic clay views of an isolated GLB for visual shape QA."""

import bpy
from mathutils import Vector
from pathlib import Path
import numpy as np
import sys

args = sys.argv[sys.argv.index("--") + 1:]
source = Path(args[0]).resolve()
destination = Path(args[1]).resolve()
destination.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
scene = bpy.context.scene
# The shipped GLB also contains a 2-unit Cube and sphere unrelated to fish
# anatomy. They otherwise shrink the actual fish to ~40% of the review frame.
for extra in [o for o in scene.objects if o.type == "MESH" and o.name in ("Cube", "棱角球")]:
    bpy.data.objects.remove(extra, do_unlink=True)
scene.frame_set(0)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = False

world = bpy.data.worlds.new("QA neutral")
world.use_nodes = True
background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
background.inputs[0].default_value = (0.12, 0.16, 0.2, 1)
background.inputs[1].default_value = 0.8
scene.world = world

clay = bpy.data.materials.new("QA clay")
clay.diffuse_color = (0.66, 0.68, 0.64, 1)
if len(args) < 3 or args[2] != "zones":
    scene.view_layers[0].material_override = clay

points = [o.matrix_world @ Vector(corner) for o in scene.objects if o.type == "MESH" for corner in o.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
center = (low + high) * 0.5
span = max(high - low)
mesh_vertices = np.array([tuple(o.matrix_world @ v.co) for o in scene.objects if o.type == "MESH" for v in o.data.vertices])
horizontal = mesh_vertices[:, :2]
_, eigenvectors = np.linalg.eigh(np.cov(horizontal.T))
long_axis = Vector((float(eigenvectors[0, -1]), float(eigenvectors[1, -1]), 0)).normalized()
side_axis = Vector((-long_axis.y, long_axis.x, 0))

cam_data = bpy.data.cameras.new("QA camera")
cam = bpy.data.objects.new("QA camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = "ORTHO"

light_data = bpy.data.lights.new("QA softbox", "AREA")
light_data.energy = 100
light_data.size = span * 3
light = bpy.data.objects.new("QA softbox", light_data)
scene.collection.objects.link(light)
light.location = center + Vector((-span, -span, 2 * span))
light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
fill_data = bpy.data.lights.new("QA fill", "AREA")
fill_data.energy = 100
fill_data.size = span * 3
fill = bpy.data.objects.new("QA fill", fill_data)
scene.collection.objects.link(fill)
fill.location = center + Vector((span, span, span))
fill.rotation_euler = (center - fill.location).to_track_quat("-Z", "Y").to_euler()

views = {
    "end_plus": long_axis, "end_minus": -long_axis,
    "side_plus": side_axis, "side_minus": -side_axis,
    "top": (0, 0, 1), "bottom": (0, 0, -1),
    "oblique_plus": long_axis + side_axis + Vector((0, 0, .35)),
    "oblique_minus": -long_axis + side_axis + Vector((0, 0, .35)),
}
for name, direction in views.items():
    cam.location = center + Vector(direction).normalized() * span * 3
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    projected = [cam.matrix_world.inverted() @ p for p in points]
    extent_x = max(p.x for p in projected) - min(p.x for p in projected)
    extent_y = max(p.y for p in projected) - min(p.y for p in projected)
    cam_data.ortho_scale = max(extent_x, extent_y) * 1.15
    scene.render.filepath = str(destination / f"{name}.png")
    bpy.ops.render.render(write_still=True)

print(f"CLAY_REPORT {{'source': '{source}', 'bbox': {tuple(round(x, 5) for x in high - low)}, 'axis': {tuple(round(x, 5) for x in long_axis)}}}")
