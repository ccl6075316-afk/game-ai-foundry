"""Offline per-species tail/root, exposed membrane taper and outline-free rims.

Preserves original front-face artwork and original rig. Only the declared tail
body interval and independently identified posterior body donor contamination
may change; no runtime shape/color patch is created.
"""
import argparse,copy,io,json,sys
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial import Delaunay
import cv2
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
from patch_existing_fin_meshes import write
from refine_native_fin_cages import load,save,sampler,line_distance,support_polygon
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def skin_mix(joints,weights,gains):
 mix=np.zeros(18)
 for js,ws,gain in zip(joints,weights,gains):
  for j,w in zip(js,ws):mix[int(j)]+=max(0,gain)*w
 mix[mix<1e-4]=0;js=np.argsort(-mix)[:4];ws=mix[js];ws/=ws.sum();return js,ws
def normals(pos,tri):
 n=np.zeros_like(pos)
 for t in tri:
  x,y,z=pos[t];q=np.cross(y-x,z-x)
  for i in t:n[i]+=q
 n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-30);return n
def nearest_body(point,body,faces):
 vertices=body['POSITION'][faces];aa=vertices[:,0];e0=vertices[:,1]-aa;e1=vertices[:,2]-aa;delta=point-aa;d00=np.einsum('ij,ij->i',e0,e0);d01=np.einsum('ij,ij->i',e0,e1);d11=np.einsum('ij,ij->i',e1,e1);den=d00*d11-d01*d01;good=np.abs(den)>1e-20;u=np.zeros(len(faces));v=u.copy();d20=np.einsum('ij,ij->i',delta,e0);d21=np.einsum('ij,ij->i',delta,e1);u[good]=(d11[good]*d20[good]-d01[good]*d21[good])/den[good];v[good]=(d00[good]*d21[good]-d01[good]*d20[good])/den[good];bary=np.c_[1-u-v,u,v];project=np.einsum('ni,nij->nj',bary,vertices);distance=((project-point)**2).sum(1);distance[~(good&(bary>=0).all(1))]=np.inf;options=[(distance,project,bary)]
 for i,j in [(0,1),(1,2),(2,0)]:
  a=vertices[:,i];edge=vertices[:,j]-a;f=np.clip(np.einsum('ij,ij->i',point-a,edge)/np.maximum(np.einsum('ij,ij->i',edge,edge),1e-30),0,1);q=a+edge*f[:,None];bw=np.zeros((len(faces),3));bw[:,i]=1-f;bw[:,j]=f;options.append((((q-point)**2).sum(1),q,bw))
 distance,q,bw=min(options,key=lambda z:z[0].min());index=int(np.argmin(distance));normal=np.cross(e0[index],e1[index]);normal/=max(np.linalg.norm(normal),1e-30);return q[index],normal,faces[index],bw[index]
