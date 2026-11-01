"""Verify actual cold tail/fin repair, forward-body invariants and donor bounds."""
import argparse,io,json,sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays,sha,material_semantics
from verify_parity import clips,node_rest_parity
from refine_native_fin_cages import load,save
def inspect(path):
 d,b=read_glb(path);p=d['meshes'][0]['primitives'][0];v={k:arrays(d,b,i)for k,i in p['attributes'].items()};idx=arrays(d,b,p['indices']).reshape(-1);iv=d['bufferViews'][d['images'][0]['bufferView']];im=np.array(Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA'));return d,b,v,idx,im
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();out=a.candidate.resolve();auth=load(out/'author/tail-donors.validation.json');model=out/'source-run/fish.glb';d,b,v,ix,im=inspect(auth['baseline']);e,c,w,iy,newim=inspect(model);records=[];lo,hi=auth['body_tail_interval_native'];assert material_semantics(d)==material_semantics(e);rest=node_rest_parity(d,e);oldclips,newclips=clips(d,b),clips(e,c);assert oldclips.keys()==newclips.keys()
 for name,channels in oldclips.items():
  assert channels.keys()==newclips[name].keys()
  for key,(t,x,interp)in channels.items():
   tt,xx,ii=newclips[name][key];assert interp==ii and np.allclose(t,tt,atol=1e-6,rtol=0)and np.allclose(x,xx,atol=1e-6,rtol=0)
 all_new=e['extras']['geometry_parts'];allowed=np.zeros(im.shape[:2],bool)
 for row in auth['body_posterior_donor_copies']:
  x,y=row['atlas_xy'];allowed[y,x]=True;assert np.array_equal(newim[y,x,:3],row['source_RGB'])and newim[y,x,3]==255
 changed=np.any(im!=newim,axis=2);assert not(changed&~allowed).any(),'Atlas changed beyond exact posterior donor copies'
 for old,new in zip(d['extras']['geometry_parts'],all_new):
  assert old['name']==new['name'];a0=old['vertex_start'];a1=a0+old['vertex_count'];z0=new['vertex_start'];z1=z0+new['vertex_count'];uv=v['TEXCOORD_0'][a0:a1]*[im.shape[1],im.shape[0]];lower=np.maximum(np.floor(uv.min(0)).astype(int),0);upper=np.minimum(np.floor(uv.max(0)).astype(int)+1,[im.shape[1],im.shape[0]])
  if old['role']=='body_skin':
   assert a1-a0==z1-z0;oi=ix[old['index_start']:old['index_start']+old['index_count']]-a0;ni=iy[new['index_start']:new['index_start']+new['index_count']]-z0;assert np.array_equal(oi,ni);forward=v['POSITION'][a0:a1,0]>=hi;errors={k:float(np.max(np.abs(v[k][a0:a1][forward].astype(float)-w[k][z0:z1][forward]))) if forward.any() else 0. for k in v};assert max(errors.values())<=1e-6,(old['name'],errors)
   for key in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']:assert np.array_equal(v[key][a0:a1],w[key][z0:z1]),(old['name'],key)
   assert np.array_equal(v['POSITION'][a0:a1,:2],w['POSITION'][z0:z1,:2]);delta=np.linalg.norm(v['POSITION'][a0:a1]-w['POSITION'][z0:z1],axis=1);assert not((delta>1e-7)&forward).any()
   records.append({'name':old['name'],'forward_attributes_max_error':errors,'all_XY_UV_named_skin_and_directed_indices_unchanged':True,'position_changes_only_declared_tail_interval':True})
  if not(old['role']=='body_skin'and old['source_surface']==0):assert np.array_equal(im[lower[1]:upper[1],lower[0]:upper[0]],newim[lower[1]:upper[1],lower[0]:upper[0]]),(old['name'],'Protected native tile changed')
 sections=load(out/'fin-sections.validation.json');assert sections['ok']and sections['model_sha256']==sha(model)
 finproof=[]
 for row in auth['records']:
  if not row.get('wall_donors'):continue
  assert row['actual_welded_closed_shell']
  part=next(p for p in all_new if p['source_node']==row['name']); packing=load(out/'author/packing.validation.json'); packed=next(p for p in packing['parts']if p['node']==part['source_node']and p['surface']==part['source_surface']); origin=np.array(packed['atlas_placement'])-packed['virtual_crop_origin']; triangles=iy[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3)
  for q in row['wall_donors']:
   actual=np.floor(w['TEXCOORD_0'][triangles[q['triangle']]]*[newim.shape[1],newim.shape[0]]).astype(int); expected=origin+q['source_cutout_xy'];assert np.all(actual==expected),'Cold wall UV differs from recorded native donor';x,y=expected;assert int(newim[y,x,3])==q['source_alpha']and newim[y,x,:3].tolist()==q['RGB']
   if q['visible_source_boundary']:assert q['distance_from_alpha_edge_px']>=auth['settings']['wall_donor_boundary_exclusion_px']and q['source_alpha']>=128
   else:assert q['source_alpha']<128,'Transparent native padding became an opaque rim'
  finproof.append({'name':row['name'],'closing_donors':len(row['wall_donors']),'native_alpha_edge_excluded':True,'transparent_padding_not_opaque':True,'welded_closed':True})
 result={'ok':True,'kind':'actual_tail_fin_donor_preservation','species':auth['species'],'baseline_sha256':sha(auth['baseline']),'model_sha256':sha(model),'actual_model':str(model),'bones':len(e['skins'][0]['joints']),'triangles':len(iy)//3,'body_parts':records,'head_mouth_eyes_geometry_UV_skin_and_donor_pixels_preserved':True,'native_fin_RGB_tiles_preserved':True,'actual_copied_body_texels':int(changed.sum()),'atlas_changes_confined_to_recorded_posterior_body_copies':True,'rig_hierarchy':rest,'native54_channels_unchanged':True,'fins':finproof,'source_sections_report':{'path':str(out/'fin-sections.validation.json'),'sha256':sha(out/'fin-sections.validation.json')},'formal_whole_fish_acceptance':False};save(out/'preservation.validation.json',result);print(json.dumps({'ok':True,'species':auth['species'],'triangles':len(iy)//3,'bones':len(e['skins'][0]['joints']),'body_texels':int(changed.sum())}))
if __name__=='__main__':main()
