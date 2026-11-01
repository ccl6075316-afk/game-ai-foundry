"""Source/actual GLB orthographic silhouette diagnostic, no source-image edits.

Both are isotropically normalized by full X extent and aligned at the nose.
This is a projection comparison, not a biological TL measurement.
"""
import argparse,base64,hashlib,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--game',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=a.game.parent/'experiments/blender-fish';a.output.mkdir(parents=True,exist_ok=True);rows=[]
    for sp,label in [('scalloped_hammerhead','路氏双髻鲨'),('great_hammerhead','大双髻鲨'),('smooth_hammerhead','无沟双髻鲨')]:
        source=root/'hammer-pair-121'/'accepted'/sp/'inputs'/f'char_{sp}_top121_nobg.png' if sp!='scalloped_hammerhead' else root/'models/scalloped_hammerhead/051-source-inputs/hammerhead-top-050r2/output/char_hammerhead_top050r2_nobg.png'
        model=a.game/'assets/models/fish'/f'{sp}.glb';d,b=read_glb(model);parts=[];wing=[]
        for n in d['nodes']:
            if 'mesh' not in n:continue
            assert not any(k in n for k in ['matrix','translation','rotation','scale']),n['name']
            for p in d['meshes'][n['mesh']]['primitives']:
                pts=accessor(d,b,p['attributes']['POSITION']);tri=accessor(d,b,p['indices']).reshape(-1,3);parts.append((pts,tri))
                if n['name']=='Cephalofoil':wing.append(pts)
        pts=np.concatenate([p for p,t in parts]);wp=np.concatenate(wing);tl=float(np.ptp(pts[:,0]));hw=float(np.ptp(wp[:,2]));nose=float(pts[:,0].max());mask=np.zeros((440,1040),np.uint8)
        for p,t in parts:
            q=np.column_stack((1000+(p[:,0]-nose)*960/tl,220-p[:,2]*960/tl));q=np.round(q).astype(np.int32)
            for face in t:cv2.fillConvexPoly(mask,q[face],255)
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        paths=''.join('<path d="M '+' L '.join(f'{x},{y}' for x,y in c[:,0,:])+' Z" fill="none" stroke="#ffb957" stroke-width="2"/>' for c in contours)
        im=np.asarray(Image.open(source).convert('RGBA'));yy,xx=np.where(im[:,:,3]>240);head=xx>xx.max()*.91;source_width=int(np.ptp(yy[head]));source_length=int(np.ptp(xx));scale=960/source_length
        source_y_center=(float(yy[head].max())+float(yy[head].min()))/2
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1040" height="440" viewBox="0 0 1040 440"><rect width="1040" height="440" fill="#182f3b"/><image x="{1000-xx.max()*scale}" y="{220-source_y_center*scale}" width="{im.shape[1]*scale}" height="{im.shape[0]*scale}" opacity=".80" xlink:href="data:image/png;base64,{base64.b64encode(source.read_bytes()).decode()}"/>{paths}<text x="24" y="28" fill="white" font-family="sans-serif" font-size="18">{label} · 原图像素 + 橙色模型投影轮廓</text><text x="24" y="420" fill="#b8ced6" font-family="sans-serif" font-size="14">整体 X 长度统一、吻端对齐、等比缩放；尾姿不同，不据此推断生物比例。</text></svg>'
        (a.output/f'{sp}-overlay.svg').write_text(svg,encoding='utf8')
        rows.append(dict(species=sp,label=label,model_sha256=sha(model),source_sha256=sha(source),source=str(source.resolve()),model_head_width_over_x_extent=hw/tl,source_head_width_over_x_extent=source_width/source_length,method='GLB rest positions including all mesh nodes, X extent; head width from Cephalofoil Z extent. Source alpha>240, head selection x>0.91*maximum_alpha_x; both isotropically normalized to X extent. Not anatomical TL or tail-length evidence.'))
    (a.output/'top-comparison.validation.json').write_text(json.dumps(dict(ok=True,status='done',next_action='human_review',records=rows,geometry_changed=False,biological_acceptance=False),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps([{'species':r['species'],'model':r['model_head_width_over_x_extent'],'source':r['source_head_width_over_x_extent']} for r in rows]))
if __name__=='__main__':main()
