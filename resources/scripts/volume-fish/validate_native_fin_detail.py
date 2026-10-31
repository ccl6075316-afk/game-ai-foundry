"""Verify source-pixel fin repair and exact preservation outside explicit fins."""
import argparse,io,json,sys
from pathlib import Path
from collections import Counter
import numpy as np,cv2
from PIL import Image
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha,material_semantics
from verify_parity import clips,node_rest_parity
from refine_native_fin_cages import load,save
def inspect(p):
 d,b=read_glb(p);pr=d['meshes'][0]['primitives'][0];v={k:arrays(d,b,a)for k,a in pr['attributes'].items()};idx=arrays(d,b,pr['indices']).reshape(-1);iv=d['bufferViews'][d['images'][0]['bufferView']];im=np.array(Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA'));return d,b,v,idx,im
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();out=a.candidate.resolve();auth=load(out/'author/author.validation.json');cfg=load(auth['input_masks']['path']);baseline=Path(auth['baseline']['path']);model=out/'source-run/fish.glb';d,b,v,idx,im=inspect(baseline);e,c,w,ix,newim=inspect(model);pack=load(out/'author/packing.validation.json');repair={r['name']for r in auth['fins']};rows=[];protected=[]
 assert material_semantics(d)==material_semantics(e);rest=node_rest_parity(d,e);oldclip,newclip=clips(d,b),clips(e,c);assert oldclip.keys()==newclip.keys()
 for name,channels in oldclip.items():
  assert channels.keys()==newclip[name].keys()
  for key,(times,values,interp)in channels.items():
   t,z,i=newclip[name][key];assert interp==i and np.allclose(times,t,atol=1e-6,rtol=0)and np.allclose(values,z,atol=1e-6,rtol=0)
 for old,new,row in zip(d['extras']['geometry_parts'],e['extras']['geometry_parts'],pack['parts']):
  assert old['name']==new['name'];a0=old['vertex_start'];a1=a0+old['vertex_count'];z0=new['vertex_start'];z1=z0+new['vertex_count'];ti=ix[new['index_start']:new['index_start']+new['index_count']].reshape(-1,3)-z0
  if new['source_node']not in repair:
   errors={k:float(np.max(np.abs(v[k][a0:a1].astype(float)-w[k][z0:z1])))for k in v};assert max(errors.values())<=1e-6,(old['name'],errors);oi=idx[old['index_start']:old['index_start']+old['index_count']]-a0;assert np.array_equal(oi,ti.reshape(-1));uv=v['TEXCOORD_0'][a0:a1]*[im.shape[1],im.shape[0]];lo=np.maximum(np.floor(uv.min(0)).astype(int),0);hi=np.minimum(np.floor(uv.max(0)).astype(int)+1,[im.shape[1],im.shape[0]]);assert np.array_equal(im[lo[1]:hi[1],lo[0]:hi[0]],newim[lo[1]:hi[1],lo[0]:hi[0]]);protected.append({'name':old['name'],'max_attribute_error':errors,'directed_indices_equal':True,'sampled_atlas_rectangle_RGBA_exact':True})
  else:
   pos=w['POSITION'][z0:z1];area=np.linalg.norm(np.cross(pos[ti[:,1]]-pos[ti[:,0]],pos[ti[:,2]]-pos[ti[:,0]]),axis=1);assert np.all(area>1e-16),(new['name'],'Degenerate finite fin face');edges=Counter(tuple(sorted((int(x),int(y))))for t in ti for x,y in zip(t,np.roll(t,-1)));assert all(n==2 for n in edges.values()),'Open fin shell'
   kind=next(k for k in ['Anal','Pectoral','Pelvic']if new['source_node'].startswith(k));mr=next(r for r in cfg['fins']if r['name']==kind);rgba=np.array(Image.open(mr['image']).convert('RGBA'));original=np.array(Image.open(mr['source_image']).convert('RGBA').crop(tuple(mr['crop'])));assert np.array_equal(rgba[:,:,:3],original[:,:,:3]);x,y=row['atlas_placement'];h,ww=rgba.shape[:2];assert np.array_equal(newim[y:y+h,x:x+ww],rgba),'Actual model tile differs from original-pixel mask';uv=w['TEXCOORD_0'][z0:z1]*[newim.shape[1],newim.shape[0]]-[x,y];coverage=np.zeros((h,ww),np.uint8)
   for t in ti:cv2.fillConvexPoly(coverage,np.rint(uv[t]).astype('int32'),1)
   missing=int(((rgba[:,:,3]>127)&(coverage==0)).sum());assert missing==0,(new['name'],'Clipped native pixels',missing);rows.append({'name':new['source_node'],'triangles':len(ti),'closed_topological_shell':True,'nonzero_area_faces':True,'minimum_double_area_native':float(area.min()),'original_RGB_exact':True,'actual_tile_RGBA_exact':True,'native_alpha_pixels_missing_from_cage':missing})
 completion=load(out/'fin490/completion.validation.json');assert completion['ok']and completion['model_sha256']==sha(model)
 result={'ok':True,'kind':'native_fin_detail_preservation_and_source','baseline':str(baseline),'baseline_sha256':sha(baseline),'model':str(model),'model_sha256':sha(model),'triangles_before':len(idx)//3,'triangles_after':len(ix)//3,'bones_before':len(d['skins'][0]['joints']),'bones_after':len(e['skins'][0]['joints']),'native_animation_channels':sum(len(a['channels'])for a in e['animations']),'rig_hierarchy':rest,'native_clips_equal_within_1e6':True,'body_mouth_eyes_and_retained_fins':protected,'refined_fins':rows,'current490_root_and_membrane_gate':str(out/'fin490/completion.validation.json'),'scope':'Fin repair review candidate only. Complete body077/GPU, final anatomical visual/SOP acceptance remain separately recorded.'};save(out/'preservation-source.validation.json',result);print(json.dumps({'ok':True,'species':cfg['species'],'triangles':len(ix)//3,'protected_parts':len(protected),'refined_fins':len(rows)}))
if __name__=='__main__':main()
