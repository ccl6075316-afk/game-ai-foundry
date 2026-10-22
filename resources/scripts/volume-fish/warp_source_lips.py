"""Bound an existing oral slit and complete jaw envelope to explicit source curves.

Retains vertex/index topology, skin, animations and every non-body primitive.
Transverse targets are per-source art constraints, not biological measurements.
"""
import argparse,copy,hashlib,json
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator,CubicHermiteSpline
from scipy.ndimage import gaussian_filter1d
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);a=ap.parse_args();rows=[]
 for p in json.loads(a.plan.read_text())['items']:
  assert sha(p['source'])==p['source_sha256'];assert sha(p['source_image'])==p['source_image_sha256']
  d,b=read_glb(Path(p['source']));old=copy.deepcopy(d);binary=bytearray(b)
  node=next(n for n in d['nodes'] if n.get('name')=='Closed_body' and 'mesh' in n);mi=node['mesh'];parts=d['meshes'][mi]['primitives'];assert len(parts)==2
  aa=[{k:accessor(d,b,i).copy() for k,i in q['attributes'].items()} for q in parts]
  triangles=[accessor(d,b,q['indices']).reshape(-1,3) for q in parts]
  oral=aa[1];skin=aa[0];join=float(p['join_u']);oldcorner=float(oral['POSITION'][:,0].min()+.5)
  im=np.array(Image.open(p['source_image']).convert('RGBA'));h,w=im.shape[:2];aspect=h/w
  lip=np.array(p['lip_pixels'],float);newcorner=lip[0,0]/w;end=float(p['end_u'])
  liproof=PchipInterpolator(lip[:,0]/w,(.5-lip[:,1]/h)*aspect);lipfloor=PchipInterpolator(lip[:,0]/w,(.5-lip[:,2]/h)*aspect)
  assert join<min(oldcorner,newcorner)
  def xmap(u):
   return np.where(u<oldcorner,join+(u-join)*(newcorner-join)/(oldcorner-join),newcorner+(u-oldcorner)*(end-newcorner)/(float(oral['POSITION'][:,0].max()+.5)-oldcorner))
  def stations(pos,mode):
   x=pos[:,0]+.5;xx=np.unique(np.round(x,7));yy=[]
   for q in xx:
    v=pos[abs(x-q)<2e-7,1];yy.append((v.max() if mode=='max' else v.min()))
   return PchipInterpolator(xx,yy)
  oldroof=stations(oral['POSITION'][oral['NORMAL'][:,1]<-.15],'max');oldfloor=stations(oral['POSITION'][oral['NORMAL'][:,1]>.15],'min')
  upper_end=float(oral['POSITION'][oral['NORMAL'][:,1]<-.15,0].max()+.5);lower_end=float(oral['POSITION'][oral['NORMAL'][:,1]>.15,0].max()+.5)
  # A tilted or rolled jaw can cross a horizontal threshold. Classify the
  # actual connected upper/lower anterior skin from its oral boundary seeds.
  skin_keys=[tuple(np.round(v,6)) for v in skin['POSITION']];unique={k:i for i,k in enumerate(dict.fromkeys(skin_keys))};coords=np.array(list(unique));edges=[]
  for f in triangles[0]:
   for i,j in zip(f,np.roll(f,-1)):
    if skin['POSITION'][i,0]+.5>oldcorner+1e-5 and skin['POSITION'][j,0]+.5>oldcorner+1e-5:edges.append([unique[skin_keys[i]],unique[skin_keys[j]]])
  ee=np.array(edges);graph=coo_matrix((np.ones(len(ee)),(ee[:,0],ee[:,1])),shape=(len(unique),len(unique)));_,labels=connected_components(graph,directed=False)
  votes=defaultdict(lambda:[0,0])
  for v,norm in zip(oral['POSITION'],oral['NORMAL']):
   k=tuple(np.round(v,6))
   if k in unique and v[0]+.5>oldcorner+1e-5 and abs(norm[1])>.15:votes[int(labels[unique[k]])][int(norm[1]>0)]+=1
  ownership={i:v[0]>v[1] for i,v in votes.items() if sum(v)>0}
  assert len(ownership)>=2,(p['species'],'Missing separate upper/lower jaw components',votes)
  xyz=skin['POSITION'][triangles[0]].astype(float)
  section_x=np.unique(np.r_[np.linspace(join,float(skin['POSITION'][:,0].max()+.5)-1e-6,160),join,.965])
  sections=[]
  for su in section_x:
   pts=[];sx=su-.5
   for ia,ib in [(0,1),(1,2),(2,0)]:
    va=xyz[:,ia];vb=xyz[:,ib];crossing=(va[:,0]<=sx)&(vb[:,0]>=sx)|(vb[:,0]<=sx)&(va[:,0]>=sx)
    crossing&=abs(va[:,0]-vb[:,0])>1e-12;va=va[crossing];vb=vb[crossing]
    t=(sx-va[:,0])/(vb[:,0]-va[:,0]);pts.extend(va+t[:,None]*(vb-va))
   pts=np.array(pts);assert len(pts)>0
   sections.append([su,pts[:,1].max(),pts[:,1].min(),abs(pts[:,2]).max()])
  sections=np.array(sections);oldtop=PchipInterpolator(sections[:,0],sections[:,1]);oldbottom=PchipInterpolator(sections[:,0],sections[:,2])
  # An explicit monotone transverse front. Preserve the original posterior
  # half width and ease into the independent lip width, without a barrel join.
  width_start=float(p.get('width_start_u',.965));target_end=float(p['half_width_stations'][-1][1])
  oldwidth=PchipInterpolator(sections[:,0],sections[:,3])
  start_width=float(oldwidth(width_start));assert p.get('preserve_width') or target_end<start_width
  width_curve=CubicHermiteSpline([width_start,end],[start_width,target_end],[float(oldwidth.derivative()(width_start)),0.])
  # Outer source envelope is smoothed only for geometry; native pixels remain.
  col=np.arange(w);top=np.full(w,np.nan);bottom=top.copy()
  for i in range(max(0,round(join*w)-5),w):
   yy=np.flatnonzero(im[:,i,3]>=200)
   if len(yy):top[i]=yy.min();bottom[i]=yy.max()
  known=np.flatnonzero(np.isfinite(top));top=gaussian_filter1d(np.interp(col,known,top[known]),2);bottom=gaussian_filter1d(np.interp(col,known,bottom[known]),2)
  originals=[q['POSITION'].copy() for q in aa]
  original_normals=[q['NORMAL'].copy() for q in aa];normal_ownership=[]
  def evaluate(test_u,test_y,upper,si):
   limit=np.where(upper,upper_end,lower_end)
   nu=np.where(test_u<oldcorner,join+(test_u-join)*(newcorner-join)/(oldcorner-join),newcorner+(np.minimum(test_u,limit)-oldcorner)*(end-newcorner)/(limit-oldcorner))
   nu=np.where(test_u>join,nu,test_u)
   ro=oldroof(np.clip(test_u,oldcorner,upper_end));fl=oldfloor(np.clip(test_u,oldcorner,lower_end))
   nr=liproof(np.clip(nu,newcorner,end));nf=lipfloor(np.clip(nu,newcorner,end));middle=(nr+nf)*.5
   fade=np.clip((nu-newcorner)/float(p['corner_blend_u']),0,1);fade=fade*fade*(3-2*fade);nr=middle+(nr-middle)*fade;nf=middle+(nf-middle)*fade
   if si==1:ny=np.where(upper,nr,nf)
   else:
    top=oldtop(test_u);bottom=oldbottom(test_u)
    tu=np.clip((test_y-ro)/np.maximum(top-ro,1e-7),0,1);tl=np.clip((fl-test_y)/np.maximum(fl-bottom,1e-7),0,1)
    ny=np.where(upper,nr+(top-nr)*tu,nf+(bottom-nf)*tl)
   blend=np.clip((test_u-join)/max(oldcorner-join,1e-5),0,1);blend=blend*blend*(3-2*blend)
   return nu,test_y+(ny-test_y)*blend
  for si,attrs in enumerate(aa):
   pos=attrs['POSITION'];oldpos=pos.copy();u=oldpos[:,0]+.5;mask=u>join;y=oldpos[:,1]
   ro=oldroof(np.clip(u,oldcorner,upper_end));fl=oldfloor(np.clip(u,oldcorner,lower_end))
   upper=(attrs['NORMAL'][:,1]<0) if si==1 else y>=(ro+fl)*.5
   if si==0:
    for i,k in enumerate(skin_keys):
     if u[i]>oldcorner+1e-5 and int(labels[unique[k]]) in ownership:upper[i]=ownership[int(labels[unique[k]])]
   normal_ownership.append(upper.copy())
   limit=np.where(upper,upper_end,lower_end)
   nu=np.where(u<oldcorner,join+(u-join)*(newcorner-join)/(oldcorner-join),newcorner+(np.minimum(u,limit)-oldcorner)*(end-newcorner)/(limit-oldcorner));nu=np.where(mask,nu,u)
   nr=liproof(np.clip(nu,newcorner,end));nf=lipfloor(np.clip(nu,newcorner,end))
   mid=(nr+nf)*.5;fade=np.clip((nu-newcorner)/float(p['corner_blend_u']),0,1);fade=fade*fade*(3-2*fade);nr=mid+(nr-mid)*fade;nf=mid+(nf-mid)*fade
   before=nu<newcorner;nr[before]=mid[before];nf[before]=mid[before]
   nt=oldtop(u);nb=oldbottom(u)
   if si==1:
    # Actual oral halves use original normal ownership, including shared rim.
    upper=attrs['NORMAL'][:,1]<0;ny=np.where(upper,nr,nf)
   else:
    ty=np.clip((y-ro)/np.maximum(oldtop(u)-ro,1e-7),0,1);by=np.clip((fl-y)/np.maximum(fl-oldbottom(u),1e-7),0,1)
    ny=np.where(upper,nr+(nt-nr)*ty,nf+(nb-nf)*by)
   blend=np.clip((u-join)/max(oldcorner-join,1e-5),0,1);blend=blend*blend*(3-2*blend)
   pos[mask,0]=nu[mask]-.5;pos[mask,1]=(y+(ny-y)*blend)[mask]
   desired=width_curve(np.clip(u,width_start,end))
   factor=np.ones(len(u)) if p.get('preserve_width') else np.where(u>width_start,desired/np.maximum(oldwidth(u),1e-7),1.)
   pos[:,2]=oldpos[:,2]*factor
   # All skin/lining common rim vertices receive exactly the same source UV.
   uv=attrs['TEXCOORD_0'];uv[mask,0]=pos[mask,0]+.5;uv[mask,1]=.5-pos[mask,1]/aspect
   if si==1 and 'TEXCOORD_1' in attrs:attrs['TEXCOORD_1'][:,0]*=factor
   assert np.array_equal(pos[~mask],oldpos[~mask])
  # Preserve welded skin/lining seams by copying the unique complete-jaw warp
  # for every original common coordinate; never independently offset a lip.
  def welded_key(v):return tuple(round(float(x),7) for x in v)
  mapped={}
  for i,v in enumerate(originals[0]):
   if v[0]+.5<=join:continue
   k=welded_key(v)
   if k not in mapped:mapped[k]=aa[0]['POSITION'][i].copy()
   else:aa[0]['POSITION'][i]=mapped[k]
  for i,v in enumerate(originals[1]):
   if welded_key(v) not in mapped:mapped[welded_key(v)]=aa[1]['POSITION'][i].copy()
   if welded_key(v) in mapped:
    aa[1]['POSITION'][i]=mapped[welded_key(v)];q=mapped[welded_key(v)];aa[1]['TEXCOORD_0'][i]=[q[0]+.5,.5-q[1]/aspect]
  for si,(attrs,tt) in enumerate(zip(aa,triangles)):
   pos=attrs['POSITION'];norm=np.zeros_like(pos);fn=np.cross(pos[tt[:,1]]-pos[tt[:,0]],pos[tt[:,2]]-pos[tt[:,0]])
   for i in range(3):np.add.at(norm,tt[:,i],fn)
   sums=defaultdict(lambda:np.zeros(3))
   for i,v in enumerate(pos):sums[tuple(np.round(v,7))]+=norm[i]
   norm=np.array([sums[tuple(np.round(v,7))] for v in pos]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12)
   if p.get('preserve_width'):
    u=originals[si][:,0]+.5;y=originals[si][:,1];upper=normal_ownership[si];eps=1e-5
    xp,yp=evaluate(u+eps,y,upper,si);xm,ym=evaluate(u-eps,y,upper,si);_,yplus=evaluate(u,y+eps,upper,si);_,yminus=evaluate(u,y-eps,upper,si)
    dx=(xp-xm)/(2*eps);dydu=(yp-ym)/(2*eps);dydy=(yplus-yminus)/(2*eps)
    good=(abs(dx)>.05)&(abs(dydy)>.05);oldn=original_normals[si].astype(float);nn=oldn.copy()
    nn[good,0]=oldn[good,0]/dx[good]-oldn[good,1]*dydu[good]/(dx[good]*dydy[good]);nn[good,1]=oldn[good,1]/dydy[good]
    nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-12);norm[good]=nn[good]
   # Check the new normals agree with the previous global winding convention.
   keep=originals[si][:,0]+.5<=join
   compare=keep if keep.any() else np.ones(len(pos),bool)
   if np.median(np.sum(norm[compare]*attrs['NORMAL'][compare],axis=1))<0:norm=-norm
   norm[keep]=attrs['NORMAL'][keep];attrs['NORMAL']=norm.astype(np.float32)
   for key in ['POSITION','NORMAL','TEXCOORD_0','TEXCOORD_1']:
    if key not in attrs:continue
    value=np.asarray(attrs[key],dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));off=len(binary);binary.extend(value.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':value.nbytes,'target':34962});idx=len(d['accessors']);d['accessors'].append({'bufferView':vi,'componentType':5126,'count':len(value),'type':'VEC'+str(value.shape[1]),'min':value.min(0).tolist(),'max':value.max(0).tolist()});parts[si]['attributes'][key]=idx
  for key in ['nodes','skins','animations','images','materials','textures','samplers']:assert d.get(key)==old.get(key)
  for i,m in enumerate(d['meshes']):
   if i!=mi:assert m==old['meshes'][i]
  assert binary[:len(b)]==b
  target=Path(p['target']);target.parent.mkdir(parents=True,exist_ok=True);write(target,d,binary)
  rows.append({'species':p['species'],'source_sha256':p['source_sha256'],'model_sha256':sha(target),'topology_indices_skin_animation_fins_preserved':True,'old_corner_u':oldcorner,'new_corner_u':newcorner,'lip_half_width':target_end,'visual_review':'pending'})
  print('SOURCE_LIP_WARP',p['species'],flush=True)
 a.report.write_text(json.dumps({'ok':True,'script_sha256':sha(__file__),'plan_sha256':sha(a.plan),'items':rows},indent=2)+'\n')
if __name__=='__main__':main()
