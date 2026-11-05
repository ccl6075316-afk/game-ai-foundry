"""Ordinary native closed lenses/open caps: physical identity and finite support.

Normal-induced export aliases do not change physical topology. Every oriented
triangle corner retains its original physical source vertex and native UV.
The independent portable077 body/opacity/GPU tests remain unchanged.
"""
import io,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from PIL import Image
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
key=lambda p:tuple(np.rint(np.asarray(p)*1e7).astype(np.int64))
gltf=lambda p:np.asarray(p)[...,[0,2,1]]*np.array([1,1,-1])
def closest_distance(p,tri):
 a=tri[:,0];ab=tri[:,1]-a;ac=tri[:,2]-a;ap=p-a;aa=np.einsum('ij,ij->i',ab,ab);bb=np.einsum('ij,ij->i',ab,ac);cc=np.einsum('ij,ij->i',ac,ac);ad=np.einsum('ij,ij->i',ab,ap);cd=np.einsum('ij,ij->i',ac,ap);den=aa*cc-bb*bb;valid=den>1e-20;v=np.zeros(len(a));w=v.copy();v[valid]=(cc[valid]*ad[valid]-bb[valid]*cd[valid])/den[valid];w[valid]=(aa[valid]*cd[valid]-bb[valid]*ad[valid])/den[valid];q=a+v[:,None]*ab+w[:,None]*ac;ds=np.linalg.norm(q-p,axis=1);ds[~(valid&(v>=0)&(w>=0)&(v+w<=1))]=np.inf
 for k,j in [(0,1),(1,2),(2,0)]:
  start=tri[:,k];d=tri[:,j]-start;t=np.clip(np.einsum('ij,ij->i',p-start,d)/np.maximum(np.einsum('ij,ij->i',d,d),1e-30),0,1);ds=np.minimum(ds,np.linalg.norm(start+t[:,None]*d-p,axis=1))
 return float(ds.min())
def primitive(doc,node):
 p=doc['meshes'][node['mesh']]['primitives'];assert len(p)==1;return p[0]
def node(doc,name):return next(n for n in doc['nodes']if n.get('name')==name and'mesh'in n)
def image(doc,blob,pr):
 mat=doc['materials'][pr['material']];pbr=mat['pbrMetallicRoughness'];assert mat.get('alphaMode','OPAQUE')=='OPAQUE'and pbr.get('baseColorFactor',[1]*4)[3]==1 and set(mat.get('extensions',{}))<={'KHR_materials_specular'};tex=doc['textures'][pbr['baseColorTexture']['index']];img=doc['images'][tex['source']];assert'bufferView'in img and'uri'not in img;bv=doc['bufferViews'][img['bufferView']];raw=blob[bv.get('byteOffset',0):bv.get('byteOffset',0)+bv['byteLength']];rgba=np.array(Image.open(io.BytesIO(raw)).convert('RGBA'));return {'png_sha256':hashlib.sha256(raw).hexdigest(),'rgba_sha256':hashlib.sha256(rgba.tobytes()).hexdigest(),'size':[rgba.shape[1],rgba.shape[0]]},rgba
def topology(ids,tri):
 edges=Counter();dirs=Counter()
 for f in tri:
  q=[int(ids[i])for i in f];assert len(set(q))==3
  for a,b in zip(q,q[1:]+q[:1]):e=tuple(sorted([a,b]));edges[e]+=1;dirs[e]+=1 if a<b else-1
 assert edges and set(edges.values())<={1,2};assert all(dirs[e]==0 for e,n in edges.items()if n==2);boundary={e for e,n in edges.items()if n==1};verts=set(map(int,ids));euler=len(verts)-len(edges)+len(tri)
 if boundary:
  graph=defaultdict(set)
  for a,b in boundary:graph[a].add(b);graph[b].add(a)
  assert all(len(v)==2 for v in graph.values());seen=set();pending=[next(iter(graph))]
  while pending:
   x=pending.pop()
   if x not in seen:seen.add(x);pending.extend(graph[x]-seen)
  assert seen==set(graph)and euler==1
 else:assert euler==2 and len(tri)==2*len(verts)-4
 return {'physical_vertices':len(verts),'triangles':len(tri),'boundary_edges':len(boundary),'closed':not boundary}
def face_signature(ids,uv,tri):
 def oriented(f):
  q=[(int(ids[i]),float(uv[i,0]),float(uv[i,1]))for i in f];return min(tuple(q[k:]+q[:k])for k in range(3))
 return Counter(oriented(f)for f in tri)
