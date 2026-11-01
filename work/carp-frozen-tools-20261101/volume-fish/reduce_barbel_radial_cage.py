"""Keep each authored barbel path/radius/UV/skin while using six radial sides."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'cli'),str(Path(__file__).parent/'portable'),str(Path(__file__).parent)]
from fish_budget import check_triangle_budget
from source_snapshot import rig_action_snapshot
from glb_io import read_glb
from patch_existing_fin_meshes import write as write_glb
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser()
for k in ['blend','config','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=json.loads(a.config.read_text(encoding='utf8'));out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();assert sha(a.blend)==cfg['blend_sha256'];bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));rig=rig_action_snapshot()
def frozen(ob):return repr(([tuple(v.co)for v in ob.data.vertices],[tuple(f.vertices)for f in ob.data.polygons],[[tuple(u.uv)for u in uv.data]for uv in ob.data.uv_layers],[[tuple((g.group,g.weight))for g in v.groups]for v in ob.data.vertices],[tuple(n.vector)for n in ob.data.corner_normals]))
protected={o.name:frozen(o)for o in bpy.data.objects if o.type=='MESH'and o.name not in cfg['nodes']};records=[]
for name in cfg['nodes']:
 ob=bpy.data.objects[name];old=ob.data;n=cfg['old_sides'];m=cfg['new_sides'];assert 5<=m<n and len(old.vertices)%n==0;nr=len(old.vertices)//n;co=np.array([v.co[:]for v in old.vertices]).reshape(nr,n,3);uv=[None]*len(old.vertices)
 for loop,item in zip(old.loops,old.uv_layers.active.data):uv[loop.vertex_index]=tuple(item.uv)
 uv=np.array(uv).reshape(nr,n,2);centers=co.mean(1);positions=[];newuv=[];skin=[];fit_errors=[]
 for k in range(nr):
  aa=(co[k,0]-co[k,n//2])*.5;bb=(co[k,n//4]-co[k,3*n//4])*.5
  fit=max(np.linalg.norm(centers[k]+aa*math.cos(j*math.tau/n)+bb*math.sin(j*math.tau/n)-co[k,j])for j in range(n));assert fit<1e-7,'Existing ring does not match the float32 source circle';fit_errors.append(float(fit))
  weights=[{ob.vertex_groups[g.group].name:g.weight for g in old.vertices[k*n+i].groups}for i in range(n)];assert all(w==weights[0]for w in weights)
  for j in range(m):
   angle=j*math.tau/m;positions.append(centers[k]+aa*math.cos(angle)+bb*math.sin(angle));newuv.append((uv[k,:,0].mean()+np.ptp(uv[k,:,0])*.5*math.cos(angle),uv[k,:,1].mean()));skin.append(weights[0])
 faces=[]
 for k in range(1,nr):
  for j in range(m):q=k*m+j;r=k*m+(j+1)%m;faces.append((q-m,r-m,r,q))
 faces +=[tuple(reversed(range(m))),tuple((nr-1)*m+j for j in range(m))];mesh=bpy.data.meshes.new(name+'_six_side_path');mesh.from_pydata(positions,[],faces);mesh.update()
 for mat in old.materials:mesh.materials.append(mat)
 layer=mesh.uv_layers.new(name='UVMap')
 for f in mesh.polygons:
  f.use_smooth=True
  for li in f.loop_indices:layer.data[li].uv=newuv[mesh.loops[li].vertex_index]
 ob.data=mesh
 for i,weights in enumerate(skin):
  for bone,w in weights.items():(ob.vertex_groups.get(bone)or ob.vertex_groups.new(name=bone)).add([i],w,'REPLACE')
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 assert all(e.is_manifold for e in bm.edges)and bm.calc_volume(signed=True)>0;bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles();records.append({'name':name,'centerline_preserved':True,'radius_preserved':True,'float32_ring_fit_max_native':max(fit_errors),'rings':nr,'old_radial_sides':n,'new_radial_sides':m,'triangles':len(mesh.loop_triangles),'skin_exact_per_station':True})
assert rig_action_snapshot()==rig and all(frozen(bpy.data.objects[n])==value for n,value in protected.items());triangles=0
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();triangles+=len(ob.data.loop_triangles)
budget=check_triangle_budget(triangles,cfg['real_length_cm']);out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True);doc,blob=read_glb(out/'fish.glb')
for node in doc['nodes']:
 if 'mesh'not in node:continue
 for prim in doc['meshes'][node['mesh']]['primitives']:
  mat=doc['materials'][prim['material']];mat['alphaMode']='MASK'if node['name']in cfg['fins']else'OPAQUE'
  if mat['alphaMode']=='MASK':mat['alphaCutoff']=.5
for s in doc.get('samplers',[]):s.update(magFilter=9728,minFilter=9728,wrapS=33071,wrapT=33071)
write_glb(out/'fish.glb',doc,blob);report={'ok':True,'kind':'native_barbel_radial_budget_reallocation','input_sha256':sha(a.blend),'config_sha256':sha(a.config),'whole_fish_budget':budget,'records':records,'all_body_mouth_fins_UV_geometry_skin_normals_exact':True,'rig_actions_exact':True,'blend_sha256':sha(out/'fish.blend'),'model_sha256':sha(out/'fish.glb'),'formal_acceptance':False};(out/'barbel-budget.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':triangles,'preferred_met':budget['preferred_met']}))
