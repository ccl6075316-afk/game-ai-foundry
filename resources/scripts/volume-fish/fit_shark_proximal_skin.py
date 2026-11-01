"""Fit explicit proximal shark skin to the actual490 finite-body trajectories.

Diagnostic construction only. No pose coverage, root domain, geometry, UV,
pixels or collision tolerance is changed. The new source needs real full gates.
"""
import json,sys,itertools
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import sha
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def skin(row,mat):
 p=np.c_[row['vertices_native'],np.ones(len(row['vertices_native']))];js=np.array(row['joints'],int).reshape(-1,4);ws=np.array(row['weights']).reshape(-1,4);return(np.einsum('pnsij,nj->pnsi',mat[:,js],p)*ws[None,:,:,None]).sum(2)
def main():
 C=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();compact=C/'compact/blacktip_reef_shark';rest=read(compact/'rest-skin.json');receipt=read(compact/'export.validation.json');assert len(receipt['samples'])==490 and sha(C/'fish.glb')==rest['model_sha256']==receipt['model_sha256'];mat=[]
 for row in receipt['samples']:
  assert sha(row['posed_mesh_json'])==row['sha256'];mat.append(read(row['posed_mesh_json'])['joint_matrices_m_per_native'])
 mat=np.array(mat);body=[];tri=[];bodyjs=[];bodyws=[];off=0
 for row in rest['surfaces']:
  if not row['body']:continue
  body.append(skin(row,mat));tri.extend(np.array(row['triangles']).reshape(-1,3)+off);bodyjs.extend(np.array(row['joints']).reshape(-1,4));bodyws.extend(np.array(row['weights']).reshape(-1,4));off+=len(row['vertices_native'])
 body=np.concatenate(body,axis=1);tri=np.array(tri);bodyjs=np.array(bodyjs);bodyws=np.array(bodyws);j_names=rest['joint_names'];a,b,c=body[0,tri[:,0]],body[0,tri[:,1]],body[0,tri[:,2]];ab=b-a;ac=c-a;aa=(ab*ab).sum(1);bb=(ab*ac).sum(1);cc=(ac*ac).sum(1);den=aa*cc-bb*bb;changes=[];metrics=[]
 for row in rest['surfaces']:
  if row['body']:continue
  pos=np.array(row['vertices_native']);js=np.array(row['joints']).reshape(-1,4);ws=np.array(row['weights']).reshape(-1,4);posed=skin(row,mat);root=set(row['root_ids']);seen=set()
  for i,p in enumerate(pos):
   key=tuple(np.round(p,7))
   if key in seen:continue
   seen.add(key);oldw={int(j):float(w)for j,w in zip(js[i],ws[i])if w>1e-6}
   if any(not(j_names[j].startswith('body_')or j_names[j]=='root')for j in oldw):continue
   q=posed[0,i];ap=q-a;dd=(ap*ab).sum(1);ee=(ap*ac).sum(1);v=(cc*dd-bb*ee)/np.maximum(den,1e-30);w=(aa*ee-bb*dd)/np.maximum(den,1e-30);betas=np.c_[1-v-w,v,w];closest=a+ab*v[:,None]+ac*w[:,None];valid=(betas>=-1e-7).all(1);distance=np.linalg.norm(closest-q,axis=1);distance[~valid]=1e9
   for x,y,k,l in[(a,b,0,1),(b,c,1,2),(c,a,2,0)]:
    edge=y-x;t=np.clip(((q-x)*edge).sum(1)/np.maximum((edge*edge).sum(1),1e-20),0,1);cp=x+t[:,None]*edge;dist=np.linalg.norm(cp-q,axis=1);mask=dist<distance;newbeta=np.zeros_like(betas);newbeta[:,k]=1-t;newbeta[:,l]=t;closest[mask]=cp[mask];betas[mask]=newbeta[mask];distance[mask]=dist[mask]
   fi=int(distance.argmin());ids=tri[fi]
   if i not in root and distance[fi]>.009:continue
   beta=betas[fi];normal=np.cross(body[:,ids[1]]-body[:,ids[0]],body[:,ids[2]]-body[:,ids[0]]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12);offset=float(np.dot(q-closest[fi],normal[0]));target=np.einsum('i,pij->pj',beta,body[:,ids])+normal*offset;candidates=sorted(set(int(j)for vi in ids for j,w in zip(bodyjs[vi],bodyws[vi])if w>1e-5)|set(oldw));features=np.einsum('pkij,j->pki',mat[:,candidates],np.r_[p,1]);errors=(features-target[:,None,:])*1000;w0=np.array([oldw.get(j,0)for j in candidates]);old_delta=np.einsum('pkj,k->pj',errors,w0);bound=max(float(abs(old_delta).max()),.01)+.01;best=None
   for size in range(1,min(4,len(candidates))+1):
    for subset in itertools.combinations(range(len(candidates)),size):
     ef=errors[:,subset,:];fn=np.einsum('pkj,pj->pk',ef,normal);xyz=ef.transpose(0,2,1).reshape(-1,size);A=np.r_[np.c_[fn,-np.ones(len(fn))],np.c_[-fn,-np.ones(len(fn))],np.c_[xyz,np.zeros(len(xyz))],np.c_[-xyz,np.zeros(len(xyz))]];B=np.r_[np.zeros(2*len(fn)),np.full(2*len(xyz),bound)];sol=linprog(np.r_[np.zeros(size),1],A_ub=A,b_ub=B,A_eq=[np.r_[np.ones(size),0]],b_eq=[1],bounds=[(0,1)]*size+[(0,None)],method='highs')
     if not sol.success:continue
     weights=sol.x[:size];weights[weights<1e-5]=0;weights/=weights.sum();delta=np.einsum('pkj,k->pj',ef,weights);score=float(abs(np.einsum('pj,pj->p',delta,normal)).max())
     if best is None or score<best[0]:best=(score,subset,weights)
   if best is None:continue
   oldscore=float(abs(np.einsum('pj,pj->p',old_delta,normal)).max());score,subset,neww=best;metrics.append({'fin':row['name'],'root':i in root,'old_normal_error_mm':oldscore,'fitted_normal_error_mm':score})
   if score+1e-5<oldscore:changes.append({'fin':row['name'],'position_gltf':p.tolist(),'weights':{j_names[candidates[k]]:float(w)for k,w in zip(subset,neww)if w>1e-6}})
 report=dict(ok=True,kind='shark_proximal_actual_pose_skin_fit',input_blend=str(C/'fish.blend'),input_blend_sha256=sha(C/'fish.blend'),model_sha256=sha(C/'fish.glb'),compact_export_sha256=sha(compact/'export.validation.json'),compact_rest_sha256=sha(compact/'rest-skin.json'),actual_pose_count=490,changes=changes,metrics=metrics,formal_acceptance=False,scope='Nonnegative normalized <=4 actual body influences; minimax normal error, component error bounded by previous worst+0.01mm. No geometry/UV/RGB/rig/actions or frozen-root domain/tolerance edits. New cold full gates mandatory.');out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'changes':len(changes),'max_old_normal_mm':max(x['old_normal_error_mm']for x in metrics),'max_fitted_normal_mm':max(x['fitted_normal_error_mm']for x in metrics)}))
if __name__=='__main__':main()