def baseline(model,release,species):
 release=Path(release).resolve();record=json.loads(release.read_text());assert record['user_acceptance']is True;row=next(r for r in record['fish']if r['species']==species);assert row['model']['sha256']==sha(model);doc,blob=read_glb(model);body=node(doc,'Closed_body');bodytri=[]
 for pr in doc['meshes'][body['mesh']]['primitives']:p=arrays(doc,blob,pr['attributes']['POSITION']);bodytri.extend(p[arrays(doc,blob,pr['indices']).reshape(-1,3)].tolist())
 eyes=[]
 for n in doc['nodes']:
  if'mesh'not in n or not('Eye_relief'in n['name']or'Native_eye'in n['name']):continue
  pr=primitive(doc,n);p=arrays(doc,blob,pr['attributes']['POSITION']);uv=arrays(doc,blob,pr['attributes']['TEXCOORD_0']);tri=arrays(doc,blob,pr['indices']).reshape(-1,3);keys=sorted(set(key(q)for q in p));ids=[keys.index(key(q))for q in p];physical=[p[ids.index(i)].tolist()for i in range(len(keys))];sig,_=image(doc,blob,pr);eyes.append({'name':n['name'],'positions_gltf':physical,'row_source_ids':ids,'uv':uv.tolist(),'triangles':tri.tolist(),'topology':topology(ids,tri),'material':sig})
 assert len(eyes)==2;return {'kind':'accepted_ordinary_native_eye_snapshot','species':species,'accepted_release':{'path':str(release),'sha256':sha(release)},'accepted_model_sha256':sha(model),'body_triangles_gltf':bodytri,'eyes':eyes}
