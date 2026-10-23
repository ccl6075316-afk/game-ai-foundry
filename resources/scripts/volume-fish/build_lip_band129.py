"""Blender: advect source rim through128, lay source-width shallow strips on128."""
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
initial=positions();obj.data.calc_loop_triangles();initial_tri=np.array([f.vertices[:] for f in obj.data.loop_triangles]);initial_bvh=BVHTree.FromPolygons(initial.tolist(),initial_tri.tolist(),all_triangles=True)
rims=np.load(root/'source-rims.npz');tracked={};initial_distances=[]
for name in ['upper','lower']:
 ids=[];weights=[]
 for p in rims[name]:
  point,normal,face,distance=initial_bvh.find_nearest(Vector(p));assert point is not None
  initial_distances.append(float(distance))
  assert distance<2*spec['voxel_size'],'Source rim outside two-cell correspondence neighborhood'
  triangle=initial_tri[face];a,b,c=initial[triangle].astype(float);v0=b-a;v1=c-a;v2=np.array(point)-a;d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01;v=(d11*(v2@v0)-d01*(v2@v1))/den;w=(d00*(v2@v1)-d01*(v2@v0))/den
  ids.append(triangle);weights.append([1-v-w,v,w])
 tracked[name]=(np.array(ids),np.array(weights))
del initial_bvh,initial_tri,initial
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
final=positions();advected={name:np.sum(final[ids]*w[:,:,None],axis=1) for name,(ids,w) in tracked.items()}
mod=obj.modifiers.new('Compact static preview','DECIMATE');mod.ratio=spec['decimation_ratio'];mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name);obj.data.update();v=positions();n=np.empty_like(v);obj.data.vertices.foreach_get('normal',n.ravel());obj.data.calc_loop_triangles();t=np.array([x.vertices[:] for x in obj.data.loop_triangles],dtype=np.int32)[:,[0,2,1]]
# Confirm this correspondence really recreates the frozen displayed128 body.
base=json.loads(Path(plan['base_gray_mesh']).read_text());assert np.array_equal(v,np.array(base['vertices'],dtype=np.float32));assert np.array_equal(t.ravel(),np.array(base['triangles']));assert np.array_equal(n,np.array(base['normals'],dtype=np.float32))
body_v=np.array(base['vertices']);body_n=np.array(base['normals']);body_tri=np.array(base['triangles']).reshape(-1,3)[:,[0,2,1]];body_bvh=BVHTree.FromPolygons(body_v.tolist(),body_tri.tolist(),all_triangles=True)
def unit(a):return a/max(np.linalg.norm(a),1e-15)
def project(p):
 point,normal,face,distance=body_bvh.find_nearest(Vector(p));assert point is not None
 # Use smooth body vertex normals, rather than a different normal per tiny face.
 ids=body_tri[face];q=body_v[ids];a,b,c=q;v0=b-a;v1=c-a;v2=np.array(point)-a;d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01
 if den>1e-25:
  vv=(d11*(v2@v0)-d01*(v2@v1))/den;ww=(d00*(v2@v1)-d01*(v2@v0))/den;nn=unit(body_n[ids].T@np.array([1-vv-ww,vv,ww]))
 else:nn=np.array(normal)
 return np.array(point),nn,float(distance)
