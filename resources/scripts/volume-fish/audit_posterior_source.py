"""Fixed full-source coordinates: last dorsal/anal fins, peduncle and caudal."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np,cv2
from PIL import Image,ImageDraw
from freeze_surface_ownership import read_glb,accessor
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--plan',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);root=Path(__file__).resolve().parents[3];rows=[];models={r['species']:Path(r['model']) for r in json.loads(a.plan.read_text(encoding='utf8'))['items']} if a.plan else {}
 for sp in ['great_hammerhead','smooth_hammerhead']:
  profile=json.loads((root/'resources/volume-fish'/f'{sp.replace("_","-")}-121.profile.json').read_text(encoding='utf8'));src=root/f'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/accepted/{sp}/inputs/char_{sp}_side121_nobg.png';im=Image.open(src).convert('RGBA');w,h=im.size
  model=models.get(sp,root/f'projects/fishing-2d/game/assets/models/fish/{sp}.glb');d,b=read_glb(model);mask=np.zeros((h,w),np.uint8);parts={}
  for node in d['nodes']:
   if 'mesh' not in node or node.get('name') not in ['Closed_body','SecondDorsal','Anal','Caudal']:continue
   mm=np.zeros_like(mask)
   for prim in d['meshes'][node['mesh']]['primitives']:
    vs=accessor(d,b,prim['attributes']['POSITION']);xy=np.c_[(vs[:,0]+.5)*w,(.5-vs[:,1]*profile['source_aspect_ratio'])*h];tri=accessor(d,b,prim['indices']).reshape(-1,3)
    for t in tri:cv2.fillConvexPoly(mm,np.round(xy[t]).astype(np.int32),255)
   mask|=mm;parts[node['name']]=mm
  source=(np.array(im)[:,:,3]>128).astype(np.uint8)*255;right=round(.405*w);crop=(0,0,right,h);base=Image.new('RGBA',im.size,(28,46,57,255));base.alpha_composite(im);base=base.convert('RGB');overlay=np.asarray(base).copy()
  for label,mm,color in [('source',source,(255,183,70)),('model',mask,(50,234,235))]:
   contours,_=cv2.findContours(mm,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(overlay,contours,-1,color,2)
  panel=Image.new('RGB',(right*2,h+48),(28,46,57));panel.paste(base.crop(crop),(0,48));panel.paste(Image.fromarray(overlay).crop(crop),(right,48));draw=ImageDraw.Draw(panel);draw.text((12,12),'SOURCE: last dorsal / anal -> peduncle -> full caudal',fill='white');draw.text((right+12,12),'ORANGE source contour / CYAN current mesh; SAME coordinates',fill='white');panel.save(a.output/f'{sp}-source-overlay.png')
  samples=[]
  for u in [.235,.245,.25,.26,.28,.30,.32,.35,.38]:
   x=round(u*w);ys=np.flatnonzero(source[:,x]);my=np.flatnonzero(parts['Closed_body'][:,x]);samples.append({'u':u,'source_top_bottom':ys[[0,-1]].tolist() if len(ys) else None,'body_top_bottom':my[[0,-1]].tolist() if len(my) else None})
  span=(.20,.28) if sp=='great_hammerhead' else (.21,.30);errors=[];worst=[]
  for x in range(round(span[0]*w),round(span[1]*w)+1):
   sy=np.flatnonzero(source[:,x]);my=np.flatnonzero(mask[:,x]);assert len(sy)>0 and len(my)>0
   errors.extend(np.abs(sy[[0,-1]]-my[[0,-1]]).tolist())
   if np.max(np.abs(sy[[0,-1]]-my[[0,-1]]))>3:worst.append([x,sy[[0,-1]].tolist(),my[[0,-1]].tolist()])
  rows.append({'species':sp,'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'fixed_crop':list(crop),'junction_u_range':list(span),'junction_envelope_error_px_max':max(errors),'junction_envelope_error_px_mean':float(np.mean(errors)),'over_three_px':worst,'samples':samples})
 (a.output/'audit.validation.json').write_text(json.dumps({'ok':True,'diagnostic_only':True,'records':rows,'method':'No local registration or independent tail resizing. Actual rest XY mesh triangles on original accepted side-source canvas. Includes last dorsal and anal, peduncle and full caudal.'},indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
