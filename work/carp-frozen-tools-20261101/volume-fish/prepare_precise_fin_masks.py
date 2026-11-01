"""Independent native-pixel fin matte: roots separate, free alpha retained exactly.

No redraw, color synthesis, global white/dark filtering or resolution change.
"""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))

def build(domain_path,annotations,out):
    domain=read(domain_path);cfg=read(annotations);s=domain['species'];out=out.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir()
    source=domain['source_image'];assert sha(source['path'])==source['sha256'];image=Image.open(source['path']).convert('RGBA');rules=cfg['species'][s];rows=[];panels=[]
    for f in domain['fins']:
        name=f['fin'];crop=f['source_crop'];rgba=np.array(image.crop(crop));h,w=rgba.shape[:2];old=np.array(Image.open(domain_path.parent/(name+'-current-cutout.png')).convert('RGBA'));rule=rules.get(name)
        if not rule:continue
        polygon=np.array(f['source_polygon_px'])-crop[:2];roi=np.zeros((h,w),np.uint8);cv2.fillPoly(roi,[np.rint(polygon).astype(np.int32)],1);radius=cfg['roi_margin_px'];roi=cv2.dilate(roi,np.ones((radius*2+1,radius*2+1),np.uint8))
        if 'clip'in rule:
            root=np.array(rule['root']);assert np.all(np.diff(root[:,0])>0);boundary=np.interp(np.arange(w)+.5,root[:,0],root[:,1]);m=((np.arange(h)[:,None]+.5<=boundary)if rule['clip']=='above'else(np.arange(h)[:,None]+.5>=boundary)).astype(np.uint8);m&=roi
            # The independent root has finite longitudinal ownership. Constant
            # extrapolation beyond it can admit detached body-colored strips.
            m[:,np.arange(w)+.5<root[0,0]]=0;m[:,np.arange(w)+.5>root[-1,0]]=0
        else:
            m=np.zeros((h,w),np.uint8);cv2.fillPoly(m,[np.array(rule['polygon'],np.int32)],1)
            if rule.get('grabcut'):
                cv2.setRNGSeed(3105);inner=cv2.erode(m,np.ones((7,7),np.uint8));outer=m.copy();labels=np.full((h,w),cv2.GC_BGD,np.uint8);labels[m>0]=cv2.GC_PR_FGD;labels[inner>0]=cv2.GC_FGD;labels[rgba[:,:,3]<16]=cv2.GC_BGD
                cv2.grabCut(rgba[:,:,:3].copy(),labels,None,np.zeros((1,65)),np.zeros((1,65)),6,cv2.GC_INIT_WITH_MASK);mask=np.isin(labels,[cv2.GC_FGD,cv2.GC_PR_FGD]).astype(np.uint8)
                # Restore the original dark outline immediately adjacent to the
                # true foreground, bounded by the independent annotation.
                edge=cv2.dilate(mask,np.ones((5,5),np.uint8))&outer;dark=rgba[:,:,:3].max(2)<90;mask|=(edge.astype(bool)&dark).astype(np.uint8);m=mask
        if rule.get('columnwise_dark_outline'):
            edge=rule['columnwise_dark_outline'];upper=np.array(edge['upper']);lower=np.array(edge['lower']);m[:]=0
            for x in range(int(upper[0,0]),int(upper[-1,0])+1):
                limits=[]
                for points,is_upper in [(upper,True),(lower,False)]:
                    expected=float(np.interp(x,points[:,0],points[:,1]));lo=max(0,int(expected-edge['search_px']));hi=min(h,int(expected+edge['search_px'])+1);colors=rgba[lo:hi,x,:3].astype(int);dark=colors.max(1)<edge['maximum_rgb'if is_upper else'lower_maximum_rgb']
                    if not is_upper and edge.get('lower_warm_chroma')is not None:dark=(colors.max(1)<edge['maximum_rgb'])|((colors[:,0]-colors[:,2])>edge['lower_warm_chroma'])
                    if is_upper and edge.get('upper_max_chroma')is not None and edge.get('upper_chroma_x_range',[0,w])[0]<=x<=edge.get('upper_chroma_x_range',[0,w])[1]:dark&=(colors.max(1)-colors.min(1))<=edge['upper_max_chroma']
                    ys=np.where(dark)[0]+lo
                    assert len(ys),(name,x,'Independently traced dark stroke missing')
                    runs=np.split(ys,np.where(np.diff(ys)>1)[0]+1);run=min(runs,key=lambda r:abs(float(r.mean())-expected));limits.append(int(run.min()if is_upper else run.max()))
                assert limits[0]<=limits[1],(name,x,limits);m[limits[0]:limits[1]+1,x]=1
        # Preserve all source-painted ray-tip fragments inside the explicit
        # domain. Largest-component deletion would silently lose fine tips.
        result=rgba.copy();result[:,:,3]*=m;assert np.array_equal(result[:,:,:3],rgba[:,:,:3]);target=out/(name+'.png');Image.fromarray(result).save(target)
        rows.append({'fin':name,'image':str(target),'image_sha256':sha(target),'source_crop':crop,'source_image':source,'source_RGB_exact':True,'native_resolution_unchanged':True,'old_mask_pixels':int((old[:,:,3]>127).sum()),'new_mask_pixels':int((result[:,:,3]>127).sum()),'source_root_local_px':rule['root'],'annotation':rule})
        bg=Image.new('RGBA',(w,h),'#556773');bg.alpha_composite(Image.fromarray(result));panels.append((name,Image.open(domain_path.parent/(name+'-source-context.png')).convert('RGBA'),Image.open(domain_path.parent/(name+'-current-cutout.png')).convert('RGBA'),bg))
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
    for page in range((len(panels)+2)//3):
        chunk=panels[page*3:page*3+3];sheet=Image.new('RGB',(1800,340*len(chunk)),'#25343c');draw=ImageDraw.Draw(sheet)
        for row,(name,*ims)in enumerate(chunk):
            for col,(label,im)in enumerate(zip(['原图上下文','旧切片','独立边界新切片'],ims)):
                bg=Image.new('RGBA',im.size,'#556773');bg.alpha_composite(im);bg=bg.convert('RGB');bg.thumbnail((590,300),Image.Resampling.NEAREST);sheet.paste(bg,(col*600+(600-bg.width)//2,row*340+34));draw.text((col*600+8,row*340+8),name+' | '+label,font=font,fill='white')
        sheet.save(out/f'mask-comparison-{page}.jpg',quality=96)
    snapshot=out/'annotations.snapshot.json';snapshot.write_bytes(annotations.read_bytes())
    report={'ok':True,'kind':'independently_annotated_precise_native_fin_masks','species':s,'domain':str(domain_path.resolve()),'domain_sha256':sha(domain_path),'annotations':str(snapshot),'annotations_sha256':sha(snapshot),'source_image':source,'fins':rows,'retained_fins':cfg['preserve_types'],'formal_acceptance':False,'visual_review':'pending','scope':'Original RGB/resolution retained; independent source root boundary and free native alpha, no redraw or generic white removal. Actual mesh UV coverage, thickness/contact, source/full candidates and final gates pending.'};(out/'masks.validation.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode());return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['domain','annotations','output']:p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args();result=build(a.domain,a.annotations,a.output);print(json.dumps({'ok':True,'species':result['species'],'fins':[(r['fin'],r['old_mask_pixels'],r['new_mask_pixels'])for r in result['fins']]}))
