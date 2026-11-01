"""Compare a source-coordinate orthographic render without fitting or rescaling it."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_erosion, distance_transform_edt

def compare(source, render, target):
    s=np.array(Image.open(source).convert('RGBA'))[:,:,3]>128
    m=np.array(Image.open(render).convert('RGBA'))[:,:,3]>128
    if s.shape!=m.shape: raise ValueError('Render must have exactly the original source dimensions')
    x0,y0,x1,y1=target['head_roi']; a=s[y0:y1,x0:x1]; b=m[y0:y1,x0:x1]
    edge=lambda q:q&~binary_erosion(q)
    ea=edge(a);eb=edge(b)
    # Cropping creates artificial boundaries; exclude those from both samples.
    ea[[0,-1],:]=False;ea[:,[0,-1]]=False
    eb[[0,-1],:]=False;eb[:,[0,-1]]=False
    dist=np.r_[distance_transform_edt(~eb)[ea],distance_transform_edt(~ea)[eb]]
    regions={'upper_tip_region':target.get('upper_tip_region',[1740,420,s.shape[1],480]),
             'lower_tip_region':target.get('lower_tip_region',[1740,485,s.shape[1],545]),
             'mouth_columns':target.get('mouth_columns',[1730,1804])}
    def tip(mask,region):
        left,top,right,bottom=region
        yy,xx=np.where(mask[top:bottom,left:right]);return int(xx.max()+left) if len(xx) else -1
    upper=tip(m,regions['upper_tip_region']);lower=tip(m,regions['lower_tip_region'])
    # Compare both edges of the actual open mouth, rather than only its envelope.
    gaps=[]
    def runs(mask,x):
        ys=np.flatnonzero(mask[:,x]); return np.split(ys,np.where(np.diff(ys)>1)[0]+1)
    for x in range(*regions['mouth_columns']):
        sr=runs(s,x);mr=runs(m,x)
        if len(sr)<2:continue
        if len(mr)<2:gaps.append({'x':x,'missing_gap':True});continue
        gaps.append({'x':x,'upper_edge_error':abs(int(sr[0][-1])-int(mr[0][-1])),
                     'lower_edge_error':abs(int(sr[-1][0])-int(mr[-1][0]))})
    valid=[g for g in gaps if not g.get('missing_gap')]
    metrics={'head_roi_silhouette_iou':float((a&b).sum()/(a|b).sum()),
             'outer_boundary_mean_pixels':float(dist.mean()),
             'upper_tip_x_error_pixels':abs(upper-target['upper_tip_source'][0]),
             'lower_tip_x_error_pixels':abs(lower-target['lower_tip_source'][0]),
             'upper_tip_x':upper,'lower_tip_x':lower,
             'mouth_gap_missing_columns':len(gaps)-len(valid),
             'mouth_upper_edge_mean_pixels':float(np.mean([g['upper_edge_error'] for g in valid])) if valid else 999,
             'mouth_lower_edge_mean_pixels':float(np.mean([g['lower_edge_error'] for g in valid])) if valid else 999}
    limits=target['limits_frozen_before_first_render']; failures=[]
    for key in ['head_roi_silhouette_iou','outer_boundary_mean_pixels','upper_tip_x_error_pixels','lower_tip_x_error_pixels']:
        bound=limits.get(key+'_min',limits.get(key+'_max'))
        if (metrics[key]<bound if key+'_min' in limits else metrics[key]>bound):failures.append(key)
    # Independent aperture requirement: no absent gap, each lip average <=3.5px.
    if metrics['mouth_gap_missing_columns'] or max(metrics['mouth_upper_edge_mean_pixels'],metrics['mouth_lower_edge_mean_pixels'])>3.5:
        failures.append('mouth_aperture_edges')
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if sha(source)!=target['source_sha256']:raise ValueError('Original source hash mismatch')
    return {'ok':not failures,'source_sha256':sha(source),'render_sha256':sha(render),'target':target,
            'metrics':metrics,'sampling_regions':regions,'mouth_gap_columns':gaps,'failures':failures,
            'scope':'Same coordinates, no independent alignment/rescaling. Side outline and aperture only; no claim of measured 3D anatomy or complete closed-lip occlusion.'},s,m

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--render',required=True);p.add_argument('--target',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    report,s,m=compare(a.source,a.render,json.loads(Path(a.target).read_text(encoding='utf-8')))
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report['metrics']));print('ok=',report['ok'])
    raise SystemExit(0 if report['ok'] else 1)
