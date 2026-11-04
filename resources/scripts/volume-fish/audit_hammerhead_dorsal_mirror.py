"""Exact written-array and bounded-RGB audit for a dorsal donor transfer."""
import argparse,json,hashlib,io
from pathlib import Path
import numpy as np
from PIL import Image
from portable.glb_io import read_glb,arrays

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pixels(d,b,i):
 im=d['images'][i];v=d['bufferViews'][im['bufferView']];return np.array(Image.open(io.BytesIO(b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGBA'))
def main():
 p=argparse.ArgumentParser()
 for name in ['baseline','model','bake','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();od,ob=read_glb(a.baseline);nd,nb=read_glb(a.model);assert od['nodes']==nd['nodes']and od['materials']==nd['materials']and od['samplers']==nd['samplers'];assert len(od['accessors'])==len(nd['accessors']);count=0
 for i,(u,v)in enumerate(zip(od['accessors'],nd['accessors'])):assert np.array_equal(arrays(od,ob,i),arrays(nd,nb,i)),i;count+=1
 assert od['skins']==nd['skins']and od['animations']==nd['animations'];bake=json.loads((a.bake/'bake.validation.json').read_text());assert bake['model_sha256']==sha(a.baseline);maps=np.load(a.bake/'applied-map.npz')['map'];body=next(n for n in od['nodes']if n.get('name')=='Reference_head_body');pr=od['meshes'][body['mesh']]['primitives'];slots={};changed=[]
 for t in pr:
  m=od['materials'][t['material']];name=m['name']
  if name.startswith(('Project-native','Own native body pixels')):
   slot=1 if name.startswith('Project-native')else 3;slots[slot]=od['textures'][m['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
 assert len(od['images'])==len(nd['images'])==17;old=[pixels(od,ob,i)for i in range(17)];new=[pixels(nd,nb,i)for i in range(17)];chart_old={s:old[i]for s,i in slots.items()};proof=[]
 for slot,index in slots.items():
  u,v=old[index],new[index];expected=np.array(Image.open(a.bake/f'skin-slot-{slot}.png').convert('RGBA'));assert np.array_equal(v,expected);rows=maps[maps[:,0]==slot];allowed=np.zeros(u.shape[:2],bool);x,y=rows[:,1].astype(int),rows[:,2].astype(int);allowed[y,x]=True;assert np.array_equal(u[~allowed],v[~allowed]);assert np.array_equal(u[:,:,3],v[:,:,3]);source=np.zeros((len(rows),3),np.uint8)
  for ss,image in chart_old.items():
   k=rows[:,3]==ss;source[k]=image[rows[k,5].astype(int),rows[k,4].astype(int),:3]
  w=rows[:,6,None];rgb=np.rint(u[y,x,:3]*(1-w)+source*w).astype(np.uint8);assert np.array_equal(v[y,x,:3],rgb);error=int(abs(v[y,x,:3].astype(int)-rgb.astype(int)).max());proof.append(dict(slot=slot,image=index,changed_texels=int(np.any(u!=v,axis=2).sum()),mapped_RGB_error=error,unmapped_RGBA_exact=True,alpha_exact=True));changed.append(index)
 for i in range(17):
  if i not in changed:assert np.array_equal(old[i],new[i]),i
 lip=np.load(a.model.parent.parent/'skin-author-r7/native-lip-pixel-map.npz')['map'];u,v=old[slots[1]],new[slots[1]];assert np.array_equal(u[lip[:,1],lip[:,0]],v[lip[:,1],lip[:,0]])
 result=dict(ok=True,kind='all_written_geometry_exact_and_dorsal_RGB_scope',model_sha256=sha(a.model),baseline_sha256=sha(a.baseline),checker_sha256=sha(__file__),all_decoded_arrays_exact=count,whole_geometry_normals_UV_skin_rig_animations_exact=True,material_sampler_node_bindings_exact=True,images=17,unchanged_RGBA_images=15,changed_charts=proof,native_lip_samples_unchanged=len(lip),bake=sha(a.bake/'bake.validation.json'),direction=bake['direction'],scope='Only declared mapped left upper-skin RGB changes. Same-project immutable right pixels used; lateral fade is declared blend. All alpha, eyes/fins/oral and unrelated pixels exact. Actual same-camera head-up views separately reviewed.',formal_acceptance=False);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
