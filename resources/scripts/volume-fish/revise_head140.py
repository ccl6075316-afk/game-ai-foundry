"""Blender: bounded additive head corrections and lips on the actual oral rim.

Material reference arrays, UV, topology and rig weights remain distinct from
new geometry. Raised strips are projected onto the final exterior surface.
"""
import sys,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def unit(v):return v/max(np.linalg.norm(v),1e-20)
def bary(p,q):
 a,b,c=q;u=b-a;v=c-a;w=p-a;uu=u@u;uv=u@v;vv=v@v;den=uu*vv-uv*uv
 assert den>1e-25
 y=(vv*(w@u)-uv*(w@v))/den;z=(uu*(w@v)-uv*(w@u))/den
 return np.array([1-y-z,y,z])

path=Path(sys.argv[sys.argv.index('--')+1]);cfg=json.loads(path.read_text());out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=True)
for p,h in cfg['frozen_inputs'].items():assert sha(p)==h,p
data=json.loads(Path(cfg['body']).read_text());parts=data['parts'];allv=np.concatenate([p['vertices'] for p in parts])
_,first,inv=np.unique(np.round(allv,7),axis=0,return_index=True,return_inverse=True);original=allv[first].copy();v=original.copy();tri=[];offset=0
for part in parts:
 tri.append(inv[np.array(part['triangles']).reshape(-1,3)+offset]);offset+=len(part['vertices'])
tri=np.concatenate(tri)
if cfg.get('crown_curve'):
 c=cfg['crown_curve'];stations=np.linspace(c['start_x'],c['end_x'],161);tree=BVHTree.FromPolygons(original.tolist(),tri.tolist(),all_triangles=True);before=[]
 for x in stations:
  hit,_,_,_=tree.ray_cast(Vector((x,.4,0)),Vector((0,-1,0)));assert hit is not None;before.append(hit.y)
 t=(stations-c['start_x'])/(c['end_x']-c['start_x']);span=c['end_x']-c['start_x'];y0,y1=c['heights'];d0,d1=c['slopes']
 target=(2*t**3-3*t*t+1)*y0+(t**3-2*t*t+t)*span*d0+(-2*t**3+3*t*t)*y1+(t**3-t*t)*span*d1
 correction=np.maximum(target-before,0);amount=np.interp(original[:,0],stations,correction,left=0,right=0)
 weight=smooth((original[:,1]-c['lower_y'])/c['fade_y']);v[:,1]+=amount*weight
for fill in cfg.get('fills',[]):
 t=(original[:,0]-fill['center_x'])/fill['radius_x'];weight=np.maximum(1-t*t,0)**3
 weight*=smooth((original[:,1]-fill['lower_y'])/fill['fade_y']) if fill['side']=='upper' else smooth((fill['upper_y']-original[:,1])/fill['fade_y'])
 v[:,1]+=fill['delta_y']*weight
 v[:,2]*=1+fill.get('width_increase',0)*weight
if cfg.get('upper_cap'):
 c=cfg['upper_cap'];support=smooth((original[:,0]-c['start_x'])/(c['full_x']-c['start_x']))*smooth((original[:,1]-c['lower_y'])/c['fade_y'])
 radial=((original[:,1]-c['center_y'])/c['radius_y'])**2+c.get('transverse_coefficient',.35)*(original[:,2]/c['radius_z'])**2
 limit=c['center_x']+c['radius_x']*np.sqrt(np.maximum(1-radial,0))
 v[:,0]-=np.maximum(v[:,0]-limit,0)*support
if cfg.get('round_upper_tip'):
 c=cfg['round_upper_tip'];edges=np.unique(np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0)
 aa=np.r_[edges[:,0],edges[:,1]];bb=np.r_[edges[:,1],edges[:,0]];degree=np.bincount(aa,minlength=len(v))
 weight=smooth((original[:,0]-c['start_x'])/(c['full_x']-c['start_x']))*smooth((original[:,1]-c['lower_y'])/c['fade_y'])
 for _ in range(c['iterations']):
  total=np.zeros_like(v);np.add.at(total,aa,v[bb]);target=total/np.maximum(degree[:,None],1)
  delta=(target-v)*c['factor']*weight[:,None];delta[:,2]*=.25
  v+=delta;change=v-original;length=np.linalg.norm(change,axis=1);v=original+change*np.minimum(1,c['maximum_displacement']/np.maximum(length,1e-20))[:,None]
