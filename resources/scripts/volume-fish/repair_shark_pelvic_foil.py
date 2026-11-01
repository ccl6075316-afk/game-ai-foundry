"""Unfold proximal pelvic foil using distance to its own complete basal curve.

Keeps every original contour pixel, X/Z silhouette and frozen basal vertex.
The old anchor-to-tip projection incorrectly gave zero span to some free skin
above the anchor. This source-only repair restores outward span there.
"""
import bpy,json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import sha
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));author=json.loads((src/'fin-authoring.json').read_text());profile=json.loads((HERE.parents[2]/'resources/volume-fish/blacktip-reef-shark-review-055.profile.json').read_text());f=next(f for f in profile['fins']if f['name']=='Pelvic');line=np.array([f['polygon'][i]for i in[6,7,8,0]]);a=line[:-1];d=np.diff(line,axis=0)
def distance(q):
 t=np.clip(((q-a)*d).sum(1)/np.maximum((d*d).sum(1),1e-20),0,1);return float(np.min(np.linalg.norm(q-a-t[:,None]*d,axis=1)))
span=distance(np.array(f['tip']));records=[]
for name in['Pelvic_left','Pelvic_right']:
 ob=bpy.data.objects[name];r=next(r for r in author['fins']if r['name']==name);roots=set(r['root_ids']);before={i:tuple(ob.data.vertices[i].co)for i in roots};uv={};sign=-1 if name.endswith('_left')else 1
 for poly in ob.data.polygons:
  for li in poly.loop_indices:uv[ob.data.loops[li].vertex_index]=tuple(ob.data.uv_layers.active.data[li].uv)
 changed=[]
 for v in ob.data.vertices:
  if v.index in roots:continue
  u,w=uv[v.index];t=min(1,distance(np.array([u,1-w]))/span);target=f['root_depth']+(f['tip_depth']-f['root_depth'])*t;delta=max(0,target-sign*v.co.y)
  if delta>1e-8:v.co.y+=sign*delta;changed.append({'vertex':v.index,'outward_native':delta,'native_source_uv':[u,1-w]})
 assert all(tuple(ob.data.vertices[i].co)==q for i,q in before.items());ob.data.update();records.append({'fin':name,'changed':changed,'complete_basal_vertices_exact':True,'source_side_XZ_exact':True})
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in['MESH','ARMATURE']:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());r=dict(ok=True,kind='native_basal_distance_pelvic_foil_repair',input_model_sha256=sha(src/'fish.glb'),input_blend_sha256=sha(src/'fish.blend'),source_basal_curve=line.tolist(),span_distance=span,records=records,model_sha256=sha(out/'fish.glb'),formal_acceptance=False,scope='Only non-basal pelvic Y coordinates increase to native basal-distance span; side silhouette, full base, UV/pixels, topology, weights, body/mouth/other fins/rig/actions unchanged. New ray/volume/cold/490 gates mandatory.');(out/'pelvic-foil.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'changed':[len(r['changed'])for r in records]}))
