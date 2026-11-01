"""Restore declared moving-fin footprints with explicit same-fish 2D skin donors."""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from fish_asset_spec import ROOT,artifact_output,require

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(config,output):
 cfg=json.loads(config.read_text(encoding='utf8'));source=(ROOT/cfg['source']).resolve();require(sha(source)==cfg['source_sha256'],'Stale native source');mfile=ROOT/cfg['masks'];require(sha(mfile)==cfg['masks_sha256'],'Stale reviewed masks');masks=json.loads(mfile.read_text(encoding='utf8'));original=np.array(Image.open(source).convert('RGBA'));H,W=original.shape[:2];result=original.copy();out=artifact_output(output,[source,config,mfile]);require(not out.exists(),'Fresh restoration output required');out.mkdir(parents=True);records=[];addresses={};all_masks={}
 for f in masks['fins']:
  canvas=np.zeros((H,W),np.uint8);pic=np.array(Image.open(f['image']).convert('RGBA'));l,t,r,b=f['crop'];canvas[t:b,l:r]=pic[:,:,3];all_masks[f['name']]=canvas>127
 for c in cfg['repairs']:
  f=next(f for f in masks['fins']if f['name']==c['fin']);require(sha(f['image'])==f['image_sha256'],'Stale native fin image');footprint=all_masks[c['fin']].copy()
  if c.get('footprint_polygon_px'):
   footprint=np.zeros((H,W),np.uint8);cv2.fillPoly(footprint,[np.asarray(c['footprint_polygon_px'],np.int32)],1);footprint=(footprint>0)&(original[:,:,3]>127)
  mask=cv2.dilate(footprint.astype('uint8'),np.ones((c['edge_expansion_px']*2+1,)*2,np.uint8))>0
  root=np.zeros((H,W),np.uint8);line=np.rint(np.asarray(f['root_px'])+f['crop'][:2]).astype('int32');cv2.polylines(root,[line],False,255,c['protected_root_width_px']);mask&=root==0
  yy,xx=np.where(mask)
  if c.get('donor_mode')=='native_tile':
   x0,y0,x1,y1=c['donor_roi_px'];require(x1>x0 and y1>y0,'Empty native tile');sx=x0+(xx-xx.min())%(x1-x0);sy=y0+(yy-yy.min())%(y1-y0)
  elif 'offset_px'in c:sx=xx+c['offset_px'][0];sy=yy+c['offset_px'][1]
  else:
   x0,y0,x1,y1=c['donor_roi_px'];sx=np.rint(x0+(xx-xx.min())/max(1,np.ptp(xx))*(x1-x0)).astype(int);sy=np.rint(y0+(yy-yy.min())/max(1,np.ptp(yy))*(y1-y0)).astype(int)
  require(np.all((sx>=0)&(sx<W)&(sy>=0)&(sy<H)),'Native donor outside source');require(np.all(original[sy,sx,3]==255),'Native skin donor is not fully opaque')
  require(not any(m[sy,sx].any()for m in all_masks.values()),'A moving fin contaminates a declared skin donor')
  result[yy,xx]=original[sy,sx];label=c.get('name',c['fin']);addresses[label+'_target_xy']=np.c_[xx,yy];addresses[label+'_donor_xy']=np.c_[sx,sy]
  records.append(dict(c,changed_pixels=len(xx),actual_donor_min_px=[int(sx.min()),int(sy.min())],actual_donor_max_px=[int(sx.max()),int(sy.max())],root_source_line_px=line.tolist(),scope='Native RGB copy confined to the declared former fin footprint, including its free outline. Explicit finite body-owned root mark retained. Hidden colors are artistic reconstruction, not observed anatomy.'))
 if cfg.get('body_alpha_profile'):
  profile=json.loads((ROOT/cfg['body_alpha_profile']).read_text(encoding='utf8'));sections=np.asarray(profile['body']['sections']);yy,xx=np.mgrid[:H,:W];u=(xx+.5)/W;top=np.interp(u,sections[:,0],sections[:,1])*H;bottom=np.interp(u,sections[:,0],sections[:,2])*H
  outside=(u<sections[0,0])|(yy<top)|(yy>bottom);outside&=xx<cfg['body_alpha_preserve_head_from_x'];result[outside,3]=0
 image=out/'body-clean.png';Image.fromarray(result).save(image);np.savez_compressed(out/'donor-addresses.npz',**addresses)
 changed=np.any(result!=original,axis=2);protected_head_from_x=cfg.get('protected_head_from_x',1650);require(isinstance(protected_head_from_x,int)and 0<protected_head_from_x<W,'Explicit protected head boundary outside source');require(not changed[:,protected_head_from_x:].any(),'Head, lips, eyes or barbels changed');sheet=Image.new('RGBA',(W*2,H),'#536572');sheet.alpha_composite(Image.fromarray(original));sheet.alpha_composite(Image.fromarray(result),(W,0));sheet.convert('RGB').save(out/'before-after.png')
 report={'ok':True,'kind':'native_2d_moving_fin_footprint_repair','source':str(source),'source_sha256':sha(source),'config_sha256':sha(config),'masks_sha256':sha(mfile),'protected_head_from_x':protected_head_from_x,'textures':{'body_clean':{'path':str(image),'sha256':sha(image),'size':[W,H]}},'repairs':records,'head_lips_eyes_barbels_native_pixels_unchanged':True,'donor_addresses':{'path':str(out/'donor-addresses.npz'),'sha256':sha(out/'donor-addresses.npz')},'formal_acceptance':False,'visual_review':'pending'}
 (out/'texture-inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=prepare(a.config,a.output);print(json.dumps({'ok':r['ok'],'repairs':len(r['repairs'])}))
