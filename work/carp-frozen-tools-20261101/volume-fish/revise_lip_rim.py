"""Preserve an actual mouth rim, adding a small lip roll and measured recess coordinates.

Append-only GLB attributes; shared skin/interior boundary remains welded. UV0,
weights, rig, animations and images are unchanged. Skin UV1 encodes actual rim
distance; oral UV1 encodes transverse rim halfwidth and upper/lower identity.
The oral shader subtracts abs(fragment rest Z), so spanning triangles retain a
recess even when their vertices all lie on the aperture border.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from cli.volume_mouth import slit_v

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_text());records=[]
 for row in plan['items']:
  assert sha(row['source'])==row['source_sha256'];d,b=read_glb(Path(row['source']));old=copy.deepcopy(d);binary=bytearray(b);prefix=bytes(b);n=next(n for n in d['nodes']if n.get('name')=='Closed_body');prims=d['meshes'][n['mesh']]['primitives'];assert len(prims)==2
  arrays=[accessor(d,b,p['attributes']['POSITION'])for p in prims];indices=[accessor(d,b,p['indices']).reshape(-1,3)for p in prims]
  keys=[[tuple(np.round(v,7))for v in vs]for vs in arrays];sets=[set(k)for k in keys];shared=sets[0]&sets[1];assert len(shared)>15,'Missing actual aperture boundary'
  counts=[]
  for ks,tris in zip(keys,indices):
   edges=set()
   for tri in tris:
    for i,j in zip(tri,np.roll(tri,-1)):
     aa,bb=ks[i],ks[j]
     if aa in shared and bb in shared and aa!=bb:edges.add(tuple(sorted((aa,bb))))
   counts.append(edges)
  border=list(counts[0]&counts[1]);assert len(border)>15,'No shared skin/inner rim edges'
  segments=np.array(border);A=segments[:,0];AB=segments[:,1]-A;L=np.linalg.norm(AB,axis=1);samples=[];segids=[]
  for i,length in enumerate(L):
   t=np.linspace(0,1,max(2,int(np.ceil(length/.00045))+1));samples.extend(A[i]+t[:,None]*AB[i]);segids.extend([i]*len(t))
  tree=cKDTree(samples);segids=np.array(segids);den=(AB*AB).sum(1);radius=row['radius_native'];roll=row['roll_native'];assert 0<roll<=.001 and 0<radius<=.006
  path=np.array(row['slit_path']);aspect=row['source_height_over_width'];start=row['start_u'];moved={};rimdata=[];newarrays=[]
  def distances(vs):
   _,near=tree.query(vs,k=min(12,len(samples)));ix=segids[near];aa=A[ix];ab=AB[ix];t=np.clip(np.sum((vs[:,None,:]-aa)*ab,axis=2)/den[ix],0,1);q=aa+t[:,:,None]*ab;dist=np.linalg.norm(vs[:,None,:]-q,axis=2);pick=dist.argmin(1);return dist[np.arange(len(vs)),pick],q[np.arange(len(vs)),pick]
  for vs,ks in zip(arrays,keys):
   dist,q=distances(vs.astype(float));u=q[:,0]+.5;line=(.5-np.array([slit_v({'slit_path':row['slit_path']},float(x)) for x in u]))*aspect;branch=(q[:,1]>=line).astype(float)
   fade=np.clip((vs[:,0]+.5-start)/.012,0,1);fade=fade*fade*(3-2*fade);amount=roll*np.maximum(0,1-dist/radius)**2*fade;new=vs.copy()
   for i,k in enumerate(ks):
    if amount[i]<=1e-10:continue
    if k not in moved:
     pos=vs[i].copy();pos[1]+=amount[i]*(1 if branch[i] else -1);moved[k]=pos
    new[i]=moved[k]
   newarrays.append(new);rimdata.append(np.column_stack((dist if len(newarrays)==1 else np.abs(q[:,2]),branch)))
  def append(values,typ):
   v=np.asarray(values,dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));off=len(binary);binary.extend(v.tobytes());bv=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':v.nbytes,'target':34962});idx=len(d['accessors']);d['accessors'].append({'bufferView':bv,'componentType':5126,'count':len(v),'type':typ,'min':v.min(0).tolist(),'max':v.max(0).tolist()});return idx
  for si,(p,vs,new,ks,tris)in enumerate(zip(prims,arrays,newarrays,keys,indices)):
   attrs=p['attributes'];changed=np.any(vs!=new,axis=1);assert changed.any();attrs['POSITION']=append(new,'VEC3')
   nn=accessor(old,b,attrs['NORMAL']);normal=nn.copy();cross=np.cross(new[tris[:,1]]-new[tris[:,0]],new[tris[:,2]]-new[tris[:,0]]);sums={}
   touched=set()
   for tri in tris[np.any(changed[tris],axis=1)]:touched.update(ks[i]for i in tri)
   for tri,face in zip(tris,cross):
    for i in tri:
     k=ks[i]
     if k in touched:sums[k]=sums.get(k,np.zeros(3))+face
   for i,k in enumerate(ks):
    if k in sums and np.linalg.norm(sums[k])>1e-12:normal[i]=sums[k]/np.linalg.norm(sums[k])
   attrs['NORMAL']=append(normal,'VEC3')
   attrs['TEXCOORD_1']=append(rimdata[si],'VEC2')
   for field in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']:assert attrs[field]==old['meshes'][n['mesh']]['primitives'][si]['attributes'][field]
  assert binary[:len(prefix)]==prefix
  for field in ['nodes','skins','animations','materials','images','textures']:assert d.get(field)==old.get(field)
  target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);write(target,d,binary)
  records.append({'species':row['species'],'source_sha256':row['source_sha256'],'model_sha256':sha(target),'aperture_edges':len(border),'shared_boundary_vertices':len(shared),'rolled_welded_vertices':len(moved),'roll_native':roll,'radius_native':radius,'original_uv0_rig_images_animation_preserved':True,'original_bin_prefix_preserved':True,'oral_rim_uv1':'transverse rim halfwidth native, upper/lower identity; per-fragment width minus abs(rest Z) gives recess; skin UV1 holds actual rim distance'})
 a.output.write_text(json.dumps({'ok':True,'plan_sha256':sha(a.plan),'script_sha256':sha(__file__),'items':records},indent=2));print(json.dumps({'ok':True,'species':[r['species']for r in records]}))
if __name__=='__main__':main()