for eye in cfg.get('protected_eyes',[]):
 radius=np.linalg.norm((original-eye['center'])/eye['radius'],axis=1);guard=smooth((radius-1)/.4)
 v=original+(v-original)*guard[:,None]
change=np.linalg.norm(v-original,axis=1);changed=change>1e-10
norm=np.zeros_like(v);cross=np.cross(v[tri[:,2]]-v[tri[:,0]],v[tri[:,1]]-v[tri[:,0]])
for k in range(3):np.add.at(norm,tri[:,k],cross)
norm/=np.maximum(np.linalg.norm(norm,axis=1),1e-20)[:,None]
offset=0
for part in parts:
 ids=inv[offset:offset+len(part['vertices'])];offset+=len(ids);oldn=np.array(part['normals']);newn=norm[ids].copy();newn[(newn*oldn).sum(1)<0]*=-1
 blend=smooth(change[ids]/.001);combined=oldn*(1-blend[:,None])+newn*blend[:,None];combined/=np.maximum(np.linalg.norm(combined,axis=1),1e-20)[:,None];combined[~changed[ids]]=oldn[~changed[ids]]
 part['normals']=combined.tolist();part['vertices']=v[ids].astype('f4').astype(float).tolist()
body=out/'body.bound.json';body.write_text(json.dumps(data,separators=(',',':')))
receipt=json.loads(Path(cfg['skinning_report']).read_text());receipt.update(ok=True,plan_sha256=sha(path),body_sha256=sha(body),geometry_revision='140; original exact per-vertex rig binding preserved')
(out/'skinning.validation.json').write_text(json.dumps(receipt,indent=2))
if cfg.get('upper_lip_cap_surface') is not None:
 si=cfg['upper_lip_cap_surface'];cap=json.loads(json.dumps(parts[si]));points=np.array(cap['vertices']);normals=np.array(cap['normals']);ymin,ymax=cfg['upper_lip_cap_y'];f=np.clip((np.array(cap['reference_positions'])[:,1]-ymin)/(ymax-ymin),0,1);relief=cfg['upper_lip_cap_relief']*np.sin(np.pi*f)**2
 points+=normals*relief[:,None];cap['vertices']=points.tolist();cap['name']='upper';(out/'upper-lip.bound.json').write_text(json.dumps({'parts':[cap]},separators=(',',':')))

