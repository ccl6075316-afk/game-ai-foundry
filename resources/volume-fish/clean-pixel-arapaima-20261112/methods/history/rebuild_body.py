"""Own low-poly ring cage with reference-guided skin and recessed oral walls."""
from pathlib import Path
import sys,json,numpy as np
from scipy.interpolate import PchipInterpolator
ROOT=Path('/Users/czl/projects/game-ai-foundry');W=ROOT/'work/arapaima-jaw-20261112'
sys.path[:0]=[str(ROOT/'resources/scripts/volume-fish'),str(ROOT/'resources/scripts/volume-fish/portable')]
from audit_body_projection_envelope import body_triangles
from glb_io import read_glb,arrays
plan=json.loads((W/'whole-plan.json').read_bytes());tri=body_triangles(plan['reference']);rn=tri[:,:,0].max();rL=np.ptp(tri[:,:,0]);tri=(tri-[rn,0,0])/rL;tri[:,:,1]-=.14221
nose=.49288877844810486;L=.9097941815853119;y0=-.00460757
def section(t):
 lines=[]
 for face in tri:
  hits=[]
  for a,b in [(0,1),(1,2),(2,0)]:
   p,q=face[a],face[b]
   if (p[0]+t)*(q[0]+t)<0:hits.append(p+(q-p)*((-t-p[0])/(q[0]-p[0])))
  if len(hits)==2:lines.append(hits)
 return np.array(lines)
def section_ring(t,count):
 lines=section(t);pts=lines.reshape(-1,3);cy=(pts[:,1].min()+pts[:,1].max())/2;center=np.array([cy,0.]);out=[]
 for theta in np.arange(count)*2*np.pi/count:
  direction=np.array([np.cos(theta),np.sin(theta)]);a=lines[:,0,1:];v=lines[:,1,1:]-a
  cross=lambda p,q:p[...,0]*q[...,1]-p[...,1]*q[...,0]
  det=cross(np.broadcast_to(direction,v.shape),v);valid=abs(det)>1e-12
  r=cross(a-center,v)/np.where(valid,det,1);s=cross(a-center,np.broadcast_to(direction,v.shape))/np.where(valid,det,1);mask=valid&(r>=0)&(s>=0)&(s<=1)
  if mask.any():point=center+direction*r[mask].max()
  else:
   # Reference body is open along some fin sockets. Close only the centerline
   # of those declared root gaps using the actual two-sided boundary height.
   assert abs(direction[1])<1e-6,(t,theta)
   point=np.array([pts[:,1].max() if direction[0]>0 else pts[:,1].min(),0.])
  out.append([-t,*point])
 return np.array(out)
def nearest(t,points):
 a,b,c=t[:,0],t[:,1],t[:,2];ab=b-a;ac=c-a;n=np.cross(ab,ac);nn=np.sum(n*n,axis=1);aa=np.sum(ab*ab,axis=1);bb=np.sum(ac*ac,axis=1);cc=np.sum(ab*ac,axis=1);den=aa*bb-cc*cc;result=[]
 for point in points:
  q=point-n*(np.sum((point-a)*n,axis=1)/np.maximum(nn,1e-24))[:,None];ap=q-a;d=np.sum(ap*ab,axis=1);e=np.sum(ap*ac,axis=1);u=(bb*d-cc*e)/np.maximum(den,1e-24);v=(aa*e-cc*d)/np.maximum(den,1e-24);inside=(u>=0)&(v>=0)&(u+v<=1)&(den>1e-24);candidates=[q];scores=[np.where(inside,np.sum((q-point)**2,axis=1),np.inf)]
  for p,r in [(a,b),(b,c),(c,a)]:
   vec=r-p;f=np.clip(np.sum((point-p)*vec,axis=1)/np.maximum(np.sum(vec*vec,axis=1),1e-24),0,1);q=p+f[:,None]*vec;candidates.append(q);scores.append(np.sum((q-point)**2,axis=1))
  scores=np.array(scores);row,col=np.unravel_index(scores.argmin(),scores.shape);result.append(candidates[row][col])
 return np.array(result)
N=24
stations=[.999,.97,.94,.90,.86,.82,.78,.74,.70,.65,.60,.55,.50,.45,.40,.35,.30,.26,.22,.18,.15,.12,.10,.08,.065]
rings=[section_ring(t,N) if t<=.90 else np.zeros((N,3)) for t in stations]
# Retain the native finite tail-cap height and side taper rather than installing
# the library's attached caudal-root flare as a second tail.
for i,t in enumerate(stations):
 if t<=.90:continue
 xs=np.array(plan['station_from_nose']);old=np.array(plan['source_ymin_ymax_halfwidth']);half=np.interp(t,xs,(old[:,1]-old[:,0])/2);center=rings[3][:,1].mean();width=np.interp(t,xs,old[:,2]);theta=np.arange(N)*2*np.pi/N;rings[i]=np.c_[np.full(N,-t),center+half*np.cos(theta),width*np.sin(theta)]
