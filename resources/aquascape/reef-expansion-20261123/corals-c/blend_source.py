"""Store the reef model, left intact with packed source texture and custom normals."""
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "resources/scripts/aquascape"))
from blender_reef_mesh import source

path = Path(sys.argv[sys.argv.index("--") + 1])
target = Path(sys.argv[sys.argv.index("--editable-dir") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
source(path,target)
raw=path.read_bytes()
n=struct.unpack_from("<I",raw,12)[0]
doc=json.loads(raw[20:20+n])
attrs=doc["meshes"][0]["primitives"][0]["attributes"]
acc=doc["accessors"][attrs["NORMAL"]]
view=doc["bufferViews"][acc["bufferView"]]
normals=np.frombuffer(raw[28+n:],dtype="<f4",count=acc["count"]*3,offset=view["byteOffset"]).reshape(-1,3)
corners=normals[:,[0,2,1]].copy()
corners[:,1]*=-1
mesh=bpy.data.objects[path.stem].data
mesh.polygons.foreach_set("use_smooth",np.full(len(mesh.polygons),True))
mesh.normals_split_custom_set(corners.tolist())
mesh.materials[0].name=doc["materials"][0]["name"]
bpy.ops.wm.save_as_mainfile(filepath=str(target / (path.stem + ".blend")),compress=True)
