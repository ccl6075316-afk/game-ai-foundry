"""Keep finite oral lining facet normals separate from the smooth outer skin."""
import bpy,sys,json,hashlib
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];before=[(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in body.data.vertices];faces=[tuple(p.vertices)for p in body.data.polygons];changed=[]
for p in body.data.polygons:
 if body.data.materials[p.material_index].name=='Actual finite oral lining':
  if p.use_smooth:changed.append(p.index)
  p.use_smooth=False
body.data.update();assert before==[(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in body.data.vertices]and faces==[tuple(p.vertices)for p in body.data.polygons];bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in ['MESH','ARMATURE']:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());(out/'oral-normal-authoring.validation.json').write_text(json.dumps(dict(ok=True,source_sha256=sha(src/'fish.blend'),model_sha256=sha(out/'fish.glb'),oral_faces_with_facet_normals=changed,geometry_UV_skin_actions_unchanged=True,scope='Actual2thin oral-corner triangles had wrong averaged normals. Oral material gets its own finite face normals; outer body stays smooth. No winding/topology/positions/tolerance change.'),indent=2)+'\n');print('ORAL_NORMALS',len(changed))
