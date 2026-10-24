"""Static material coordinate transport through the frozen128 deformation."""
import bpy,sys,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

plan_path=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(plan_path.read_text());root=plan_path.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(plan['base_gray_mesh'])==plan['base_gray_sha256'];assert sha(plan['base_surface_plan'])==plan['base_surface_plan_sha256']
base_plan=json.loads(Path(plan['base_surface_plan']).read_text());assert sha(base_plan['input'])==base_plan['input_sha256'];data=np.load(base_plan['input']);spec=base_plan['surface']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new('Exact128 correspondence');mesh.from_pydata(data['vertices'].tolist(),[],data['triangles'].tolist());mesh.update();obj=bpy.data.objects.new('Exact128 correspondence',mesh);bpy.context.collection.objects.link(obj);bpy.context.view_layer.objects.active=obj;obj.select_set(True)
mod=obj.modifiers.new('Uniform topology','REMESH');mod.mode='VOXEL';mod.voxel_size=spec['voxel_size'];mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
def positions():
 v=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',v);return v.reshape(-1,3)
def smoothstep(t):
 t=np.clip(t,0,1);return t**3*(t*(t*6-15)+10)
initial=positions();obj.data.calc_loop_triangles();initial_tri=np.array([f.vertices[:] for f in obj.data.loop_triangles],dtype=np.int32)
for index,stage in enumerate(spec['stages']):
 v=positions();w=np.clip((v[:,0]-stage['start_x'])/(stage['full_x']-stage['start_x']),0,1);w=w*w*w*(w*(w*6-15)+10);group=obj.vertex_groups.new(name='Curvature fade '+str(index))
 for i,value in enumerate(w):
  if value>0:group.add([i],float(value),'REPLACE')
 mod=obj.modifiers.new('Continuous surface '+str(index),'SMOOTH');mod.factor=stage['factor'];mod.iterations=stage['iterations'];mod.vertex_group=group.name;bpy.ops.object.modifier_apply(modifier=mod.name)
if spec.get('forehead_bow'):
 v=positions();shape=spec['forehead_bow'];t=np.clip((v[:,1]-shape['minimum_y'])/(shape['maximum_y']-shape['minimum_y']),0,1);longitudinal=smoothstep((v[:,0]-shape['start_x'])/(shape['full_x']-shape['start_x']));v[:,0]+=shape['inset_native']*np.sin(np.pi*t)**4*longitudinal
 if spec.get('lower_jaw_position_restore'):
  shape=spec['lower_jaw_position_restore'];v[:,0]+=shape['restore_native']*smoothstep((v[:,0]-shape['start_x'])/(shape['full_x']-shape['start_x']))*smoothstep((shape['upper_y']-v[:,1])/(shape['upper_y']-shape['full_y']))
 obj.data.vertices.foreach_set('co',v.ravel());obj.data.update()
if spec.get('transverse_roundness'):
 v=positions();shape=spec['transverse_roundness'];v[:,2]*=1+(shape['maximum_scale']-1)*smoothstep((v[:,0]-shape['start_x'])/(shape['full_x']-shape['start_x']));obj.data.vertices.foreach_set('co',v.ravel());obj.data.update()
final=positions();obj.data.calc_loop_triangles();final_tri=np.array([f.vertices[:] for f in obj.data.loop_triangles],dtype=np.int32)
transport_bvh=BVHTree.FromPolygons(final.tolist(),final_tri.tolist(),all_triangles=True)
source=np.load(plan['source_attributes']);assert sha(plan['source_attributes'])==plan['source_attributes_sha256']
sv=source['vertices'];sn=source['normals'];su=source['uv'];su2=source['uv2'];st=source['triangles'];ss=source['surface'];source_bvh=BVHTree.FromPolygons(sv.tolist(),st.tolist(),all_triangles=True)
base=json.loads(Path(plan['base_gray_mesh']).read_text());v=np.asarray(base['vertices']);n=np.asarray(base['normals']);tri=np.array(base['triangles']).reshape(-1,3)
def bary(p,abc):
 a,b,c=abc.astype(float);v0=b-a;v1=c-a;v2=np.asarray(p)-a;d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01
 if den<1e-25:return np.array([1.,0,0])
 vv=(d11*(v2@v0)-d01*(v2@v1))/den;ww=(d00*(v2@v1)-d01*(v2@v0))/den;return np.array([1-vv-ww,vv,ww])
uv=[];uv2=[];refs=[];refn=[];labels=[];transport_distance=[];source_distance=[];source_faces=[];source_bary=[]
for i,point in enumerate(v):
 q,normal,face,distance=transport_bvh.find_nearest(Vector(point));assert q is not None
 ids=final_tri[face];weights=bary(q,final[ids]);reference=initial[ids].T@weights
 q,normal,face,sd=source_bvh.find_nearest(Vector(reference));assert q is not None
 ids=st[face];weights=np.maximum(bary(q,sv[ids]),0);weights/=weights.sum();source_faces.append(int(face));source_bary.append(weights.tolist());q=sv[ids].T@weights;uv.append((su[ids].T@weights).tolist());uv2.append((su2[ids].T@weights).tolist());refs.append(np.asarray(q).tolist());nn=sn[ids].T@weights;refn.append((nn/max(np.linalg.norm(nn),1e-15)).tolist());labels.append(ss[face]);transport_distance.append(distance);source_distance.append(sd)
 if i%50000==0:print('TRANSPORT_VERTICES',i,len(v),flush=True)
uv=np.array(uv);uv2=np.array(uv2);refs=np.array(refs);refn=np.array(refn);labels=np.array(labels);kind=np.sum(labels[tri],axis=1)>=2
assert max(transport_distance)<2*spec['voxel_size'];assert max(source_distance)<2*spec['voxel_size']
parts=[]
for si in [0,1]:
 faces=tri[kind==bool(si)];assert len(faces)>0;ids,inverse=np.unique(faces,return_inverse=True)
 parts.append({'source_surface':si,'vertices':v[ids].tolist(),'normals':n[ids].tolist(),'uv':uv[ids].tolist(),'uv2':uv2[ids].tolist(),'source_face_ids':np.asarray(source_faces)[ids].tolist(),'source_bary_weights':np.asarray(source_bary)[ids].tolist(),'reference_positions':refs[ids].tolist(),'reference_normals':refn[ids].tolist(),'triangles':inverse.tolist()})
out=root/'textured-body.mesh.json';out.write_text(json.dumps({'parts':parts},separators=(',',':')))
report={'schema_version':1,'ok':True,'command':'fish.transport-material130','stage':'validate','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(plan_path),'helper_sha256':sha(__file__),'source_attributes_sha256':sha(plan['source_attributes']),'base_gray_sha256':sha(plan['base_gray_mesh'])},'outputs':[{'path':str(out),'sha256':sha(out)}],'summary':{'vertices':len(v),'triangles':len(tri),'source_surface_triangles':[int(np.sum(kind==False)),int(np.sum(kind==True))],'geometry_and_normals_exactly_frozen128':True,'deformed_surface_transport_max_distance_native':float(max(transport_distance)),'original_surface_reference_max_distance_native':float(max(source_distance)),'scope':'Static material reference transfer only;128 gray positions/normals/topology unchanged. Source surface ownership determined by majority transported source face labels; boundary semantics require visual review. No rig transfer or full delivery gates.'},'failures':[]}
(root/'geometry.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report),flush=True)