def rebuild_pelvic(v,tri,mask,origin,size,body,bodyfaces,scale,cfg):
 rgba=np.array(Image.open(mask['image']).convert('RGBA'));root=np.array(mask['root_px']);hull=support_polygon(rgba[:,:,3]>127,10);center=np.mean(np.argwhere(rgba[:,:,3]>127)[:,::-1],axis=0);rootseeds=[]
 # A finite source strip with explicit transverse stations prevents the old
 # nearest-point root fit from folding a long, almost-collinear basal fan.
 cumulative=np.r_[0,np.cumsum(np.linalg.norm(np.diff(root,axis=0),axis=1))]
 for s in np.linspace(0,cumulative[-1],6):
  i=min(len(root)-2,int(np.searchsorted(cumulative,s,side='right')-1));i=max(0,i);f=(s-cumulative[i])/max(cumulative[i+1]-cumulative[i],1e-9);base=root[i]*(1-f)+root[i+1]*f;direction=center-base;direction/=max(np.linalg.norm(direction),1e-9)
  for distance in [0,8,17,40]:rootseeds.append(base+direction*distance)
 q=np.unique(np.round(np.r_[hull,np.array(rootseeds),center[None,:]],5),axis=0);front=Delaunay(q).simplices.copy();functions=stable_layers(v['TEXCOORD_0']*size,v['POSITION'].copy(),v['JOINTS_0'],v['WEIGHTS_0'],tri);sourceorigin=np.array(mask['crop'][:2]);rootfull=root+sourceorigin;W=Image.open(mask['source_image']).width
 def old(q):
  atlas=q+origin;pa,ja,wa=functions[0](atlas);pb,jb,wb=functions[1](atlas);js,ws=skin_mix(np.array([ja,jb]),np.array([wa,wb]),[.5,.5]);return (pa+pb)/2,js,ws
 def closest(q):
  a=root[:-1];e=np.diff(root,axis=0);t=np.clip(np.einsum('ij,ij->i',q-a,e)/np.maximum(np.einsum('ij,ij->i',e,e),1e-20),0,1);base=a+e*t[:,None];dist=np.linalg.norm(base-q,axis=1);i=int(np.argmin(dist));return base[i],float(dist[i])
 mids=[];skin=[];distance=[]
 for point in q:
  basal,d=closest(point);oldbase,_,_=old(basal);hit,n,face,bw=nearest_body(oldbase,body,bodyfaces);tangent=np.array([1.,0,0]);tangent-=n*np.dot(tangent,n);tangent/=max(np.linalg.norm(tangent),1e-9);circum=np.cross(n,tangent);circum/=max(np.linalg.norm(circum),1e-9)
  if circum[1]>0:circum=-circum
  step=min(d,17);delta=(point-basal)/W;rootpoint=hit+tangent*delta[0]*(step/max(d,1e-9))+circum*(step/W)*.6;rootpoint,_,rootface,rbw=nearest_body(rootpoint,body,bodyfaces);free,j,w=old(point);blend=float(smooth((d-17)/40));mid=rootpoint*(1-blend)+free*blend;bj,bw=skin_mix(body['JOINTS_0'][rootface],body['WEIGHTS_0'][rootface],rbw);j,w=skin_mix(np.array([bj,j]),np.array([bw,w]),[1-blend,blend]);mids.append(mid);skin.append((j,w));distance.append(d)
 mids=np.array(mids);distance=np.array(distance)
 # The source winding owns a continuous chart normal, including the full
 # finite wrap on the body. No layer is inferred from a folded UV sign.
 for i,t in enumerate(front):
  a,b,c=q[t]
  if np.linalg.det(np.array([b-a,c-a]))<0:front[i]=t[::-1]
 normal=normals(mids,front);thick=(cfg['fin_edge_mm']+(cfg['fin_proximal_mm']-cfg['fin_edge_mm'])*(1-smooth(np.maximum(0,distance-17)/max(1,distance.max()-17))))/2000/scale;N=len(q);pos=np.r_[mids+normal*thick[:,None],mids-normal*thick[:,None]];faces=[*front,*[t[::-1]+N for t in front]];edges={}
 for t in front:
  for a,b in zip(t,np.roll(t,-1)):edges.setdefault(tuple(sorted((int(a),int(b)))),[]).append((int(a),int(b)))
 for rows in edges.values():
  if len(rows)==1:a,b=rows[0];faces.extend([(b,a,a+N),(b,a+N,b+N)])
 faces=np.array(faces,dtype=int);uv=(q+origin)/size;out={'POSITION':pos.astype('<f4'),'NORMAL':normals(pos,faces).astype('<f4'),'TEXCOORD_0':np.r_[uv,uv].astype('<f4'),'JOINTS_0':np.array([j for j,w in skin]*2,dtype='<u2'),'WEIGHTS_0':np.array([w for j,w in skin]*2,dtype='<f4')};roots=np.where(distance<=17.001)[0].tolist();roots+= [i+N for i in roots];return out,faces,{'root_ids':roots,'root_rest_points_gltf':pos[roots].tolist(),'root_source_band_px':17,'source_origin':sourceorigin.tolist(),'source_baseline':rootfull.tolist(),'root_rebuilt_as_finite_transverse_strip':True,'source_strip_stations':6,'old_folded_root_geometry_not_reused':True,'layer_vertices':N}
def stable_layers(uv,pos,joints,weights,tri):
 """Cap connectivity owns a side; UV winding may flip at a curved basal fit."""
 t=uv[tri];det=np.linalg.det(np.stack([t[:,1]-t[:,0],t[:,2]-t[:,0]],2));longest=np.maximum.reduce([np.linalg.norm(t[:,1]-t[:,0],axis=1),np.linalg.norm(t[:,2]-t[:,0],axis=1),np.linalg.norm(t[:,2]-t[:,1],axis=1)]);ids=np.where(np.abs(det)>np.maximum(longest,1e-9)*.0015)[0];parent={int(i):int(i)for i in ids}
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 owner={}
 for i in ids:
  for v in tri[i]:
   v=int(v)
   if v in owner:parent[find(int(i))]=find(owner[v])
   else:owner[v]=int(i)
 groups={}
 for i in ids:groups.setdefault(find(int(i)),[]).append(int(i))
 assert len(groups)==2,('Expected two UV cap components',list(map(len,groups.values())))
 output=[]
 for group in groups.values():
  rows=tri[group];t=uv[rows];aa=t[:,0];matrix=np.stack([t[:,1]-aa,t[:,2]-aa],2);inv=np.linalg.inv(matrix)
  def sample(q,rows=rows,aa=aa,inv=inv):
   bc=np.einsum('nij,nj->ni',inv,q-aa);bw=np.c_[1-bc.sum(1),bc];cl=np.maximum(bw,0);cl/=cl.sum(1)[:,None];projected=np.einsum('ni,nij->nj',cl,uv[rows]);distance=((projected-q)**2).sum(1);distance[(bw>=-1e-6).all(1)]=0;i=int(np.argmin(distance));p=bw[i]@pos[rows[i]];j,w=skin_mix(joints[rows[i]],weights[rows[i]],cl[i]);return p,j,w
  sample.vertex_ids=set(rows.reshape(-1).tolist());output.append(sample)
 return output
def orient_shell(pos,tri):
 tri=tri.copy();edges={}
 for i,t in enumerate(tri):
  for a,b in zip(t,np.roll(t,-1)):edges.setdefault(tuple(sorted((int(a),int(b)))),[]).append((i,int(a),int(b)))
 assert all(len(rows)==2 for rows in edges.values()),'Nonmanifold pre-UV shell'
 adjacent={i:[]for i in range(len(tri))}
 for rows in edges.values():
  (i,a,b),(j,c,d)=rows;same=(a,b)==(c,d);adjacent[i].append((j,same));adjacent[j].append((i,same))
 flipped={0:False};todo=[0]
 while todo:
  i=todo.pop()
  for j,same in adjacent[i]:
   target=flipped[i]^same
   if j in flipped:assert flipped[j]==target,'Nonorientable shell'
   else:flipped[j]=target;todo.append(j)
 assert len(flipped)==len(tri)
 for i,f in flipped.items():
  if f:tri[i]=tri[i,::-1]
 volume=np.sum(np.einsum('ij,ij->i',pos[tri[:,0]],np.cross(pos[tri[:,1]],pos[tri[:,2]])))/6
 if volume<0:tri=tri[:,::-1]
 return tri
