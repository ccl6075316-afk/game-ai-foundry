"""Preserve native animation inputs and lace threshold in the editable source."""
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

bpy.context.preferences.filepaths.save_version=0
model=Path(sys.argv[-1])
data=model.read_bytes()
size=struct.unpack_from("<I",data,12)[0]
doc=json.loads(data[20:20+size])
attrib=doc["meshes"][0]["primitives"][0]["attributes"]

def read(key, width):
    acc=doc["accessors"][attrib[key]]
    buff=doc["bufferViews"][acc["bufferView"]]
    return np.frombuffer(data[28+size:],dtype="<f4",count=acc["count"]*width,offset=buff["byteOffset"]).copy()

m=bpy.data.objects[model.stem].data
motion=read("TEXCOORD_1",2)
motion[1::2]=1-motion[1::2]
layer=m.uv_layers.new(name="Water movement")
layer.data.foreach_set("uv",motion)
color=m.color_attributes.new(name="Water pivots",type="FLOAT_COLOR",domain="CORNER")
rgba=read("COLOR_0",4)
color.data.foreach_set("color",rgba)
m.uv_layers.active_index=0
paint=m.materials[0]
if doc["materials"][0].get("alphaMode")=="MASK":
    graph=paint.node_tree
    node=next(n for n in graph.nodes if n.type=="TEX_IMAGE")
    operation=graph.nodes.new("ShaderNodeMath")
    operation.operation="GREATER_THAN"
    operation.inputs[1].default_value=.5
    graph.links.new(node.outputs["Alpha"],operation.inputs[0])
    graph.links.new(operation.outputs[0],graph.nodes.get("Principled BSDF").inputs["Alpha"])
m["rooted_current_uv"]="UV2 X = bend weight, Y = temporal phase, COLOR RGB = author anchor"
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
