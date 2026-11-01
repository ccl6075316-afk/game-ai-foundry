"""Cut explicitly annotated original fin domains without redrawing or color filters."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fish_asset_spec import ROOT, artifact_output, require


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare(config, output):
    cfg=json.loads(config.read_text(encoding='utf8'))
    source=(ROOT/cfg['source']).resolve()
    require(source.is_file() and sha(source)==cfg['source_sha256'],'Stale original source')
    image=Image.open(source).convert('RGBA')
    require(list(image.size)==cfg['source_size'],'Native resolution changed')
    out=artifact_output(output,[source,config]);require(not out.exists(),'Choose fresh mask output')
    out.mkdir(parents=True);rows=[]
    sheet=Image.new('RGB',(1500,360*len(cfg['fins'])),'#26363e')
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    for n,fin in enumerate(cfg['fins']):
        polygon=np.asarray(fin['polygon_px'],float)
        require(polygon.ndim==2 and polygon.shape[1]==2 and len(polygon)>=3,'Explicit polygon required')
        require(len(fin['root_px'])>=2 and fin['root_band_px']>0,'Explicit complete root required')
        padding=fin.get('crop_padding_px',4)
        lo=np.maximum(np.floor(polygon.min(axis=0)-padding).astype(int),0)
        hi=np.minimum(np.ceil(polygon.max(axis=0)+padding+1).astype(int),image.size)
        crop=[*lo.tolist(),*hi.tolist()]
        original=image.crop(crop);mask=Image.new('L',original.size)
        ImageDraw.Draw(mask).polygon([tuple(p-lo)for p in polygon],fill=255)
        raw=np.array(original);result=raw.copy()
        selected=np.asarray(mask)>0
        if fin.get('polygon_margin_px',0):
            import cv2
            radius=fin['polygon_margin_px']
            require(type(radius)is int and 0<radius<=32,'Bounded native polygon margin required')
            selected=cv2.dilate(selected.astype('uint8'),np.ones((2*radius+1,2*radius+1),np.uint8))>0
        if fin.get('source_side'):
            c=fin['source_side'];line=np.asarray(c['polyline_px'],float)
            require(c['side'] in ('above','below','left','right'),'Explicit source side required')
            transpose=c['side'] in ('left','right')
            if transpose:line=line[:,::-1]
            line=line[np.argsort(line[:,0])]
            require(len(line)>=2 and np.all(np.diff(line[:,0])>0),'Independent monotone root polyline required')
            yy,xx=np.indices(selected.shape);u,v=(yy+lo[1]+.5,xx+lo[0]+.5)if transpose else(xx+lo[0]+.5,yy+lo[1]+.5)
            boundary=np.interp(u,line[:,0],line[:,1]);offset=float(c.get('inside_root_px',0))
            require(0<=offset<=4,'Only a finite native root ownership margin is allowed')
            selected&=(v<=boundary+offset)if c['side'] in ('above','left')else(v>=boundary-offset)
        if fin.get('grabcut'):
            import cv2
            outer=cv2.dilate(selected.astype('uint8'),np.ones((11,11),np.uint8))
            inner=cv2.erode(selected.astype('uint8'),np.ones((9,9),np.uint8))
            labels=np.full(selected.shape,cv2.GC_BGD,np.uint8)
            labels[outer>0]=cv2.GC_PR_FGD;labels[inner>0]=cv2.GC_FGD
            labels[raw[:,:,3]<16]=cv2.GC_BGD
            cv2.setRNGSeed(3105)
            cv2.grabCut(raw[:,:,:3].copy(),labels,None,np.zeros((1,65)),np.zeros((1,65)),6,cv2.GC_INIT_WITH_MASK)
            selected=np.isin(labels,[cv2.GC_FGD,cv2.GC_PR_FGD])
            adjacent=cv2.dilate(selected.astype('uint8'),np.ones((3,3),np.uint8))>0
            selected|=adjacent&(outer>0)&(raw[:,:,:3].max(axis=2)<90)
        edge_trace=[]
        if fin.get('trim_above_native_edge'):
            c=fin['trim_above_native_edge'];line=np.asarray(c['polyline_px'],float)
            require(np.all(np.diff(line[:,0])>0),'Edge trace must increase in source X')
            for x in range(max(int(line[0,0]),int(lo[0])),min(int(line[-1,0])+1,int(hi[0]))):
                expected=float(np.interp(x,line[:,0],line[:,1]));a=max(0,int(expected-c['search_radius_px'])-int(lo[1]));z=min(raw.shape[0],int(expected+c['search_radius_px'])-int(lo[1])+1);col=x-int(lo[0])
                ids=np.flatnonzero((raw[a:z,col,:3].max(axis=1)<=c['dark_max_channel'])&(raw[a:z,col,3]>127))
                require(len(ids)>0,f'No original edge in explicit source strip at {x}')
                y=a+int(ids[0]);selected[:y,col]=False;edge_trace.append([x,y+int(lo[1])])
        result[:,:,3]=np.where(selected,raw[:,:,3],0)
        require(np.array_equal(result[:,:,:3],raw[:,:,:3]),'Source RGB changed')
        dest=out/(fin['name']+'.png');Image.fromarray(result).save(dest)
        row={**fin,'image':str(dest),'image_sha256':sha(dest),'crop':crop,
             'size':list(original.size),'root_px':(np.asarray(fin['root_px'])-lo).tolist(),
             'source_RGB_exact':True,'native_pixels':int((result[:,:,3]>127).sum())}
        if edge_trace:row['actual_native_edge_trace_px']=edge_trace
        rows.append(row)
        for col,pic in enumerate([original,Image.fromarray(result)]):
            bg=Image.new('RGBA',pic.size,'#566b77');bg.alpha_composite(pic)
            bg.thumbnail((730,310),Image.Resampling.NEAREST)
            sheet.paste(bg.convert('RGB'),(col*750,n*360+35))
        ImageDraw.Draw(sheet).text((8,n*360+7),fin['name']+' | Original context / independently selected native pixels',fill='white',font=font)
    sheet.save(out/'fin-domain-review.jpg',quality=96)
    report={'ok':True,'kind':'explicit_native_fin_domains','species':cfg['species'],
            'source':{'path':str(source),'sha256':sha(source)},'config_sha256':sha(config),
            'fins':rows,'formal_acceptance':False,'visual_review':'pending',
            'scope':'Exact original RGB and within-domain alpha. Anatomy, fine edges, roots, geometry coverage, volume and current actions require separate review.'}
    (out/'masks.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();r=prepare(a.config,a.output)
    print(json.dumps({'ok':r['ok'],'species':r['species'],'fins':len(r['fins'])}))
