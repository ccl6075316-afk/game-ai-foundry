"""Give an existing closed fin a tapered foil cross-section without new UVs.

This is a declared art construction, not a species thickness measurement. Root
faces are transported to the actual closed body, with barycentric body skin.
Existing topology, native pixels, source planform and rig/animation are retained.
"""
from pathlib import Path
import sys,json,hashlib,copy,struct
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import read as read_glb,write
from closed_body_index140 import build
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def accessor(d,b,index):
 a=d['accessors'][index];v=d['bufferViews'][a['bufferView']];dt=np.dtype('<'+{5126:'f4',5125:'u4',5123:'u2',5121:'u1'}[a['componentType']]);c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
 return np.ndarray((a['count'],c),dtype=dt,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',c*dt.itemsize),dt.itemsize)).copy()
def main():
 args=sys.argv[sys.argv.index('--')+1:];p=json.loads(Path(args[0]).read_text());src=Path(p['source']);assert sha(src)==p['source_sha256'];assert sha(p['body'])==p['body_sha256'];d,b=read_glb(src);old=copy.deepcopy(d);original=bytes(b);b=bytearray(b);out=Path(p['output']);out.mkdir(parents=True,exist_ok=True)
 body=json.loads(Path(p['body']).read_text());vv=[];tt=[];bs=[]
 for part in body['parts']:
  off=len(vv);vv.extend(part['vertices']);tt.extend((np.array(part['triangles']).reshape(-1,3)+off).tolist());bs.extend(dict(zip(j,w))for j,w in zip(part['joints'],part['weights']))
 bv=np.array(vv);bt=np.array(tt);volume=np.einsum('ij,ij->i',bv[bt[:,0]],np.cross(bv[bt[:,1]],bv[bt[:,2]])).sum()
 if volume<0:bt=bt[:,[0,2,1]]
 tree=BVHTree.FromPolygons(bv.tolist(),bt.tolist(),all_triangles=True);inside=build(bv,bt);plan=json.loads(Path(p['fin_plan']).read_text());spec=plan['items'][0];records=[]
 def put(idx,values):
  a=copy.deepcopy(d['accessors'][idx]);ctype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];values=np.asarray(values,dtype=ctype);b.extend(b'\0'*(-len(b)%4));off=len(b);b.extend(values.tobytes());a.update(bufferView=len(d['bufferViews']),byteOffset=0,count=len(values));a.pop('min',None);a.pop('max',None)
  if a['type']=='VEC3':a.update(min=values.min(0).tolist(),max=values.max(0).tolist())
  d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':values.nbytes});d['accessors'].append(a);return len(d['accessors'])-1
 for f in p['fins']:
  name=f['name'];node=next(n for n in d['nodes']if n.get('name')==name and'mesh'in n);prims=d['meshes'][node['mesh']]['primitives'];assert len(prims)==1;prim=prims[0];attrs=prim['attributes'];v=accessor(old,original,attrs['POSITION']).astype(float);n=accessor(old,original,attrs['NORMAL']).astype(float);j=accessor(old,original,attrs['JOINTS_0']).copy();weights=accessor(old,original,attrs['WEIGHTS_0']).astype(float);tri=accessor(old,original,prim['indices']).reshape(-1,3);axis=f['normal_axis'];span=f['span_axis'];scale=p['meters_per_native'];rootids=np.array(spec['fins'][name]['ids'],int);rootset=set(rootids.tolist());rootpos=np.array(spec['fins'][name]['rest_points_gltf']);assert np.max(np.linalg.norm(v[rootids]-rootpos,axis=1))<1e-6
  # Slice the real 2D mesh at many span stations; do not replace its concavity
  # with a convex hull or rescale its silhouette to an idealized generic fin.
  edges=np.unique(np.sort(np.vstack([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0);a=v[edges[:,0]];c=v[edges[:,1]];stations=np.linspace(v[:,span].min()+1e-8,v[:,span].max()-1e-8,300);lo=[];hi=[]
  for s in stations:
   valid=(a[:,span]-s)*(c[:,span]-s)<=0;valid&=abs(c[:,span]-a[:,span])>1e-10;aa=a[valid];cc=c[valid];xx=aa[:,0]+(s-aa[:,span])/(cc[:,span]-aa[:,span])*(cc[:,0]-aa[:,0]);assert len(xx);lo.append(xx.min());hi.append(xx.max())
  query=np.clip(v[:,span],stations[0],stations[-1]);back=np.interp(query,stations,lo);front=np.interp(query,stations,hi);chord=np.maximum(front-back,1e-7);u=np.clip((front-v[:,0])/chord,0,1)
  shape=.2969*np.sqrt(u)-.1260*u-.3516*u**2+.2843*u**3-.1036*u**4
  half=np.maximum(f['edge_mm']/2000/scale,5*f['thickness_ratio']*chord*shape);half=np.minimum(half,f['max_thickness_mm']/2000/scale)
  # The old two-sided shell has local normal sign. Preserve any existing mild
  # camber by estimating the center from both source-UV mates when available.
  uv=accessor(old,original,attrs['TEXCOORD_0']);groups={}
  for i,q in enumerate(uv):groups.setdefault(tuple(q),[]).append(i)
  centre=np.zeros(len(v));paired=0
  for ids in groups.values():
   pp=v[ids,axis];centre[ids]=(pp.min()+pp.max())*.5
   if len(ids)==2:paired+=2
  sign=np.where(n[:,axis]>=0,1.,-1.);new=v.copy();new[:,axis]=centre+sign*half
  roots=[];moved_free=0
  for i,q in enumerate(new):
   hit,normal,face,distance=tree.find_nearest(Vector(q))
   if i in rootset:
    new[i]=np.array(hit-normal*p['root_inset_native']);roots.append(i)
    aa,bb,cc=bt[face];bw=barycentric_transform(hit,Vector(bv[aa]),Vector(bv[bb]),Vector(bv[cc]),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
    for vi,gain in zip((aa,bb,cc),bw):
     for bone,amount in bs[vi].items():mix[bone]=mix.get(bone,0)+max(0,gain)*amount
    items=sorted(mix.items(),key=lambda x:-x[1])[:4]
    while len(items)<4:items.append((0,0.))
    total=sum(x[1]for x in items);j[i]=[x[0]for x in items];weights[i]=[x[1]/total for x in items]
   elif distance<p['free_clearance_native']or inside(q):
    new[i]=np.array(hit+normal*p['free_clearance_native']);moved_free+=1
  # Recompute smooth normals from the authored closed shell winding.
  normals=np.zeros_like(new);face_norm=np.cross(new[tri[:,1]]-new[tri[:,0]],new[tri[:,2]]-new[tri[:,0]])
  for k in range(3):np.add.at(normals,tri[:,k],face_norm)
  lengths=np.linalg.norm(normals,axis=1);valid=lengths>1e-12;normals[valid]/=lengths[valid,None];normals[~valid]=n[~valid]
  attrs['POSITION']=put(attrs['POSITION'],new);attrs['NORMAL']=put(attrs['NORMAL'],normals);attrs['JOINTS_0']=put(attrs['JOINTS_0'],j);attrs['WEIGHTS_0']=put(attrs['WEIGHTS_0'],weights)
  if 'TANGENT'in attrs:
   tangent=accessor(old,original,attrs['TANGENT']).copy();t=tangent[:,:3];t-=normals*np.einsum('ij,ij->i',t,normals)[:,None];t/=np.maximum(np.linalg.norm(t,axis=1)[:,None],1e-12);tangent[:,:3]=t;attrs['TANGENT']=put(attrs['TANGENT'],tangent)
  spec['fins'][name]['rest_points_gltf']=new[rootids].tolist();spec['fins'][name]['rule']='Whole frozen root band transported to finite body, tapered foil volume159; unchanged source planform and UV, finite clearance still pending'
  records.append({'name':name,'normal_axis':axis,'thickness_ratio':f['thickness_ratio'],'nominal_full_thickness_mm_percentiles':np.percentile(half*2*scale*1000,[0,50,90,100]).tolist(),'root_vertices':len(roots),'free_vertices_clearance_adjusted':moved_free,'uv_pair_fraction':paired/len(v),'native_pixels_uv_topology_preserved':True})
 assert bytes(b[:len(original)])==original
 for key in ['animations','images','textures','samplers','skins','nodes']:assert d.get(key)==old.get(key),key
 target=out/'fish.glb';write(target,d,b);spec.update(model=str(target),model_sha256=sha(target));spec['membrane_clearance']['targets']=[f['name']for f in p['fins']];spec['repair_body_geometry']=p['body'];spec['repair_body_geometry_sha256']=sha(p['body']);(out/'candidate.plan.json').write_text(json.dumps(plan,indent=2));report={'ok':True,'model_sha256':sha(target),'source_sha256':sha(src),'plan_sha256':sha(args[0]),'records':records,'scope':'Foil construction candidate, not species-measured thickness. Body/static features/native pixels/UV/topology/rig/animation untouched; full finite root/free-surface and visual/action tests required.'};(out/'build.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
