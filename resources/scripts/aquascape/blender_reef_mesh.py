"""Blender backend for manifold decimation and packed reef mesh authoring sources."""

import argparse
import io
import json
from pathlib import Path
import struct
import sys
import tempfile

import bmesh
import bpy
import numpy as np


def make_object(name, vertices, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def clean(obj):
    graph = bmesh.new()
    graph.from_mesh(obj.data)
    bmesh.ops.remove_doubles(graph, verts=list(graph.verts), dist=0.000003)
    bmesh.ops.dissolve_degenerate(graph, edges=list(graph.edges), dist=0.0000005)
    border = [edge for edge in graph.edges if edge.is_boundary]
    if border:
        bmesh.ops.holes_fill(graph, edges=border, sides=16)
    bmesh.ops.triangulate(graph, faces=list(graph.faces))
    bmesh.ops.recalc_face_normals(graph, faces=list(graph.faces))
    graph.to_mesh(obj.data)
    graph.free()


def reduce(path, goal):
    input_mesh = np.load(path)
    obj = make_object(path.stem, input_mesh["vertices"], input_mesh["faces"])
    clean(obj)
    modifier = obj.modifiers.new("Low-poly collapse", "DECIMATE")
    modifier.ratio = min(1.0, (goal - 4) / len(obj.data.polygons))
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    clean(obj)
    vertices = np.array([vertex.co for vertex in obj.data.vertices], dtype=np.float32)
    faces = np.array([face.vertices[:] for face in obj.data.polygons], dtype=np.int32)
    np.savez_compressed(path, vertices=vertices, faces=faces)


def source(path, packed_dir):
    packed_dir.mkdir(parents=True, exist_ok=True)
    authored = np.load(path.with_suffix(".npz"))
    vertices = authored["vertices"][:, [0, 2, 1]].copy()
    vertices[:, 1] *= -1
    obj = make_object(path.stem, vertices, authored["faces"])
    raw = path.read_bytes()
    json_size = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20 + json_size])
    binary = raw[28 + json_size:]
    prim = doc["meshes"][0]["primitives"][0]
    uv_acc = doc["accessors"][prim["attributes"]["TEXCOORD_0"]]
    uv_view = doc["bufferViews"][uv_acc["bufferView"]]
    uv = np.frombuffer(binary, dtype="<f4", count=uv_acc["count"] * 2, offset=uv_view["byteOffset"]).copy()
    uv[1::2] = 1 - uv[1::2]
    uv_layer = obj.data.uv_layers.new(name="Baked art")
    uv_layer.data.foreach_set("uv", uv)
    texture_view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    start = texture_view["byteOffset"]
    material = bpy.data.materials.new(path.stem + " · rock")
    material.use_nodes = True
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    with tempfile.TemporaryDirectory() as temp:
        png = Path(temp) / (path.stem + "-atlas.png")
        png.write_bytes(binary[start:start + texture_view["byteLength"]])
        texture.image = bpy.data.images.load(str(png))
        texture.image.pack()
    texture.interpolation = "Closest"
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 1.0
    material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.append(material)
    bpy.ops.wm.save_as_mainfile(filepath=str(packed_dir / (path.stem + ".blend")), compress=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh", type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--triangles", type=int)
    action.add_argument("--editable-dir", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if args.triangles:
        reduce(args.mesh, args.triangles)
    else:
        source(args.mesh, args.editable_dir)


if __name__ == "__main__":
    main()
