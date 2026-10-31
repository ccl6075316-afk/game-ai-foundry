"""Make original-pixel fin masks from independent per-species source annotations."""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',type=Path,required=True);p.add_argument('--annotations',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 audit=json.loads(a.audit.read_text(encoding='utf8'));cfg=json.loads(a.annotations.read_text(encoding='utf8'));sp=audit['species'];out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True)
 assert sha(audit['model'])==audit['model_sha256']and sha(audit['source_image'])==audit['source_image_sha256'];orig=Image.open(audit['source_image']).convert('RGBA');W,H=orig.size;pad=cfg['padding_px'];records=[]
 canvas=Image.new('RGB',(1400,830),'#25343c');dr=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20);dr.text((12,6),sp+' 旧切片（左）/ 原像素精修切片（右）',font=font,fill='white')
 for ordinal,name in enumerate(cfg['repair_types']):
  old=next(r for r in audit['fins']if r['fin']==name);ann=cfg['species'][sp][name];l,t,r,b=old['source_crop'];crop=[max(0,l-pad),max(0,t-pad),min(W,r+pad),min(H,b+pad)];offset=np.array([l-crop[0],t-crop[1]],float);rgba=np.array(orig.crop(tuple(crop)));h,w=rgba.shape[:2]
  oldpoly=np.array(old['source_polygon_px'])-[crop[0],crop[1]];roi=np.zeros((h,w),np.uint8);cv2.fillPoly(roi,[np.rint(oldpoly).astype('int32')],1);roi=cv2.dilate(roi,np.ones((41,41),np.uint8))
  if 'polygon'in ann:
   m=np.zeros((h,w),np.uint8);cv2.fillPoly(m,[np.rint(np.array(ann['polygon'])+offset).astype('int32')],1);m=cv2.dilate(m,np.ones((3,3),np.uint8))
  else:
   line=np.array(ann.get('clip_root',np.array(old['source_baseline_px'])-[l,t]))+offset
   order=np.argsort(line[:,0]);line=line[order];xx=np.arange(w)+.5;yb=np.interp(xx,line[:,0],line[:,1],left=line[0,1],right=line[-1,1]);m=(np.arange(h)[:,None]+.5>=yb[None,:]).astype('uint8')
  # Padding is available for a clipped free tip, but must not admit adjacent
  # fish-body pixels beyond the original source patch's longitudinal extent.
  m[:,:int(offset[0])]=0;m[:,int(offset[0])+r-l:]=0
  m&=roi;m&=(rgba[:,:,3]>32).astype('uint8');n,labels,stats,_=cv2.connectedComponentsWithStats(m,8);assert n>1
  m=(labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))).astype('uint8')
  assert m.sum()>50;new=rgba.copy();new[:,:,3]*=m
  path=out/(name+'.png');Image.fromarray(new).save(path)
  root=np.array(ann.get('root',np.array(old['source_baseline_px'])-[l,t]))+offset
  oldimage=Image.open(a.audit.parent/(name+'-current-cutout.png')).convert('RGBA');oldpad=Image.new('RGBA',(w,h));oldpad.paste(oldimage,tuple(offset.astype(int)))
  sc=min(620/w,215/h);y=45+ordinal*260;dr.text((12,y),name,font=font,fill='white')
  for j,im in enumerate([oldpad,Image.fromarray(new)]):
   bg=Image.new('RGBA',(w,h),'#566773');bg.alpha_composite(im);bg=bg.convert('RGB').resize((int(w*sc),int(h*sc)),Image.Resampling.NEAREST);canvas.paste(bg,(12+j*700,y+29))
  records.append({'name':name,'image':str(path),'image_sha256':sha(path),'crop':crop,'size':[w,h],'source_image':audit['source_image'],'source_image_sha256':audit['source_image_sha256'],'old_mask_pixels':old['current_mask_pixels'],'new_mask_pixels':int(m.sum()),'root_px':root.tolist(),'max_layer_vertices':ann['max_layer_vertices'],'observation':ann['observation'],'source_RGB_exact':bool(np.array_equal(new[:,:,:3],rgba[:,:,:3])),'root_annotation_uncertainty_px':3})
 canvas.save(out/'mask-comparison.png')
 (out/'masks.validation.json').write_text(json.dumps({'ok':True,'kind':'native_fin_detail_masks','species':sp,'audit':str(a.audit.resolve()),'audit_sha256':sha(a.audit),'annotations':str(a.annotations.resolve()),'annotations_sha256':sha(a.annotations),'model':audit['model'],'model_sha256':audit['model_sha256'],'input_blend':audit['source_blend'],'source_image':audit['source_image'],'source_image_sha256':audit['source_image_sha256'],'root_blend_px':cfg['root_blend_px'],'fins':records,'formal_acceptance':False,'visual_review':'pending'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'ok':True,'species':sp,'pixels':[(r['name'],r['old_mask_pixels'],r['new_mask_pixels'])for r in records]}))
if __name__=='__main__':main()
