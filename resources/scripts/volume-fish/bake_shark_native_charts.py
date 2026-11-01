"""Bake explicit native-pixel UV donor charts for the shark source cage.

This is deterministic source-coordinate transport for the 3D authoring material,
not generated artwork or evidence of unseen anatomy. Original inputs stay exact.
"""
import json,hashlib,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 s=json.loads((ROOT/sys.argv[1]).read_text(encoding='utf-8-sig'));p=json.loads((ROOT/s['source_profile']).read_text());out=(ROOT/sys.argv[2]).resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir();records=[]
 for key in['side','front']:
  src=ROOT/s[key];a=np.array(Image.open(src).convert('RGBA'));h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w];u=(xx+.5)/w;v=(yy+.5)/h;du=u.copy();dv=v.copy();changed=np.zeros((h,w),bool)
  if key=='side':
   patches=p['body_uv_patches'];poly=patches[0]['polygon'];inside=np.zeros((h,w),bool)
   for (ax,ay),(bx,by)in zip(poly,poly[1:]+poly[:1]):
    if abs(by-ay)>1e-12:inside^=((ay>v)!=(by>v))&(u<(bx-ax)*(v-ay)/(by-ay)+ax)
   du[inside]=u[inside]-.145;dv[inside]=.64+(v[inside]-.63)*.65;changed|=inside
   # Eyes belong to the original continuous body skin; preserve their exact
   # source pixels. No additional globe or overlapping painted eye is added.
   mouth=(u>.868)&(u<.978)&(v>.572)&(v<.665);du[mouth]=.81+(u[mouth]-.868)*.15;dv[mouth]=.60+(v[mouth]-.553)*.35;changed|=mouth
  else:
   for q in p['head_projection']['uv_patches']:
    xy=np.array(q['polygon']);mask=(u>xy[:,0].min())&(u<xy[:,0].max())&(v>xy[:,1].min())&(v<xy[:,1].max());du[mask]+=q['offset'][0];changed|=mask
  iy=np.clip((dv*h).astype(int),0,h-1);ix=np.clip((du*w).astype(int),0,w-1);result=a[iy,ix,:3];valid=(a[:,:,3]>240)&(a[iy,ix,3]>240);ids=distance_transform_edt(~valid,return_distances=False,return_indices=True);result=result[ids[0],ids[1]];target=out/(key+'-body.png');Image.fromarray(result).save(target);protected=~changed&(a[:,:,3]>240);assert np.array_equal(result[protected],a[:,:,:3][protected]);records.append(dict(role=key,path=str(target),sha256=sha(target),source_sha256=sha(src),changed_pixels=int(changed.sum()),opaque_padding_pixels=int((~valid).sum()),outside_patches_painted_RGB_exact=True))
  if key=='side':
   # Opaque padding for finite source-contour walls. All valid original pixels
   # remain exact, including the species' natural black tips and white bands.
   valid=a[:,:,3]>240;ids=distance_transform_edt(~valid,return_distances=False,return_indices=True);filled=a[ids[0],ids[1],:3];assert np.array_equal(filled[valid],a[:,:,:3][valid]);target=out/'native-fin-eye.png';Image.fromarray(filled).save(target);records.append(dict(role='fin_eye',path=str(target),sha256=sha(target),original_opaque_pixels_exact=True))
 (out/'validation.json').write_text(json.dumps(dict(ok=True,kind='native_source_coordinate_material_bake',records=records,scope='Explicit shark-only donor mapping; no geometry or anatomical/visual acceptance.'),indent=2)+'\n');print(json.dumps(records))
if __name__=='__main__':main()
