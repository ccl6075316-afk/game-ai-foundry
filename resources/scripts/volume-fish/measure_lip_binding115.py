"""Measure the actual skin/oral rim and inverse native UV attachment of confirmed lip lines."""
import argparse,json,hashlib,sys
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def measure(model,source,points):
 d,b=read_glb(model);node=next(n for n in d['nodes'] if n.get('name')=='Closed_body');pr=d['meshes'][node['mesh']]['primitives']
 attrs=[{k:accessor(d,b,v).copy() for k,v in q['attributes'].items()} for q in pr];skin,oral=attrs
 w,h=Image.open(source).size;points=np.asarray(points,float);target=PchipInterpolator(points[:,0],points[:,1],extrapolate=False)
 keys=lambda v:tuple(np.round(v,7))
 boundaries=[]
 for part,at in zip(pr,attrs):
  counts=Counter();idx=accessor(d,b,part['indices']).reshape(-1,3)
  for face in idx:
   for i,j in zip(face,np.roll(face,-1)):
    aa,bb=keys(at['POSITION'][i]),keys(at['POSITION'][j])
    if aa!=bb:counts[tuple(sorted([aa,bb]))]+=1
  boundaries.append({edge for edge,count in counts.items() if count==1})
 common=boundaries[0]&boundaries[1];assert common and len(common)==len(boundaries[0])==len(boundaries[1])
 graph=defaultdict(list)
 for aa,bb in common:graph[aa].append(bb);graph[bb].append(aa)
 assert all(len(v)==2 for v in graph.values()),'Rim is not a simple closed loop'
 corner_x=min(v[0] for v in graph);corners=sorted([v for v in graph if abs(v[0]-corner_x)<2e-7],key=lambda v:v[2]);assert len(corners)==2
 paths=[]
 for first in graph[corners[0]]:
  path=[corners[0],first]
  while path[-1]!=corners[1]:
   following=next(v for v in graph[path[-1]] if v!=path[-2]);assert following not in path
   path.append(following)
  paths.append(path)
 lower_path=min(paths,key=lambda row:np.mean([p[1] for p in row]));lower_vertices=set(lower_path)
 by_pos=defaultdict(list)
 for i,v in enumerate(skin['POSITION']):by_pos[keys(v)].append(i)
 rim=[]
 for i,(v,n) in enumerate(zip(oral['POSITION'],oral['NORMAL'])):
  if keys(v) not in lower_vertices or keys(v) not in by_pos:continue
  x=(float(v[0])+.5)*w;y=h*.5-float(v[1])*w
  # Exclude internal/front cross-width joins; lateral oral boundary is the
  # actual rim, while the anterior cap also shares the row's interior points.
  same=np.asarray([p for p in lower_path if abs(p[0]-v[0])<2e-7])
  if abs(v[2])<abs(same[:,2]).max()-1e-6:continue
  uv=[(skin['TEXCOORD_0'][j]*[w,h]).tolist() for j in by_pos[keys(v)]]
  rim.append({'position_native':v.tolist(),'screen_native_px':[x,y],'actual_skin_uv_px':uv,'target_y_px':float(target(x)) if points[0,0]<=x<=points[-1,0] else None})
 tri=accessor(d,b,pr[0]['indices']).reshape(-1,3);uv=skin['TEXCOORD_0'].astype(float)*[w,h];xyz=skin['POSITION'].astype(float)
 t=uv[tri];a=t[:,0];e=t[:,1]-a;f=t[:,2]-a;det=e[:,0]*f[:,1]-e[:,1]*f[:,0];valid=abs(det)>1e-8
 # Raw UV placement on positive-Z flank, distinguishing actual interior hit
 # from extrapolation into the old slit. Do not call an empty inverse a hit.
 inverse=[]
 for q in points:
  g=q-a;s=np.divide(g[:,0]*f[:,1]-g[:,1]*f[:,0],det,out=np.zeros(len(det)),where=valid);tt=np.divide(e[:,0]*g[:,1]-e[:,1]*g[:,0],det,out=np.zeros(len(det)),where=valid)
  weights=np.c_[1-s-tt,s,tt];p=(xyz[tri]*weights[:,:,None]).sum(1)
  domain=np.maximum(-weights,0).sum(1);domain[~valid]=np.inf;domain[p[:,2]<0]=np.inf
  # Reject front donor charts when resolving the side's actual artwork.
  affine=np.max(np.linalg.norm((xyz[tri][:,:,:2]*[w,-w]+[w*.5,h*.5])-t,axis=2),axis=1)<.02
  domain[~affine]=np.inf;i=int(domain.argmin());assert np.isfinite(domain[i])
  inverse.append({'source_px':q.tolist(),'surface':0,'triangle':int(i),'barycentric':weights[i].tolist(),'position_native':p[i].tolist(),'is_inside_actual_uv_triangle':bool(domain[i]<1e-5),'negative_barycentric_sum':float(domain[i]),'projected_native_px':[float((p[i,0]+.5)*w),float(h*.5-p[i,1]*w)]})
 residual=[abs(r['screen_native_px'][1]-r['target_y_px']) for r in rim if r['target_y_px'] is not None]
 corner=min(r['screen_native_px'][0] for r in rim);coverage=max(0.,corner-points[0,0])
 tip=[r for r in rim if r['screen_native_px'][0]>points[-1,0]-10]
 cap=skin['POSITION'][:,0]>skin['POSITION'][:,0].max()-.0003
 transport=np.linalg.norm((skin['TEXCOORD_0']-np.c_[skin['POSITION'][:,0]+.5,.5-skin['POSITION'][:,1]/(h/w)])*[w,h],axis=1)
 ordered=[[float(x) for x in v] for v in lower_path]
 return {'model_sha256':sha(model),'source_sha256':sha(source),'source_size':[w,h],'physical_lower_rim':rim,'ordered_lower_boundary_native':ordered,'common_boundary_edges':len(common),'inverse_uv_constraints':inverse,'missing_posterior_lip_px':float(coverage),'maximum_physical_source_residual_px':max(residual),'maximum_rim_uv_transport_px':max(np.linalg.norm(np.asarray(u)-r['screen_native_px']) for r in tip for u in r['actual_skin_uv_px']),'maximum_front_uv_transport_px':float(transport[cap].max()),'ok':bool(coverage<=2. and max(residual)<=2.5),'limits':'Native orthographic projection, actual skin/lining welded boundary and UV barycentric inverse. Slit-region extrapolation explicitly flagged; production shader sampling and posed GPU views require separate verification.'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();rows=[]
 for item in json.loads(a.plan.read_text())['items']:
  r=measure(a.game/'assets/models/fish'/(item['species']+'.glb'),Path(item['original_image']),item['lower_lip_source_px']);r['species']=item['species'];rows.append(r)
 ok=all(r['ok'] for r in rows);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({'schema_version':1,'ok':ok,'command':'fish.lip-binding115','status':'done' if ok else 'failed','next_action':'human_review' if ok else 'fix_input','items':rows,'script_sha256':sha(__file__)},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':ok,'items':[{k:r[k] for k in ['species','missing_posterior_lip_px','maximum_physical_source_residual_px','maximum_front_uv_transport_px']} for r in rows]}));return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
