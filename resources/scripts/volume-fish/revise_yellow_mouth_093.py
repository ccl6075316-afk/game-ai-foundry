from pathlib import Path
import sys,json,copy,shutil,hashlib
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from PIL import Image
R=next(p for p in Path(__file__).resolve().parents if (p/'cli/gamefactory.py').exists());W=R/'projects/fishing-2d/experiments/blender-fish/yellow-mouth-093';G=R/'projects/fish-093-yellow-mouth/game';S=R/'resources/scripts/volume-fish';sys.path.insert(0,str(S))
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
parameters=json.loads((R/'resources/volume-fish/mouth-yellow-croaker-093.json').read_text());geometry=parameters['geometry'];uv_parameters=parameters['uv']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for rel in ['assets/models/fish/yellow_croaker.glb','assets/models/fish/motion/head-source.json','assets/models/fish/motion/mouth-pigment.json','assets/models/fish/motion/body-opacity.json','assets/models/fish/motion/surface-ownership.json','scripts/aquarium/FishHeadSource.gd','scripts/aquarium/FishHeadSource.gdshaderinc','scripts/aquarium/FishMouthPigment.gdshader']:
 p=W/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():shutil.copy2(G/rel,p)
source=W/'inputs/baseline.glb';d,b=read_glb(source);old=copy.deepcopy(d);node=next(n for n in d['nodes']if n.get('name')=='Closed_body');pr=d['meshes'][node['mesh']]['primitives'];vs=[accessor(d,b,p['attributes']['POSITION'])for p in pr]
cfg=json.loads((W/'inputs/baseline-head-source.json').read_text());profile=cfg['profiles']['yellow_croaker'];aspect=profile['model_aspect'];old_path=np.array(profile['model_path']);old_center=PchipInterpolator(old_path[:,0],old_path[:,1],extrapolate=True)
skin_tri=vs[0][accessor(d,b,pr[0]['indices']).reshape(-1,3)];sample_x=np.linspace(.28,float(vs[0][:,0].max())-1e-8,400);bounds=[]
for x in sample_x:
 points=[]
 for j,k in [(0,1),(1,2),(2,0)]:
  a=skin_tri[:,j];z=skin_tri[:,k];valid=((a[:,0]<=x)&(z[:,0]>x))|((z[:,0]<=x)&(a[:,0]>x));a=a[valid];z=z[valid];t=(x-a[:,0])/(z[:,0]-a[:,0]);points.extend(a+t[:,None]*(z-a))
 points=np.array(points);bounds.append([points[:,1].min(),points[:,1].max(),np.max(abs(points[:,2]))])
bounds=np.array(bounds);im=np.asarray(Image.open(W/'inputs/yellow_croaker.png'));source_x=[];source_lo=[];source_hi=[]
for x in range(int(.775*im.shape[1]),im.shape[1]):
 rows=np.where(im[:,x,3]>128)[0]
 if len(rows):source_x.append((x+.5)/im.shape[1]);source_lo.append((.5-(rows[-1]+.5)/im.shape[0])*aspect);source_hi.append((.5-(rows[0]+.5)/im.shape[0])*aspect)