# The last body section is a finite vertical cap, not a pointed cone. The
# caudal bank spans that complete section at the original body endpoint.
rings[0][:,0]=-1.
# Join the reference trunk to the native finite tail cap with one monotone
# curve. Reusing the old half-height at .94 after the narrower reference .90
# section creates an artificial pinched waist and secondary bulge.
tail_t=np.array([.78,.82,.86,1.])
tail_controls=np.array([[rings[stations.index(t)][:,1].min(),rings[stations.index(t)][:,1].max()] for t in tail_t[:-1]]+[[rings[0][:,1].min(),rings[0][:,1].max()]])
tail_lo=PchipInterpolator(tail_t,tail_controls[:,0]);tail_hi=PchipInterpolator(tail_t,tail_controls[:,1])
for i,t in enumerate(stations):
 if t<=.86:continue
 t=1. if i==0 else t
 lo,hi=float(tail_lo(t)),float(tail_hi(t));theta=np.arange(N)*2*np.pi/N
 rings[i][:,1]=(lo+hi)/2+(hi-lo)/2*np.cos(theta)
upper=np.array(plan['upper_lip_reference']);lower=np.array(plan['lower_lip_reference']);corner=(upper[0]+lower[0])/2;upper[0]=corner;lower[0]=corner
def rail(curve,t):
 arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))];arc/=arc[-1]
 return np.array([PchipInterpolator(arc,curve[:,k])(t) for k in range(3)])
rim=[]
for theta in np.arange(N)*2*np.pi/N:
 a=np.arccos(np.cos(theta));s=abs(a-np.pi/2)/(np.pi/2);q=rail(upper if a<=np.pi/2 else lower,s);q[2]*=1 if theta<=np.pi else -1;rim.append(q)
rim=np.array(rim)
top=np.array([[-.065,.17523,0],[-.04598,.16648,0],[-.03366,.16272,0],[-.02184,.16087,0],[-.01368,.1601,0],[-.01139,.15756,0],[-.01201,.15492,0]])
bottom=np.array([[-.065,.1169,0],[-.03868,.11883,0],[-.01749,.12438,0],[-.00488,.13285,0],[0.,.14436,0],[-.00624,.14802,0]])
top[:,1]-=.14221;bottom[:,1]-=.14221
c=tri.mean(1);normal=-np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12);profiles=np.array(plan['reference_ymin_ymax_halfwidth']);mid=np.interp(-c[:,0],plan['station_from_nose'],profiles[:,:2].mean(1));rad=np.c_[np.zeros(len(c)),c[:,1]-mid,c[:,2]];rad/=np.maximum(np.linalg.norm(rad,axis=1)[:,None],1e-12);outside=(np.sum(normal*rad,axis=1)>-.1)&(c[:,0]>-.07);upY=np.interp(c[:,0],upper[:,0],upper[:,1]);loY=np.interp(c[:,0],lower[:,0],lower[:,1]);upmask=outside&((c[:,0]<-.043)|(c[:,1]>=upY-.001));lomask=outside&((c[:,0]<-.043)|(c[:,1]<=loY+.001))
neck=rings[-1].copy()
for s in [.18,.36,.54,.70,.83,.93]:
 ring=neck*(1-s)+rim*s
 for j,theta in enumerate(np.arange(N)*2*np.pi/N):
  guide=top if np.cos(theta)>=0 else bottom;point=rail(guide,s);linear=guide[0]*(1-s)+guide[-1]*s;ring[j]+=(point-linear)*np.cos(theta)**2
 for positive,mask in [(True,upmask),(False,lomask)]:
  ids=[i for i in range(N) if (np.cos(i*2*np.pi/N)>=0)==positive];ring[ids]=nearest(tri[mask],ring[ids])
 rings.append(ring)
rings.append(rim)
p=np.concatenate(rings);faces=[];oral=[];jaw=[]
for i,t in enumerate(stations):jaw.extend([0.]*N)
for k in range(len(rings)-len(stations)):
 s=[.18,.36,.54,.70,.83,.93,1.][k]
 jaw.extend([float(s*s*(3-2*s)) if np.cos(j*2*np.pi/N)<0 else 0. for j in range(N)])
for i in range(len(rings)-1):
 for j in range(N):
  a=i*N+j;b=i*N+(j+1)%N;c=(i+1)*N+j;d=(i+1)*N+(j+1)%N
  faces.extend([[a,b,d],[a,d,c]]);oral.extend([False,False])
tail=len(p);p=np.vstack([p,[-1.,rings[0][:,1].mean(),0]]);jaw.append(0.)
for j in range(N):faces.append([tail,(j+1)%N,j]);oral.append(False)
rim_ids=np.arange((len(rings)-1)*N,len(rings)*N)
inner=rim.copy();inner[:,0]=-.058;inner[:,1]=-.001+(.55*(inner[:,1]+.001));inner[:,2]*=.68
inner_ids=np.arange(len(p),len(p)+N);p=np.vstack([p,inner]);jaw.extend([v*.35 for v in np.array(jaw)[rim_ids]])
for j in range(N):
 a,b=rim_ids[j],rim_ids[(j+1)%N];c,d=inner_ids[j],inner_ids[(j+1)%N];faces.extend([[a,b,d],[a,d,c]]);oral.extend([True,True])
