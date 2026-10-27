"""Native source-coordinate skin quilting with explicit fin/outline exclusions.

Uses nearest whole-patch candidates and minimum-error overlap cuts, following
Efros/Freeman image quilting. No neural training, rescaling or RGB painting.
Every repaired texel records its original safe source coordinate.
"""
import argparse,json,hashlib
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from freeze_surface_ownership import read_glb,accessor
from build_surface_charts import raster,seam

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);a=p.parse_args();cfg=json.loads(a.plan.read_text());out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=True)
 for path,digest in cfg['frozen_inputs'].items():assert sha(path)==digest,path
 original=np.array(Image.open(cfg['source']).convert('RGBA'));base=np.array(Image.open(cfg['opaque']).convert('RGBA'));h,w=original.shape[:2]
 assert base.shape==original.shape and np.all(base[:,:,3]==255)
 base[original[:,:,3]>=250]=original[original[:,:,3]>=250];base[:,:,3]=255
 d,b=read_glb(Path(cfg['model']));fin=np.zeros((h,w),np.uint8)
 for node in d['nodes']:
  if 'mesh' not in node or node.get('name') not in cfg['fins']:continue
  for part in d['meshes'][node['mesh']]['primitives']:
   uv=accessor(d,b,part['attributes']['TEXCOORD_0']);tri=accessor(d,b,part['indices']).reshape(-1,3);fin=np.maximum(fin,raster(uv,tri,w,h))
 for polygon in cfg.get('painted_fin_polygons_px',[]):cv2.fillPoly(fin,[np.asarray(polygon,np.int32)],255)
 excluded=cv2.dilate(fin,np.ones((cfg['fin_margin_px']*2+1,)*2,np.uint8))>0
 if cfg.get('body'):
  part=json.loads(Path(cfg['body']).read_text())['parts'][0];body=raster(np.asarray(part['uv']),np.asarray(part['triangles']).reshape(-1,3),w,h)>0
 else:
  body=np.zeros((h,w),bool)
  for node in d['nodes']:
   if node.get('name')!=cfg.get('body_node','Closed_body') or 'mesh' not in node:continue
   for part in d['meshes'][node['mesh']]['primitives']:
    uv=accessor(d,b,part['attributes']['TEXCOORD_0']);tri=accessor(d,b,part['indices']).reshape(-1,3)
    body|=raster(uv,tri,w,h)>0
  assert body.any(),'No actual GLB body UV coverage'
 opaque=original[:,:,3]>=250;interior=cv2.erode(opaque.astype(np.uint8),np.ones((cfg['outline_margin_px']*2+1,)*2,np.uint8))>0
 yy,xx=np.indices((h,w));head=xx>=round(cfg['head_start_u']*w)
 target=body&~head&(excluded|~interior)
 valid=body&~excluded&interior&~head
 if cfg.get('repair_only_polygons_px'):
  allowed=np.zeros((h,w),np.uint8)
  for polygon in cfg['repair_only_polygons_px']:cv2.fillPoly(allowed,[np.asarray(polygon,np.int32)],1)
  target&=allowed>0
 if cfg.get('protected_body_marks_polygons_px'):
  protected=np.zeros((h,w),np.uint8)
  for polygon in cfg['protected_body_marks_polygons_px']:cv2.fillPoly(protected,[np.asarray(polygon,np.int32)],1)
  target&=protected==0
  valid&=protected==0
 assert target.any(),'No scoped body repair target'
 for rect in cfg.get('protected_rects_px',[]):
  x0,y0,x1,y1=rect;valid[y0:y1,x0:x1]=False
 block=cfg['patch_px'];half=block//2;overlap=block//3;step=block-overlap
 centers=cv2.erode(valid.astype(np.uint8),np.ones((block,block),np.uint8))>0
 cy,cx=np.where(centers);assert len(cx)>500,'No safe whole native patches'
 tree=cKDTree(np.c_[cx,cy*cfg['vertical_distance_weight']]);known=~target;filled=np.zeros((h,w),bool);mapping=np.stack([xx,yy],axis=-1).astype(np.int32);result=base.copy();patches=0
 # A low-frequency vertical guide transports the local body lighting through
 # the removed fin. It affects candidate selection only; output still copies
 # complete native source patches without colour blending or new RGB values.
 numerator=cv2.GaussianBlur(original[:,:,:3].astype('float32')*valid[:,:,None],(0,0),10)
 denominator=cv2.GaussianBlur(valid.astype('float32'),(0,0),10)
 smooth_source=numerator/np.maximum(denominator[:,:,None],1e-8);guide=np.zeros((h,w,3),np.float32)
 for x in range(w):
  rows=np.flatnonzero(valid[:,x])
  if len(rows)>2:
   for k in range(3):guide[:,x,k]=np.interp(np.arange(h),rows,smooth_source[rows,x,k])
  else:guide[:,x]=base[:,x,:3]
 # Keep each connected target's native coordinates. Large fin-shaped holes
 # borrow from neighbouring skin at matching height; no flat colour fill.
 count,labels,stats,_=cv2.connectedComponentsWithStats(target.astype(np.uint8),8)
 for label in range(1,count):
  x0,y0,bw,bh,area=stats[label];xlo=max(half,x0-half);xhi=min(w-half,x0+bw+half);ylo=max(half,y0-half);yhi=min(h-half,y0+bh+half)
  for y in range(ylo,yhi,step):
   for x in range(xlo,xhi,step):
    ys=slice(y-half,y+half+1);xs=slice(x-half,x+half+1);mask=target[ys,xs]
    if not mask.any():continue
    current=result[ys,xs,:3].astype(float);confidence=known[ys,xs]|filled[ys,xs];oldfilled=filled[ys,xs].copy();candidate_ids=np.atleast_1d(tree.query([x,y*cfg['vertical_distance_weight']],k=min(256,len(cx)))[1]);best=None;bestcost=np.inf
    for idx in candidate_ids:
     sx,sy=int(cx[idx]),int(cy[idx]);patch=original[sy-half:sy+half+1,sx-half:sx+half+1,:3].astype(float);error=((patch-current)**2).mean(2)
     cost=float(error[confidence].mean()) if confidence.any() else 0.
     cost+=.85*float(((patch-guide[ys,xs])**2).mean())
     cost+=cfg['spatial_penalty']*((sx-x)**2+cfg['vertical_distance_weight']**2*(sy-y)**2)
     if cost<bestcost:bestcost=cost;best=(sx,sy,error)
    sx,sy,error=best;dy,dx=np.mgrid[-half:half+1,-half:half+1];mx=sx+dx;my=sy+dy;assert valid[my,mx].all()
    keep=np.zeros(mask.shape,bool)
    if oldfilled.any():
     if x>xlo:
      path=seam(error[:,:overlap]);keep|=np.arange(block)[None,:]<path[:,None]
     if y>ylo:
      path=seam(error[:overlap,:].T);keep|=np.arange(block)[:,None]<path[None,:]
    replace=mask&~(keep&oldfilled);view=result[ys,xs];view[replace]=original[my[replace],mx[replace]];view[:,:,3]=255
    m=mapping[ys,xs];m[:,:,0][replace]=mx[replace];m[:,:,1][replace]=my[replace];filled[ys,xs][replace]=True;patches+=1
  print('QUILT140',cfg['species'],label,'pixels',int(area),'patches',patches,flush=True)
 missing=target&~filled
 # Thin one-pixel source-edge slivers can fall beyond the last block centre;
 # map them to safe native pixels with the same height-weighted metric.
 if missing.any():
  sy,sx=np.where(valid);pixels=cKDTree(np.c_[sx,sy*cfg['vertical_distance_weight']]);qy,qx=np.where(missing);_,ids=pixels.query(np.c_[qx,qy*cfg['vertical_distance_weight']]);mapping[qy,qx]=np.c_[sx[ids],sy[ids]];result[qy,qx]=original[sy[ids],sx[ids]];result[qy,qx,3]=255;filled[missing]=True
 assert np.array_equal(result[~target],base[~target]);assert np.all(result[:,:,3]==255)
 donors=mapping[target];assert valid[donors[:,1],donors[:,0]].all();assert np.array_equal(result[target,:3],original[donors[:,1],donors[:,0],:3])
 Image.fromarray(result).save(out/'skin.png');np.savez_compressed(out/'donors.npz',xy=mapping,target=target,valid=valid,fin_excluded=excluded,body_uv=body)
 Image.fromarray(target.astype('uint8')*255).save(out/'repair-mask.png');Image.fromarray(valid.astype('uint8')*255).save(out/'safe-donors.png');Image.fromarray(excluded.astype('uint8')*255).save(out/'fin-exclusion.png')
 report={'ok':True,'species':cfg['species'],'plan_sha256':sha(a.plan),'builder_sha256':sha(__file__),'source_sha256':sha(cfg['source']),'source_modified':False,'repaired_pixels':int(target.sum()),'patches':patches,'fallback_thin_pixels':int(missing.sum()),'donors_outside_safe_domain':0,'outside_target_rgb_preserved':True,'native_source_rgb_exact':True,'body_uv_source':'actual_glb' if not cfg.get('body') else 'exported_body_json','scoped_repair':bool(cfg.get('repair_only_polygons_px')),'protected_body_marks':bool(cfg.get('protected_body_marks_polygons_px')),'outputs':{n:sha(out/n) for n in ['skin.png','donors.npz','repair-mask.png','safe-donors.png','fin-exclusion.png']},'method':'Native whole-patch matching and minimum-error overlap cuts; no interpolation or neural generation. Hidden skin is artistic reconstruction.','references':['https://graphics.cs.cmu.edu/people/efros/research/quilting.html','https://github.com/z-o-e/Texture-Synthesis/blob/master/ImageQuilting.py'],'scope':'Source/donor ownership gate only. Actual hidden-fin, tail-peduncle, belly, water, movement and GPU review still required.'}
 (out/'skin.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['ok','species','repaired_pixels','patches']}),flush=True)
if __name__=='__main__':main()
