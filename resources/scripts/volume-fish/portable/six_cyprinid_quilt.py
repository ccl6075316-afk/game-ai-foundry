"""Quilt a clean, illumination-normalized native skin donor without random RGB."""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from build_surface_charts import seam
ROOT=Path(__file__).resolve().parents[4];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=json.loads(a.config.read_text());n=c['native_material'];source=ROOT/n['source'];assert sha(source)==n['source_sha256'];raw=np.array(Image.open(source).convert('RGBA'));x0,y0,x1,y1=n['roi_px'];native=raw[y0:y1,x0:x1];assert np.all(native[:,:,3]==255);rgb=native[:,:,:3].astype(float)
sigma=float(c.get('illumination_sigma',2));assert .1<=sigma<=32
detail=rgb-gaussian_filter(rgb,(sigma,sigma,0));normalized=np.clip(np.rint(np.array(c['plain_RGB'])+detail*.9),0,255).astype(np.uint8);W,H=768,512;B,O=24,8;tile=np.zeros((H,W,3),np.uint8);mapping=np.zeros((H,W,2),np.int32);known=np.zeros((H,W),bool);rng=np.random.default_rng(541);records=[]
for y in range(0,H,B-O):
 for x in range(0,W,B-O):
  h,w=min(B,H-y),min(B,W-x);current=tile[y:y+h,x:x+w];filled=known[y:y+h,x:x+w];candidates=[]
  for _ in range(96):
   sy=int(rng.integers(0,normalized.shape[0]-h+1));sx=int(rng.integers(0,normalized.shape[1]-w+1));candidate=normalized[sy:sy+h,sx:sx+w];err=((candidate.astype(float)-current)**2).mean(2);cost=err[filled].mean()if filled.any()else 0;candidates.append((cost,sx,sy,err))
  candidates.sort(key=lambda v:v[0]);_,sx,sy,err=candidates[int(rng.integers(min(4,len(candidates))))];keep=np.zeros((h,w),bool)
  if x>0:
   path=seam(err[:,:min(O,w)]);keep|=np.arange(w)[None,:]<path[:,None]
  if y>0:
   path=seam(err[:min(O,h),:].T);keep|=np.arange(h)[:,None]<path[None,:]
  replace=~(keep&filled);current[replace]=normalized[sy:sy+h,sx:sx+w][replace];yy,xx=np.mgrid[sy:sy+h,sx:sx+w];m=mapping[y:y+h,x:x+w];m[replace]=np.c_[xx[replace]+x0,yy[replace]+y0];known[y:y+h,x:x+w]=True;records.append([x,y,sx+x0,sy+y0])
assert known.all();assert np.array_equal(tile,normalized[mapping[:,:,1]-y0,mapping[:,:,0]-x0]);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True);Image.fromarray(tile).save(out/'skin.png');np.savez_compressed(out/'native-donors.npz',xy=mapping);report={'ok':True,'kind':'clean_native_skin_material_quilting','source_sha256':sha(source),'source_roi_px':n['roi_px'],'tile':str(out/'skin.png'),'tile_sha256':sha(out/'skin.png'),'size':[W,H],'native_pixel_density_preserved':True,'no_random_RGB_or_procedural_noise':True,'every_texel_has_native_source_address':True,'normalization':f'Native ROI RGB minus Gaussian sigma{sigma} illumination plus declared target palette; residual gain0.9. Color-corrected material, not raw RGB-exact.','illumination_sigma':sigma,'patch_px':B,'overlap_px':O,'method':'Whole native patches with minimum-error overlap cuts; deterministic patch selection, no enlarged donor or mirrored-repeat grid.','patches':records};(out/'material.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'patches':len(records)}))
