"""Compare actual caudal rest projection and UV against the fixed side canvas."""
import argparse, hashlib, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb, accessor

def main():
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[3];out=a.review.resolve();records=[]
    ownership=json.loads((root/'projects/fishing-2d/game/assets/models/fish/motion/surface-ownership.json').read_text(encoding='utf8'))
    for sp in ['great_hammerhead','smooth_hammerhead']:
        profile=json.loads((root/'resources/volume-fish'/f"{sp.replace('_','-')}-121.profile.json").read_text(encoding='utf8'))
        source=root/'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/accepted'/sp/'inputs'/f'char_{sp}_side121_nobg.png'
        w,h=Image.open(source).size;fin=next(f for f in profile['fins'] if f['name']=='Caudal');target=np.zeros((h,w),np.uint8)
        cv2.fillPoly(target,[np.round(np.array(fin['polygon'])*[w,h]).astype(np.int32)],1);measure={}
        for label,path in [('before',out/'baseline'/f'{sp}.glb'),('after',root/'projects/fishing-2d/game/assets/models/fish'/f'{sp}.glb')]:
            d,b=read_glb(path);n=next(n for n in d['nodes'] if n.get('name')=='Caudal' and 'mesh'in n);prim=d['meshes'][n['mesh']]['primitives'][0]
            pos=accessor(d,b,prim['attributes']['POSITION']);uv=accessor(d,b,prim['attributes']['TEXCOORD_0']);tri=accessor(d,b,prim['indices']).reshape(-1,3)
            projected=np.c_[pos[:,0]+.5,.5-pos[:,1]*profile['source_aspect_ratio']];error=np.linalg.norm((projected-uv)*[w,h],axis=1);mask=np.zeros((h,w),np.uint8)
            for t in tri:cv2.fillConvexPoly(mask,np.round(projected[t]*[w,h]).astype(np.int32),1)
            measure[label]={'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_polygon_iou':float(np.logical_and(mask,target).sum()/np.logical_or(mask,target).sum()),'source_uv_position_disagreement_px_max':float(error.max())}
        assert measure['after']['source_polygon_iou']>.98 and measure['after']['source_uv_position_disagreement_px_max']<.001
        assert measure['before']['source_polygon_iou']<.95 and measure['before']['source_uv_position_disagreement_px_max']>20
        base=np.asarray(fin['source_baseline'])*[w,h];point=base.mean(axis=0);edges=np.asarray(ownership['profiles'][sp]['fins']['Caudal']['0']['edges']).reshape(-1,2,2)*[w,h]
        ab=edges[:,1]-edges[:,0];t=np.clip(np.sum((point-edges[:,0])*ab,axis=1)/np.maximum(np.sum(ab*ab,axis=1),1e-12),0,1)
        distance=float(np.linalg.norm(point-edges[:,0]-t[:,None]*ab,axis=1).min());assert distance>10,'Basal midpoint still receives free-edge ink'
        records.append({'species':sp,**measure,'basal_midpoint_nearest_ink_edge_px':distance})
    report={'ok':True,'records':records,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'method':'Fixed original canvas and scale. Actual GLB rest XY triangles versus authored caudal polygon; UV mismatch in native source pixels. Old installed mesh is a negative control. No local fit. Attached basal midpoint must be outside free-edge ink.','limits':'Source-art conformity, not biological measurement; physical/motion gates independent.'}
    (out/'source-alignment.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
