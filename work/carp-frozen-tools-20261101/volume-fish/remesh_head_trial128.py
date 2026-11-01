"""Whole forehead-to-snout static curvature study; no production/UV/rig export."""
import bpy,sys,json,hashlib
from pathlib import Path
import numpy as np

plan_path=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(plan_path.read_text());root=plan_path.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(plan['input'])==plan['input_sha256']
data=np.load(plan['input']);spec=plan['surface']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new('Static whole-head study');mesh.from_pydata(data['vertices'].tolist(),[],data['triangles'].tolist());mesh.update()
obj=bpy.data.objects.new('Continuous forehead and snout',mesh);bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
mod=obj.modifiers.new('Uniform topology','REMESH');mod.mode='VOXEL';mod.voxel_size=spec['voxel_size'];mod.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=mod.name)
for index,stage in enumerate(spec['stages']):
 v=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',v);v=v.reshape(-1,3)
 w=np.clip((v[:,0]-stage['start_x'])/(stage['full_x']-stage['start_x']),0,1)
 w=w*w*w*(w*(w*6-15)+10)
 group=obj.vertex_groups.new(name='Curvature fade '+str(index))
 for i,value in enumerate(w):
  if value>0:group.add([i],float(value),'REPLACE')
 mod=obj.modifiers.new('Continuous surface '+str(index),'SMOOTH');mod.factor=stage['factor'];mod.iterations=stage['iterations'];mod.vertex_group=group.name
 bpy.ops.object.modifier_apply(modifier=mod.name)
 print('STAGE_DONE',index,flush=True)
if spec.get('forehead_bow'):
 v=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',v);v=v.reshape(-1,3)
 shape=spec['forehead_bow']
 t=np.clip((v[:,1]-shape['minimum_y'])/(shape['maximum_y']-shape['minimum_y']),0,1)
 longitudinal=np.clip((v[:,0]-shape['start_x'])/(shape['full_x']-shape['start_x']),0,1)
 longitudinal=longitudinal**3*(longitudinal*(longitudinal*6-15)+10)
 # A broad C2 field fills the forehead-to-snout arc; endpoints and source
 # eye level fade continuously. This is not an appended front spike.
 v[:,0]+=shape['inset_native']*np.sin(np.pi*t)**4*longitudinal
 if spec.get('lower_jaw_position_restore'):
  shape=spec['lower_jaw_position_restore']
  xw=np.clip((v[:,0]-shape['start_x'])/(shape['full_x']-shape['start_x']),0,1)
  yw=np.clip((shape['upper_y']-v[:,1])/(shape['upper_y']-shape['full_y']),0,1)
  xw=xw**3*(xw*(xw*6-15)+10);yw=yw**3*(yw*(yw*6-15)+10)
  v[:,0]+=shape['restore_native']*xw*yw
 obj.data.vertices.foreach_set('co',v.ravel());obj.data.update()
if spec.get('transverse_roundness'):
 v=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',v);v=v.reshape(-1,3)
 shape=spec['transverse_roundness']
 w=np.clip((v[:,0]-shape['start_x'])/(shape['full_x']-shape['start_x']),0,1)
 w=w**3*(w*(w*6-15)+10)
 # Broaden the whole rostral envelope continuously instead of retaining a
 # long straight cone followed by a rounded cap. Native XY stays unchanged.
 v[:,2]*=1+(shape['maximum_scale']-1)*w
 obj.data.vertices.foreach_set('co',v.ravel());obj.data.update()
mod=obj.modifiers.new('Compact static preview','DECIMATE');mod.ratio=spec['decimation_ratio'];mod.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=mod.name)
obj.data.update();v=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',v);v=v.reshape(-1,3)
n=np.empty_like(v);obj.data.vertices.foreach_get('normal',n.ravel());obj.data.calc_loop_triangles();t=np.array([x.vertices[:] for x in obj.data.loop_triangles],dtype=np.int32)[:,[0,2,1]]
out=root/'whole-head-gray.mesh.json';out.write_text(json.dumps({'vertices':v.tolist(),'normals':n.tolist(),'triangles':t.ravel().tolist()},separators=(',',':')))
report={'schema_version':1,'ok':True,'command':'fish.whole-head-curvature128','stage':'validate','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(plan_path),'helper_sha256':sha(__file__),'input_sha256':sha(plan['input'])},'outputs':[{'path':str(out),'sha256':sha(out)}],'summary':{'scope':'Static gray curvature study only. No UV/rig transfer, production installation, anatomy or fish delivery acceptance.','vertices':len(v),'triangles':len(t),'surface':spec,'blender':bpy.app.version_string},'failures':[]}
(root/'geometry.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
