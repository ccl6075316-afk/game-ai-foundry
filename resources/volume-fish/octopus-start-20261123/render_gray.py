import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'r2'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'octopus-gray.blend'))
scene=bpy.context.scene;cam=scene.camera;final=bpy.data.collections['GRAY_REVIEW']
views={'oblique':((3.5,-4.8,4.5),(0,-.05,.30)),'top':((0,-.05,7),(0,-.05,0)),'side':((6,-.1,1.5),(0,-.05,.40)),'underside':((2,-3,-5),(0,0,.25))}
for name,(loc,target) in views.items():
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    local=[cam.matrix_world.inverted()@(o.matrix_world@v.co) for o in final.objects for v in o.data.vertices]
    cam.data.ortho_scale=1.12*max(2*max(abs(v.x) for v in local),2*max(abs(v.y) for v in local)*1400/1100)
    scene.render.filepath=str(OUT/f'gray-{name}.png');bpy.ops.render.render(write_still=True)
loc,target=views['oblique'];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_distance=5;a.spaces.active.region_3d.view_location=(0,0,.3)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'octopus-gray.blend'))
