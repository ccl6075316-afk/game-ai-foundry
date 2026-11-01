"""Apply frozen actual-pose weights to the editable source; geometry untouched."""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];plan=Path(args[0]).resolve();out=Path(args[1]).resolve();r=json.loads(plan.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(r['input_blend'])==r['input_blend_sha256'];assert '/experiments/'in out.as_posix()and not out.exists();out.mkdir();bpy.ops.wm.open_mainfile(filepath=r['input_blend']);objects={o.name:o for o in bpy.context.scene.objects if o.type=='MESH'}
def geometry():return {n:hashlib.sha256(repr(([(tuple(v.co))for v in o.data.vertices],[tuple(p.vertices)for p in o.data.polygons],[tuple(v.uv)for v in o.data.uv_layers.active.data])).encode()).hexdigest()for n,o in objects.items()}
before=geometry();changed=0
for row in r['changes']:
 ob=objects[row['fin']];p=row['position_gltf'];q=Vector((p[0],-p[2],p[1]));nearest=min(ob.data.vertices,key=lambda v:(v.co-q).length);assert(nearest.co-q).length<1e-6;matches=[v.index for v in ob.data.vertices if(v.co-nearest.co).length<1e-7]
 for i in matches:
  for g in ob.vertex_groups:g.remove([i])
  for name,w in row['weights'].items():(ob.vertex_groups.get(name)or ob.vertex_groups.new(name=name)).add([i],w,'REPLACE')
  changed+=1
assert geometry()==before;bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in['MESH','ARMATURE']:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((Path(r['input_blend']).parent/'fin-authoring.json').read_bytes());(out/'skin-fit.validation.json').write_text(json.dumps(dict(ok=True,fit_plan=str(plan),fit_sha256=sha(plan),changed_vertices=changed,geometry_uv_fingerprints=before,model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),formal_acceptance=False),indent=2)+'\n');print('SOURCE_SKIN_FIT',changed)
