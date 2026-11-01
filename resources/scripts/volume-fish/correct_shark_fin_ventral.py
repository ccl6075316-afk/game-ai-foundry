"""Keep anatomical fin-layer ownership through curved bases, not normal switches."""
import bpy,json,sys,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();atlas=Path(args[1]).resolve();out=Path(args[2]).resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'))
def signature(o):
 return hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(p.vertices)for p in o.data.polygons])).encode()).hexdigest()
before={o.name:signature(o)for o in bpy.context.scene.objects if o.type=='MESH'};rows=[];author=json.loads((src/'fin-authoring.json').read_text())
finmat=bpy.data.objects['FirstDorsal'].data.materials[0];tex=next(n for n in finmat.node_tree.nodes if n.type=='TEX_IMAGE');im=bpy.data.images.load(str(atlas),check_existing=False);im.pack();tex.image=im
for o in bpy.context.scene.objects:
 if o.type!='MESH'or not(o.name.startswith('Pectoral_')or o.name.startswith('Pelvic_')):continue
 uv=o.data.uv_layers.active
 def original(face):
  q=np.array([tuple(uv.data[li].uv)for li in face.loop_indices]);q[:,0]=(q[:,0]% .5)*2;return q
 def area(q):return float(np.cross(q[1]-q[0],q[2]-q[0]))
 roots=set(next(r for r in author['fins']if r['name']==o.name)['root_ids']);height_groups={};vertex_keys={}
 for face in o.data.polygons:
  q=original(face)
  for vi,p in zip(face.vertices,q):
   k=tuple(np.round(p,6));vertex_keys[int(vi)]=k;height_groups.setdefault(k,[]).append(float(o.data.vertices[vi].co.z))
 votes={-1:0.,1:0.}
 for face in o.data.polygons:
  s=area(original(face));rank=[]
  for vi in face.vertices:
   if vi in roots:continue
   z=height_groups[vertex_keys[int(vi)]];lo,hi=min(z),max(z)
   if hi-lo>1e-7:rank.append((o.data.vertices[vi].co.z-(hi+lo)/2)/(hi-lo))
  if rank and np.mean(rank)<-.1 and abs(s)>1e-10:votes[1 if s>0 else -1]+=abs(s)*-float(np.mean(rank))
 assert max(votes.values())>0;lower_sign=max(votes,key=votes.get);counts={'lower':0,'upper':0,'walls':0}
 for face in o.data.polygons:
  q=original(face);s=area(q)
  lower=(s*lower_sign>0)if abs(s)>1e-10 else face.normal.z<0;counts['walls'if abs(s)<1e-10 else'lower'if lower else'upper']+=1
  for li,p in zip(face.loop_indices,q):uv.data[li].uv=(float(p[0])*.5+(.5 if lower else 0),float(p[1]))
 rows.append({'name':o.name,'lower_source_uv_winding_sign':lower_sign,'faces':counts,'free_layer_height_votes':votes,'layer_basis':'Actual lower/upper vertex height within each matched native UV pair; full native two-sided orientation extended through the basal band. Curved basal normals do not switch tissue color.'})
assert all(signature(bpy.data.objects[n])==h for n,h in before.items())
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes())
(out/'ventral-ownership.validation.json').write_text(json.dumps({'ok':True,'kind':'shark_anatomical_lower_fin_layer_ownership','input_model_sha256':sha(src/'fish.glb'),'model_sha256':sha(out/'fish.glb'),'atlas_sha256':sha(atlas),'geometry_triangles_weights_exact':True,'rows':rows,'formal_acceptance':False},indent=2)+'\n');print(json.dumps(rows))
