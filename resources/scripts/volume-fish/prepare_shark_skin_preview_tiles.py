"""Remove low-frequency baked light from declared interior skin preview ROIs.

Derived texture only: never call these modified RGB pixels original/native.
The real native lip domain continues to read the immutable ventral source.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

p=argparse.ArgumentParser();p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();c=json.loads(a.config.read_text());assert not a.output.exists();a.output.mkdir();records={}
for name,item in c['sources'].items():
    src=Path(item['path']);assert hashlib.sha256(src.read_bytes()).hexdigest()==item['sha256'];im=np.array(Image.open(src).convert('RGBA'));x0,y0,x1,y1=c['derived_preview_skin_roi_px'];raw=im[y0:y1,x0:x1];assert(raw[:,:,3]==255).all();rgb=raw[:,:,:3].astype(float);low=gaussian_filter(rgb,(10,10,0),mode='reflect');mean=rgb.mean((0,1));residual=rgb-low
    h,w=residual.shape[:2];yy,xx=np.mgrid[:h,:w];edge=np.minimum.reduce([xx,yy,w-1-xx,h-1-yy]);gain=np.clip(edge/6,0,1);gain=gain*gain*(3-2*gain);result=np.clip(np.rint(mean+residual*gain[:,:,None]),0,255).astype(np.uint8);target=a.output/(name+'.png');Image.fromarray(result).save(target);records[name]=dict(path=str(target.resolve()),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256=item['sha256'],roi=c['derived_preview_skin_roi_px'],mean_srgb=mean.tolist(),original_native_pixels=False)
r=dict(ok=True,kind='derived_delit_skin_preview_only',records=records,method='Subtract sigma10px low-frequency lighting, preserve high-frequency painted clusters, neutralize six-pixel tile seam. All RGB is derived. No eyes/gills/fin marks are created. Native mouth transport bypasses this chart.',formal_acceptance=False);(a.output/'validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
