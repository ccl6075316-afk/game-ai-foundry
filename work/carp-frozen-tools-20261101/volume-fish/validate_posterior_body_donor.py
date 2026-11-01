"""Independently check actual cold RGB donors and unchanged whole-fish arrays."""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np,cv2
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import sha,material_semantics
from validate_tail_donor_preservation import inspect,load,save
from verify_parity import clips,node_rest_parity
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();out=a.candidate.resolve();proof=load(out/'author/posterior-body.validation.json');before=Path(proof['input_model']);after=out/'source-run/fish.glb';d,b,v,ix,old=inspect(before);e,c,w,iy,new=inspect(after);assert sha(before)==proof['input_model_sha256'];assert material_semantics(d)==material_semantics(e);node_rest_parity(d,e);assert np.array_equal(ix,iy);errors={}
 for k in v:
  assert v[k].shape==w[k].shape;errors[k]=float(np.max(np.abs(v[k].astype(float)-w[k].astype(float))));assert errors[k]<=1e-6,(k,errors[k])
 oldclips,newclips=clips(d,b),clips(e,c);assert oldclips.keys()==newclips.keys()
 for name in oldclips:
  assert oldclips[name].keys()==newclips[name].keys()
  for key,(t,x,interp)in oldclips[name].items():
   tt,xx,ii=newclips[name][key];assert interp==ii and np.allclose(t,tt,rtol=0,atol=1e-6)and np.allclose(x,xx,rtol=0,atol=1e-6)
 allowed=np.zeros(old.shape[:2],bool);input_digest=sha(before)
 for q in proof['changes']:
  x,y=q['atlas_xy'];sx,sy=q['source_atlas_xy'];assert q['source_model_sha256']==input_digest;assert old[sy,sx,:3].tolist()==q['source_RGB']==new[y,x,:3].tolist();assert old[y,x,:3].tolist()==q['rejected_RGB'];assert new[y,x,3]==old[y,x,3];allowed[y,x]=True
 changed=np.any(old!=new,axis=2);assert np.array_equal(changed,allowed),'Actual atlas change outside exact donor list'
 # A deliberately rejected previous image is the negative control. Report
 # near-zero RGB pixels only on the target body UV support, not the full atlas.
 packing=load(out/'author/packing.validation.json');part,row=next((p,r)for p,r in zip(e['extras']['geometry_parts'],packing['parts'])if p['role']=='body_skin'and p['source_surface']==0);origin=np.array(row['atlas_placement'])-row['virtual_crop_origin'];audit=load(out.parent/'audit/audit.validation.json');from PIL import Image
 source=Image.open(audit['source_image']);mask=np.zeros((source.height,source.width),np.uint8);cv2.fillPoly(mask,[np.array(proof['parameters']['target_polygon_px'],np.int32)],1);cover=np.zeros_like(mask);uv=w['TEXCOORD_0']*[new.shape[1],new.shape[0]]-origin
 for triangle in iy[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3):cv2.fillConvexPoly(cover,np.rint(uv[triangle]).astype('int32'),1)
 yy,xx=np.nonzero(mask&cover);yy+=origin[1];xx+=origin[0];counts={str(th):[int((np.max(old[yy,xx,:3],axis=1)<=th).sum()),int((np.max(new[yy,xx,:3],axis=1)<=th).sum())]for th in [5,12,16,24,32,40]};assert counts['5'][1]==0,'Near-zero RGB remains on sampled target skin'
 save(out/'posterior-preservation.validation.json',{'ok':True,'kind':'material_only_posterior_body_repair','input_model_sha256':input_digest,'model_sha256':sha(after),'all_attributes_maximum_error':errors,'all_directed_triangles_unchanged':True,'rig_hierarchy_and_54_native_channels_unchanged':True,'exact_previous_atlas_donors_verified':True,'outside_exact_change_set_RGBA_unchanged':True,'changed_texels':int(changed.sum()),'actual_body_UV_dark_RGB_counts_diagnostic_before_after':counts,'color_metric_limit':'Diagnostic only: crucian artifact is dark olive, not literal zero RGB. Threshold counts cannot identify anatomy or replace actual isolated/whole posterior image review.','scope':'Target posterior body RGB only. No geometry, UV or skin edits. Color continuity requires visual review.','formal_acceptance':False});print(json.dumps({'ok':True,'species':proof['species'],'changed':int(changed.sum()),'dark_RGB_counts':counts,'max_array_error':max(errors.values())}))
if __name__=='__main__':main()
