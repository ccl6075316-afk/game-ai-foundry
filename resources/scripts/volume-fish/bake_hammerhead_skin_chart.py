"""Bake only nearest native source-body pixels for a new continuous cap chart."""
import argparse,hashlib,json,io
from pathlib import Path
import numpy as np
from PIL import Image
from portable.glb_io import read_glb
def main():
 ap=argparse.ArgumentParser()
 for k in ['source','mapping','output','report']:ap.add_argument('--'+k,type=Path,required=True)
 ap.add_argument('--clean-side',type=Path)
 a=ap.parse_args();assert not a.output.exists();d,b=read_glb(a.source);n=next(n for n in d['nodes']if n.get('name')=='Reference_head_body');p=next(p for p in d['meshes'][n['mesh']]['primitives']if'Project-native'in d['materials'][p['material']]['name']);tx=d['materials'][p['material']]['pbrMetallicRoughness']['baseColorTexture'];im=d['images'][d['textures'][tx['index']]['source']];v=d['bufferViews'][im['bufferView']];src=np.array(Image.open(io.BytesIO(b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGBA'));uv=np.load(a.mapping)['uv'];assert np.isfinite(uv).all()and uv.min()>=0 and uv.max()<=1
 x=np.minimum(src.shape[1]-1,(uv[:,:,0]*src.shape[1]).astype(int));y=np.minimum(src.shape[0]-1,((1-uv[:,:,1])*src.shape[0]).astype(int));out=src[y,x].copy();clean_proof=None
 if a.clean_side:
  data=np.load(a.mapping);clean=np.array(Image.open(a.clean_side).convert('RGBA'));cx=np.clip(np.rint(data['clean_u']*(clean.shape[1]-1)).astype(int),12,clean.shape[1]-13);lo=np.zeros(clean.shape[1]);hi=lo.copy();validcols=np.flatnonzero(np.any(clean[:,:,3]==255,axis=0));near=np.searchsorted(validcols,cx);l=validcols[np.maximum(0,near-1)];r=validcols[np.minimum(len(validcols)-1,near)];cx=np.where(abs(cx-l)<=abs(cx-r),l,r)
  for k in range(clean.shape[1]):
   ids=np.flatnonzero(clean[:,k,3]==255)
   if len(ids):lo[k],hi[k]=ids[0],ids[-1]
  inset=np.minimum(12,np.maximum(1,(hi[cx]-lo[cx])*.2));cy=np.rint(lo[cx]+inset+np.clip(data['height_fraction'],0,1)*(hi[cx]-lo[cx]-2*inset)).astype(int)
  # The source has transparent notches inside some columns; sample the nearest
  # actual opaque source pixel instead of inventing a fill or accepting alpha.
  for column in np.unique(cx):
   ids=np.flatnonzero(clean[:,column,3]==255);assert len(ids),int(column)
   mask=cx==column;target=cy[mask];at=np.searchsorted(ids,target);left=ids[np.maximum(0,at-1)];right=ids[np.minimum(len(ids)-1,at)];cy[mask]=np.where(abs(target-left)<=abs(target-right),left,right)
  donor=clean[cy,cx];assert np.all(donor[:,:,3]==255);w=data['boundary_blend'][:,:,None];out[:,:,:3]=np.rint(out[:,:,:3]*(1-w)+donor[:,:,:3]*w).astype(np.uint8);clean_proof=dict(path=str(a.clean_side),sha256=hashlib.sha256(a.clean_side.read_bytes()).hexdigest(),scope='Same-project reviewed clean-side donor only in integrated cap; 6mm boundary blend, native eye/lips excluded. Nearest donor sampling, derived boundary colors declared.')
 assert np.all(out[:,:,3]==255);Image.fromarray(out).save(a.output);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();a.report.write_text(json.dumps(dict(ok=True,kind='continuous_cap_nearest_native_body_pixel_chart',source_sha256=sha(a.source),mapping_sha256=sha(a.mapping),output_sha256=sha(a.output),size=[out.shape[1],out.shape[0]],source_RGBA_sha256=hashlib.sha256(src.tobytes()).hexdigest(),clean_side=clean_proof,no_generated_or_interpolated_colors=not bool(clean_proof),alpha_all_255=True,samples=int(x.size)),indent=2)+'\n')
if __name__=='__main__':main()
