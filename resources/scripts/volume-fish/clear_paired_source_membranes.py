"""Source-space outward clearance for diagnosed free paired-fin faces only.

Frozen complete root bands, source silhouette X/Z, UV, thickness pairs, skin and
animation remain explicit. Every new candidate requires current posed gates.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(Path(__file__).parent/'portable'),str(ROOT/'cli'),str(Path(__file__).parent)]
from source_snapshot import rig_action_snapshot
from fish_budget import check_triangle_budget
from glb_io import read_glb
from patch_existing_fin_meshes import write as write_glb
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser()
for k in ['blend','config','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=json.loads(a.config.read_text(encoding='utf8'));out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();assert sha(a.blend)==cfg['blend_sha256'];profile=json.loads((ROOT/cfg['profile']).read_text(encoding='utf8'));bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));rig=rig_action_snapshot()
def invariant(ob,positions=True,normals=True):return repr(([tuple(v.co)for v in ob.data.vertices]if positions else[],[tuple(f.vertices)for f in ob.data.polygons],[[tuple(u.uv)for u in uv.data]for uv in ob.data.uv_layers],[[tuple((g.group,g.weight))for g in v.groups]for v in ob.data.vertices],[tuple(n.vector)for n in ob.data.corner_normals]if normals else[]))
protected={o.name:invariant(o)for o in bpy.data.objects if o.type=='MESH'and o.name not in cfg['free_offsets_mm']};records=[]
body=bpy.data.objects['Closed_body'];body.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co.copy()for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True)
for name,mm in cfg['free_offsets_mm'].items():
 ob=bpy.data.objects[name];before=invariant(ob,False,False);f=next(f for f in profile['fins']if name.startswith(f['name']+'_'));assert f['paired'];band=f['root_attachment']['root_band'];ts=[x.value for x in ob.data.attributes['foundry_fin_source_t'].data];old=np.array([v.co[:]for v in ob.data.vertices]);roots=[i for i,t in enumerate(ts)if t<=band+1e-7];changed=[];side=-1 if '_left_'in name else 1
 for i,t in enumerate(ts):
  if t<=band+1e-7:
   if 'root_reproject_inset_mm'in cfg:
    hit,normal,face,distance=tree.find_nearest(ob.data.vertices[i].co);ob.data.vertices[i].co=hit-normal*cfg['root_reproject_inset_mm']/1000/cfg['model_scale']
   continue
  ob.data.vertices[i].co.y+=side*mm/1000/cfg['model_scale'];changed.append(i)
 assert changed
 if 'root_reproject_inset_mm'not in cfg:assert all(np.array_equal(np.array(ob.data.vertices[i].co[:]),old[i])for i in roots)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 assert all(e.is_manifold for e in bm.edges)and bm.calc_volume(signed=True)>0;bm.to_mesh(ob.data);bm.free();assert invariant(ob,False,False)==before
 records.append({'name':name,'free_outward_offset_mm':mm,'root_source_t_max':band,'all_root_positions_preserved':'root_reproject_inset_mm'not in cfg,'root_domain_preserved':True,'root_reproject_inset_mm':cfg.get('root_reproject_inset_mm'),'root_vertices':len(roots),'changed_free_vertices':changed,'free_source_XZ_silhouette_UV_weights_faces_unchanged':True})
assert all(invariant(bpy.data.objects[n])==v for n,v in protected.items())and rig_action_snapshot()==rig;triangles=0
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();triangles+=len(ob.data.loop_triangles)
budget=check_triangle_budget(triangles,cfg['real_length_cm']);out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True);doc,blob=read_glb(out/'fish.glb')
for node in doc['nodes']:
 if 'mesh'not in node:continue
 for primitive in doc['meshes'][node['mesh']]['primitives']:
  mat=doc['materials'][primitive['material']];mat['alphaMode']='MASK'if node['name']in cfg['fins']else'OPAQUE'
  if mat['alphaMode']=='MASK':mat['alphaCutoff']=.5
for s in doc.get('samplers',[]):s.update(magFilter=9728,minFilter=9728,wrapS=33071,wrapT=33071)
write_glb(out/'fish.glb',doc,blob);report={'ok':True,'kind':'source_paired_free_membrane_clearance','diagnosis':cfg['diagnosis'],'input_sha256':sha(a.blend),'config_sha256':sha(a.config),'records':records,'whole_fish_budget':budget,'other_body_mouth_fins_and_barbels_exact':True,'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'formal_acceptance':False};(out/'clearance.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':triangles,'changed_fins':len(records)}))
frozen_roots={}
for f in profile['fins']:
 for suffix in(['_left','_right']if f['paired']else['']):
  ob=bpy.data.objects[f['name']+suffix+'_mesh'];ts=[x.value for x in ob.data.attributes['foundry_fin_source_t'].data];ids=[i for i,t in enumerate(ts)if t<=f['root_attachment']['root_band']+1e-7]
  frozen_roots[ob.name]={'ids':ids,'rest_points_gltf':[[ob.data.vertices[i].co.x,ob.data.vertices[i].co.z,-ob.data.vertices[i].co.y]for i in ids],'vertices':len(ob.data.vertices),'source_baseline':f['source_baseline'],'source_t_max':f['root_attachment']['root_band'],'rule':'Entire original persisted source-t domain, updated actual authored root positions; no selection shrink.'}
length=max(v.co.x for ob in bpy.data.objects if ob.type=='MESH'for v in ob.data.vertices)-min(v.co.x for ob in bpy.data.objects if ob.type=='MESH'for v in ob.data.vertices)
item={'species':profile['species'],'model':str(out/'fish.glb'),'model_sha256':sha(out/'fish.glb'),'body':'Closed_body','body_bones':[f'body_{i:02d}'for i in range(len(profile['rig']['spine']))],'length_native':length,'scale_cm':profile['real_length_cm']/length,'fins':frozen_roots,'profile':str(ROOT/cfg['profile']),'profile_sha256':sha(ROOT/cfg['profile']),'source_sha256':cfg['source_sha256']}
(out/'authored-roots.plan.json').write_text(json.dumps({'kind':'authored_fin_completion_plan','items':[item]},indent=2)+'\n',encoding='utf8')
