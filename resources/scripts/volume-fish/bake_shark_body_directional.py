"""Native two-dimensional back/belly charts from explicit anatomical source ROIs.

Retain all own painted pixels inside each ROI, pad beyond its real boundary,
exclude old median/pelvic fin outlines. All actual fin textures remain exact.
"""
import json,sys,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
ROOT=Path(__file__).resolve().parents[3];s=json.loads((ROOT/sys.argv[1]).read_text(encoding='utf8'));charts=(ROOT/sys.argv[2]).resolve();out=(ROOT/sys.argv[3]).resolve();assert not out.exists()and out.is_relative_to(ROOT/'projects/fishing-2d/experiments');out.mkdir();p=json.loads((ROOT/s['source_profile']).read_text());a=np.array(Image.open(ROOT/s['side']).convert('RGBA'));clean=np.array(Image.open(charts/'side-body.png').convert('RGB'));H,W=a.shape[:2];yy,xx=np.mgrid[:H,:W];u=(xx+.5)/W;v=(yy+.5)/H;sec=np.array(p['body']['sections']);top=np.interp(u,sec[:,0],sec[:,1]);bottom=np.interp(u,sec[:,0],sec[:,2]);fraction=(v-top)/np.maximum(bottom-top,1e-10);excluded=np.zeros((H,W),np.uint8)
for f in p['fins']:
 xy=np.rint(np.array(f['polygon'])*[W,H]).astype(np.int32);cv2.rectangle(excluded,tuple(xy.min(0)),tuple(xy.max(0)),1,-1)
# Gills belong to the lateral head skin, never an unseen back/belly donor.
cv2.rectangle(excluded,(int(.72*W),int(.50*H)),(int(.82*W),int(.72*H)),1,-1)
excluded=cv2.dilate(excluded,np.ones((17,17),np.uint8))>0;rows=[];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name,lo,hi in[('back',.25,.45),('belly',.65,.82)]:
 valid=(fraction>=lo)&(fraction<=hi)&(a[:,:,3]>240)&~excluded&(u>.148)&(u<.90);assert valid.sum()>10000;ids=distance_transform_edt(~valid,return_distances=False,return_indices=True);result=clean[ids[0],ids[1]];assert np.array_equal(result[valid],clean[valid]);target=out/(name+'.png');Image.fromarray(result).save(target);rows.append({'role':name,'path':str(target),'sha256':sha(target),'painted_source_pixels_exact':int(valid.sum()),'source_fraction':[lo,hi],'longitudinal_domain':[.148,.90]})
(out/'validation.json').write_text(json.dumps({'ok':True,'kind':'anatomical_native_directional_body_charts','source_sha256':sha(ROOT/s['side']),'clean_side_sha256':sha(charts/'side-body.png'),'records':rows,'fin_outline_exclusion_padding_px':8,'scope':'Own source 2D back and countershaded belly ROIs, nearest opaque boundary padding, no one-row transport, RGB color threshold or fin texture edit. Material/source appearance remains visual review.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'pixels':[r['painted_source_pixels_exact']for r in rows]}))
