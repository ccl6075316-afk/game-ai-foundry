"""Material-only posterior dorsal footprint repair on an existing cold fish.

The polygon and continuous interior strip are species-specific. The rejected
pointwise raw-source prototype is archived as evidence, not an active mode. Geometry,
UVs, skin and every animation accessor remain byte-identical in the author GLB.
"""
import argparse,io,json,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays,sha
from patch_existing_fin_meshes import write
from refine_native_fin_cages import load,save

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--parameters',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 base=a.candidate.resolve();out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True);base_digest=sha(base/'source-run/fish.glb')
 old=load(base/'author/tail-donors.validation.json');sp=old['species'];cfg=load(a.parameters)['species'][sp];audit=load(base.parent/'audit/audit.validation.json');source=np.array(Image.open(audit['source_image']).convert('RGBA'));d,b=read_glb(base/'source-run/fish.glb');b=bytearray(b);packing=load(base/'author/packing.validation.json');iv=d['bufferViews'][d['images'][0]['bufferView']];atlas=np.array(Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA'));before=atlas.copy();size=np.array([atlas.shape[1],atlas.shape[0]])
 part,row=next((q,z)for q,z in zip(d['extras']['geometry_parts'],packing['parts'])if q['role']=='body_skin'and q['source_surface']==0);origin=np.array(row['atlas_placement'])-row['virtual_crop_origin'];roi=np.zeros(source.shape[:2],np.uint8);cv2.fillPoly(roi,[np.array(cfg['target_polygon_px'],np.int32)],1)
 primitive=d['meshes'][0]['primitives'][0];uv=arrays(d,b,primitive['attributes']['TEXCOORD_0'])*size-origin;indices=arrays(d,b,primitive['indices']).reshape(-1);coverage=np.zeros_like(roi)
 for triangle in indices[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3):cv2.fillConvexPoly(coverage,np.rint(uv[triangle]).astype('int32'),1)
 roi&=cv2.dilate(coverage,np.ones((3,3),np.uint8));covered_columns=np.flatnonzero(coverage.any(axis=0))
 assert cfg.get('mode')=='continuous_previous_body_strip','Only the reviewed continuous strip mode is supported'
 changes=[];unresolved=[]
 for y,x in zip(*np.nonzero(roi)):
  ax,ay=np.array([x,y])+origin;left,top=row['atlas_placement'];rw,rh=row['virtual_crop_size']
  if not(left<=ax<left+rw and top<=ay<top+rh):continue
  if cfg.get('mode')=='continuous_previous_body_strip':
   owned_x=int(np.clip(x,covered_columns[0],covered_columns[-1]));rows=np.flatnonzero(coverage[:,owned_x]);assert len(rows);y0=int(rows[0]);x0,x1=cfg['longitudinal_interval_px'];fade=cfg['lateral_fade_px'];t0=np.clip((x-x0)/fade,0,1);t1=np.clip((x1-x)/fade,0,1);gain=(t0*t0*(3-2*t0))*(t1*t1*(3-2*t1));band=cfg['strip_depth_px']*gain;distance=y0+band-y
   if distance<=0:continue
   t=float(np.clip(distance/max(band,1e-9),0,1));sy=int(round(y+2*distance*t*t*(3-2*t)));sx=owned_x;dx,dy=np.array([sx,sy])+origin
   assert left<=dx<left+rw and top<=dy<top+rh
   atlas[ay,ax,:3]=before[dy,dx,:3]
   if not np.array_equal(before[ay,ax],atlas[ay,ax]):changes.append({'part':part['name'],'fin':'Dorsal','atlas_xy':[int(ax),int(ay)],'source_atlas_xy':[int(dx),int(dy)],'source_kind':'previous_frozen_body_atlas','source_model_sha256':base_digest,'source_RGB':before[dy,dx,:3].tolist(),'rejected_RGB':before[ay,ax,:3].tolist(),'method':'continuous_mirrored_interior_strip'})
   continue
 if unresolved:save(out/'unresolved.validation.json',{'ok':False,'unresolved':unresolved,'parameters':cfg,'reason':'No source-owned same-column donor. Do not fabricate a color or relax donor ownership.'})
 assert changes and not unresolved,unresolved[:10]
 Image.fromarray(atlas).save(out/'atlas.png');b.extend(b'\0'*(-len(b)%4));idx=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':len(b),'byteLength':(out/'atlas.png').stat().st_size});b.extend((out/'atlas.png').read_bytes());d['images'][0]['bufferView']=idx;model=out/'author-reference.glb';write(model,d,b)
 packing.update(candidates={'author-reference':{'path':str(model),'sha256':sha(model)}},atlas={'path':str(out/'atlas.png'),'sha256':sha(out/'atlas.png'),'size':size.tolist()});save(out/'packing.validation.json',packing);save(out/'parts.json',load(base/'author/parts.json'))
 copies={tuple(q['atlas_xy']):q for q in old['body_posterior_donor_copies']}
 for q in changes:copies[tuple(q['atlas_xy'])]=q
 old.update(model=str(model),model_sha256=sha(model),body_posterior_donor_copies=list(copies.values()),physical_and_visual_acceptance='pending');save(out/'tail-donors.validation.json',old)
 save(out/'posterior-body.validation.json',{'ok':True,'species':sp,'input_model':str(base/'source-run/fish.glb'),'input_model_sha256':sha(base/'source-run/fish.glb'),'parameters':cfg,'parameters_sha256':sha(a.parameters),'model_sha256':sha(model),'changed_texels':len(changes),'unresolved':unresolved,'changes':changes,'scope':'Only recorded posterior body atlas RGB; all geometry, UVs, joints, weights, indices, hierarchy and animation accessors untouched. Whole-fish and visual review pending.'})
 print(json.dumps({'ok':True,'species':sp,'changed_texels':len(changes),'unresolved':len(unresolved)}))
if __name__=='__main__':main()
