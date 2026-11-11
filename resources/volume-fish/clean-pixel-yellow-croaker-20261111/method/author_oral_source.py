"""Update just the existing shared oral chart datablock with its protected RGB patch."""
import json
from pathlib import Path
import sys
import bpy

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[1]
sys.path[:0]=[str(ROOT/"resources/scripts/volume-fish"),str(ROOT/"resources/scripts/volume-fish/portable"),str(WORK)]
from author_source import signature,sha
from export_ordinary_source_owned import export_source

out=WORK/"mouth-r4"
assert not (out/"fish.blend").exists()
source=WORK/"mouth-r3/fish.blend"
source_hash=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source))
before=signature()
patch=out/"oral-chart.png"
data=patch.read_bytes()
assert json.loads((out/"oral-color.validation.json").read_text())["chart_sha256"]==sha(patch)
images=[next(n.image for n in bpy.data.materials[name].node_tree.nodes if n.type=="TEX_IMAGE")
        for name in ("Front mouth oral chart","Front skin source chart")]
assert images[0]==images[1]
images[0].pack(data=data,data_len=len(data))
assert bytes(images[0].packed_file.data)==data and signature()==before
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/"fish.blend"))
proof=export_source(out/"fish.glb")
assert signature()==before and sha(source)==source_hash
proof.update(source_sha256=sha(out/"fish.blend"),input_source_sha256=source_hash,oral_chart_sha256=sha(patch))
(out/"source-authoring.validation.json").write_text(json.dumps(proof,indent=2)+"\n")
