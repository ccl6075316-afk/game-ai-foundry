import bpy,numpy as np,json,sys
from pathlib import Path
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W));import author as A
from author_three import CONTRACT
from mathutils import Vector
out=W/'rebuild-r2';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(W/'whole-r1/fish.blend'))
data=json.loads((W/'rebuilt-body.json').read_bytes());p=np.array(data['vertices']);faces=data['faces'];oral=data['oral'];weights=data['weights'];rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');order=json.loads(rig['foundry_exact_joint_names']);ob=bpy.data.objects['Closed_body'];old=ob.data
mesh=bpy.data.meshes.new('Arapaima independently rebuilt whole body cage');mesh.from_pydata(A.blender(p).tolist(),[],faces);mesh.update()
def material(name,rgb,base):
 m=base.copy();m.name=name;con=json.loads(m[CONTRACT]);con['fields']['name']=name;m[CONTRACT]=json.dumps(con,sort_keys=True)
 im=bpy.data.images.new(name,width=2,height=2,alpha=True);im.pixels=list(rgb+[1])*4;im.pack()
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE':n.image=im;n.interpolation='Closest';n.extension='EXTEND'
 return m
mesh.materials.append(material('Whole body gray construction preview',[.55,.58,.61],old.materials[2]));mesh.materials.append(material('Finite oral cavity gray construction preview',[.025,.028,.03],old.materials[3]))
mesh.uv_layers.new(name='GrayPreviewUV')
for a in A.JOINT_ATTRIBUTES+A.WEIGHT_ATTRIBUTES:mesh.attributes.new(name=a,type='FLOAT',domain='CORNER')
mesh.attributes.new(name=A.EXACT_NORMAL_ATTRIBUTE,type='FLOAT_VECTOR',domain='CORNER')
acc=[{},{}]
for f,isoral in zip(faces,oral):
 v=p[f];n=np.cross(v[1]-v[0],v[2]-v[0]);n/=max(np.linalg.norm(n),1e-15)
 for k,i in enumerate(f):
  a=v[(k+1)%3]-v[k];b=v[(k+2)%3]-v[k];angle=np.arccos(np.clip(a@b/max(np.linalg.norm(a)*np.linalg.norm(b),1e-15),-1,1));acc[int(isoral)][i]=acc[int(isoral)].get(i,np.zeros(3))+n*angle
normal_rows=[]
for poly,isoral in zip(mesh.polygons,oral):
 poly.material_index=int(isoral);poly.use_smooth=True
 for vi,li in zip(poly.vertices,poly.loop_indices):
  n=acc[int(isoral)][vi];n=n/max(np.linalg.norm(n),1e-15);mesh.attributes[A.EXACT_NORMAL_ATTRIBUTE].data[li].vector=n;normal_rows.append(n);mesh.uv_layers.active.data[li].uv=(.5,.5);pairs=[(order.index(name),value) for name,value in weights[vi].items()]+[(0,0)]*4
  for k,(a,w) in enumerate(zip(A.JOINT_ATTRIBUTES,A.WEIGHT_ATTRIBUTES)):mesh.attributes[a].data[li].value=pairs[k][0];mesh.attributes[w].data[li].value=pairs[k][1]
ob.data=mesh
for g in list(ob.vertex_groups):ob.vertex_groups.remove(g)
for name in order:ob.vertex_groups.new(name=name)
for vi,ws in enumerate(weights):
 for name,value in ws.items():ob.vertex_groups[name].add([vi],value,'REPLACE')
mesh.normals_split_custom_set(A.blender(np.array(normal_rows)).tolist())
skin=p[np.array([f for f,o in zip(faces,oral) if not o])]
# Complete original fin banks are transported by their unchanged source
# coordinates, then attached to this new finite skin at the same longitudinal
# position. Do not reselect a smaller bank to hide a gap.
A.WHOLE=json.loads((W/'whole-plan.json').read_bytes())
domains=json.loads((A.ROOT/'resources/volume-fish/tail-closure-repair-20261106/arapaima/complete-root-domains.json').read_bytes())['current_export_domains'];root_report={}
def skin_at_x(point):
 hits=[]
 for v in skin:
  row=[]
  for a,b in [(0,1),(1,2),(2,0)]:
   q,r=v[a],v[b]
   if (q[0]-point[0])*(r[0]-point[0])<0:row.append(q+(r-q)*(point[0]-q[0])/(r[0]-q[0]))
  if len(row)==2:hits.append(row)
 if not hits:return None
 lines=np.array(hits);a,b=lines[:,0],lines[:,1];v=b-a;t=np.clip(np.sum((point-a)*v,axis=1)/np.maximum(np.sum(v*v,axis=1),1e-20),0,1);q=a+t[:,None]*v;k=np.argmin(np.sum((q-point)**2,axis=1));target=q[k];center=np.array([point[0],(q[:,1].min()+q[:,1].max())*.5,0]);direction=target-center;direction/=max(np.linalg.norm(direction),1e-15);return target-direction*.00012