parts=[];metrics={};cfg=plan['geometry'];count=cfg['longitudinal_samples'];cross_count=cfg['cross_samples']
for name in ['upper','lower']:
 p=advected[name].astype(float);source=np.array(rims[name]);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];s=np.linspace(0,arc[-1],count);curve=np.array([np.interp(s,arc,p[:,i]) for i in range(3)]).T;source_x=np.interp(s,arc,(source[:,0]+.5)*1986)
 for _ in range(cfg['curve_smoothing_iterations']):curve[1:-1]=.2*curve[:-2]+.6*curve[1:-1]+.2*curve[2:]
 projected=[project(q) for q in curve];curve=np.array([q[0] for q in projected]);normals=np.array([q[1] for q in projected]);tangents=np.gradient(curve,axis=0);tangents=np.array([unit(q) for q in tangents]);directions=np.cross(normals,tangents)
 if np.median(directions[:,1])*(1 if name=='upper' else -1)<0:directions*=-1
 directions=np.array([unit(q) for q in directions]);band=plan['bands'][name];bounds=np.asarray(band['source_bounds']);srcx=np.minimum(source_x,band['central_source_column']);outer=np.interp(srcx,bounds[:,0],bounds[:,1]);inner=np.interp(srcx,bounds[:,0],bounds[:,2]);slope=np.interp(srcx,bounds[:,0],np.gradient(bounds[:,2],bounds[:,0]));width=abs(outer-inner)/1986/np.sqrt(1+slope*slope)
 # Across the front, continue the last side width in actual surface distance.
 central=source_x>=band['central_source_column'];last_width=abs(bounds[-1,1]-bounds[-1,2])/1986/np.sqrt(1+float(np.gradient(bounds[:,2],bounds[:,0])[-1])**2);width[central]=last_width
 verts=[];uv=[];base_points=[];offsets=[];actual_width=[]
 for i in range(count):
  if i in [0,count-1]:
   verts.append(curve[i].tolist());base_points.append(curve[i].tolist());offsets.append(0.);uv.append([0.,0.]);actual_width.append(0.);continue
  steps=max(1,int(np.ceil(width[i]/cfg['projection_step_native'])));path=[curve[i]];path_n=[normals[i]];d=directions[i]
  for _ in range(steps):
   d=unit(d-path_n[-1]*(d@path_n[-1]));point,nn,dist=project(path[-1]+d*(width[i]/steps));path.append(point);path_n.append(nn)
  path=np.array(path);path_n=np.array(path_n);length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];actual_width.append(float(length[-1]))
  for j,f in enumerate(np.linspace(0,1,cross_count)):
   at=f*length[-1];point=np.array([np.interp(at,length,path[:,k]) for k in range(3)]);nn=unit(np.array([np.interp(at,length,path_n[:,k]) for k in range(3)]));point,nn,_=project(point)
   relief=cfg['relief_native']*np.sin(np.pi*f)**2+cfg['surface_offset_native']
   verts.append((point+nn*relief).tolist());base_points.append(point.tolist());offsets.append(relief)
   safe_margin=plan['atlas']['ink_exclusion_margin_px'];sy=(inner[i]-np.sign(inner[i]-outer[i])*safe_margin)*(1-f)+(outer[i]+np.sign(inner[i]-outer[i])*safe_margin)*f
   if band.get('central_safe_color_y'):
    blend=float(smoothstep((source_x[i]-band['central_color_blend_start_x'])/(band['central_source_column']-band['central_color_blend_start_x'])))
    safe_outer,safe_inner=band['central_safe_color_y'];central_y=safe_inner*(1-f)+safe_outer*f
    sy=sy*(1-blend)+central_y*blend
   low=min(outer[i],inner[i]);col=srcx[i]-plan['atlas']['minimum_x'];row=sy-np.floor(low)+band['atlas_offset_y'];uv.append([(col+.5)/plan['atlas']['width'],(row+.5)/plan['atlas']['height']])
 def index(i,j):return 0 if i==0 else len(verts)-1 if i==count-1 else 1+(i-1)*cross_count+j
 faces=[]
 for i in range(count-1):
  for j in range(cross_count-1):
   candidates=[(index(i,j),index(i+1,j),index(i+1,j+1)),(index(i,j),index(i+1,j+1),index(i,j+1))]
   for face in candidates:
    if len(set(face))==3:faces.append(face)
 verts=np.array(verts);faces=np.array(faces);cross=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]]);area=np.linalg.norm(cross,axis=1);assert np.all(area>1e-15)
 centers=verts[faces].mean(1);ref=np.array([project(q)[1] for q in centers]);flip=np.sum(cross*ref,axis=1)<0;faces[flip]=faces[flip][:,[0,2,1]]
 nn=np.zeros_like(verts);cross=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]])
 for k in range(3):np.add.at(nn,faces[:,k],cross)
 nn/=np.maximum(np.linalg.norm(nn,axis=1),1e-20)[:,None]
 actual_width=np.array(actual_width);relative=abs(actual_width[1:-1]-width[1:-1])/np.maximum(width[1:-1],1e-9)
 # Preserve the final native top-left UV convention; Godot arrays use CW.
 parts.append({'name':name,'vertices':verts.tolist(),'normals':nn.tolist(),'uv':uv,'triangles':faces[:,[0,2,1]].ravel().tolist()})
 assert np.max(relative)<.02,'Strip surface width drifts more than2% from frozen source width'
 metrics[name]={'source_front_column':band['central_source_column'],'central_width_target_native':float(last_width),'central_projected_width_native_min_max':[float(actual_width[central].min()),float(actual_width[central].max())],'width_distance_relative_error_p50_p95_max':np.percentile(relative,[50,95,100]).tolist(),'vertices':len(verts),'triangles':len(faces),'surface_offset_native':cfg['surface_offset_native'],'maximum_outer_relief_native':float(max(offsets)),'all_base_rows_projected_to_frozen128_body':True}
 print('BAND_DONE',name,metrics[name],flush=True)
out=root/'lip-band.mesh.json';out.write_text(json.dumps({'parts':parts},separators=(',',':')))
report={'schema_version':1,'ok':True,'command':'fish.build-lip-band129','stage':'validate','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(plan_path),'builder_sha256':sha(__file__),'base_gray_sha256':sha(plan['base_gray_mesh']),'source_rims_sha256':sha(root/'source-rims.npz'),'atlas_sha256':sha(root/'lip-band-native.png')},'outputs':[{'path':str(out),'sha256':sha(out)}],'summary':{'base128_geometry_reproduced_exactly':True,'base_body_unchanged':True,'maximum_initial_rim_projection_native':max(initial_distances),'initial_rim_projection_limit_native':2*spec['voxel_size'],'bands':metrics,'scope':'Static surface-conforming lip strip with shallow relief and independent native-texel atlas. Original128 gray, source model/image, rig and production files unchanged. Visual continuity and lips still require review; no full fish delivery gates.'},'failures':[]}
(root/'geometry.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False),flush=True)
