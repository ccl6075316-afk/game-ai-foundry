import bpy
from mathutils import Vector
from pathlib import Path
import sys

blend = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = blend.parent / 'perspective-probe'
out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
scene.frame_set(0)
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 900
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new('Probe world')
world.use_nodes = True
background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs[0].default_value = (.13, .16, .19, 1)
scene.world = world
light_data = bpy.data.lights.new('Probe light', 'AREA')
light_data.energy = 35
light_data.size = 3
light = bpy.data.objects.new('Probe light', light_data)
scene.collection.objects.link(light)
light.location = (0, -2, 3)
light.rotation_euler = (-light.location).to_track_quat('-Z', 'Y').to_euler()
cam_data = bpy.data.cameras.new('Perspective probe')
cam = bpy.data.objects.new('Perspective probe', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = 'PERSP'
cam_data.lens = 35
cam_data.sensor_width = 36
head_x = max(v.co.x for o in scene.objects if o.type == 'MESH' for v in o.data.vertices)
target = Vector((head_x - .075, 0, 0))
for dist in (.4, .65, 1.0):
    cam.location = (head_x + dist, 0, 0)
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(out / f'front_{dist:.2f}.png')
    bpy.ops.render.render(write_still=True)
