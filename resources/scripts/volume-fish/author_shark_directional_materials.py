"""Assign native directional body charts; source UV/geometry/skin/fins exact."""
import bpy,json,sys,hashlib
from pathlib import Path
import numpy as np
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();charts=Path(args[1]).resolve();out=Path(args[2]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();r=json.loads((charts/'validation.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Closed_body'];ROOT=Path(__file__).resolve().parents[3];p=json.loads((ROOT/'resources/volume-fish/blacktip-reef-shark-review-055.profile.json').read_text());sec=np.array(p['body']['sections']);aspect=1/p['source_aspect_ratio'];slots={};sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(include_uv=True):return {o.name:hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(p.vertices)for p in o.data.polygons],[tuple(v.uv)for v in o.data.uv_layers.active.data]if include_uv else[])).encode()).hexdigest()for o in bpy.context.scene.objects if o.type=='MESH'}
before=signature();before_geo=signature(False);counts={}
for row in r['records']:
 assert sha(row['path'])==row['sha256'];mat=body.data.materials[0].copy();mat.name='Own native '+row['role']+' body chart / opaque';nodes=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'];assert len(nodes)==1;im=bpy.data.images.load(row['path'],check_existing=False);im.pack();nodes[0].image=im;slots[row['role']]=len(body.data.materials);body.data.materials.append(mat);counts[row['role']]=0
for poly in body.data.polygons:
 if poly.material_index!=0:continue
 points=np.array([tuple(body.data.vertices[i].co)for i in poly.vertices]);u=points[:,0]+.5
 if u.max()>=.90:continue
 v=.5-points[:,2]/aspect;top=np.interp(u,sec[:,0],sec[:,1]);bottom=np.interp(u,sec[:,0],sec[:,2]);q=float(((v-(top+bottom)/2)/((bottom-top)/2)).mean());role='back'if q<-.60 else'belly'if q>.60 else None
 if role:
  poly.material_index=slots[role];counts[role]+=1
  for li in poly.loop_indices:
   vi=body.data.loops[li].vertex_index;point=body.data.vertices[vi].co;uu=point.x+.5;width=float(np.interp(uu,sec[:,0],sec[:,3]));fraction=(.35 if role=='back'else .735)+(point.y/max(width,1e-6))*(.08 if role=='back'else .065);vv=float(np.interp(uu,sec[:,0],sec[:,1])+(np.interp(uu,sec[:,0],sec[:,2])-np.interp(uu,sec[:,0],sec[:,1]))*fraction);body.data.uv_layers.active.data[li].uv=(uu,1-vv)
assert before_geo==signature(False);bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());(out/'directional-materials.validation.json').write_text(json.dumps({'ok':True,'input_model_sha256':sha(src/'fish.glb'),'chart_receipt_sha256':sha(charts/'validation.json'),'model_sha256':sha(out/'fish.glb'),'body_faces_by_chart':counts,'geometry_weights_fins_head_mouth_exact':True,'body_roof_uv_method':'Independent full face source charts; longitudinal own-source u, signed transverse fraction into interior native back .25-.45 / belly .65-.82. Side, u>=.90, oral and fin UVs exact.','geometry_fingerprints':before,'formal_acceptance':False},indent=2)+'\n');print(json.dumps(counts))
