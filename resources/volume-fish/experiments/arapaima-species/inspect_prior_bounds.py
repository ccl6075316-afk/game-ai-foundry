import bpy
from mathutils import Vector

bpy.ops.import_scene.gltf(filepath=r"E:\game-ai-foundry\projects\fishing-2d\game\assets\models\fish\arapaima.glb")
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    span = tuple(round(max(p[i] for p in pts)-min(p[i] for p in pts), 4) for i in range(3))
    print('BOUND', o.name, span, 'hide_render', o.hide_render)