source_lo=gaussian_filter1d(source_lo,1.1);source_hi=gaussian_filter1d(source_hi,1.1)
# Annotated native pixels: oral cleft is below the maxillary plate.
gap_pixels=np.array(parameters['oral_edges_canvas_px'],float)
gap=np.column_stack([gap_pixels[:,0]/2014,gap_pixels[:,1:]/727]);target_upper=PchipInterpolator(gap[:,0],gap[:,1]);target_lower=PchipInterpolator(gap[:,0],gap[:,2])
def deform(points):
 out=points.astype(float).copy();x=points[:,0];y=points[:,1];u=x+.5
 center=(.5-old_center(u))*aspect;f=np.clip((u-.93)/.012,0,1);f=f*f*(3-2*f);roll=profile['model_lip_roll']*f
 ol=center-profile['model_gap']/2-roll;ou=center+profile['model_gap']/2+roll
 low=np.interp(x,sample_x,bounds[:,0]);high=np.interp(x,sample_x,bounds[:,1])
 nx=x.copy() # preserve upper/lower reach and native transverse envelope
 cu=np.clip(nx+.5,gap[0,0],gap[-1,0]);tu=(.5-target_upper(cu))*aspect;tl=(.5-target_lower(cu))*aspect
 # Match both the chin and forehead to the original canvas, independently of
 # the cleft. Keeping the old chin was what made 090 a thin mandibular blade.
 dest_low=np.interp(nx+.5,source_x,source_lo);dest_high=np.interp(nx+.5,source_x,source_hi)
 dest_low=np.minimum(dest_low,tl-.0015);dest_high=np.maximum(dest_high,tu+.0015)
 below=tl+(y-ol)*(tl-dest_low)/np.maximum(ol-low,1e-5)
 above=tu+(y-ou)*(dest_high-tu)/np.maximum(high-ou,1e-5)
 between=tl+(y-ol)*(tu-tl)/np.maximum(ou-ol,1e-5)
 cleft_shape=np.where(y<ol,below,np.where(y>ou,above,between))
 section_shape=dest_low+(y-low)*(dest_high-dest_low)/np.maximum(high-low,1e-6)
 oral_blend=np.clip((x-geometry['oral_blend_start'])/geometry['oral_blend_span'],0,1);oral_blend=oral_blend*oral_blend*(3-2*oral_blend)
 ny=section_shape*(1-oral_blend)+cleft_shape*oral_blend
 blend=np.clip((x-geometry['influence_start'])/(geometry['influence_full']-geometry['influence_start']),0,1);blend=blend*blend*(3-2*blend)
 out[:,1]=y+(ny-y)*blend;out[:,0]=nx
 out[:,2]=points[:,2] # no species transverse measurements: preserve existing width
 return out
original_vs=[v.copy()for v in vs];vs=[deform(v).astype('<f4')for v in vs]
def add_array(data,kind):
 global binary
 data=np.asarray(data,dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(data.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=data.nbytes,target=34962));ac=len(d['accessors']);d['accessors'].append(dict(bufferView=vi,componentType=5126,count=len(data),type=kind,min=data.min(0).tolist(),max=data.max(0).tolist()));return ac
binary=bytearray(b);min_jacobian=1.
for pi,vertices in enumerate(original_vs):
 jac=[]
 for axis in range(3):
  delta=np.zeros(3);delta[axis]=.000002;jac.append((deform(vertices+delta)-deform(vertices-delta))/.000004)
 jac=np.stack(jac,axis=2);min_jacobian=min(min_jacobian,float(np.linalg.det(jac).min()));assert min_jacobian>0,'Folded shape mapping'
 normal=accessor(d,b,pr[pi]['attributes']['NORMAL']);mapped_normal=np.linalg.solve(jac.transpose(0,2,1),normal[:,:,None])[:,:,0];mapped_normal/=np.linalg.norm(mapped_normal,axis=1)[:,None]
 mapped_normal[vertices[:,0]<=.29]=normal[vertices[:,0]<=.29]
 pr[pi]['attributes']['POSITION']=add_array(vs[pi],'VEC3');pr[pi]['attributes']['NORMAL']=add_array(mapped_normal,'VEC3')
ks=[[tuple(np.round(v,7))for v in a]for a in vs];shared=set(ks[0])&set(ks[1]);edges=[]
for p,kk in zip(pr,ks):
 es=set()
 for tri in accessor(d,b,p['indices']).reshape(-1,3):
  for i,j in zip(tri,np.roll(tri,-1)):
   if kk[i]in shared and kk[j]in shared and kk[i]!=kk[j]:es.add(tuple(sorted((kk[i],kk[j]))))
 edges.append(es)
