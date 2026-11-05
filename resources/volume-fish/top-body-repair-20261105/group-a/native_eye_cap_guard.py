"""Strict native open disk cap identity, opaque donor and finite body support.

An open overlay never satisfies or modifies the independently closed body gate.
Topology/boundary inventory is read from the frozen actual canonical cap, not an
arbitrary caller topology allowance. No original UV/RGB/shape inventory changes.
"""
import io,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from PIL import Image
from glb_io import arrays,read_glb,sha

def closest_distance(p,tri):
 a=tri[:,0];ab=tri[:,1]-a;ac=tri[:,2]-a;ap=p-a;aa=np.einsum('ij,ij->i',ab,ab);bb=np.einsum('ij,ij->i',ab,ac);cc=np.einsum('ij,ij->i',ac,ac);ad=np.einsum('ij,ij->i',ab,ap);cd=np.einsum('ij,ij->i',ac,ap);den=aa*cc-bb*bb;valid=den>1e-20;v=np.zeros(len(a));w=v.copy();v[valid]=(cc[valid]*ad[valid]-bb[valid]*cd[valid])/den[valid];w[valid]=(aa[valid]*cd[valid]-bb[valid]*ad[valid])/den[valid];q=a+v[:,None]*ab+w[:,None]*ac;ds=np.linalg.norm(q-p,axis=1);ds[~(valid&(v>=0)&(w>=0)&(v+w<=1))]=np.inf
 for k,j in [(0,1),(1,2),(2,0)]:
  start=tri[:,k];d=tri[:,j]-start;t=np.clip(np.einsum('ij,ij->i',p-start,d)/np.maximum(np.einsum('ij,ij->i',d,d),1e-30),0,1);ds=np.minimum(ds,np.linalg.norm(start+t[:,None]*d-p,axis=1))
 return float(ds.min())

def disk_topology(pos,tri):
 keys=[tuple(np.rint(p*1e7).astype(np.int64))for p in pos];edges=Counter();directions=Counter();boundary_ids=set()
 for f in tri:
  q=[keys[int(i)]for i in f];assert len(set(q))==3
  for a,b in zip(q,q[1:]+q[:1]):e=tuple(sorted([a,b]));edges[e]+=1;directions[e]+=1 if a<b else-1
 assert edges and set(edges.values())=={1,2},'Native cap must have real open boundary and manifold interior'
 assert all(directions[e]==0 for e,n in edges.items()if n==2),'Inconsistent native cap interior winding'
 boundary={e for e,n in edges.items()if n==1};graph=defaultdict(set)
 for a,b in boundary:graph[a].add(b);graph[b].add(a)
 assert graph and all(len(neighbours)==2 for neighbours in graph.values()),'Branched native cap boundary'
 seen=set();pending=[next(iter(graph))]
 while pending:
  k=pending.pop()
  if k in seen:continue
  seen.add(k);pending.extend(graph[k]-seen)
 assert seen==set(graph)and len(set(keys))-len(edges)+len(tri)==1,'Native cap must be one original disk with one boundary loop'
 boundary_ids={i for i,k in enumerate(keys)if k in graph}
 return {'vertices':len(pos),'welded_vertices':len(set(keys)),'triangles':len(tri),'boundary_edges':len(boundary),'boundary_ids':boundary_ids,'closed':False,'one_manifold_disk':True}

