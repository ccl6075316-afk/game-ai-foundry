"""Cold export and verify the finalized Blender sources are self-contained."""
from pathlib import Path
import json
import subprocess
import tempfile

from build import BATCH, BLENDER, WORK, dump, expand_blender_glb, sha

candidates=BATCH/"candidate-catalog.json"
rows=json.loads(candidates.read_text())["assets"]
WORK.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix="cold-export-",dir=WORK) as folder:
    for row in rows:
        item=BATCH/row["id"]
        source=item/(row["id"]+".blend")
        current=item/(row["id"]+".glb")
        native=Path(folder)/current.name
        finalized=native.with_suffix(".final.glb")
        script=("import bpy;"
                "images=[image for image in bpy.data.images if image.type=='IMAGE'];"
                "assert len(images)==1 and images[0].packed_file is not None;"
                f"bpy.ops.export_scene.gltf(filepath={str(native)!r},export_format='GLB',"
                "export_texcoords=True,export_vertex_color='ACTIVE',export_animations=False,export_extras=True)")
        with (WORK/f"{row['id']}-cold-export.log").open("w") as log:
            subprocess.run([str(BLENDER),"-b",str(source),"-t","2","--python-exit-code","9","--python-expr",script],
                           check=True,stdout=log,stderr=subprocess.STDOUT)
        expand_blender_glb(native,finalized)
        validation=item/"asset.validation.json"
        evidence=json.loads(validation.read_text())
        evidence["cold_blend_export"]={"packed_image":True,"source_sha256":sha(source),"normalized_export_sha256":sha(finalized),
                                       "current_glb_sha256":sha(current),"byte_identical":sha(finalized)==sha(current)}
        print(row["id"], evidence["cold_blend_export"]["byte_identical"], flush=True)
        dump(validation,evidence)