edges=sorted(edges[0]&edges[1]);segments=np.array(edges);a=segments[:,0];ab=segments[:,1]-a;den=(ab*ab).sum(1)
identity=accessor(d,b,pr[1]['attributes']['TEXCOORD_1'])[:,1];upper={k:float(q>.5)for k,q in zip(ks[1],identity)}
adj={}
for q,r in edges:adj.setdefault(q,[]).append(r);adj.setdefault(r,[]).append(q)
assert all(len(q)==2 for q in adj.values());start=min(adj);chain=[start];prev=None;cur=start
while True:
 nxt=next(q for q in adj[cur]if q!=prev)
 if nxt==start:break
 chain.append(nxt);prev,cur=cur,nxt
assert len(chain)==len(adj)
def rdp(points,tol):
 if len(points)<3:return points
 aa=points[0];bb=points[-1]-aa;dist=np.linalg.norm(points-(aa+np.clip((points-aa)@bb/max(bb@bb,1e-20),0,1)[:,None]*bb),axis=1);i=int(dist.argmax())
 return np.concatenate([rdp(points[:i+1],tol)[:-1],rdp(points[i:],tol)])if dist[i]>tol else points[[0,-1]]
chain=np.array(chain);n=len(chain)//2;reduced=np.concatenate([rdp(chain[:n+1],.000035)[:-1],rdp(np.concatenate([chain[n:],chain[:1]]),.000035)])
assert len(reduced)<160,len(reduced)
p=cfg['profiles']['yellow_croaker'];p['mouth_source_edges']=gap.tolist();source_path=np.array(p['mouth_source_edges']);su=PchipInterpolator(source_path[:,0],source_path[:,1]);sl=PchipInterpolator(source_path[:,0],source_path[:,2]);aspect=p['model_aspect']
def nearest(points):
 best=np.full(len(points),np.inf);idx=np.zeros(len(points),int);ts=np.zeros(len(points))
 for j in range(0,len(points),500):
  pts=points[j:j+500];tt=np.clip(((pts[:,None,:]-a)*ab).sum(2)/den,0,1);dd=np.linalg.norm(pts[:,None,:]-(a+tt[:,:,None]*ab),axis=2);ii=dd.argmin(1);best[j:j+len(pts)]=dd[np.arange(len(pts)),ii];idx[j:j+len(pts)]=ii;ts[j:j+len(pts)]=tt[np.arange(len(pts)),ii]
 return best,idx,ts
def source_rim(points,idx,ts):
 q=a[idx]+ts[:,None]*ab[idx];u=q[:,0]+.5
 # Side lips retain source progression; the unseen front turns into the same
 # native lip strip instead of taking the source silhouette's black endcap.
 front=np.clip((u-uv_parameters['rim_front_u_start'])/uv_parameters['rim_front_u_span'],0,1);front=front*front*(3-2*front)
 across=np.clip(np.abs(q[:,2])/uv_parameters['rim_width_native'],0,1);donor=(1-front)*u+front*(uv_parameters['rim_donor_u_start']+uv_parameters['rim_donor_u_span']*across)
 donor=np.clip(donor,source_path[0,0],source_path[-1,0]);up=np.array([upper[edges[i][0]]for i in idx]);v=np.where(up>.5,su(donor),sl(donor));v+=np.where(up>.5,*uv_parameters['rim_source_offset_px'])/727
 return np.column_stack([donor,v]),up