def verify(doc,blob,plan,n,definition):
 assert definition['kind']=='native_body_supported_eye'and definition['underlying_body']==plan['body'];path=Path(definition['binding_report']);assert sha(path)==definition['binding_report_sha256'];report=json.loads(path.read_text());assert report['model_sha256']==plan['model_sha256']and report['kind']=='ordinary_native_eyes_actual_finite_support';snapref=report['baseline'];assert sha(snapref['path'])==snapref['sha256'];snap=json.loads(Path(snapref['path']).read_text());assert snap['kind']=='accepted_ordinary_native_eye_snapshot'and snap['species']==plan['species'];rel=snap['accepted_release'];assert sha(rel['path'])==rel['sha256'];release=json.loads(Path(rel['path']).read_text());assert release['user_acceptance']is True;assert next(r for r in release['fish']if r['species']==plan['species'])['model']['sha256']==snap['accepted_model_sha256'];old=next(e for e in snap['eyes']if e['name']==n['name']);eye=next(e for e in report['eyes']if e['name']==n['name']);bindings=eye['bindings'];oldpos=np.array(old['positions_gltf']);oldbody=np.array(snap['body_triangles_gltf']);pr=primitive(doc,n);p=arrays(doc,blob,pr['attributes']['POSITION']);uv=arrays(doc,blob,pr['attributes']['TEXCOORD_0']);tri=arrays(doc,blob,pr['indices']).reshape(-1,3);assert len(bindings)==len(oldpos);sources=gltf([b['source_position_native']for b in bindings]);oldids=[]
 for q in sources:
  dist=np.linalg.norm(oldpos-q,axis=1);assert dist.min()<2e-6;oldids.append(int(dist.argmin()))
 assert len(set(oldids))==len(oldpos);expected=np.array([gltf(b['support_native'])+gltf(b['source_normal'])*b['normal_offset_native']for b in bindings]);rowbind=[]
 for q in p:
  ds=np.linalg.norm(expected-q,axis=1);assert ds.min()<2e-6;rowbind.append(int(ds.argmin()))
 assert set(rowbind)==set(range(len(bindings)));ids=np.array([oldids[i]for i in rowbind]);assert face_signature(ids,uv,tri)==face_signature(np.array(old['row_source_ids']),np.array(old['uv']),np.array(old['triangles'])),'Native physical oriented face/corner UV identity changed';top=topology(ids,tri);assert top==old['topology'];sig,rgba=image(doc,blob,pr);assert sig==old['material'],'Original eye pixel donor changed';H,W=rgba.shape[:2];x0=max(0,int(np.floor(uv[:,0].min()*W)));x1=min(W,int(np.floor(uv[:,0].max()*W))+1);y0=max(0,int(np.floor(uv[:,1].min()*H)));y1=min(H,int(np.floor(uv[:,1].max()*H))+1);assert x1>x0 and y1>y0 and np.all(rgba[y0:y1,x0:x1,3]==255)
 body=node(doc,plan['body']);bn=[doc['nodes'][i]['name']for i in doc['skins'][body['skin']]['joints']];bypos={};bodytri=[]
 for bp in doc['meshes'][body['mesh']]['primitives']:
  a=bp['attributes'];bpv=arrays(doc,blob,a['POSITION']);bj=arrays(doc,blob,a['JOINTS_0']);bw=arrays(doc,blob,a['WEIGHTS_0']);bodytri.extend(bpv[arrays(doc,blob,bp['indices']).reshape(-1,3)])
  for q,j,w in zip(bpv,bj,bw):
   named={bn[int(i)]:float(x)for i,x in zip(j,w)if x>1e-7};k=key(q)
   if k in bypos:assert set(named)==set(bypos[k])and max(abs(named[n]-bypos[k][n])for n in named)<2e-5
   bypos[k]=named
 bodytri=np.array(bodytri);actualbody=bodytri.reshape(-1,3);triset={tuple(sorted(key(q)for q in t))for t in bodytri};en=[doc['nodes'][i]['name']for i in doc['skins'][n['skin']]['joints']];ej=arrays(doc,blob,pr['attributes']['JOINTS_0']);ew=arrays(doc,blob,pr['attributes']['WEIGHTS_0']);assert np.isfinite(p).all()and np.isfinite(ew).all()and np.all(ew>=0)and np.all(abs(ew.sum(1)-1)<1e-5);maxerr=0;peak=0
 for j,b in enumerate(bindings):
  t=gltf(b['body_triangle_positions_native']);matched=[]
  for point in t:
   ds=np.linalg.norm(actualbody-point,axis=1);assert ds.min()<2e-6,'Missing actual finite body vertex';matched.append(actualbody[int(ds.argmin())])
  t=np.array(matched);bc=np.array(b['barycentric']);assert tuple(sorted(key(q)for q in t))in triset;assert bc.min()>-1e-4 and abs(bc.sum()-1)<1e-5;bc=np.maximum(bc,0);bc/=bc.sum();support=bc@t;assert np.linalg.norm(support-gltf(b['support_native']))<2e-6;normal=gltf(b['source_normal']);assert abs(np.linalg.norm(normal)-1)<1e-5;offset=b['normal_offset_native'];assert offset>=(-.00004 if top['closed']else-1e-7);q=expected[j];distance=closest_distance(q,bodytri);olddistance=closest_distance(oldpos[oldids[j]],oldbody);assert abs(distance-abs(offset))<2e-6 and distance<=olddistance+2e-6,'Eye relief enlarged or support is not actual nearest';face_normal=np.cross(t[1]-t[0],t[2]-t[0]);face_normal/=np.linalg.norm(face_normal)
  if abs(offset)>2e-6:assert normal@face_normal>.85,'Eye relief direction incompatible with support face'
  weights={}
  for point,gain in zip(t,bc):
   for name,w in bypos[key(point)].items():weights[name]=weights.get(name,0)+gain*w
  weights={k:w for k,w in weights.items()if w>1e-7};total=sum(weights.values());weights={k:w/total for k,w in weights.items()};decl=b['expected_named_weights'];assert len(weights)<=4 and set(weights)==set(decl)
  for i in np.flatnonzero(np.array(rowbind)==j):
   actual={en[int(k)]:float(w)for k,w in zip(ej[i],ew[i])if w>1e-7};assert set(actual)==set(weights);err=max([abs(weights[k]-actual[k])for k in weights]+[abs(weights[k]-decl[k])for k in weights]);assert err<2e-5;maxerr=max(maxerr,err)
  peak=max(peak,distance)
 return {'ok':True,'kind':'native_body_supported_eye','name':n['name'],**top,'export_rows':len(p),'original_physical_topology_oriented_UV_corner_identity':True,'native_RGB_alpha_preserved':True,'actual_nearest_finite_body_named_skin':True,'relief_not_enlarged':True,'maximum_named_weight_error':maxerr,'maximum_relief_native':peak,'underlying_body_independently_closed':True,'binding_report_sha256':sha(path)}
