"""Freeze candidate lip widths against each fish's own source aperture.

Painted widths are explicit per-species inputs, not anatomical measurements.
Existing112 traced upper-lip stations are reused where available. All plans
still require source/strip/actual-material visual comparison before installation.
"""
import argparse,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
WIDTHS={'yellow_croaker':(18,18),'zander':(14,18),'atlantic_salmon':(12,16),
 'red_emperor':(24,22),'bluegill':(14,16),'brown_trout':(12,20),
 'grass_carp':(12,14),'nile_tilapia':(14,18),'sea_bass':(18,20),
 'rainbow_trout':(14,18),'crucian':(12,14)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--parameters',type=Path,required=True);ap.add_argument('--species',nargs='*');a=ap.parse_args()
 rows=json.loads(a.parameters.read_text())['items'];traced={r['species']:r for r in json.loads(Path('resources/volume-fish/source-lips-112.json').read_text())['items']}
 for row in rows:
  sp=row['species']
  if a.species and sp not in a.species:continue
  root=Path(row['output']).resolve();folder=root/'lips';inspection=json.loads((folder/'source-inspection.json').read_text());w,h=inspection['source_size']
  d,b=read_glb(Path(row['model']));node=next(x for x in d['nodes'] if x.get('name')=='Closed_body');pr=d['meshes'][node['mesh']]['primitives'];sets=[]
  for part in pr:
   v=accessor(d,b,part['attributes']['POSITION']);tri=accessor(d,b,part['indices']).reshape(-1,3)
   counts=Counter(tuple(sorted((tuple(np.round(v[i],7)),tuple(np.round(v[j],7))))) for t in tri for i,j in zip(t,np.roll(t,-1)))
   sets.append({e for e,n in counts.items() if n==1})
  common=sets[0]&sets[1];assert common==sets[0]==sets[1]
  graph=defaultdict(list)
  for x,y in common:graph[x].append(y);graph[y].append(x)
  assert all(len(v)==2 for v in graph.values())
  # A rear collar can have four equal-X vertices. Select opposite sides
  # deterministically; choosing any first two can select a tiny rear edge.
  start=min((p for p in graph if p[2]<-1e-7),key=lambda p:(p[0],-p[1]))
  end=min((p for p in graph if p[2]>1e-7),key=lambda p:(p[0],-p[1]));rims=[]
  for nxt in graph[start]:
   path=[start];prev=start
   while nxt!=end:
    path.append(nxt);after=next(p for p in graph[nxt] if p!=prev);prev,nxt=nxt,after
   path.append(end);rims.append(np.array(path))
  rims.sort(key=lambda p:p[:,1].mean(),reverse=True)
  front=int(min((p[:,0].max()+.5)*w for p in rims))-12
  back=int(max((p[:,0].min()+.5)*w for p in rims))+3
  assert front>back+20
  bands={};offset=0
  for i,name in enumerate(['upper','lower']):
   p=rims[i];sx=(p[:,0]+.5)*w;sy=h/2-p[:,1]*w;order=np.argsort(sx);sx=sx[order];sy=sy[order]
   stations=[]
   for col in np.linspace(back,front,7):
    inner=float(np.interp(col,sx,sy));width=WIDTHS[sp][i]*(.25+.75*np.clip((col-back)/(front-back),0,1))
    outer=inner-width if i==0 else inner+width
    if i==0 and sp in traced:
     bb=np.array(traced[sp]['lip_pixels']);outer=float(np.interp(col,bb[:,0],bb[:,1]));inner=float(np.interp(col,bb[:,0],bb[:,2]))
    stations.append([round(col),round(outer),round(inner)])
   height=max(abs(p[1]-p[2]) for p in stations)+12
   bands[name]={'source_bounds':stations,'central_source_column':front,'atlas_offset_y':offset,'atlas_rows':height};offset+=height
  source=folder/'native-source.png';gray=root/'whole-head-gray.mesh.json';surface=root/'surface.plan.json'
  plan={'species':sp,'source_model':row['model'],'source_model_sha256':row['model_sha256'],
   'opaque_skin':inspection['opaque'],'opaque_skin_sha256':sha(inspection['opaque']),
   'source_image':str(source),'source_image_sha256':sha(source),'source_size':[w,h],
   'base_gray_mesh':str(gray),'base_gray_sha256':sha(gray),'base_surface_plan':str(surface),'base_surface_plan_sha256':sha(surface),
   'inspection_roi':inspection['roi'],'atlas':{'minimum_x':back,'width':front-back+2,'height':offset,'ink_exclusion_margin_px':1},'bands':bands,
   'geometry':{'longitudinal_samples':257,'cross_samples':17,'relief_native':.00018,'curve_smoothing_iterations':8,'projection_step_native':.00025,'surface_offset_native':.000035},
   'interpretation':'Frozen source-aperture correspondence.112 painted upper stations reused where present; remaining explicitly chosen source lip widths are artistic candidates requiring actual-image review, not biological measurements.'}
  (folder/'band.plan.json').write_text(json.dumps(plan,indent=2));print('LIP_PLAN',sp,[(k,v['source_bounds'][-1]) for k,v in bands.items()],flush=True)
if __name__=='__main__':main()