def verify(doc,blob,plan,node,definition):
 assert definition['kind']=='native_open_eye_cap'and definition['underlying_body']==plan['body']
 path=Path(definition['binding_report']);assert sha(path)==definition['binding_report_sha256'];report=json.loads(path.read_text());assert report['kind']=='native_open_eye_caps_finite_body_support'and report['model_sha256']==plan['model_sha256'];eye=next(q for q in report['eyes']if q['name']==node['name']);baseline=report['canonical_model'];assert sha(baseline['path'])==baseline['sha256'];old,oldblob=read_glb(baseline['path']);oldpr=old['meshes'][0]['primitives'][0];oldparts=old['extras']['geometry_parts'];oldpart=next(q for q in oldparts if q['name']==eye['part_name']and q['role']=='eyes');lo=oldpart['vertex_start'];hi=lo+oldpart['vertex_count'];op=arrays(old,oldblob,oldpr['attributes']['POSITION']);oi=arrays(old,oldblob,oldpr['indices']).reshape(-1,3);oldcap=op[lo:hi];oldtri=oi[oldpart['index_start']//3:(oldpart['index_start']+oldpart['index_count'])//3]-lo;oldtop=disk_topology(oldcap,oldtri)
 prims=doc['meshes'][node['mesh']]['primitives'];assert len(prims)==1;prim=prims[0];attrs=prim['attributes'];pos=arrays(doc,blob,attrs['POSITION']);tri=arrays(doc,blob,prim['indices']).reshape(-1,3);uv=arrays(doc,blob,attrs['TEXCOORD_0']);old_uv=arrays(old,oldblob,oldpr['attributes']['TEXCOORD_0'])[lo:hi];assert np.array_equal(uv,old_uv),'Native eye UV identity changed';oriented=lambda face:min(tuple(int(x)for x in np.roll(face,-k))for k in range(3));assert Counter(map(oriented,tri))==Counter(map(oriented,oldtri)),'Native cap topology/winding changed';top=disk_topology(pos,tri)
 for key in ['vertices','welded_vertices','triangles','boundary_edges']:assert top[key]==oldtop[key]==eye[key]if key in eye else top[key]==oldtop[key]
 assert top['boundary_ids']==oldtop['boundary_ids'],'Original native cap boundary identity changed'
 mat=doc['materials'][prim['material']];pbr=mat['pbrMetallicRoughness'];assert mat.get('alphaMode','OPAQUE')in('OPAQUE','MASK')and pbr.get('baseColorFactor',[1,1,1,1])[3]==1 and set(mat.get('extensions',{}))<={'KHR_materials_specular'}
 img=doc['images'][doc['textures'][pbr['baseColorTexture']['index']]['source']];assert'bufferView'in img and'uri'not in img;view=doc['bufferViews'][img['bufferView']];raw=blob[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']];oldimg=old['images'][0];ov=old['bufferViews'][oldimg['bufferView']];oldraw=oldblob[ov.get('byteOffset',0):ov.get('byteOffset',0)+ov['byteLength']];assert raw==oldraw,'Native RGB/alpha donor changed';rgba=np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA'));H,W=rgba.shape[:2];x0=max(0,int(np.floor(uv[:,0].min()*W)));x1=min(W,int(np.floor(uv[:,0].max()*W))+1);y0=max(0,int(np.floor(uv[:,1].min()*H)));y1=min(H,int(np.floor(uv[:,1].max()*H))+1);assert x1>x0 and y1>y0 and np.all(rgba[y0:y1,x0:x1,3]==255),'Transparent native eye donor domain'
 body=next(q for q in doc['nodes']if q.get('name')==plan['body']and'mesh'in q);body_names=[doc['nodes'][i]['name']for i in doc['skins'][body['skin']]['joints']];by_pos={};triangles=[];key=lambda p:tuple(np.rint(np.asarray(p,dtype=float)*1e7).astype(np.int64))
 for bp in doc['meshes'][body['mesh']]['primitives']:
  p=arrays(doc,blob,bp['attributes']['POSITION']);j=arrays(doc,blob,bp['attributes']['JOINTS_0']);w=arrays(doc,blob,bp['attributes']['WEIGHTS_0'])
  for q,js,ws in zip(p,j,w):
   named={body_names[int(i)]:float(v)for i,v in zip(js,ws)if v>1e-7};k=key(q)
   if k in by_pos:assert set(named)==set(by_pos[k])and max(abs(named[n]-by_pos[k][n])for n in named)<2e-5
   by_pos[k]=named
  triangles.extend(p[arrays(doc,blob,bp['indices']).reshape(-1,3)])
 triangles=np.array(triangles);tri_set={tuple(sorted(key(p)for p in t))for t in triangles};oldbody=np.concatenate([oi[p['index_start']//3:(p['index_start']+p['index_count'])//3]for p in oldparts if p['role']in('body_skin','mouth')]);oldbody=op[oldbody];eye_names=[doc['nodes'][i]['name']for i in doc['skins'][node['skin']]['joints']];ej=arrays(doc,blob,attrs['JOINTS_0']);ew=arrays(doc,blob,attrs['WEIGHTS_0']);assert np.isfinite(pos).all()and np.isfinite(ew).all()and np.all(ew>=0)and np.all(abs(ew.sum(1)-1)<1e-5);assert len(eye['bindings'])==len(pos);max_weight_error=0.;max_position_error=0.;old_boundary=[];new_boundary=[]
 for i,q in enumerate(eye['bindings']):
  t=np.array(q['body_triangle_positions_gltf']);bc=np.array(q['barycentric']);assert tuple(sorted(key(p)for p in t))in tri_set,'Absent actual finite body support triangle';assert bc.min()>-1e-4 and abs(bc.sum()-1)<1e-5;bc=np.maximum(bc,0);bc/=bc.sum();support=bc@t;assert np.linalg.norm(support-q['support_position'])<2e-6;normal=np.array(q['support_normal']);assert abs(np.linalg.norm(normal)-1)<1e-5;face_normal=np.cross(t[1]-t[0],t[2]-t[0]);face_normal/=np.linalg.norm(face_normal);assert normal@face_normal>.85;offset=q['normal_offset_native'];expected=support+normal*offset;err=float(np.linalg.norm(expected-pos[i]));assert err<2e-6;max_position_error=max(max_position_error,err)
  olddistance=closest_distance(oldcap[i],oldbody);newdistance=closest_distance(pos[i],triangles);assert offset>=-1e-7 and offset<=olddistance+2e-6,'Native relief enlarged beyond original finite-body distance';assert abs(newdistance-offset)<2e-6,'Declared support is not actual nearest finite body';weights={}
  for point,gain in zip(t,bc):
   for name,w in by_pos[key(point)].items():weights[name]=weights.get(name,0)+gain*w
  total=sum(weights.values());weights={k:w/total for k,w in weights.items()if w/total>1e-7};declared=q['expected_named_weights'];actual={eye_names[int(j)]:float(w)for j,w in zip(ej[i],ew[i])if w>1e-7};assert len(weights)<=4 and set(weights)==set(declared)==set(actual);err=max([abs(weights[n]-actual[n])for n in weights]+[abs(weights[n]-declared[n])for n in weights]);assert err<2e-5,'Native cap actual named skin differs from finite body barycentric support';max_weight_error=max(max_weight_error,err)
  if i in top['boundary_ids']:old_boundary.append(olddistance);new_boundary.append(newdistance)
 return {'ok':True,'kind':'native_open_eye_cap','vertices':len(pos),'triangles':len(tri),'boundary_edges':top['boundary_edges'],'closed':False,'underlying_body_independently_closed':True,'canonical_topology_UV_RGB_boundary_identity':True,'opaque_actual_UV_domain':True,'actual_finite_body_barycentric_named_skin':True,'maximum_position_error_native':max_position_error,'maximum_named_weight_error':max_weight_error,'old_boundary_max_body_distance_native':max(old_boundary),'new_boundary_max_body_distance_native':max(new_boundary),'relief_not_enlarged_from_canonical':True,'binding_report_sha256':sha(path)}
