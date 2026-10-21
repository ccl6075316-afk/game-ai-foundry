"""Round an existing lower jaw silhouette, keeping mouth rim and other meshes fixed.

The target is a bounded smoothing fit of the actual side-projection lower skin
contour. It is a production shape constraint, not a biological measurement.
Conforming local edge splits let the mesh represent that target curve.
"""
import argparse,copy,hashlib,json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.interpolate import UnivariateSpline,PchipInterpolator
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def keys(v):return [tuple(round(float(x),7) for x in q) for q in v]
def ease(t):
 t=np.clip(t,0.,1.);return t*t*t*(10.+t*(-15.+6.*t))
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ['input','source','parameters','contour','head-config','output','config-output','report']:ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();cfg=json.loads(a.parameters.read_text());assert sha(a.input)==cfg['baseline_sha256'];assert sha(a.source)==cfg['source_sha256']
 d,b=read_glb(a.input);original=copy.deepcopy(d);binary=bytearray(b)
 mi=next(n['mesh'] for n in d['nodes'] if n.get('name')=='Closed_body');pr=d['meshes'][mi]['primitives'];assert len(pr)==2
 attrs={k:accessor(d,b,ix).copy() for k,ix in pr[0]['attributes'].items()};v=attrs['POSITION'];f=accessor(d,b,pr[0]['indices']).reshape(-1,3)
 oral=accessor(d,b,pr[1]['attributes']['POSITION']);oral_f=accessor(d,b,pr[1]['indices']).reshape(-1,3);oral_up=accessor(d,b,pr[1]['attributes']['TEXCOORD_1'])[:,1]
 old_v=v.copy();old_faces=f.copy();old_keys=keys(v);shared=set(old_keys)&set(keys(oral));rim_mask=np.array([k in shared for k in keys(oral)]);lower=oral[rim_mask&(oral_up<.5)]
 samples=np.linspace(lower[:,0].min(),lower[:,0].max(),64);lip_y=PchipInterpolator(samples,[np.median(lower[np.argsort(abs(lower[:,0]-x))[:6],1]) for x in samples])
 contour=json.loads(a.contour.read_text());assert contour['model_sha256']==sha(a.input)
 rows=np.array(contour['rows_native_canvas_and_actual_point']);lo,hi=cfg['source_x_range'];rows=rows[(rows[:,0]>=lo)&(rows[:,0]<=hi)];px,py=rows[:,0],rows[:,1]
 target=UnivariateSpline(px,py,k=3,s=len(rows)*cfg['smoothing_rms_px']**2);bottom=PchipInterpolator(px,(363.5-py)/2014)
 assert abs(target(px)-py).max()<=cfg['max_target_deviation_px']
 vals={k:[q.copy() for q in ar] for k,ar in attrs.items()};rim_edges=set();counts=Counter()
 for face in f:
  for i,j in zip(face,np.roll(face,-1)):
   if old_keys[i]!=old_keys[j]:counts[tuple(sorted((old_keys[i],old_keys[j])))]+=1
 rim_edges={k for k,n in counts.items() if n==1};split_count=0
 def midpoint(i,j,cache):
  pair=tuple(sorted((int(i),int(j))))
  if pair in cache:return cache[pair]
  idx=len(vals['POSITION']);cache[pair]=idx
  for k in vals:
   if k in ['JOINTS_0','WEIGHTS_0']:continue
   vals[k].append(((vals[k][i]+vals[k][j])*.5).astype(attrs[k].dtype))
  weight={}
  for q in [i,j]:
   for bone,w in zip(vals['JOINTS_0'][q],vals['WEIGHTS_0'][q]):weight[int(bone)]=weight.get(int(bone),0.)+float(w)*.5
  top=sorted(weight.items(),key=lambda q:-q[1])[:4];total=sum(w for _,w in top);assert total>0
  vals['JOINTS_0'].append(np.array([bone for bone,_ in top]+[0]*(4-len(top)),dtype=attrs['JOINTS_0'].dtype));vals['WEIGHTS_0'].append(np.array([w/total for _,w in top]+[0.]*(4-len(top)),dtype=attrs['WEIGHTS_0'].dtype))
  return idx
 for iteration in range(cfg['max_split_iterations']):
  vv=np.asarray(vals['POSITION']);kk=keys(vv);marked=set()
  for face in f:
   for i,j in zip(face,np.roll(face,-1)):
    pair=tuple(sorted((kk[i],kk[j])));mid=(vv[i]+vv[j])*.5;xpix=(mid[0]+.5)*2014
    if pair in rim_edges or not lo<xpix<hi:continue
    by=bottom(np.clip(xpix,lo,hi));ly=lip_y(np.clip(mid[0],samples[0],samples[-1]));depth=max(float(ly-by),.001)
    if (ly-mid[1])/depth<cfg['subdivide_depth_fraction']:continue
    if np.linalg.norm(vv[i]-vv[j])*2014>cfg['max_edge_px']:marked.add(pair)
  if not marked:break
  cache={};nf=[]
  for face in f:
   mids=[midpoint(i,j,cache) if tuple(sorted((kk[i],kk[j]))) in marked else None for i,j in zip(face,np.roll(face,-1))];n=sum(q is not None for q in mids)
   if n==0:nf.append(face.tolist())
   elif n==1:
    k=next(i for i,q in enumerate(mids) if q is not None);i,j,z=[int(face[(k+t)%3]) for t in range(3)];m=mids[k];nf.extend([[i,m,z],[m,j,z]])
   elif n==2:
    k=next(i for i,q in enumerate(mids) if q is None);i,j,z=[int(face[(k+t)%3]) for t in range(3)];m1,m2=mids[(k+1)%3],mids[(k+2)%3];nf.extend([[i,j,m2],[j,m1,m2],[m2,m1,z]])
   else:
    i,j,z=map(int,face);ab,bc,ca=mids;nf.extend([[i,ab,ca],[ab,j,bc],[ca,bc,z],[ab,bc,ca]])
  f=np.asarray(nf,dtype='<u4');split_count+=len(cache)
 else:raise AssertionError('Required lower-jaw subdivision did not converge')
 before=np.asarray(vals['POSITION'],dtype='<f4');new=before.copy();xpx=(before[:,0]+.5)*2014;xx=np.clip(xpx,lo,hi)
 by=bottom(xx);ly=lip_y(np.clip(before[:,0],samples[0],samples[-1]));fraction=(ly-before[:,1])/np.maximum(ly-by,.001)
 depth_weight=ease((fraction-cfg['deform_start_depth_fraction'])/(1-cfg['deform_start_depth_fraction']))
 window=ease((xpx-lo)/cfg['endpoint_fade_px'])*ease((hi-xpx)/cfg['endpoint_fade_px'])
 dy=((363.5-target(xx))/2014-by)*window*depth_weight
 fixed=np.array([k in shared for k in keys(before)]);dy[fixed]=0.;new[:,1]+=dy.astype('<f4')
 # All upper/lip points are frozen; changed lower skin has welded geometric normals.
 q=new[f];area=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);sums=np.zeros_like(new)
 for j in range(3):np.add.at(sums,f[:,j],area)
 all_keys=keys(new);_,inverse=np.unique(np.round(new,7),axis=0,return_inverse=True);weld=np.zeros((inverse.max()+1,3));np.add.at(weld,inverse,sums);normals=weld[inverse];normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-15)
 base_normals=np.asarray(vals['NORMAL']);unchanged=(abs(dy)<1e-9);normals[unchanged]=base_normals[unchanged]
 values={k:np.asarray(vv,dtype=attrs[k].dtype) for k,vv in vals.items()};values['POSITION']=new;values['NORMAL']=normals.astype('<f4')
 edge_counts=Counter()
 for vertices,faces in [(new,f),(oral,oral_f)]:
  kk=keys(vertices)
  for face in faces:
   t=[kk[i] for i in face];assert len(set(t))==3,'Degenerate triangle'
   for u,w in zip(t,t[1:]+t[:1]):edge_counts[tuple(sorted((u,w)))]+=1
 assert all(n==2 for n in edge_counts.values()),'Body must remain welded closed'
 assert np.array_equal(new[fixed],before[fixed]);assert np.array_equal(new[:len(old_v)][old_v[:,0]<lo/2014-.5],old_v[old_v[:,0]<lo/2014-.5])
 def add(ar,kind):
  ar=np.ascontiguousarray(ar);binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(ar.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':ar.nbytes});ai=len(d['accessors']);ct={np.dtype('float32'):5126,np.dtype('uint32'):5125,np.dtype('uint16'):5123,np.dtype('uint8'):5121}[ar.dtype];d['accessors'].append({'bufferView':vi,'componentType':ct,'count':len(ar),'type':kind,'min':np.atleast_1d(ar.min(0)).tolist(),'max':np.atleast_1d(ar.max(0)).tolist()});return ai
 for k,ar in values.items():pr[0]['attributes'][k]=add(ar,'VEC'+str(ar.shape[1]))
 pr[0]['indices']=add(f.ravel(),'SCALAR');a.output.parent.mkdir(parents=True,exist_ok=True);write(a.output,d,binary)
 assert pr[1]==original['meshes'][mi]['primitives'][1]
 assert all(m==original['meshes'][i] for i,m in enumerate(d['meshes']) if i!=mi)
 assert d['animations']==original['animations'] and d['skins']==original['skins'] and d['images']==original['images']
 h=json.loads(a.head_config.read_text());p=h['profiles'][cfg['species']];p['model_sha256']=sha(a.output);nt=new[f];cross=[]
 for x in np.linspace(.29,float(nt[:,:,0].max())-.00005,32):
  hits=[]
  for i,j in [(0,1),(1,2),(2,0)]:
   v,w=nt[:,i],nt[:,j];sel=((v[:,0]<=x)&(w[:,0]>x))|((w[:,0]<=x)&(v[:,0]>x));v,w=v[sel],w[sel];t=(x-v[:,0])/(w[:,0]-v[:,0]);hits.extend(v+t[:,None]*(w-v))
  pts=np.array(hits);mn,mx=pts[:,1].min(),pts[:,1].max();cross.append([float(x),float((mn+mx)/2),float((mx-mn)/2),float(abs(pts[:,2]).max())])
 p['rim_local']['cross_sections']=cross;a.config_output.write_text(json.dumps(h,indent=2)+'\n')
 r={'schema_version':1,'ok':True,'status':'done','next_action':'human_review','input_sha256':sha(a.input),'model_sha256':sha(a.output),'source_sha256':sha(a.source),'parameters_sha256':sha(a.parameters),'original_skin_vertices':len(old_v),'skin_vertices':len(new),'original_skin_triangles':len(old_faces),'skin_triangles':len(f),'new_midpoint_vertices':split_count,'max_displacement_source_px':float(abs(dy).max()*2014),'target_max_difference_px':float(abs(target(px)-py).max()),'fitted_curve_knots_source_x':target.get_knots().tolist(),'mouth_rim_positions_exact':True,'oral_primitive_exact':True,'other_meshes_fins_skins_animations_source_exact':True,'closed_welded_body':True,'scope':cfg['limits']};a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
