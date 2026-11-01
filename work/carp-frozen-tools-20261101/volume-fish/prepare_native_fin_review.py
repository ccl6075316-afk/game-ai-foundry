"""Bind cold fin candidate to new actual-part, source-band and GPU review plans."""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
from parts import freeze
from refine_native_fin_cages import load,save,ROOT
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();out=a.candidate.resolve();author=load(out/'author/author.validation.json');base=Path(author['baseline']['path']);width=load(base.parent/'deformation.plan.json');old=Path(width['inputs']['model']['path']);spec=load(out/'source-run/final-spec.json');model=out/'source-run/fish.glb';manifest=out/'parts-manifest.json';freeze(model,spec,manifest)
 oldplan=load(old.parent.parent/'fin.plan.json')['items'][0];plan=copy.deepcopy(oldplan);plan.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(manifest),packed_parts_manifest_sha256=sha(manifest),packed_helper_script=str(HERE/'portable/PackedFishParts.gd'),packed_canonicalizer=str(HERE/'portable/parts.py'))
 d,b=read_glb(old);e,c=read_glb(base);f,g=read_glb(model)
 def pos(doc,blob):return arrays(doc,blob,doc['meshes'][0]['primitives'][0]['attributes']['POSITION'])
 oldpos=pos(d,b);basepos=pos(e,c);newpos=pos(f,g);repaired={r['name']:r for r in author['fins']}
 for name,root in plan['fins'].items():
  if name in repaired:
   row=repaired[name];root.update(rest_points_gltf=row['root_band_rest_points_gltf'],ids=row['root_band_ids'],rule='Frozen complete source baseline distance <=17native px, both finite shell layers; not a nearest-body subset.')
  else:
   parts=[r for r in d['extras']['geometry_parts']if r.get('logical_name')==name];ids=np.concatenate([np.arange(r['vertex_start'],r['vertex_start']+r['vertex_count'])for r in parts]);points=np.array(root['rest_points_gltf']);nearest=np.argmin(((points[:,None,:]-oldpos[ids][None,:,:])**2).sum(2),axis=1);error=np.linalg.norm(points-oldpos[ids[nearest]],axis=1);assert error.max()<3e-5,(name,float(error.max()));root['rest_points_gltf']=basepos[ids[nearest]].tolist();root['rule']='Original complete authored source band, identity transported through accepted width vertex map.'
 plan['frozen_inputs']={str(p.resolve()):sha(p)for p in [model,manifest,out/'source-run/final-spec.json',out/'author/author.validation.json',base,HERE/'portable/PackedFishParts.gd',HERE/'portable/parts.py',HERE/'portable/export_fin_poses.gd']};save(out/'fin.plan.json',{'kind':'native_fin_detail_current_root_plan','items':[plan]})
 capture=load(base.parent/'capture.plan.json');capture['models']={'before':str(base),'after':str(model)};capture['bindings']={k:v for k,v in capture['bindings'].items()if not k.endswith('.glb')};capture['bindings'].update({str(p):sha(p)for p in [base,model]});save(out/'capture.plan.json',capture)
 review=load(old.parent.parent/'local/review.plan.json');review.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(manifest),packed_parts_manifest_sha256=sha(manifest),expected_triangles=spec['expected']['triangles'],frozen_inputs=plan['frozen_inputs']);save(out/'fin-review.plan.json',review)
 save(out/'binding.validation.json',{'ok':True,'model_sha256':sha(model),'full_fin_inventory':list(plan['fins']),'all_root_bands_nonempty':all(r['rest_points_gltf']for r in plan['fins'].values()),'physical_checks_pending':True});print(json.dumps({'ok':True,'candidate':str(out),'fins':len(plan['fins'])}))
if __name__=='__main__':main()