for name,domain in domains.items():
 fin=bpy.data.objects[name];m=fin.data;fp=A.gltf(np.array([v.co[:] for v in m.vertices]));expected=A.field(np.array(domain['rest_points_gltf']));distance=np.linalg.norm(expected[:,None,:]-fp[None,:,:],axis=2);ids=np.argmin(distance,axis=1);assert distance.min(axis=1).max()<2e-6,(name,distance.min(axis=1).max());ids=np.unique(ids)
 if name in ['Dorsal','Anal','Caudal']:
  # Undo the old whole-body vertical scaling for the complete rear fin.
  # Keep its original membrane height, then follow the new smooth root curve.
  transfer=data['fin_transfer']
  grid=np.array(A.WHOLE['field_grid']);xm=np.array(A.WHOLE['field_target_x']);t=np.interp(fp[:,0],xm[::-1],grid[::-1]);oldy=(fp[:,1]-np.interp(t,grid,A.WHOLE['field_yoffset']))/np.interp(t,grid,A.WHOLE['field_yscale'])-.00460757
  sections=p[:25*24].reshape(25,24,3);xs=sections[:,0,0];body_lo=sections[:,:,1].min(1);body_hi=sections[:,:,1].max(1)
  if name=='Caudal':
   oldcenter=(np.array(A.WHOLE['source_ymin_ymax_halfwidth'])[:,:2].mean(1))*.9097941815853119-.00460757
   shift=float((body_lo[0]+body_hi[0])/2)-float(np.interp(.999,A.WHOLE['station_from_nose'],oldcenter));fp[:,1]=oldy+shift
  else:
   k=1 if name=='Dorsal' else 0
   oldedge=np.interp(t,transfer['t'],transfer['old_upper' if k else 'old_lower'])
   newedge=np.interp(fp[:,0],transfer['x'],transfer['upper' if k else 'lower']);fp[:,1]=oldy-oldedge+newedge
 roots=fp[ids];delta=[]
 for q in roots:
  target=skin_at_x(q)
  # The caudal bank meets the finite posterior cap, where an X slice is empty.
  if target is None:target=q
  delta.append(target-q)
 delta=np.array(delta);near=np.linalg.norm(fp[:,None,:]-roots[None,:,:],axis=2);radius=max(float(near.min(axis=1).max())*.55,.002)
 def move(points):
  dist=np.linalg.norm(points[:,None,:]-roots[None,:,:],axis=2);order=np.argsort(dist,axis=1)[:,:min(4,len(roots))];d=np.take_along_axis(dist,order,axis=1);wt=1/np.maximum(d,1e-8)**2;wt/=wt.sum(1)[:,None];offset=np.sum(delta[order]*wt[:,:,None],axis=1);fade=1-A.smooth(d[:,0]/radius);return points+offset*fade[:,None]
 moved=move(fp);moved[ids]=roots+delta
 normal=np.array([d.vector[:] for d in m.attributes[A.EXACT_NORMAL_ATTRIBUTE].data]);loop_points=fp[[l.vertex_index for l in m.loops]];eps=1e-5;J=np.stack([(move(loop_points+e)-move(loop_points-e))/(2*eps) for e in np.eye(3)*eps],axis=2);nn=np.linalg.solve(J.transpose(0,2,1),normal[:,:,None])[:,:,0];nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-15)
 for v,q in zip(m.vertices,A.blender(moved)):v.co=q
 for d,q in zip(m.attributes[A.EXACT_NORMAL_ATTRIBUTE].data,nn):d.vector=q
 if name in ['Dorsal','Anal','Caudal']:
  # Recompute the rear-fin normals from the final finite faces. The earlier
  # normal field describes the rejected scaled/creased shape.
  accum=np.zeros_like(moved)
  for poly in m.polygons:
   vi=list(poly.vertices);q=moved[vi];n=np.cross(q[1]-q[0],q[2]-q[0])
   for j in vi:accum[j]+=n
  accum/=np.maximum(np.linalg.norm(accum,axis=1)[:,None],1e-15);nn=accum[[l.vertex_index for l in m.loops]]
  for row,q in zip(m.attributes[A.EXACT_NORMAL_ATTRIBUTE].data,nn):row.vector=q
 m.normals_split_custom_set(A.blender(nn).tolist());root_report[name]={'full_bank_points':len(expected),'source_vertices':len(ids),'max_bank_mapping_error':float(distance.min(axis=1).max()),'max_attachment_move_native':float(np.linalg.norm(delta,axis=1).max()),'longitudinal_positions_preserved':bool(np.max(abs(delta[:,0]))<1e-10),'dynamic_status':'pending'}
