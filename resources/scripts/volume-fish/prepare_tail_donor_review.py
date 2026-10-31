"""Bind every revised fin root and actual body/tail review camera to cold output."""
import argparse,copy,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import sha
from parts import freeze
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();out=a.candidate.resolve();report=load(out/'author/tail-donors.validation.json');base=Path(report['baseline']).parent.parent;spec=load(out/'source-run/final-spec.json');model=out/'source-run/fish.glb';manifest=out/'parts-manifest.json';freeze(model,spec,manifest);plan=load(base/'fin.plan.json');row=plan['items'][0];row.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(manifest),packed_parts_manifest_sha256=sha(manifest));records={r['name']:r for r in report['records']if 'root_rest_points_gltf'in r}
 assert set(row['fins'])==set(records)
 for name,fin in row['fins'].items():fin.update(ids=records[name]['root_ids'],rest_points_gltf=records[name]['root_rest_points_gltf'],rule='Complete original basal domains carried through current membrane/tail repair; complete actual tail section knots added. No contact-driven narrowing.')
 deps=[model,manifest,out/'source-run/final-spec.json',out/'author/tail-donors.validation.json',HERE/'portable/PackedFishParts.gd',HERE/'portable/parts.py',HERE/'portable/export_fin_poses.gd'];row['frozen_inputs']={str(p):sha(p)for p in deps};save(out/'fin.plan.json',plan)
 review=load(base/'fin-review.plan.json');review.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(manifest),packed_parts_manifest_sha256=sha(manifest),expected_triangles=spec['expected']['triangles'],frozen_inputs=row['frozen_inputs']);lo=report['body_tail_interval_native'][0];scale=review['model_scale'];review['details'].append({'name':'tail-junction','size':review['whole_camera_size']*.36,'at':[lo*scale,0,0]});save(out/'fin-review.plan.json',review)
 capture=load(base/'capture.plan.json');capture.update(models={'before':str(Path(report['baseline'])),'after':str(model)});capture['bindings']={k:v for k,v in capture['bindings'].items()if not k.endswith('.glb')};capture['bindings'].update({p:sha(p)for p in capture['models'].values()});save(out/'capture.plan.json',capture);print(json.dumps({'ok':True,'candidate':str(out),'fins':len(records)}))
if __name__=='__main__':main()
