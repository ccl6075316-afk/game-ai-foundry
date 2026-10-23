"""Freeze source-painted lip widths and native texels for the isolated 129 trial."""
import argparse,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from freeze_surface_ownership import read_glb,accessor

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);args=parser.parse_args();plan=json.loads(args.plan.read_text());root=args.plan.parent
assert sha(plan['source_model'])==plan['source_model_sha256'];assert sha(plan['source_image'])==plan['source_image_sha256']
doc,binary=read_glb(Path(plan['source_model']));node=next(n for n in doc['nodes'] if n.get('name')=='Closed_body');parts=doc['meshes'][node['mesh']]['primitives'];sets=[]
for part in parts:
 v=accessor(doc,binary,part['attributes']['POSITION']);t=accessor(doc,binary,part['indices']).reshape(-1,3)
 edges=Counter(tuple(sorted((tuple(np.round(v[a],7)),tuple(np.round(v[b],7))))) for tri in t for a,b in zip(tri,np.roll(tri,-1)))
 sets.append({e for e,n in edges.items() if n==1})
common=sets[0]&sets[1];assert common==sets[0]==sets[1]
neighbors=defaultdict(list)
for a,b in common:neighbors[a].append(b);neighbors[b].append(a)
assert all(len(v)==2 for v in neighbors.values())
corners=sorted(neighbors,key=lambda p:p[0])[:2];start=min(corners,key=lambda p:p[2]);end=max(corners,key=lambda p:p[2]);paths=[]
for neighbor in neighbors[start]:
 path=[start];prev=start;current=neighbor
 while current!=end:
  path.append(current);nextp=next(p for p in neighbors[current] if p!=prev);prev,current=current,nextp
 path.append(end);paths.append(np.array(path,dtype=float))
paths.sort(key=lambda p:p[:,1].mean(),reverse=True)
np.savez_compressed(root/'source-rims.npz',upper=paths[0],lower=paths[1])
source=Image.open(plan['source_image']).convert('RGBA');atlas=Image.new('RGBA',(plan['atlas']['width'],plan['atlas']['height']));a=np.asarray(source);central=[]
for name,band in plan['bands'].items():
 bounds=np.asarray(band['source_bounds']);minimum=plan['atlas']['minimum_x'];offset=band['atlas_offset_y'];rows=band['atlas_rows']
 for col in range(plan['atlas']['width']):
  x=min(minimum+col,band['central_source_column']);outer,inner=np.interp(x,bounds[:,0],bounds[:,1]),np.interp(x,bounds[:,0],bounds[:,2]);low,high=sorted([outer,inner]);lo=int(np.ceil(low+plan['atlas']['ink_exclusion_margin_px']));hi=int(np.floor(high-plan['atlas']['ink_exclusion_margin_px']))
  if hi<lo:lo=hi=int(round((low+high)/2))
  for row in range(rows):
   y=int(np.clip(int(np.floor(low))+row,lo,hi));pixel=tuple(a[y,x]);assert pixel[3]==255,(name,x,y,pixel)
   atlas.putpixel((col,offset+row),pixel)
   if x==band['central_source_column']:central.append(pixel)
atlas.save(root/'lip-band-native.png')
central=np.array(central);assert np.all(central[:,3]==255);assert np.all(central[:,:3].max(1)>65),'Confirmed central donors contain near-black source ink'
roi=(1810,515,1986,645);display=Image.new('RGBA',source.size,(30,43,50,255));display.alpha_composite(source);draw=ImageDraw.Draw(display)
for name,color in [('upper',(0,235,255,255)),('lower',(255,175,40,255))]:
 bounds=np.array(plan['bands'][name]['source_bounds']);draw.line([tuple(p) for p in bounds[:,[0,1]]],fill=color,width=1);draw.line([tuple(p) for p in bounds[:,[0,2]]],fill=color,width=1)
display.crop(roi).resize(((roi[2]-roi[0])*5,(roi[3]-roi[1])*5),Image.Resampling.NEAREST).save(root/'source-lip-boundaries.png')
report={'schema_version':1,'ok':True,'command':'fish.prepare-lip-band129','stage':'validate','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(args.plan),'helper_sha256':sha(__file__),'source_sha256':sha(plan['source_image'])},'outputs':[{'path':str((root/n).resolve()),'sha256':sha(root/n)} for n in ['source-rims.npz','lip-band-native.png','source-lip-boundaries.png']],'summary':{'actual_shared_aperture_edges':len(common),'central_native_donor_samples':len(central),'central_all_opaque_and_not_near_black':True,'source_pixels_modified':0,'scope':'Manually traced source material edges; existing128 surface is unapproved gray study. No biological lip-width measurement or final UV/rig transfer.'},'failures':[]}
(root/'source.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
