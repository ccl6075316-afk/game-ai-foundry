"""Finite mesh foil sections in an explicit per-fin landmark frame.

Library frame/ROI is reviewed on the retained wire diagram; exact species is
unknown. Chord-normal finite ray intersections, not mesh AABB thickness.
"""
import json,hashlib,sys,argparse
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from measure_hammerhead_head_field import load_reference
from portable.glb_io import read_glb,arrays

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def frame(a,b,tip):
 a,b,tip=map(lambda q:np.array(q,float),(a,b,tip));u=b-a;u/=np.linalg.norm(u);o=(a+b)/2;v=tip-o;v-=u*np.dot(v,u);span=np.linalg.norm(v);v/=span;n=np.cross(u,v);return o,np.array([u,v,n]),span

def section(tri,y):
 b=np.roll(tri,-1,axis=1);k=(tri[:,:,1]-y)*(b[:,:,1]-y)<0
 hits=tri[k]+((y-tri[:,:,1][k])/(b[:,:,1][k]-tri[:,:,1][k]))[:,None]*(b[k]-tri[k])
 return (float(hits[:,0].min()),float(hits[:,0].max()))if len(hits)>1 else None

def ray(tri,x,y):
 a,b,c=tri[:,0],tri[:,1],tri[:,2];den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);valid=abs(den)>1e-14;aa=np.zeros(len(tri));bb=aa.copy();aa[valid]=((b[valid,1]-c[valid,1])*(x-c[valid,0])+(c[valid,0]-b[valid,0])*(y-c[valid,1]))/den[valid];bb[valid]=((c[valid,1]-a[valid,1])*(x-c[valid,0])+(a[valid,0]-c[valid,0])*(y-c[valid,1]))/den[valid];cc=1-aa-bb;k=valid&(aa>=-1e-8)&(bb>=-1e-8)&(cc>=-1e-8);z=np.unique(np.round((aa*a[:,2]+bb*b[:,2]+cc*c[:,2])[k],10));return z.tolist()

def sample(v,f,definition):
 o,B,S=frame(*[definition[x]for x in ['root_front','root_rear','tip']]);tri=((v-o)@B.T)[f];roi=definition.get('roi')
 if roi:
  world=v[f];mask=np.ones(len(f),bool)
  for axis,(lo,hi)in enumerate(roi):mask&=(world[:,:,axis].max(1)>=lo)&(world[:,:,axis].min(1)<=hi)
  tri=tri[mask]
 rows=[]
 for s in [.25,.5,.75,.9]:
  y=S*s;bounds=section(tri,y)
  if bounds is None:rows.append(dict(s=s,valid=False,reason='No finite section'));continue
  lo,hi=bounds;probes=[]
  for q in [.1,.2,.3,.4,.5,.6,.7,.8,.9]:
   z=ray(tri,lo+(hi-lo)*q,y);pairs=list(zip(z[::2],z[1::2])) if len(z)%2==0 else []
   pair=min(pairs,key=lambda ab:abs(sum(ab)/2))if pairs else None
   probes.append(dict(chord_fraction=q,hits=z,thickness_over_length=pair[1]-pair[0]if pair else None))
  t=[x['thickness_over_length']for x in probes if x['thickness_over_length']is not None];rows.append(dict(s=s,valid=len(t)>=5 and max(t)/(hi-lo)<.4,chord_over_length=hi-lo,maximum_thickness_over_length=max(t)if t else None,median_thickness_over_length=float(np.median(t))if t else None,peak_t_over_c=max(t)/(hi-lo)if t else None,probes=probes))
 return dict(frame=dict(origin=o.tolist(),basis=B.tolist(),span_over_length=float(S)),rows=rows)

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=json.loads(a.config.read_text());ref=Path(c['reference']);assert sha(ref)==c['reference_sha256'];rv,rf=load_reference(ref);d,b=read_glb(Path(c['candidate']));own={}
 for n in d['nodes']:
  if n.get('name')not in c['fins']:continue
  vs=[];fs=[];off=0
  for pr in d['meshes'][n['mesh']]['primitives']:
   v=arrays(d,b,pr['attributes']['POSITION']).astype(float);v[:,0]=c['nose_x_m']-v[:,0];v[:,2]*=-1;v/=c['length_m'];vs.append(v);fs.append(arrays(d,b,pr['indices']).reshape(-1,3)+off);off+=len(v)
  own[n['name']]=(np.concatenate(vs),np.concatenate(fs))
 result=[]
 for name,definition in c['fins'].items():
  lib=sample(rv,rf,definition['library']);cv,cf=own[name];current=sample(cv,cf,definition['own']);result.append(dict(name=name,library=lib,current=current))
 out=dict(kind='explicit_landmark_finite_foil_sections',reference_sha256=sha(ref),model_sha256=sha(c['candidate']),config_sha256=sha(a.config),checker_sha256=sha(__file__),length_normalization='Whole longitudinal finite extent; both models normalized independently. Each fin has independent actual root/tip frame. Ratios t/c and t/L reported separately.',unknowns=['Library exact biological species and tissue accuracy unknown.','Root landmarks are reviewed game-mesh engineering landmarks, not anatomical dissection.','Chord-normal thickness differs from surface-normal rays; both are reported by separate gates.'],fins=result,formal_acceptance=False);a.output.write_text(json.dumps(out,indent=2)+'\n')
 for r in result:print(r['name'],[(tag,[(x['s'],None if not x.get('maximum_thickness_over_length')else round(x['maximum_thickness_over_length']*c['length_m']*1000,2),None if not x.get('peak_t_over_c')else round(x['peak_t_over_c'],3),x['valid'])for x in r[tag]['rows']])for tag in ['library','current']])
if __name__=='__main__':main()
