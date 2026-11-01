"""Trace the five already painted slits; RGB stays in the accepted side source."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir();im=np.array(Image.open(a.source).convert('RGBA'));H,W=im.shape[:2];marks=np.zeros((H,W),bool);curves=[]
for center in [1624,1600,1576,1552,1528]:
    curve=[]
    for y in range(314,395,4):
        lo,hi=center-9,center+10;values=im[y,lo:hi,:3].mean(1);dark=np.where(values<75)[0]
        if len(dark):curve.append([float(lo+dark.mean()),y])
    assert len(curve)>=10;curves.append(curve);canvas=Image.new('L',(W,H));d=ImageDraw.Draw(canvas);d.line([tuple(p)for p in curve],fill=255,width=2);marks|=np.array(canvas)>0
distance=distance_transform_edt(~marks);u=np.clip((distance-5)/4,0,1);alpha=(1-u*u*(3-2*u));result=im.copy();result[:,:,3]=np.rint(alpha*255).astype(np.uint8);result[alpha==0,:3]=0;target=a.output/'native-five-gills.png';Image.fromarray(result).save(target);report=dict(ok=True,kind='five_native_side_gill_pixel_domains',source_path=str(a.source.resolve()),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),path=str(target.resolve()),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),curves_px=curves,slits_per_side=5,core_radius_px=5,outer_fade_px=4,core_rgb_unchanged=bool(np.array_equal(result[distance<=5,:3],im[distance<=5,:3])),source_body_opaque=bool((im[alpha>0,3]==255).all()),scope='Already painted five slits, opaque RGB source exact in core. Alpha is a semantic transfer mask only; body stays opaque. No extra drawn slit or 3D slit-depth claim.');assert report['core_rgb_unchanged']and report['source_body_opaque'];(a.output/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(ok=True,slits=5)))
