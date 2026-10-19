"""Match the oral lining UV to its actual adjacent skin rim without moving geometry."""
from pathlib import Path
import argparse,json,copy,hashlib
import numpy as np
from scipy.spatial import cKDTree
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();rows=[]
 for row in json.loads(a.plan.read_text())['items']:
  assert sha(row['source'])==row['source_sha256'];d,b=read_glb(Path(row['source']));old=copy.deepcopy(d);n=next(n for n in d['nodes']if n.get('name')=='Closed_body');pr=d['meshes'][n['mesh']]['primitives'];assert len(pr)==2
  skin=accessor(d,b,pr[0]['attributes']['POSITION']);uv=accessor(d,b,pr[0]['attributes']['TEXCOORD_0']);oral=accessor(d,b,pr[1]['attributes']['POSITION'])
  ks=[[tuple(np.round(v,7))for v in vs]for vs in [skin,oral]];shared=set(ks[0])&set(ks[1]);edge_sets=[]
  for p,keys in zip(pr,ks):
   edges=set()
   for tri in accessor(d,b,p['indices']).reshape(-1,3):
    for i,j in zip(tri,np.roll(tri,-1)):
     a1,b1=keys[i],keys[j]
     if a1 in shared and b1 in shared and a1!=b1:edges.add(tuple(sorted((a1,b1))))
   edge_sets.append(edges)
  edges=list(edge_sets[0]&edge_sets[1]);assert len(edges)>15;segments=np.array(edges);aa=segments[:,0];ab=segments[:,1]-aa;den=(ab*ab).sum(1);lookup={k:u for k,u in zip(ks[0],uv)};ua=np.array([lookup[e[0]]for e in edges]);ub=np.array([lookup[e[1]]for e in edges]);points=[];ids=[]
  for i,length in enumerate(np.sqrt(den)):
   ts=np.linspace(0,1,max(2,int(np.ceil(length/.0003))+1));points.extend(aa[i]+ts[:,None]*ab[i]);ids.extend([i]*len(ts))
  _,near=cKDTree(points).query(oral,k=12);ix=np.array(ids)[near];tt=np.clip(((oral[:,None,:]-aa[ix])*ab[ix]).sum(2)/den[ix],0,1);qq=aa[ix]+tt[:,:,None]*ab[ix];dd=np.linalg.norm(oral[:,None,:]-qq,axis=2);pick=dd.argmin(1);dist=dd[np.arange(len(oral)),pick];chosen=ix[np.arange(len(oral)),pick];t=tt[np.arange(len(oral)),pick]
  # Interior lining vertices explicitly project to the closest actual rim edge;
  # shared boundary vertices copy their exact adjacent skin UV instead.
  mapped=(ua[chosen]+t[:,None]*(ub[chosen]-ua[chosen])).astype('<f4')
  for i,k in enumerate(ks[1]):
   if k in lookup:mapped[i]=lookup[k]
  binary=bytearray(b);binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(mapped.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=mapped.nbytes,target=34962));ac=len(d['accessors']);d['accessors'].append(dict(bufferView=vi,componentType=5126,count=len(mapped),type='VEC2',min=mapped.min(0).tolist(),max=mapped.max(0).tolist()));pr[1]['attributes']['TEXCOORD_0']=ac
  for i in range(2):
   for key in ['POSITION','NORMAL','JOINTS_0','WEIGHTS_0','TEXCOORD_1']:assert pr[i]['attributes'].get(key)==old['meshes'][n['mesh']]['primitives'][i]['attributes'].get(key)
  assert pr[0]==old['meshes'][n['mesh']]['primitives'][0];target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);write(target,d,binary)
  rows.append(dict(species=row['species'],source_sha256=row['source_sha256'],model_sha256=sha(target),max_adjacent_skin_distance_native=float(dist.max()),boundary_uv_error_pixels=0,geometry_rig_animation_skin_uv0_fin_primitives_preserved=True))
 a.report.write_text(json.dumps(dict(ok=True,items=rows,plan_sha256=sha(a.plan),script_sha256=sha(__file__)),indent=2));print(json.dumps(dict(ok=True,fish=len(rows))))
if __name__=='__main__':main()
