"""Apply the existing arapaima source pictures to the isolated v3 clay mesh.

Diagnostic UVs only: no accepted UV unwrap, repaint, or game asset mutation.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


source_glb, side_png, front_png, target_glb, mode = sys.argv[sys.argv.index("--") + 1:]
source_glb, side_png, front_png, target_glb = map(lambda p: Path(p).resolve(),
                                                   (source_glb, side_png, front_png, target_glb))
target_glb.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source_glb))

side = bpy.data.images.load(str(side_png), check_existing=False)
front = bpy.data.images.load(str(front_png), check_existing=False)
side.pack()
front.pack()
aspect = 1 / 4.406565656565657
side_pixels = list(side.pixels[:])
front_pixels = list(front.pixels[:])
side_columns = {}
front_columns = {}


def side_uv(u, v):
    w, h = side.size[:]
    x = max(0, min(w-1, int(u*w)))
    y = max(0, min(h-1, int(v*h)))
    if x not in side_columns:
        side_columns[x] = [row for row in range(h)
                           if side_pixels[(row*w+x)*4+3] > .85]
    rows = side_columns[x]
    if rows and side_pixels[(y*w+x)*4+3] <= .85:
        y = min(rows, key=lambda row: abs(row-y))
    return ((x+.5)/w, (y+.5)/h)


def front_uv(u, v):
    w, h = front.size[:]
    x = max(0, min(w-1, int(u*w)))
    if x not in front_columns:
        rows = [row for row in range(int((1-.89)*h), int((1-.55)*h))
                if front_pixels[(row*w+x)*4+3] > .85]
        front_columns[x] = (min(rows)+2, max(rows)-2) if rows else None
    bounds = front_columns[x]
    if not bounds:
        return ((x+.5)/w, 1-v)
    low, high = bounds
    t = max(0, min(1, (v-.55)/(.89-.55)))
    y = high - (high-low)*t
    return ((x+.5)/w, (y+.5)/h)


def image_material(name, image):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 1
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest"
    tex.extension = "EXTEND"
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


side_mat = image_material("Accepted side picture · nearest", side)
front_mat = image_material("Existing v11 front picture · nearest", front)
report = {"mode": mode, "source_mesh": str(source_glb), "side_source": str(side_png),
          "front_source": str(front_png), "objects": {}}

for obj in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    name = obj.name
    if name.startswith("Eye_") or name.startswith("Operculum_edge_") or name.startswith("Closed_mouth_"):
        continue
    mesh = obj.data
    mesh.materials.clear()
    mesh.materials.append(side_mat)
    if mode == "side-and-front" and name in ("Bony_upper_skull", "Projecting_lower_jaw", "Continuous_head"):
        mesh.materials.append(front_mat)
    uv = mesh.uv_layers.get("DiagnosticSourceUV") or mesh.uv_layers.new(name="DiagnosticSourceUV")
    # Grafted meshes also carry their original UV set. The image texture node
    # reads the active render UV, so select this projection explicitly.
    mesh.uv_layers.active = uv
    uv.active_render = True
    front_faces = 0
    for poly in mesh.polygons:
        center = sum((mesh.vertices[k].co for k in poly.vertices), Vector()) / len(poly.vertices)
        use_front = (len(mesh.materials) == 2 and center.x + .5 >= .84 and poly.normal.x > .35)
        poly.material_index = 1 if use_front else 0
        front_faces += use_front
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            if use_front:
                lateral = max(0, min(1, (co.y + .08) / .16))
                vertical = max(0, min(1, ((.5 - co.z/aspect) - .22) / (.79 - .22)))
                # Reuse the accepted v11 profile's front crop and axis mapping.
                uv.data[li].uv = front_uv(.25 + .5*lateral, .55 + .34*vertical)
            else:
                uv.data[li].uv = side_uv(max(0, min(1, co.x+.5)),
                                         max(0, min(1, .5+co.z/aspect)))
    report["objects"][name] = {"faces": len(mesh.polygons), "front_faces": front_faces,
                               "uv_layers": len(mesh.uv_layers)}

bpy.ops.export_scene.gltf(filepath=str(target_glb), export_format="GLB", export_animations=False)
(target_glb.parent / "texture-probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("TEXTURE_PROBE " + json.dumps(report))
