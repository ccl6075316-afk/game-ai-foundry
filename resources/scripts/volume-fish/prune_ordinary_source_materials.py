"""Remove unused source material slots/datablocks without changing render data."""
import bpy,json,sys,hashlib
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]);out=Path(args[1]);assert not out.exists();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));records=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    before=[ob.data.materials[f.material_index].name for f in ob.data.polygons];used={f.material_index for f in ob.data.polygons};removed=[]
    for i in reversed(range(len(ob.data.materials))):
        if i not in used:removed.append(ob.data.materials[i].name);ob.data.materials.pop(index=i)
    assert before==[ob.data.materials[f.material_index].name for f in ob.data.polygons];records.append(dict(mesh=ob.name,unused_slots_removed=removed))
bpy.data.orphans_purge(do_recursive=True);bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in ['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());(out/'source-prune.validation.json').write_text(json.dumps(dict(ok=True,records=records,actual_face_material_identity_unchanged=True,model_sha256=hashlib.sha256((out/'fish.glb').read_bytes()).hexdigest()),indent=2)+'\n')
