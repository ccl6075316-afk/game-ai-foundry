"""Source-owned native opaque padding, with geometry/UV/skin and fins exact."""
import bpy,json,sys,hashlib
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();charts=Path(args[1]).resolve();out=Path(args[2]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();r=json.loads((charts/'validation.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert r['ok'];out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'))
def geometry():return {o.name:hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(p.vertices)for p in o.data.polygons],[tuple(v.uv)for v in o.data.uv_layers.active.data])).encode()).hexdigest()for o in bpy.context.scene.objects if o.type=='MESH'}
before=geometry();body=bpy.data.objects['Closed_body'];records=[]
for i,role in[(0,'side'),(1,'front')]:
 row=next(r for r in r['records']if r['role']==role);assert sha(row['path'])==row['sha256'];mat=body.data.materials[i].copy();body.data.materials[i]=mat;nodes=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'];assert len(nodes)==1;im=bpy.data.images.load(row['path'],check_existing=False);im.pack();nodes[0].image=im;records.append(row)
assert before==geometry();bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());(out/'native-materials.validation.json').write_text(json.dumps(dict(ok=True,source_model_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),chart_receipt_sha256=sha(charts/'validation.json'),records=records,geometry_UV_weights_fins_exact=True,geometry_fingerprints=before,formal_acceptance=False),indent=2)+'\n');print('NATIVE_BODY_MATERIALS_SAVED')