if cfg.get('bands'):
 outer_ids=cfg.get('outer_surfaces',[0]);oral_ids=cfg.get('oral_surfaces',[1]);sets=[]
 for selected in [outer_ids,oral_ids]:
  edges=Counter()
  for si in selected:
   part=parts[si];p=[tuple(x) for x in np.round(np.array(part['vertices']),7)]
   for face in np.array(part['triangles']).reshape(-1,3):
    for a,b in zip(face,np.roll(face,-1)):edges[tuple(sorted((p[a],p[b])))]+=1
  sets.append({e for e,n in edges.items() if n==1})
 common=sets[0]&sets[1];neighbors=defaultdict(list)
 for a,b in common:neighbors[a].append(b);neighbors[b].append(a)
 assert neighbors
 if cfg.get('guide_lips'):
  # Surface partitions can contain additional seams and four-way boundary
  # junctions. Locate the intended oral branch with the frozen accepted lip
  # guide, then snap to actual shared edges; never guess the entire partition
  # boundary is a single mouth loop.
  guides={p['name']:p for p in json.loads(Path(cfg['guide_lips']).read_text())['parts']}
  segments=np.array(list(common));a=segments[:,0];ab=segments[:,1]-a;den=(ab*ab).sum(1)
  paths=[]
  for name in ['upper','lower']:
   q=np.array(guides[name]['vertices']);q=np.concatenate([q[:1],q[1:-1].reshape(255,17,3)[:,0],q[-1:]])
   selected=[]
   for point in q:
    t=np.clip(((point-a)*ab).sum(1)/den,0,1);projections=a+t[:,None]*ab;dist=((projections-point)**2).sum(1);selected.append(projections[dist.argmin()])
   paths.append(np.array(selected))
 else:
  assert all(len(q)==2 for q in neighbors.values()),('Ambiguous actual oral branch',Counter(map(len,neighbors.values())))
  start=min((p for p in neighbors if p[2]<-1e-7),key=lambda p:(p[0],-p[1]));end=min((p for p in neighbors if p[2]>1e-7),key=lambda p:(p[0],-p[1]));paths=[]
  for neighbor in neighbors[start]:
   p=[start];prev=start;cur=neighbor
   while cur!=end:
    p.append(cur);nxt=next(q for q in neighbors[cur] if q!=prev);prev,cur=cur,nxt
    assert len(p)<=len(neighbors)
   paths.append(np.array(p+[end]))
  paths.sort(key=lambda p:p[:,1].mean(),reverse=True)
 vv=[];nn=[];refs=[];uvs=[];joints=[];weights=[];tt=[];offset=0
 for si in outer_ids:
  part=parts[si];vv.extend(part['vertices']);nn.extend(part['normals']);refs.extend(part['reference_positions']);uvs.extend(part['uv']);joints.extend(part['joints']);weights.extend(part['weights']);tt.extend((np.array(part['triangles']).reshape(-1,3)[:,[0,2,1]]+offset).tolist());offset+=len(part['vertices'])
 vv=np.array(vv);nn=np.array(nn);tt=np.array(tt);refs=np.array(refs);uvs=np.array(uvs);joints=np.array(joints);weights=np.array(weights)
 tree=BVHTree.FromPolygons(vv.tolist(),tt.tolist(),all_triangles=True)
 def project(p):
  point,normal,face,distance=tree.find_nearest(Vector(p));assert point is not None
  b=bary(np.array(point),vv[tt[face]]);normal=unit(nn[tt[face]].T@b)
  return np.array(point),normal,face,b,float(distance)
 lip_parts=[];metrics={}
 for name,c in cfg['bands'].items():
  p=paths[0 if name=='upper' else 1];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];station=np.linspace(0,arc[-1],257);curve=np.array([np.interp(station,arc,p[:,k]) for k in range(3)]).T
  # Keep the actual aperture edge rather than advecting an old rim through a
  # different remesh. Every cross row walks outward on the final exterior.
  normals=np.array([project(q)[1] for q in curve]);tangent=np.gradient(curve,axis=0);direction=np.cross(normals,tangent);direction[direction[:,1]*(1 if name=='upper' else -1)<0]*=-1
  verts=[];norms=[];uv=[];uv2=[];js=[];ws=[];widths=[];base=[]
  bounds=np.array(c['source_bounds']);source_w,source_h=cfg['source_size']
  existing=None
  if cfg.get('guide_lips'):
   old=np.array(guides[name]['vertices']);existing=np.concatenate([np.repeat(old[:1,None,:],17,axis=1),old[1:-1].reshape(255,17,3),np.repeat(old[-1:,None,:],17,axis=1)])
  for i in range(257):
   center,normal,face,b,_=project(curve[i]);source_x=float((refs[tt[face]].T@b)[0]+.5)*source_w;sx=min(source_x,c['central_source_column']);outer=np.interp(sx,bounds[:,0],bounds[:,1]);inner=np.interp(sx,bounds[:,0],bounds[:,2]);slope=np.interp(sx,bounds[:,0],np.gradient(bounds[:,2],bounds[:,0]));width=abs(outer-inner)/source_w/np.sqrt(1+slope*slope)*c.get('width_scale',1)
   if existing is not None:
    # Preserve the source-calibrated full cross-band and transport it through
    # the same bounded body field, then reproject every point. Partition seams
    # at the mouth corners are not reliable tangent-walk boundaries.
    samples=existing[i].copy();samples=samples[0]+(samples-samples[0])*cfg.get('band_cross_scale',{}).get(name,1.);previous=samples.copy()
    for fill in cfg.get('fills',[]):
     t=(previous[:,0]-fill['center_x'])/fill['radius_x'];ww=np.maximum(1-t*t,0)**3
     ww*=smooth((previous[:,1]-fill['lower_y'])/fill['fade_y']) if fill['side']=='upper' else smooth((fill['upper_y']-previous[:,1])/fill['fade_y'])
     samples[:,1]+=fill['delta_y']*ww;samples[:,2]*=1+fill.get('width_increase',0)*ww
    projected=[project(q) for q in samples];points=np.array([q[0] for q in projected]);normals_path=np.array([q[1] for q in projected]);lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))];distance=lengths[-1];width=distance
   else:
    points=[center];normals_path=[normal];distance=0.;d=unit(direction[i]);lengths=[0.]
    for _ in range(240):
     remain=width-distance
     if remain<1e-7:break
     d=unit(d-normals_path[-1]*(d@normals_path[-1]));q,n,_,_,_=project(points[-1]+d*min(.00015,remain));step=np.linalg.norm(q-points[-1])
     assert step>1e-10,('Lip surface walk stalled',name,i)
     points.append(q);normals_path.append(n);distance+=step;lengths.append(distance)
    assert distance>=width-1e-7
   points=np.array(points);normals_path=np.array(normals_path);widths.append(distance)
   fractions=[0.] if i in [0,256] else np.linspace(0,1,17)
   for f in fractions:
    q=np.array([np.interp(f*width,lengths,points[:,k]) for k in range(3)]);q,n,face,b,_=project(q)
    taper=smooth(i/10)*smooth((256-i)/10);relief=(cfg['relief_native']*np.sin(np.pi*f)**2+cfg['surface_offset_native'])*taper
    verts.append((q+n*relief).tolist());norms.append(n.tolist());base.append(q.tolist());uv.append((uvs[tt[face]].T@b).tolist());uv2.append([0,0])
    accum={}
    for at,jw in zip(tt[face],b):
     for j,w in zip(joints[at],weights[at]):accum[int(j)]=accum.get(int(j),0)+max(0.,float(jw*w))
    ordered=sorted(accum.items(),key=lambda z:-z[1])[:4];total=sum(w for j,w in ordered);ordered+= [(0,0)]*(4-len(ordered));js.append([j for j,w in ordered]);ws.append([w/total for j,w in ordered])
  def idx(i,j):return 0 if i==0 else len(verts)-1 if i==256 else 1+(i-1)*17+j
  faces=[];verts=np.array(verts)
  for i in range(256):
   for j in range(16):
    for face in [(idx(i,j),idx(i+1,j),idx(i+1,j+1)),(idx(i,j),idx(i+1,j+1),idx(i,j+1))]:
     if len(set(face))==3:faces.append(face)
  faces=np.array(faces);cross=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]]);ref=np.array(norms)[faces].mean(1);flip=(cross*ref).sum(1)<0;faces[flip]=faces[flip][:,[0,2,1]]
  lip_parts.append({'name':name,'vertices':verts.tolist(),'normals':norms,'uv':uv,'uv2':uv2,'colors':[[0,0,0,1]]*len(verts),'triangles':faces[:,[0,2,1]].ravel().tolist(),'joints':js,'weights':ws})
  metrics[name]={'actual_aperture_edges':len(common),'source_width_native_min_max':[float(min(widths)),float(max(widths))],'maximum_relief_native':cfg['relief_native'],'all_rows_on_final_exterior':True,'branch_locator':'Frozen source-calibrated139 strip transported through body field and individually reprojected; actual shared-edge graph used for branch diagnosis.'}
 (out/'lips.raw.json').write_text(json.dumps({'parts':lip_parts},separators=(',',':')))
report={'ok':True,'species':cfg['species'],'plan_sha256':sha(path),'changed_unique_vertices':int(changed.sum()),'maximum_body_displacement_native':float(change.max()),'posterior_changed':int(changed[original[:,0]<cfg.get('minimum_change_x',.35)].sum()),'lip_metrics':metrics if cfg.get('bands') else {},'scope':'Bounded local candidate. Original weights/topology/UV/reference semantics retained; actual visual, posed fins and GPU checks required.'}
if cfg.get('crown_curve'):report['crown_constraint']={'stations':stations.tolist(),'old_midline_y':before,'target_hermite_y':target.tolist(),'nonnegative_fill_native':correction.tolist(),'scope':'Artistically continuous envelope frozen from this fish endpoints/tangents, not biological measurements.'}
(out/'geometry.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