cap=len(p);p=np.vstack([p,[-.066,-.001,0]]);jaw.append(0.)
for j in range(N):faces.append([inner_ids[j],inner_ids[(j+1)%N],cap]);oral.append(True)
faces=np.array(faces)
# Choose globally outward winding. The mouth interior is part of this same
# closed body and must retain the opposite facing direction to the outer skin.
volume=np.sum(np.einsum('ij,ij->i',p[faces[:,0]],np.cross(p[faces[:,1]],p[faces[:,2]])))/6
if volume<0:faces=faces[:,[0,2,1]]
edge={}
for f in faces:
 for a,b in zip(f,np.roll(f,-1)):edge[tuple(sorted((int(a),int(b))))]=edge.get(tuple(sorted((int(a),int(b)))),0)+1
assert all(v==2 for v in edge.values()),{k:v for k,v in edge.items() if v!=2}
directed={}
for f in faces:
 for a,b in zip(f,np.roll(f,-1)):directed[(int(a),int(b))]=directed.get((int(a),int(b)),0)+1
assert all(count==1 and directed.get((b,a))==1 for (a,b),count in directed.items()),'Inconsistent oriented skin/cavity seam'
native=p*L+[nose,y0,0]
# Original skeleton labels/weights are evaluated in the inverse whole-body
# deformation, then the lower-jaw amount replaces only its declared shell.
d,b=read_glb(plan['baseline']['path']);node=next(n for n in d['nodes'] if n.get('name')=='Closed_body' and 'mesh' in n);names=[d['nodes'][i]['name'] for i in d['skins'][node['skin']]['joints']];op=[];ow=[]
for pr in d['meshes'][node['mesh']]['primitives']:
 a=pr['attributes'];pos=arrays(d,b,a['POSITION']);ji=arrays(d,b,a['JOINTS_0']);we=arrays(d,b,a['WEIGHTS_0']);op.extend(pos)
 for ids,weights in zip(ji,we):ow.append({names[int(i)]:float(w) for i,w in zip(ids,weights) if w>1e-8})
op=np.array(op);grid=np.array(plan['field_grid']);xmap=np.array(plan['field_target_x']);t=np.interp(native[:,0],xmap[::-1],grid[::-1]);query=native.copy();query[:,0]=nose-t*L;query[:,1]=(native[:,1]-np.interp(t,grid,plan['field_yoffset']))/np.interp(t,grid,plan['field_yscale'])+y0;query[:,2]/=np.interp(t,grid,plan['field_zscale']);weights=[]
for i,q in enumerate(query):
 if p[i,0]>-.12:base={'body_00':1.}
 else:
  ids=np.argsort(np.sum((op-q)**2,axis=1))[:3];dist=np.linalg.norm(op[ids]-q,axis=1);f=1/np.maximum(dist,1e-7)**2;f/=f.sum();base={}
  for j,w in zip(ids,f):
   for name,value in ow[j].items():base[name]=base.get(name,0)+w*value
  base=dict(sorted(base.items(),key=lambda x:-x[1])[:4]);s=sum(base.values());base={k:v/s for k,v in base.items()}
 amount=jaw[i];base={k:v*(1-amount) for k,v in base.items() if v*(1-amount)>1e-8}
 if amount>0:base['jaw_lower']=amount
 assert len(base)<=4
 weights.append(base)
out={'vertices':native.tolist(),'faces':faces.tolist(),'oral':oral,'weights':weights,'rings':len(rings),'segments':N,'body_triangles':len(faces),'source':'independent sampled cage, no library topology/UV copied','reference':plan['reference'],'reference_scope':'body/eye/mouth form; game art, not biological measurement','tail_cap_scope':'native connected taper retained, reference caudal flare excluded','status':'gray construction, finite shape and full runtime validation pending'}
xs=native[:25*N].reshape(25,N,3)[:,0,0];sections=native[:25*N].reshape(25,N,3)
gx=np.linspace(xs[0],xs[-1],1001);gt=np.linspace(.001,.999,1001);old=np.array(plan['source_ymin_ymax_halfwidth'])
out['fin_transfer']={'x':gx.tolist(),'lower':PchipInterpolator(xs,sections[:,:,1].min(1))(gx).tolist(),'upper':PchipInterpolator(xs,sections[:,:,1].max(1))(gx).tolist(),'t':gt.tolist(),'old_lower':(PchipInterpolator(plan['station_from_nose'],old[:,0])(gt)*L+y0).tolist(),'old_upper':(PchipInterpolator(plan['station_from_nose'],old[:,1])(gt)*L+y0).tolist()}
(W/'rebuilt-body.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('own cage',len(p),'vertices',len(faces),'triangles','watertight_edges',len(edge))
