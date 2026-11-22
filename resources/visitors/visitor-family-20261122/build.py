"""Export the four accepted, editable visitor models in Blender background mode."""
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent
GAME = ROOT.parents[2] / "projects/fishing-2d/game/assets/visitors-c"


def export(name, atlas):
    source = ROOT / (name + ".blend")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    material = obj.data.materials[0]
    node = next(n for n in material.node_tree.nodes if n.type == "TEX_IMAGE")
    # An edited atlas must also be present when opening the source on another machine.
    if node.image.packed_file.data != atlas.read_bytes():
        old = node.image
        image_name = old.name
        node.image = bpy.data.images.load(str(atlas), check_existing=False)
        if not old.users:
            bpy.data.images.remove(old)
        node.image.name = image_name
        node.image.pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    bpy.ops.export_scene.gltf(filepath=str(GAME / (name + ".glb")), export_format="GLB")


if __name__ == "__main__":
    GAME.mkdir(parents=True, exist_ok=True)
    for name in ("woman", "man", "child", "elder"):
        atlas_name = "face-layout.png" if name == "woman" else name + ".png"
        export(name, ROOT / atlas_name)