# Eye patch vertices follow actual new support triangles, not stale source IDs.
for eye in [o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Eye_support')]:
 m=eye.data;points=A.gltf(np.array([v.co[:] for v in m.vertices]));center=(points.min(0)+points.max(0))/2;span=points.max(0)-points.min(0);sgn=np.sign(center[2]);a,b,c=skin[:,0],skin[:,1],skin[:,2];den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);valid=abs(den)>1e-14;d=np.where(valid,den,1.)
 for i,q in enumerate(points):
  u=((b[:,1]-c[:,1])*(q[0]-c[:,0])+(c[:,0]-b[:,0])*(q[1]-c[:,1]))/d;v=((c[:,1]-a[:,1])*(q[0]-c[:,0])+(a[:,0]-c[:,0])*(q[1]-c[:,1]))/d;mask=valid&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1.000001);assert mask.any();z=(u*a[:,2]+v*b[:,2]+(1-u-v)*c[:,2])[mask];rad=((q[0]-center[0])/(span[0]/2))**2+((q[1]-center[1])/(span[1]/2))**2;points[i,2]=(z.max() if sgn>0 else z.min())+sgn*(.00005+.0020*max(0.,1-rad))
 for v,q in zip(m.vertices,A.blender(points)):v.co=q
 # The visible gray patch is small; finite-face normals are used on its own
 # current surface so the former head field cannot leave a lighting imprint.
 sums=np.zeros_like(points)
 for f in m.polygons:
  ids=list(f.vertices);q=points[ids];n=np.cross(q[1]-q[0],q[2]-q[0]);
  for i in ids:sums[i]+=n
 n=sums/np.maximum(np.linalg.norm(sums,axis=1)[:,None],1e-15);nn=n[[l.vertex_index for l in m.loops]]
 for row,q in zip(m.attributes[A.EXACT_NORMAL_ATTRIBUTE].data,nn):row.vector=q
 m.normals_split_custom_set(A.blender(nn).tolist())
for o in [o for o in bpy.data.objects if o.type=='MESH']:
 o.data['foundry_normal_geometry_sha256']=A.geometry_signature(o);o.data['foundry_exact_normal_sha256']=A.normal_attribute_signature(o)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));A.export(out/'fish.glb')
d,b=A.read_glb(out/'fish.glb');triangles=sum(d['accessors'][pr['indices']]['count']//3 for m in d['meshes'] for pr in m['primitives']);assert triangles<=4000
report={'status':'whole_rebuild_gray_candidate','model_sha256':A.sha(out/'fish.glb'),'source_sha256':A.sha(out/'fish.blend'),'body_triangles':len(faces),'triangles':triangles,'bones':len(order),'jaw_maximum_degrees':14,'jaw_hinge_gltf':[.4473990693688393,-.015716156957156655,0],'materials':'neutral construction only; new UV/color bake pending','reference':data['reference'],'builder_sha256':A.sha(__file__),'cage_sha256':A.sha(W/'rebuilt-body.json'),'whole_field_plan_sha256':A.sha(W/'whole-plan.json'),'canonical_installed':False,'user_acceptance':'pending','full_fin_body_motion_validation':'pending'}
report['complete_fin_banks_static_transfer']=root_report
(out/'build.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report))
