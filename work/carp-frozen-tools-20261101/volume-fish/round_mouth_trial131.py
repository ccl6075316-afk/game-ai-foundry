"""Blender: subtract a smooth anterior field; re-lay source-width lip strips.

This isolated black-seabream trial preserves130's material coordinates. Hidden
curvature is an artistic trial, not a species measurement or delivery approval.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

pp=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(pp.read_text());root=pp.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for key,value in plan['frozen_inputs'].items():assert sha(key)==value,key
body=json.loads(Path(plan['baseline_body']).read_text());lips=json.loads(Path(plan['baseline_lips']).read_text())
cfg=plan['rounding']
def smooth(t):
 t=np.clip(t,0,1);return t**3*(t*(t*6-15)+10)
def warp(p):
 q=np.array(p,dtype=float,copy=True);x,y,z=q.T
 wx=smooth((x-cfg['start_x'])/(cfg['full_x']-cfg['start_x']))
 displacement=np.zeros(len(q))
 for spec in cfg['lobes']:
  lo,lf,hf,hi=spec['y_support']
  wy=smooth((y-lo)/(lf-lo))*smooth((hi-y)/(hi-hf))
  square=spec['vertical_curvature']*(y-spec['center_y'])**2+spec['transverse_curvature']*z*z
  displacement+=wx*wy*cfg['maximum_inset']*(-np.expm1(-square/cfg['maximum_inset']))
 q[:,0]-=displacement
 return q
def jacobian(p):
 eps=1e-6;j=np.zeros((len(p),3,3))
 for axis in range(3):
  delta=np.zeros(3);delta[axis]=eps
  j[:,:,axis]=(warp(p+delta)-warp(p-delta))/(2*eps)
 return j
def unit(n):return n/np.maximum(np.linalg.norm(n,axis=-1,keepdims=True),1e-20)
def transport(p,n):return unit(np.linalg.solve(np.swapaxes(jacobian(p),1,2),n[:,:,None])[:,:,0])
vertices=[];normals=[];triangles=[];metrics=[];offset=0
for part in body['parts']:
 p=np.array(part['vertices']);n=np.array(part['normals']);t=np.array(part['triangles']).reshape(-1,3)[:,[0,2,1]]
 q=warp(p).astype(np.float32).astype(float);nn=transport(p,n)
 cross=np.cross(q[t[:,1]]-q[t[:,0]],q[t[:,2]]-q[t[:,0]])
 area=np.linalg.norm(cross,axis=1);ref=transport(p[t].mean(1),unit(np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]])))
 agreement=np.sum(unit(cross)*ref,axis=1)
 assert np.min(area)>1e-15 and np.min(agreement)>.9
 determinant=np.linalg.det(jacobian(p));assert determinant.min()>.65
 assert np.array_equal(q[p[:,0]<=cfg['start_x']],p[p[:,0]<=cfg['start_x']])
 assert np.max(q[:,0]-p[:,0])<=1e-9 and np.array_equal(q[:,1:],p[:,1:])
 metrics.append({'source_surface':part['source_surface'],'moved_vertices':int(np.sum(np.linalg.norm(q-p,axis=1)>1e-8)),'maximum_inset_native':float(np.max(p[:,0]-q[:,0])),'minimum_jacobian':float(determinant.min()),'minimum_face_transport_agreement':float(agreement.min())})
 part['vertices']=q.tolist();part['normals']=nn.tolist()
 vertices.append(q);normals.append(nn);triangles.append(t+offset);offset+=len(q)
v=np.concatenate(vertices);n=np.concatenate(normals);t=np.concatenate(triangles)
bvh=BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True)
def project(p):
 point,normal,face,distance=bvh.find_nearest(Vector(p));assert point is not None
 ids=t[face];a,b,c=v[ids];q=np.array(point);v0=b-a;v1=c-a;v2=q-a
 d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01
 vv=(d11*(v2@v0)-d01*(v2@v1))/den;ww=(d00*(v2@v1)-d01*(v2@v0))/den
 return q,unit(n[ids].T@np.array([1-vv-ww,vv,ww]))
lip_metrics={}
for part in lips['parts']:
 old=np.array(part['vertices']);old_rows=old[1:-1].reshape(255,17,3);old_normals=np.array(part['normals'])[1:-1].reshape(255,17,3)
 deformed=warp(old)[1:-1].reshape(255,17,3);new_rows=[];widths=[];target_widths=[]
 for i,row in enumerate(deformed):
  # Retain each original surface strip's own width; do not stretch the central
  # chart to fit the extra curvature or add a tubular lip.
  old_base=[]
  for j,p in enumerate(old_rows[i]):
   # Remove the known129 shallow relief before measuring its source width.
   relief=plan['lip_relief']*np.sin(np.pi*j/16)**2+plan['lip_clearance']
   old_base.append(p-old_normals[i,j]*relief)
  width=float(np.linalg.norm(np.diff(old_base,axis=0),axis=1).sum());target_widths.append(width)
  if np.max(np.linalg.norm(row-old_rows[i],axis=1))<1e-8:
   new_rows.append(old_rows[i]);widths.append(width);continue
  # Advect the already accepted cross-row itself. An unconstrained walk from
  # its chord can take a different branch near a tight mouth corner.
  projected=[project(p) for p in warp(np.array(old_base))]
  path=[p[0] for p in projected];path_n=[p[1] for p in projected]
  current=float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum())
  while current<width:
   direction=unit(path[-1]-path[-2]);direction=unit(direction-path_n[-1]*(direction@path_n[-1]))
   point,normal=project(path[-1]+direction*.0001)
   step=float(np.linalg.norm(point-path[-1]));assert step>1e-10
   path.append(point);path_n.append(normal);current+=step
  path=np.array(path);length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
  result=[];base=[]
  for j,f in enumerate(np.linspace(0,1,17)):
   p=np.array([np.interp(f*width,length,path[:,k]) for k in range(3)]);p,nn=project(p);base.append(p)
   result.append(p+nn*(plan['lip_relief']*np.sin(np.pi*f)**2+plan['lip_clearance']))
  new_rows.append(result);widths.append(float(np.linalg.norm(np.diff(base,axis=0),axis=1).sum()))
 start=warp(old[:1])[0];end=warp(old[-1:])[0];q=np.concatenate([start[None],np.array(new_rows).reshape(-1,3),end[None]])
 faces=np.array(part['triangles']).reshape(-1,3)[:,[0,2,1]];cross=np.cross(q[faces[:,1]]-q[faces[:,0]],q[faces[:,2]]-q[faces[:,0]])
 ref=np.array([project(p)[1] for p in q[faces].mean(1)]);agreement=np.sum(unit(cross)*ref,axis=1)
 changed=np.max(np.linalg.norm(q[faces]-old[faces],axis=2),axis=1)>1e-8
 old_cross=unit(np.cross(old[faces[:,1]]-old[faces[:,0]],old[faces[:,2]]-old[faces[:,0]]))
 transported=transport(old[faces].mean(1),old_cross)
 orientation=np.sum(unit(cross)*transported,axis=1)
 # The existing tapered corner contains near-tangent faces. Check changed
 # faces against their transported orientation, rather than inventing a new
 # absolute normal angle that would also reject the unchanged input corner.
 assert orientation.min()>.2,('Lip changed orientation',part['name'],float(orientation.min()))
 assert agreement[changed].min()>0,('Changed lip faces point into body',part['name'],float(agreement[changed].min()))
 nn=np.zeros_like(q)
 for k in range(3):np.add.at(nn,faces[:,k],cross)
 nn=unit(nn);part['vertices']=q.tolist();part['normals']=nn.tolist()
 widths=np.array(widths);target_widths=np.array(target_widths);error=abs(widths-target_widths)/np.maximum(target_widths,1e-9)
 assert error.max()<.02
 lip_metrics[part['name']]={'maximum_width_error_fraction':float(error.max()),'central_width_native_min_max':[float(widths[115:140].min()),float(widths[115:140].max())],'minimum_changed_face_surface_agreement':float(agreement[changed].min()),'minimum_face_transport_agreement':float(orientation.min()),'unchanged_corner_faces_preserved':True,'uv_unchanged':True,'clearance_native':plan['lip_clearance'],'relief_native':plan['lip_relief']}
outputs=[]
for filename,data in [('rounded-body.mesh.json',body),('rounded-lips.mesh.json',lips)]:
 path=root/filename;path.write_text(json.dumps(data,separators=(',',':')));outputs.append({'path':str(path),'sha256':sha(path)})
report={'schema_version':1,'ok':True,'command':'fish.round-mouth131','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(pp),'helper_sha256':sha(__file__),'frozen_inputs':plan['frozen_inputs']},'outputs':outputs,'summary':{'body':metrics,'lips':lip_metrics,'no_forward_extension':True,'outside_support_unchanged':True,'source_material_coordinates_and_atlas_unchanged':True,'production_installed':False,'scope':'Static isolated anterior curvature trial. Positive sampled differential and finite-face orientation checked; not a complete self-intersection, motion, body-opacity or fin delivery gate.'},'failures':[]}
(root/'geometry.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report),flush=True)
