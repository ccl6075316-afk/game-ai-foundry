"""Blender: source-width raised bands on an existing native oral boundary.

Uses the same surface-distance, native-pigment and measured-join method as
129/135/140, without recreating a black-sea-bream-specific voxel remesh.
Only decorative lip candidates are written. Body and rig are immutable.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def main(path):
 path=Path(path);plan=json.loads(path.read_text());root=path.parent
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 assert sha(plan['native_surface'])==plan['native_surface_sha256']
 body=json.loads(Path(plan['native_surface']).read_text());skin=body['parts'][0]
 v=np.array(skin['vertices']);n=np.array(skin['normals']);t=np.array(skin['triangles']).reshape(-1,3)[:,[0,2,1]]
 tree=BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True)
 def unit(q):return q/max(np.linalg.norm(q),1e-15)
 def project(q):
  hit,normal,face,dist=tree.find_nearest(Vector(q));a,b,c=v[t[face]];u=b-a;w=c-a;z=np.array(hit)-a;den=(u@u)*(w@w)-(u@w)**2
  bb=((w@w)*(z@u)-(u@w)*(z@w))/den;cc=((u@u)*(z@w)-(u@w)*(z@u))/den;weights=np.array([1-bb-cc,bb,cc])
  nn=unit(n[t[face]].T@weights)
  return np.array(hit),nn,t[face],weights
 rims=np.load(root/'source-rims.npz');cfg=plan['geometry'];count=cfg['longitudinal_samples'];cross=cfg['cross_samples'];parts=[];metrics=[]
 assert count==257 and cross==17,'135 correspondence contract'
 for name in ['upper','lower']:
  rim=rims[name];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(rim,axis=0),axis=1))];s=np.linspace(0,arc[-1],count);curve=np.array([np.interp(s,arc,rim[:,i])for i in range(3)]).T
  # Inward-starting rounded oral corners are preserved, not smoothed away.
  projected=[project(p)for p in curve];hook=plan['bands'][name].get('posterior_source_hook');hook_rows=0;hook_audit=[]
  if hook:
   hook_rows=int(hook['replace_rows']);assert 8<hook_rows<90
   # Only the posterior strip changes. The existing anterior arc and measured
   # central pigment joins retain their original rows and physical positions.
   for side in [-1,1]:
    end_index=hook_rows-3 if side<0 else count-1-(hook_rows-3)
    endpoint=projected[end_index][0];W,H=plan['source_size'];control=[]
    fallback=0;maximum_error=0.
    for xy in hook['source_path_px']:
     xy=np.array(xy)
     x=xy[0]/W-.5;y=(H*.5-xy[1])/W
     hit,_,_,_=tree.ray_cast(Vector((x,y,side*.25)),Vector((0,0,-side)))
     if hit is None:
      hit=project(np.array([x,y,side*abs(projected[end_index][0][2])]))[0];fallback+=1
     assert float(hit[2])*side>0,'Hook projected onto opposite skin'
     error=float(np.linalg.norm(np.array([hit[0]-x,hit[1]-y]))*W);maximum_error=max(maximum_error,error)
     assert error<2.,('Hook source outside native surface',xy.tolist(),error)
     control.append(np.array(hit))
    # Connect to the already measured3D commissure/rim, not a2D ray aimed
    # exactly at the open aperture (which has no skin to hit).
    ids=range(0,end_index+1) if side<0 else range(count-1,end_index-1,-1)
    control.extend(projected[i][0]for i in ids);poly=np.array(control)
    length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(poly,axis=0),axis=1))]
    for k,s0 in enumerate(np.linspace(0,length[-1],hook_rows-2)):
     if k==hook_rows-3:continue
     index=k if side<0 else count-1-k
     point=np.array([np.interp(s0,length,poly[:,j])for j in range(3)])
     projected[index]=project(point)
    hook_audit.append({'side':side,'rows':hook_rows,'fallback_points':fallback,'maximum_source_xy_error_px':maximum_error})
  curve=np.array([q[0]for q in projected]);normals=np.array([q[1]for q in projected]);tangent=np.array([unit(q)for q in np.gradient(curve,axis=0)]);raw_direction=np.cross(normals,tangent);direction=raw_direction.copy();direction[direction[:,1]*(1 if name=='upper'else -1)<0]*=-1;direction=np.array([unit(q)for q in direction])
  if hook:
   # A returned commissure rotates through more than90 degrees. Propagate the
   # existing cross-strip side instead of flipping it to global up at the bend.
   for ids in [range(hook_rows-1,-1,-1),range(count-hook_rows,count)]:
    previous=direction[hook_rows] if ids.start==hook_rows-1 else direction[count-hook_rows-1]
    for i in ids:
     d=unit(raw_direction[i]);d*=1 if d@previous>=0 else -1;direction[i]=d;previous=d
  bounds=np.array(plan['bands'][name]['source_bounds']);srcx=np.minimum((curve[:,0]+.5)*plan['source_size'][0],plan['bands'][name]['central_source_column']);outer=np.interp(srcx,bounds[:,0],bounds[:,1]);inner=np.interp(srcx,bounds[:,0],bounds[:,2]);slope=np.interp(srcx,bounds[:,0],np.gradient(bounds[:,2],bounds[:,0]));width=abs(outer-inner)/plan['source_size'][0]/np.sqrt(1+slope*slope)
  verts=[];uv=[];joints=[];weights=[];widths=[]
  def bind(point):
   hit,nn,ids,bw=project(point);merged={}
   for idx,f in zip(ids,bw):
    for joint,w in zip(skin['joints'][idx],skin['weights'][idx]):merged[int(joint)]=merged.get(int(joint),0)+float(f*w)
   ordered=sorted(merged,key=lambda k:-merged[k]);assert sum(merged[k]for k in ordered[4:])<=1e-5,'Lip skinning discards significant influence'
   jj=ordered[:4];ww=[merged[k]for k in jj];total=sum(ww);jj += [0]*(4-len(jj));ww=[w/total for w in ww]+[0]*(4-len(ww));return jj,ww
  for i in range(count):
   if i in [0,count-1]:
    verts.append(curve[i].tolist());uv.append([0.,0.]);jj,ww=bind(curve[i]);joints.append(jj);weights.append(ww);widths.append(0.);continue
   pathpts=[curve[i]];pathnorm=[normals[i]];d=direction[i].copy();walked=0.
   for step_i in range(300):
    remaining=width[i]-walked
    if remaining<1e-7:break
    d=unit(d-pathnorm[-1]*(d@pathnorm[-1]));step=min(cfg['projection_step_native'],remaining);point,nn,_,_=project(pathpts[-1]+d*step);distance=np.linalg.norm(point-pathpts[-1]);assert distance>step*.001,('Stalled native lip walk',name,i)
    if distance>remaining:point,nn,_,_=project(pathpts[-1]+(point-pathpts[-1])*(remaining/distance));distance=np.linalg.norm(point-pathpts[-1])
    pathpts.append(point);pathnorm.append(nn);walked+=distance
   assert abs(walked-width[i])<max(1e-7,width[i]*.005),(name,i,walked,width[i])
   pp=np.array(pathpts);pn=np.array(pathnorm);aa=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pp,axis=0),axis=1))];widths.append(walked)
   for f in np.linspace(0,1,cross):
    point=np.array([np.interp(f*walked,aa,pp[:,k])for k in range(3)]);point,nn,ids,bw=project(point);relief=cfg['surface_offset_native']+cfg['relief_native']*np.sin(np.pi*f)**2
    verts.append((point+nn*relief).tolist());uv.append((np.array(skin['uv'])[ids].T@bw).tolist());jj,ww=bind(point);joints.append(jj);weights.append(ww)
  def index(i,j):return 0 if i==0 else len(verts)-1 if i==count-1 else 1+(i-1)*cross+j
  faces=[]
  for i in range(count-1):
   for j in range(cross-1):
    for face in [(index(i,j),index(i+1,j),index(i+1,j+1)),(index(i,j),index(i+1,j+1),index(i,j+1))]:
     if len(set(face))==3:faces.append(face)
  verts=np.array(verts);faces=np.array(faces);nn=np.zeros_like(verts);norm=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]]);assert np.linalg.norm(norm,axis=1).min()>1e-15,'Collapsed native lip triangle';ref=np.array([project(q)[1]for q in verts[faces].mean(1)]);flip=(norm*ref).sum(1)<0;faces[flip]=faces[flip][:,[0,2,1]];norm=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]])
  for k in range(3):np.add.at(nn,faces[:,k],norm)
  nn/=np.maximum(np.linalg.norm(nn,axis=1),1e-20)[:,None]
  parts.append({'name':name,'vertices':verts.tolist(),'normals':nn.tolist(),'uv':uv,'triangles':faces[:,[0,2,1]].ravel().tolist(),'joints':joints,'weights':weights})
  metrics.append({'part':name,'vertices':len(verts),'faces':len(faces),'maximum_width_error':float(np.max(abs(np.array(widths)[1:-1]-width[1:-1]))),'maximum_relief_native':cfg['surface_offset_native']+cfg['relief_native'],'posterior_source_hook':hook_audit})
 (root/'lip-band.mesh.json').write_text(json.dumps({'parts':parts},separators=(',',':')))
 (root/'geometry.validation.json').write_text(json.dumps({'ok':True,'plan_sha256':sha(path),'builder_sha256':sha(__file__),'native_surface_sha256':sha(plan['native_surface']),'source_rims_sha256':sha(root/'source-rims.npz'),'body_geometry_unchanged':True,'parts':metrics,'limits':'Candidate only: whole triangle contact, native material joins, GPU and posed attachment require independent checks.'},indent=2))
 print(json.dumps(metrics),flush=True)
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1])
