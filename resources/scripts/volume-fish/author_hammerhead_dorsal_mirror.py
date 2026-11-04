"""Bind a verified same-fish dorsal bake into ordinary editable source."""
import bpy,json,sys,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot
cp,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert not out.exists()
for p,h in c['inputs'].items():assert sha(p)==h,p
src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));actions=rig_action_snapshot();body=bpy.data.objects[c['body']];records=[]
for row in c['textures']:
 material=body.data.materials[row['slot']];node=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE');old=node.image;image=bpy.data.images.load(row['path'],check_existing=False);assert tuple(image.size)==tuple(old.size);image.pack();node.image=image;node.interpolation='Closest';records.append(dict(slot=row['slot'],material=material.name,old_image=old.name,new_image=image.name,texture_sha256=sha(row['path'])))
assert rig_action_snapshot()==actions;out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT');meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for ob in meshes+[rig]:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());report=dict(ok=True,kind='existing_right_dorsal_material_bound_to_left',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),baseline_sha256=sha(src/'fish.glb'),config_sha256=sha(cp),author_sha256=sha(__file__),rig_and_actions_exact=True,all_geometry_normals_UV_weights_unedited=True,fin_authoring_bytes_exact=True,records=records,formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