reports=[]
for pi,vertices in enumerate(vs):
 uv=accessor(old,b,old['meshes'][node['mesh']]['primitives'][pi]['attributes']['TEXCOORD_0']);uvold=uv.copy();dist,idx,tt=nearest(vertices);mapped,up=source_rim(vertices,idx,tt)
 if pi==0:
  head=vertices[:,0]>.29;uv[head]=np.column_stack([vertices[head,0]+.5,.5-vertices[head,1]/aspect])
  lateral=np.clip(abs(vertices[:,2])/uv_parameters['lateral_native'],0,1)
  front=np.clip((vertices[:,0]-uv_parameters['front_start'])/uv_parameters['front_span'],0,1)*(1-lateral)**2
  mapped[:,1]+=np.where(up>.5,-1.,1.)*dist/aspect
  uv=uv*(1-front[:,None])+mapped*front[:,None]
 else:
  uv=mapped
  for i,k in enumerate(ks[1]):
   if k in skin_uv_lookup:uv[i]=skin_uv_lookup[k]
 uv=uv.astype('<f4');binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(uv.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=uv.nbytes,target=34962));ac=len(d['accessors']);d['accessors'].append(dict(bufferView=vi,componentType=5126,count=len(uv),type='VEC2',min=uv.min(0).tolist(),max=uv.max(0).tolist()));pr[pi]['attributes']['TEXCOORD_0']=ac
 if pi==0:skin_uv_lookup=dict(zip(ks[0],uv))
 reports.append(dict(surface=pi,changed_uv_vertices=int(np.any(uvold!=uv,axis=1).sum())))
target=W/'yellow_croaker.glb';write(target,d,binary)
# A compact true 3D rim supports per-fragment distance even where every oral
# triangle vertex lies on the border (vertex distance interpolation is invalid).
starts=[];ends=[]
for q,r in zip(reduced[:-1],reduced[1:]):
 starts.append([*map(float,q),upper[tuple(q)]]);ends.append([*map(float,r),upper[tuple(r)]])
cross=[]
verts=vs[0];faces=accessor(old,b,pr[0]['indices']).reshape(-1,3);tri=verts[faces]
for x in np.linspace(.29,float(verts[:,0].max())-1e-7,32):
 intersections=[]
 for j,k in [(0,1),(1,2),(2,0)]:
  aa=tri[:,j];bb=tri[:,k];valid=((aa[:,0]<=x)&(bb[:,0]>x))|((bb[:,0]<=x)&(aa[:,0]>x));v=aa[valid];w=bb[valid];t=(x-v[:,0])/(w[:,0]-v[:,0]);intersections.extend(v+t[:,None]*(w-v))
 q=np.array(intersections);lo=q[:,1].min();hi=q[:,1].max();cross.append([float(x),float((lo+hi)/2),float((hi-lo)/2),float(np.max(np.abs(q[:,2])))])
eye_x=float(p['eye']['center'][0]-.5);eye_halfheight=np.interp(eye_x,np.array(cross)[:,0],np.array(cross)[:,2]);eye_angle=float(np.arcsin(min(.95,p['eye']['radius'][1]*aspect*.90/eye_halfheight)))
p['rim_local']=dict(starts=starts,ends=ends,cross_sections=cross,eye_native_center_x=eye_x,eye_native_radius_x=float(p['eye']['radius'][0]*.90),eye_center_angle=.10,eye_angular_radius=eye_angle)
p['model_sha256']=sha(target);(W/'head-source.json').write_text(json.dumps(cfg,indent=2))
for pi in range(2):
 for k in ['JOINTS_0','WEIGHTS_0','TEXCOORD_1']:assert pr[pi]['attributes'][k]==old['meshes'][node['mesh']]['primitives'][pi]['attributes'][k]
for i,(before,after)in enumerate(zip(old['meshes'],d['meshes'])):
 if i!=node['mesh']:assert before==after
assert old['skins']==d['skins'] and old['animations']==d['animations'] and old['images']==d['images']
report=dict(ok=True,source_sha256=sha(source),model_sha256=sha(target),actual_rim_edges=len(edges),shader_rim_segments=len(starts),weights_bones_animations_fins_source_image_bytes_unchanged=True,eye_scope=parameters['eye_scope'],parameter_sha256=sha(R/'resources/volume-fish/mouth-yellow-croaker-093.json'),geometry_change='Source-canvas full chin, forehead and oral-cleft fit; existing transverse width preserved, no new biological width claim',minimum_deformation_jacobian=min_jacobian,max_position_change=float(np.linalg.norm(vs[0]-original_vs[0],axis=1).max()),uv_changes=reports)
(W/'build.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
