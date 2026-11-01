"""Measure explicit silhouette sections in a reviewed photographic/model preview.

Only projected image ratios are produced. Camera calibration, biological size
and geometric correctness are not inferred. Authored landmarks remain visible.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

def measure(config_path, output):
    cfg=json.loads(Path(config_path).read_text(encoding='utf8'))
    image=Path(cfg['image']); raw=image.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==cfg['image_sha256']
    assert cfg['camera_limitations'] and cfg['landmark_observations']
    raw=Image.open(image).convert('RGBA');alpha=np.asarray(raw)[:,:,3]
    im=raw.convert('RGB'); pixels=np.asarray(im);draw=ImageDraw.Draw(im)
    section_mode=cfg.get('section_mode','first_background')
    assert section_mode in ('first_background','outermost_foreground')
    marks=cfg['correspondence']; us=[m['source_u']for m in marks]
    xy=np.array([m['center_px']for m in marks],float)
    assert all(a<b for a,b in zip(us,us[1:]))
    length=sum(np.linalg.norm(b-a)for a,b in zip(xy,xy[1:])); assert length>0
    rows=[]
    for i,u in enumerate(cfg['sample_source_u']):
        assert us[0]<=u<=us[-1]
        j=min(len(us)-2,max(0,int(np.searchsorted(us,u,side='right')-1)))
        t=(u-us[j])/(us[j+1]-us[j]);center=xy[j]*(1-t)+xy[j+1]*t
        axis=xy[j+1]-xy[j];normal=np.array([-axis[1],axis[0]])/np.linalg.norm(axis)
        ends=[]
        for sign in [-1,1]:
            last=center.copy()
            for distance in np.arange(0,cfg['maximum_half_scan_px'],.5):
                pt=center+sign*distance*normal;x,y=np.rint(pt).astype(int)
                if not(0<=x<pixels.shape[1]and 0<=y<pixels.shape[0]):break
                foreground=max(pixels[y,x])>=cfg['foreground_rgb_max_threshold'] and alpha[y,x]>=cfg.get('foreground_alpha_min',0)
                if not foreground:
                    if section_mode=='outermost_foreground':continue
                    break
                last=pt
            ends.append(last)
        width=float(np.linalg.norm(ends[1]-ends[0]));assert width>2
        rows.append({'source_u':u,'center_px':center.tolist(),'endpoints_px':[p.tolist()for p in ends],
                     'projected_width_px':width,'half_width_native':width*(us[-1]-us[0])/(2*length)})
        draw.line([tuple(p)for p in ends],fill=(20,240,235),width=2)
        if i in cfg.get('label_samples',[]):draw.text(tuple(ends[1]+[4,3]),f'u={u:.3f} {width:.1f}px',fill=(255,255,0))
    for mark,pt in zip(marks,xy):
        x,y=pt;draw.ellipse((x-3,y-3,x+3,y+3),fill=(255,80,80));draw.text((x+5,y-15),mark['landmark'],fill=(255,200,100))
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    overlay=output/'head-sections-overlay.png';im.save(overlay)
    report={'ok':True,'kind':'actual_preview_projected_section_measurement','image':str(image),'image_sha256':cfg['image_sha256'],
            'config':str(Path(config_path).resolve()),'config_sha256':hashlib.sha256(Path(config_path).read_bytes()).hexdigest(),
            'image_head_axis_length_px':float(length),'source_u_interval':[us[0],us[-1]],'correspondence':marks,'rows':rows,
            'camera_limitations':cfg['camera_limitations'],'landmark_observations':cfg['landmark_observations'],'section_mode':section_mode,
            'conversion':'Measured projected width / measured piecewise neck-eye-mouth image axis length * source-art head u-span / 2.',
            'overlay':str(overlay),'scope':'Traceable projected reference proportions only. Not orthographic scan dimensions or biological measurements; actual candidate head review remains required.'}
    (output/'head-sections.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=measure(a.config,a.output);print(json.dumps({'ok':r['ok'],'sections':len(r['rows']),'scope':r['scope']}))