def close_cap_boundaries(v,tri,size):
 """Discard legacy subdivided closing walls; stitch actual cap perimeters."""
 uv=v['TEXCOORD_0']*size;t=uv[tri];det=np.linalg.det(np.stack([t[:,1]-t[:,0],t[:,2]-t[:,0]],2));longest=np.maximum.reduce([np.linalg.norm(t[:,1]-t[:,0],axis=1),np.linalg.norm(t[:,2]-t[:,0],axis=1),np.linalg.norm(t[:,2]-t[:,1],axis=1)]);significant=np.abs(det)>np.maximum(longest,1e-9)*.0015;caps=stable_layers(uv,v['POSITION'],v['JOINTS_0'],v['WEIGHTS_0'],tri);capfaces=[];loops=[]
 for cap in caps:
  faces=[tuple(map(int,t))for t,keep in zip(tri,significant)if keep and all(int(i)in cap.vertex_ids for i in t)];counts=Counter(tuple(sorted((a,b)))for t in faces for a,b in zip(t,np.roll(t,-1)));boundary=[e for e,n in counts.items()if n==1];adjacent={}
  for a,b in boundary:adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
  assert adjacent and all(len(row)==2 for row in adjacent.values()),('Non-simple source cap boundary',[len(row)for row in adjacent.values()if len(row)!=2]);start=min(adjacent,key=lambda i:tuple(uv[i]));path=[start];previous=None;current=start
  while True:
   nxt=next(i for i in adjacent[current]if i!=previous)
   if nxt==start:break
   assert nxt not in path;path.append(nxt);previous,current=current,nxt
  assert len(path)==len(adjacent),'Source cap has additional holes'
  q=uv[path];area=np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1))
  if area<0:path=[path[0]]+path[:0:-1]
  capfaces.extend(faces);loops.append(path)
 a,b=loops;qa=uv[a];qb=uv[b];la=np.linalg.norm(np.roll(qa,-1,axis=0)-qa,axis=1);lb=np.linalg.norm(np.roll(qb,-1,axis=0)-qb,axis=1);assert abs(la.sum()-lb.sum())<.01,'Different source cap perimeters';ta=np.r_[0,np.cumsum(la)]/la.sum();tb=np.r_[0,np.cumsum(lb)]/lb.sum();i=j=0;walls=[]
 while i<len(a)or j<len(b):
  ai=a[i%len(a)];bj=b[j%len(b)];na=ta[i+1]if i<len(a)else np.inf;nb=tb[j+1]if j<len(b)else np.inf
  if abs(na-nb)<1e-7:
   an=a[(i+1)%len(a)];bn=b[(j+1)%len(b)];walls.extend([(ai,an,bn),(ai,bn,bj)]);i+=1;j+=1
  elif na<nb:walls.append((ai,a[(i+1)%len(a)],bj));i+=1
  else:walls.append((ai,b[(j+1)%len(b)],bj));j+=1
 return np.array(capfaces+walls,dtype=int),{'legacy_wall_faces_replaced':int((~significant).sum()),'new_finite_wall_faces':len(walls),'cap_boundary_vertices':[len(a),len(b)]}
def cap_knots(pos,bodyids):
 lo=pos[bodyids,0].min();ids=np.unique(bodyids[np.abs(pos[bodyids,0]-lo)<1e-6]);points=pos[ids];ys=np.unique(np.round(points[:,1],7));widths=np.array([np.max(np.abs(points[np.abs(points[:,1]-y)<1e-6,2]))for y in ys]);return lo,ids,ys,widths
