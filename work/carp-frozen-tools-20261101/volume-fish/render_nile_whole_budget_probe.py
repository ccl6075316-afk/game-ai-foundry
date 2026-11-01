"""Render fixed-camera clay comparison for the Nile whole-fish budget probe."""

import bpy
import sys
from pathlib import Path
from mathutils import Vector


repo = Path(__file__).resolve().parents[3]
trial = repo / "projects/fishing-2d/experiments/nile-dorsal-route-trial"
out = trial / "round3-whole-budget-probe"
assert out.is_dir()
sources = {
    "baseline": trial / "round2/fins-candidate.blend",
    "sourcefin1500": out / "whole-1500-source-fin-probe.blend",
}
textured = "--textured" in sys.argv
views = {
    "side": ((0.07, -2.0, 0.0), 1.12),
    "front": ((2.0, 0.0, 0.0), 0.56),
    "oblique": ((1.55, -1.55, 0.62), 1.16),
}
for label, source in sources.items():
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    if textured:
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.image_settings.color_mode = "RGBA"
        light_data = bpy.data.lights.new("budget_probe_light", "AREA")
        light_data.energy = 700
        light_data.shape = "DISK"
        light_data.size = 3
        light = bpy.data.objects.new("budget_probe_light", light_data)
        scene.collection.objects.link(light)
        light.location = (0.3, -1.0, 1.6)
    else:
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "SINGLE"
        scene.display.shading.single_color = (0.7, 0.73, 0.7)
        scene.display.shading.show_cavity = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 620
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.045, 0.055, 0.065)
    camera_data = bpy.data.cameras.new("budget_probe_camera")
    camera = bpy.data.objects.new("budget_probe_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    for name, (position, scale) in views.items():
        camera.location = position
        camera.rotation_euler = (Vector((0.07, 0.0, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera_data.ortho_scale = scale
        scene.render.filepath = str(out / f"{label}-{name}-{'texture' if textured else 'clay'}.png")
        bpy.ops.render.render(write_still=True)
