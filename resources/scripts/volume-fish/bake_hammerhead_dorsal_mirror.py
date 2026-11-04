"""Bake a mapped same-fish dorsal donor into existing 3D material charts."""
import argparse,json,hashlib,io
from pathlib import Path
import numpy as np
from PIL import Image
from portable.glb_io import read_glb,arrays

def main():
 p=argparse.ArgumentParser()
 for k in ['model','mapping','output']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();assert not a.output.exists();a.output.mkdir();d,b=read_glb(a.model);node=next(n for n in d['nodes']if n.get('name')=='Reference_head_body');parts=d['meshes'][node['mesh']]['primitives'];images={};protect={};by_slot={};sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 for pr in parts:
  mat=d['materials'][pr['material']];name=mat['name']
  if not name.startswith(('Project-native','Own native body pixels')):continue
  slot=1 if name.startswith('Project-native')else 3;tx=mat['pbrMetallicRoughness']['baseColorTexture']['index'];im=d['images'][d['textures'][tx]['source']];view=d['bufferViews'][im['bufferView']];pixels=np.array(Image.open(io.BytesIO(b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])).convert('RGBA'));images[slot]=pixels;H,W=pixels.shape[:2];mask=np.zeros((H,W),bool);protect[slot]=mask;v=arrays(d,b,pr['attributes']['POSITION']);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);faces=arrays(d,b,pr['indices']).reshape(-1,3)
  # Protect every texel geometrically owned by the requested right donor,
  # even if any UV island happens to overlap the left receiver chart.
  for ids in faces:
   pos=v[ids]
   if pos[:,2].max()<=1e-6:continue
   u=uv[ids];q=np.stack([u[:,0]*W-.5,u[:,1]*H-.5],1);aa,bb,cc=q;den=(bb[0]-aa[0])*(cc[1]-aa[1])-(bb[1]-aa[1])*(cc[0]-aa[0])
   if abs(den)<1e-10:continue
   lo=np.maximum(np.floor(q.min(0)).astype(int),0);hi=np.minimum(np.ceil(q.max(0)).astype(int),[W-1,H-1]);x,y=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));pts=np.stack([x.ravel(),y.ravel()],1);be=((pts[:,0]-aa[0])*(cc[1]-aa[1])-(pts[:,1]-aa[1])*(cc[0]-aa[0]))/den;ce=((bb[0]-aa[0])*(pts[:,1]-aa[1])-(bb[1]-aa[1])*(pts[:,0]-aa[0]))/den;beta=np.stack([1-be-ce,be,ce],1);k=(beta.min(1)>=-1e-7)&((beta@pos)[:,2]>1e-6);pp=pts[k];mask[pp[:,1],pp[:,0]]=True
 for slot,mask in protect.items():
  expanded=mask.copy()
  for dy in [-1,0,1]:
   for dx in [-1,0,1]:
    srcy=slice(max(0,-dy),mask.shape[0]-max(0,dy));srcx=slice(max(0,-dx),mask.shape[1]-max(0,dx));dsty=slice(max(0,dy),mask.shape[0]-max(0,-dy));dstx=slice(max(0,dx),mask.shape[1]-max(0,-dx));expanded[dsty,dstx]|=mask[srcy,srcx]
  protect[slot]=expanded
 lip=np.load(a.model.parent.parent/'skin-author-r7/native-lip-pixel-map.npz')['map'];protect[1][lip[:,1],lip[:,0]]=True;rows=np.load(a.mapping)['map'];outputs=[];maps=[]
 for slot,src in images.items():
  H,W=src.shape[:2];data=rows[rows[:,0]==slot];x,y=data[:,1].astype(int),data[:,2].astype(int);allowed=~protect[slot][y,x];data=data[allowed];key=data[:,2]*W+data[:,1];_,ix=np.unique(key,return_index=True);data=data[ix];out=src.copy();donor=np.zeros((len(data),4),np.uint8)
  for donor_slot,im in images.items():
   k=data[:,3]==donor_slot;donor[k]=im[data[k,5].astype(int),data[k,4].astype(int)]
  assert np.all(donor[:,3]==255);x,y=data[:,1].astype(int),data[:,2].astype(int);w=data[:,6,None];rgb=np.rint(src[y,x,:3]*(1-w)+donor[:,:3]*w).astype(np.uint8);out[y,x,:3]=rgb;assert np.array_equal(out[protect[slot]],src[protect[slot]])and np.array_equal(out[:,:,3],src[:,:,3]);f=a.output/f'skin-slot-{slot}.png';Image.fromarray(out).save(f);changed=np.any(out!=src,axis=2);outputs.append(dict(slot=slot,path=str(f.resolve()),sha256=sha(f),changed_texels=int(changed.sum()),right_and_native_lip_protected_texels=int(protect[slot].sum()),protected_error=0,alpha_exact=True,full_transfer_samples=int(np.sum(data[:,6]>=1-1e-7)),source_rgba_sha256=hashlib.sha256(src.tobytes()).hexdigest()));maps.append(data)
 np.savez_compressed(a.output/'applied-map.npz',map=np.concatenate(maps));report=dict(ok=True,kind='same_fish_right_dorsal_material_transfer',model_sha256=sha(a.model),mapping_sha256=sha(a.mapping),script_sha256=sha(__file__),outputs=outputs,applied_map_sha256=sha(a.output/'applied-map.npz'),direction='Head up, back toward viewer: screen-right donor to screen-left receiver. Native Y<0 to Y>0.',unrelated_images_unedited=True,formal_acceptance=False);(a.output/'bake.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