def caudal(v,tri,root,cap_y,cap_width,cap_ids,body,scale,length,cfg):
 uv=v['TEXCOORD_0'];uvtri=uv[tri];det=np.linalg.det(np.stack([uvtri[:,1]-uvtri[:,0],uvtri[:,2]-uvtri[:,0]],2));caps=tri[det>1e-12];old_ids=sorted(set(caps.reshape(-1).tolist()));q=uv[old_ids].copy();lookup={old:i for i,old in enumerate(old_ids)};faces=[tuple(lookup[int(i)]for i in t)for t in caps];sample=sampler(uv,v['POSITION'],v['JOINTS_0'],v['WEIGHTS_0'],tri)
 oldroot=float(v['POSITION'][:,0].max());edges=Counter(tuple(sorted((a,b)))for t in faces for a,b in zip(t,np.roll(t,-1)));basal=[edge for edge,count in edges.items()if count==1 and all(abs(v['POSITION'][old_ids[i],0]-oldroot)<1e-6 for i in edge)];assert basal,'Missing complete tail source boundary'
 seeds=list(q);roots=[];newfaces=faces[:]
 for aa,bb in basal:
  ya,yb=v['POSITION'][old_ids[[aa,bb][0]],1],v['POSITION'][old_ids[[aa,bb][1]],1];knots=[]
  for y in cap_y:
   f=float((y-ya)/(yb-ya))
   if 1e-5<f<1-1e-5:knots.append((f,len(seeds)));seeds.append(q[aa]+f*(q[bb]-q[aa]))
  chain=[aa]+[i for _,i in sorted(knots)]+[bb];rebuilt=[]
  for t in newfaces:
   if aa not in t or bb not in t:rebuilt.append(t);continue
   for k in range(3):
    a,b,c=t[k],t[(k+1)%3],t[(k+2)%3]
    if {a,b}=={aa,bb}:
     ordered=chain if a==aa else chain[::-1];rebuilt.extend((x,y,c)for x,y in zip(ordered,ordered[1:]));break
  newfaces=rebuilt
 seeds=np.array(seeds);N=len(seeds);pos=[];js=[];ws=[];tailrootids=[];taper=cfg['caudal_taper_fraction']*length
 for layer,fn in enumerate(sample):
  # UV orientation, rather than a hardcoded side, owns each finite shell layer.
  probe=fn(seeds.mean(0))[0];opposite=sample[1-layer](seeds.mean(0))[0];sign=1 if probe[2]>opposite[2]else -1
  for i,seed in enumerate(seeds):
   p,j,w=fn(seed);distance=max(0,oldroot-p[0]);s=float(smooth(distance/taper));width=max(cfg['caudal_edge_mm']/2000/scale,float(np.interp(p[1],cap_y,cap_width)));half=(1-s)*width+s*cfg['caudal_edge_mm']/2000/scale;p[2]=sign*half;p[0]+=(root+.00004/scale-oldroot)*(1-s)
   if distance<1e-5:
    # Complete finite end section follows the actual body endpoint weights.
    ring=body['POSITION'][cap_ids];near=np.argsort(((ring-np.array([root,p[1],p[2]]))**2).sum(1))[:2];dd=np.linalg.norm(ring[near]-[root,p[1],p[2]],axis=1);gain=1/np.maximum(dd,1e-8);gain/=gain.sum();j,w=skin_mix(body['JOINTS_0'][cap_ids[near]],body['WEIGHTS_0'][cap_ids[near]],gain);tailrootids.append(layer*N+i)
   pos.append(p);js.append(j);ws.append(w)
 pos=np.array(pos);front=np.array(newfaces,dtype=int);direction=(pos[:N]-pos[N:]).mean(0)
 for i,t in enumerate(front):
  a,b,c=pos[t]
  if np.dot(np.cross(b-a,c-a),direction)<0:front[i]=t[::-1]
 fs=[*front,*[t[::-1]+N for t in front]];edge_rows={}
 for t in front:
  for a,b in zip(t,np.roll(t,-1)):edge_rows.setdefault(tuple(sorted((int(a),int(b)))),[]).append((int(a),int(b)))
 for rows in edge_rows.values():
  if len(rows)==1:a,b=rows[0];fs.extend([(b,a,a+N),(b,a+N,b+N)])
 fs=np.array(fs,dtype=int);out={'POSITION':pos.astype('<f4'),'NORMAL':normals(pos,fs).astype('<f4'),'TEXCOORD_0':np.r_[seeds,seeds].astype('<f4'),'JOINTS_0':np.array(js,dtype='<u2'),'WEIGHTS_0':np.array(ws,dtype='<f4')};return out,fs,{'root_ids':tailrootids,'complete_cap_height_knots':cap_y.tolist(),'root_rest_points_gltf':pos[tailrootids].tolist(),'native_front_outline_preserved':True,'taper_length_native':taper}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();base=a.candidate.resolve();out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True);oldspec=load(base/'source-run/final-spec.json');audit=load(base.parent/'audit/audit.validation.json');sp=audit['species'];settings=ROOT/'resources/volume-fish/three-fish-tail-donors-20261031.json';cfg=load(settings)['species'][sp];plan=load(base/'fin.plan.json')['items'][0];scale=load(base/'fin-review.plan.json')['model_scale'];d,b=read_glb(base/'source-run/fish.glb');b=bytearray(b);pr=d['meshes'][0]['primitives'][0];at={k:arrays(d,b,v)for k,v in pr['attributes'].items()};indices=arrays(d,b,pr['indices']).reshape(-1);parts=d['extras']['geometry_parts'];pack=load(base/'author/packing.validation.json');iv=d['bufferViews'][d['images'][0]['bufferView']];atlas=np.array(Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA'));original_atlas=atlas.copy();size=np.array([atlas.shape[1],atlas.shape[0]]);bodyids=np.concatenate([indices[r['index_start']:r['index_start']+r['index_count']]for r in parts if r['role']=='body_skin']);rear,cap_ids,cap_y,cap_w=cap_knots(at['POSITION'],bodyids);length=float(np.ptp(at['POSITION'][bodyids,0]));blend=cfg['body_blend_fraction']*length;endfactor=cfg['tail_end_width_mm']/1000/scale/(2*cap_w.max());assert 0<endfactor<1
 body=copy.deepcopy(at);factor=endfactor+(1-endfactor)*smooth((at['POSITION'][:,0]-rear)/blend);body['POSITION'][:,2]*=factor;bodyfaces=np.concatenate([indices[p['index_start']:p['index_start']+p['index_count']].reshape(-1,3)for p in parts if p['role']=='body_skin']);bodyvolume=np.sum(np.einsum('ij,ij->i',body['POSITION'][bodyfaces[:,0]],np.cross(body['POSITION'][bodyfaces[:,1]],body['POSITION'][bodyfaces[:,2]])))/6
 if bodyvolume<0:bodyfaces=bodyfaces[:,::-1]
 _,_,new_y,new_w=cap_knots(body['POSITION'],bodyids);records=[];new_at={k:[]for k in at};new_ix=[];new_parts=[];new_pack=[];vo=ioff=0;paired_templates={}
 # Source-owned posterior fin/body outlines, never arbitrary dark markings.
 oldauthor=load(base/'author/author.validation.json');native_masks={r['name']:r for r in load(oldauthor['input_masks']['path'])['fins']}
 donor_rows=[];source=np.array(Image.open(audit['source_image']).convert('RGBA'));fin_exclusion=np.zeros(source.shape[:2],np.uint8)
 for f in audit['fins']:cv2.fillPoly(fin_exclusion,[np.rint(f['source_polygon_px']).astype('int32')],1)
 body_depth=distance_transform_edt((source[:,:,3]>127)&(fin_exclusion==0));safe_body=body_depth>=8
 for part,row in zip(parts,pack['parts']):
  start=part['vertex_start'];end=start+part['vertex_count'];i=part['index_start'];tri=indices[i:i+part['index_count']].reshape(-1,3).astype(int)-start;v={k:x[start:end].copy()for k,x in at.items()};name=part['source_node'];origin=np.array(row['atlas_placement'])-row['virtual_crop_origin'];proof={'name':name,'original_triangles':len(tri)}
  if part['role']=='body_skin':
   v['POSITION']=body['POSITION'][start:end].copy();changed=(at['POSITION'][start:end,0]<rear+blend)&(np.abs(v['POSITION'][:,2]-at['POSITION'][start:end,2])>1e-10);nn=normals(v['POSITION'],tri);v['NORMAL'][changed]=nn[changed];proof.update(tail_vertices_changed=int(changed.sum()),all_forward_attributes_unchanged=True)
   if part['source_surface']==0:
    for fin in ['Dorsal','Anal']:
     rootline=np.array(next(z for z in audit['fins']if z['fin']==fin)['source_baseline_px']);xx0=int(max(0,rootline[0,0]-22));xx1=int(min(source.shape[1],rootline[min(2,len(rootline)-1),0]+10));count=0
     for x in range(xx0,xx1):
      ybase=float(np.interp(x,rootline[:,0],rootline[:,1]));sign=1 if fin=='Dorsal'else -1;donory=None
      for extra in range(cfg['body_donor_inset_px'],cfg['body_donor_inset_px']+100):
       yy=int(round(ybase+sign*extra))
       if 0<=yy<source.shape[0]and safe_body[yy,x]:donory=yy;break
      if donory is None:continue
      for y in range(max(0,int(ybase-18)),min(source.shape[0],int(ybase+19))):
       ax,ay=np.array([x,y])+origin
       if not (0<=ax<size[0]and 0<=ay<size[1]):continue
       left,top=row['atlas_placement'];rw,rh=row['virtual_crop_size']
       if not(left<=ax<left+rw and top<=ay<top+rh):continue
       color=atlas[ay,ax,:3];luma=float(color@[.2126,.7152,.0722])
       if luma>=cfg['body_outline_dark_luma_max']or int(color.max())-int(color.min())>28:continue
       if body_depth[y,x]>=5:continue
       # Preserve the source-side narrow connection mark; repair wrong outward
       # outline/transparent-footprint donors and the broad posterior fringe.
       if 0<=sign*(y-ybase)<=3 and body_depth[y,x]>=2:continue
       # Transport a two-dimensional interior strip, not one color repeated
       # down an entire column. Original pixel clusters/vertical variation stay.
       sy=int(round(donory+sign*cfg['body_donor_inset_px']+(y-ybase)))
       if not(0<=sy<source.shape[0]and safe_body[sy,x]):continue
       atlas[ay,ax,:3]=source[sy,x,:3];donor_rows.append({'part':part['name'],'fin':fin,'atlas_xy':[int(ax),int(ay)],'source_xy':[x,sy],'source_RGB':source[sy,x,:3].tolist()});count+=1
     proof[fin+'_posterior_body_outline_texels']=count
  elif part['role']=='fin':
   fin=next(k for k in ['Dorsal','Anal','Caudal','Pectoral','Pelvic']if name.startswith(k));oldroot=np.array(plan['fins'][name]['rest_points_gltf']);sourceinfo=next(z for z in audit['fins']if z['fin']==fin)
   if fin=='Caudal':v,tri,tail=caudal(v,tri,rear,new_y,new_w,cap_ids,body,scale,length,cfg);proof.update(tail)
   elif fin=='Pelvic'and sp in ['crucian','grass_carp']:v,tri,pelvic=rebuild_pelvic(v,tri,native_masks[fin],origin,size,body,bodyfaces,scale,cfg);proof.update(pelvic)
   else:
    # UV-owned front/back sampling preserves every existing outline/crest.
    source_origin=np.array(native_masks[fin]['crop'][:2]if fin in native_masks else sourceinfo['source_crop'][:2]);root=np.array(native_masks[fin]['root_px'])+source_origin if fin in native_masks else np.array(sourceinfo['source_baseline_px']);sample=stable_layers(v['TEXCOORD_0']*size,v['POSITION'].copy(),v['JOINTS_0'],v['WEIGHTS_0'],tri);px=v['TEXCOORD_0']*size-origin+source_origin;dist=np.array([line_distance(q,root)for q in px]);maxdist=max(dist.max(),18);moved=0;proof.update(source_origin=source_origin.tolist(),source_baseline=root.tolist())
    qv=v['TEXCOORD_0']*size;pairs=[(sample[0](q)[0],sample[1](q)[0])for q in qv];centers=np.array([(a+b)/2 for a,b in pairs]);normal_by_uv={};keys=[tuple(np.round(q,4))for q in qv]
    if fin=='Pelvic'and sp in ['crucian','grass_carp']:
     # Previous nearest-body projection folded the almost horizontal source
     # basal strip in XY. Keep a single injective source-plane chart, fitting
     # its placement to the COMPLETE existing band, rather than retaining that
     # fold or narrowing the band. Z camber and original source pixels remain.
     qcenter=qv.mean(0);qscale=max(np.ptp(qv[:,0]),np.ptp(qv[:,1]));design=np.c_[np.ones(len(qv)),(qv-qcenter)/qscale];gain=np.where(dist<=17,10.,1.);fit=np.linalg.lstsq(design*gain[:,None],centers[:,:2]*gain[:,None],rcond=None)[0];proposed=design@fit;error=np.linalg.norm(proposed-centers[:,:2],axis=1)*scale*1000;assert abs(np.linalg.det(fit[1:]))>1e-9,'Degenerate native fin chart';centers[:,:2]=proposed;proof['pelvic_injective_source_chart']={'complete_basal_band_preserved':True,'maximum_XY_adjustment_mm':float(error.max()),'maximum_basal_XY_adjustment_mm':float(error[dist<=17].max()),'Z_camber_preserved':True}
    for tv in tri:
     q=qv[tv];det=float(np.linalg.det(np.array([q[1]-q[0],q[2]-q[0]])));longest=max(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[0]),np.linalg.norm(q[2]-q[1]))
     if abs(det)<=max(longest,1e-9)*.0015:continue
     ca,cb,cc=centers[tv];normal=np.cross(cb-ca,cc-ca)*np.sign(det)
     for j in tv:normal_by_uv[keys[j]]=normal_by_uv.get(keys[j],np.zeros(3))+normal
    reference=np.median(np.array([a-b for a,b in pairs]),axis=0);total=sum(normal_by_uv.values());orientation=1 if np.dot(total,reference)>=0 else -1
    for j,(q,(p0,p1))in enumerate(zip(qv,pairs)):
     normal=normal_by_uv.get(keys[j])
     if normal is None or np.linalg.norm(normal)<1e-12:
      nearest=min(normal_by_uv,key=lambda k:np.linalg.norm(np.array(k)-q));normal=normal_by_uv[nearest]
     normal=normal/np.linalg.norm(normal)*orientation
     if j in sample[0].vertex_ids:sign=1
     elif j in sample[1].vertex_ids:sign=-1
     else:sign=1 if np.linalg.norm(v['POSITION'][j]-p0)<np.linalg.norm(v['POSITION'][j]-p1)else -1
     s=float(smooth((dist[j]-17)/max(1,maxdist-17)));target=cfg['fin_edge_mm']+(cfg['fin_proximal_mm']-cfg['fin_edge_mm'])*(1-s);v['POSITION'][j]=centers[j]+normal*sign*target/2000/scale;moved+=1
    # Carry the existing basal domain through the declared posterior field.
    v['POSITION'][:,2]*=endfactor+(1-endfactor)*smooth((v['POSITION'][:,0]-rear)/blend);v['NORMAL']=normals(v['POSITION'],tri).astype('<f4');nearest=np.argmin(((oldroot[:,None,:]-at['POSITION'][None,start:end,:])**2).sum(2),axis=1);proof.update(root_ids=nearest.tolist(),root_rest_points_gltf=v['POSITION'][nearest].tolist(),exposed_taper_authored_mm=[cfg['fin_proximal_mm'],cfg['fin_edge_mm']],exposed_vertices_repositioned=moved)
   if fin in cfg.get('clearance',{}):
    margin=cfg['clearance'][fin];source_origin=np.array(native_masks[fin]['crop'][:2]);baseline=np.array(native_masks[fin]['root_px'])+source_origin;pixel=v['TEXCOORD_0']*size-origin+source_origin;amounts=[];direction=np.array(margin['direction'],float)
    if fin=='Pectoral':direction[2]=abs(direction[2])*np.sign(v['POSITION'][:,2].mean())
    for vi,point in enumerate(v['POSITION'].copy()):
     distance=line_distance(pixel[vi],baseline);mix=float(smooth((distance-17)/margin['transition_px']));_,normal,_,_=nearest_body(point,body,bodyfaces);outward=normal*(1-mix)+direction*mix;outward/=max(np.linalg.norm(outward),1e-20);gain=margin['root_mm']+(margin['free_mm']-margin['root_mm'])*mix;v['POSITION'][vi]+=outward*gain/1000/scale;amounts.append(gain)
    if 'root_ids'in proof:proof['root_rest_points_gltf']=v['POSITION'][proof['root_ids']].tolist()
    proof['current_pose_clearance_margin_mm']={'minimum':min(amounts),'maximum':max(amounts),'source_band_unchanged':True,'basis':'Responds to current490 finite-face counterexample; original contact and penetration limits unchanged.'}
   if fin!='Caudal':
    tri,closing=close_cap_boundaries(v,tri,size);proof['closing_surface_rebuild']=closing
    # Full frozen anatomical source band, reselected on its actual cap surface
    # after replacing only obsolete wall-interior topology.
    if not proof.get('root_rebuilt_as_finite_transverse_strip'):
     old_ids=np.argmin(((oldroot[:,None,:]-at['POSITION'][None,start:end,:])**2).sum(2),axis=1);threshold=17. if fin in native_masks else float(np.max(dist[old_ids]));selected=np.where(dist<=threshold+1e-3)[0];used=set(tri.reshape(-1));selected=[int(i)for i in selected if int(i)in used];proof.update(root_ids=selected,root_rest_points_gltf=v['POSITION'][selected].tolist(),original_full_source_band_px=threshold)
   tri=orient_shell(v['POSITION'],tri);v['NORMAL']=normals(v['POSITION'],tri).astype('<f4')
   # Separate finite closing-wall UVs from original face artwork. Donors are
   # interior original fin pixels, at least Npixels from the frozen alpha edge.
   x0,y0=origin;sw,sh=row['source_size'];cut=original_atlas[max(0,y0):min(size[1],y0+sh),max(0,x0):min(size[0],x0+sw)]
   assert cut.shape[:2]==(sh,sw),'Fin tile is not fully represented';mask=cut[:,:,3]>127;depth=distance_transform_edt(mask);safe=depth>=cfg['wall_donor_boundary_exclusion_px'];assert safe.any();_,nearest=distance_transform_edt(~safe,return_indices=True);uvtri=v['TEXCOORD_0'][tri]*size;det=np.linalg.det(np.stack([uvtri[:,1]-uvtri[:,0],uvtri[:,2]-uvtri[:,0]],2));longest=np.maximum.reduce([np.linalg.norm(uvtri[:,1]-uvtri[:,0],axis=1),np.linalg.norm(uvtri[:,2]-uvtri[:,0],axis=1),np.linalg.norm(uvtri[:,2]-uvtri[:,1],axis=1)]);wallids=np.where(np.abs(det)<=np.maximum(longest,1e-9)*.0015)[0];lists={k:list(x)for k,x in v.items()};wall_proofs=[]
   for ti in wallids:
    t=tri[ti].copy();q=np.mean(v['TEXCOORD_0'][t]*size-origin,axis=0);x,y=np.clip(np.floor(q).astype(int),[0,0],[sw-1,sh-1]);visible=bool(mask[y,x]);dy,dx=nearest[:,y,x]if visible else (y,x);target=(origin+[dx+.5,dy+.5])/size;face_n=np.cross(v['POSITION'][t[1]]-v['POSITION'][t[0]],v['POSITION'][t[2]]-v['POSITION'][t[0]]);face_n/=max(np.linalg.norm(face_n),1e-30)
    for corner,vi in enumerate(t):
     ni=len(lists['POSITION'])
     for key in lists:lists[key].append(target if key=='TEXCOORD_0'else face_n if key=='NORMAL'else v[key][vi].copy())
     tri[ti,corner]=ni
    wall_proofs.append({'triangle':int(ti),'source_cutout_xy':[int(dx),int(dy)],'distance_from_alpha_edge_px':float(depth[dy,dx]),'RGB':cut[dy,dx,:3].tolist(),'source_alpha':int(cut[dy,dx,3]),'native_boundary_midpoint_xy':[int(x),int(y)],'visible_source_boundary':visible})
   v={k:np.array(x,dtype='<u2'if k=='JOINTS_0'else'<f4')for k,x in lists.items()};proof.update(wall_triangles=len(wallids),wall_donors=wall_proofs,front_face_UV_and_native_RGB_unchanged=True)
  if part['role']=='fin':
   positions=v['POSITION'];area=np.linalg.norm(np.cross(positions[tri[:,1]]-positions[tri[:,0]],positions[tri[:,2]]-positions[tri[:,0]]),axis=1);zero=np.where(area<=1e-18)[0]
   if len(zero):
    assert all(len(np.unique(positions[tri[i]],axis=0))<3 for i in zero),'Do not delete finite skinny/collinear faces';keep=area>1e-18;face_map=np.cumsum(keep)-1;tri=tri[keep];proof['removed_zero_length_faces']=zero.tolist();proof['wall_donors']=[{**r,'triangle':int(face_map[r['triangle']])}for r in proof['wall_donors']if keep[r['triangle']]];proof['wall_triangles']=len(proof['wall_donors'])
   _,weld=np.unique(v['POSITION'],axis=0,return_inverse=True);welded=weld[tri];counts=Counter(tuple(sorted((int(a),int(b))))for t in welded for a,b in zip(t,np.roll(t,-1)));assert all(n==2 for n in counts.values()),(name,'Welded finite shell open');proof['actual_welded_closed_shell']=True
  if name=='Pectoral_left_mesh':paired_templates['Pectoral']=(copy.deepcopy(v),tri.copy(),copy.deepcopy(proof),copy.deepcopy(row))
  if name=='Pectoral_right_mesh':
   left,lt,lp,lr=paired_templates['Pectoral'];assert lr['atlas_placement']==row['atlas_placement']and lr['source_RGBA_sha256']==row['source_RGBA_sha256'],'Bilateral source pixels must be identical';v=copy.deepcopy(left);v['POSITION'][:,2]*=-1;v['NORMAL'][:,2]*=-1;tri=lt[:,::-1].copy();names=[d['nodes'][j]['name']for j in d['skins'][0]['joints']];jmap=np.arange(len(names));left_bone=names.index('Pectoral_left');right_bone=names.index('Pectoral_right');jmap[left_bone]=right_bone;jmap[right_bone]=left_bone;v['JOINTS_0']=jmap[v['JOINTS_0']].astype('<u2');proof=lp;proof['name']=name;proof['root_rest_points_gltf']=(np.array(lp['root_rest_points_gltf'])*[1,1,-1]).tolist();proof['bilateral_source_identity_verified']=True;proof['right_cap_repair']='Mirror own same-source left finite cage and remap its own left/right fin bones; original right cage had inverted/folded cap near root. Full current right-body contact required.'
  used=np.unique(tri);remap=np.full(len(v['POSITION']),-1,dtype=int);remap[used]=np.arange(len(used));tri=remap[tri];proof['unused_original_wall_vertices_removed']=len(v['POSITION'])-len(used);v={k:x[used]for k,x in v.items()}
  if 'root_rest_points_gltf'in proof:
   points=np.array(proof['root_rest_points_gltf']);near=np.argmin(((points[:,None,:]-v['POSITION'][None,:,:])**2).sum(2),axis=1);assert np.max(np.linalg.norm(points-v['POSITION'][near],axis=1))<1e-6;proof['root_ids']=np.unique(near).tolist();proof['root_rest_points_gltf']=v['POSITION'][proof['root_ids']].tolist()
  if name.startswith('Pectoral')and cfg.get('pectoral_extra_outset_mm',0):
   shift=np.sign(v['POSITION'][:,2].mean())*cfg['pectoral_extra_outset_mm']/1000/scale;v['POSITION'][:,2]+=shift;proof['root_rest_points_gltf']=v['POSITION'][proof['root_ids']].tolist();proof['extra_outward_clearance_mm']=cfg['pectoral_extra_outset_mm']
  for k in at:new_at[k].append(v[k])
  n=len(v['POSITION']);nr=copy.deepcopy(part);nr.update(vertex_start=vo,source_vertex_start=vo,vertex_count=n,index_start=ioff,index_count=tri.size);new_parts.append(nr);r=copy.deepcopy(row);r.update(new_vertex_range=[vo,vo+n],new_index_range=[ioff,ioff+tri.size]);new_pack.append(r);new_ix.extend((tri.reshape(-1)+vo).tolist());vo+=n;ioff+=tri.size;proof.update(final_triangles=len(tri));records.append(proof)
 assert ioff//3<=2000,(sp,ioff//3)
 def append(raw):
  b.extend(b'\0'*(-len(b)%4));off=len(b);b.extend(raw);idx=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(raw)});return idx
 def put(ar,kind,ctype):
  ar=np.ascontiguousarray(ar);idx=len(d['accessors']);r={'bufferView':append(ar.tobytes()),'componentType':ctype,'count':len(ar),'type':kind}
  if kind=='VEC3':r.update(min=ar.min(0).tolist(),max=ar.max(0).tolist())
  d['accessors'].append(r);return idx
 for k in at:pr['attributes'][k]=put(np.concatenate(new_at[k]).astype('<u2'if k=='JOINTS_0'else'<f4'),{'POSITION':'VEC3','NORMAL':'VEC3','TEXCOORD_0':'VEC2','JOINTS_0':'VEC4','WEIGHTS_0':'VEC4'}[k],5123 if k=='JOINTS_0'else 5126)
 pr['indices']=put(np.array(new_ix,dtype='<u4'),'SCALAR',5125);Image.fromarray(atlas).save(out/'atlas.png');d['images'][0]['bufferView']=append((out/'atlas.png').read_bytes());d['extras']['geometry_parts']=new_parts;dest=out/'author-reference.glb';write(dest,d,b);pack.update(parts=new_pack,candidates={'author-reference':{'path':str(dest),'sha256':sha(dest)}},atlas={'path':str(out/'atlas.png'),'sha256':sha(out/'atlas.png'),'size':size.tolist()});save(out/'packing.validation.json',pack);save(out/'parts.json',{k:oldspec[k]for k in ['parts','species','game','motion','viewer']if k in oldspec});save(out/'tail-donors.validation.json',{'ok':True,'species':sp,'baseline':str(base/'source-run/fish.glb'),'baseline_sha256':sha(base/'source-run/fish.glb'),'model':str(dest),'model_sha256':sha(dest),'settings':cfg,'settings_sha256':sha(settings),'body_tail_interval_native':[float(rear),float(rear+blend)],'body_end_width_before_after_mm':[float(2*cap_w.max()*scale*1000),float(2*new_w.max()*scale*1000)],'body_X_Y_unchanged':True,'forward_body_and_head_geometry_unchanged':True,'bones':18,'triangles':ioff//3,'records':records,'body_posterior_donor_copies':donor_rows,'physical_and_visual_acceptance':'pending'});print(json.dumps({'ok':True,'species':sp,'triangles':ioff//3,'body_width_mm':[float(2*cap_w.max()*scale*1000),float(2*new_w.max()*scale*1000)],'body_repaired_texels':len(donor_rows),'wall_triangles':sum(r.get('wall_triangles',0)for r in records)}))
if __name__=='__main__':main()
