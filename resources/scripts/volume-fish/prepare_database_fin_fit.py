"""Prepare an explicitly measured whole-fin translation; retains original domains."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE/'portable')]
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__)
for k in ['model','failure','output']:p.add_argument('--'+k,type=Path,required=True)
p.add_argument('--part',required=True);p.add_argument('--offset-mm',type=float,required=True);p.add_argument('--model-scale',type=float,required=True);a=p.parse_args();m=a.model.resolve();out=a.output.resolve();assert not out.exists() and out.is_relative_to(ROOT/'projects/fishing-2d/experiments/five-fish-database-20261103');report=json.loads(a.failure.read_text());assert not report['ok'] and report['model_sha256']==sha(m)
d,b=read_glb(m);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);n=arrays(d,b,pr['attributes']['NORMAL']);new=v.copy();part=next(x for x in d['extras']['geometry_parts'] if x['name']==a.part and x['role']=='fin');new[part['vertex_start']:part['vertex_start']+part['vertex_count'],2]+=a.offset_mm/(1000*a.model_scale)
plan={'kind':'single_fish_transverse_width_trial','stage':'measured_whole_fin_fit','species':m.parent.parent.name,'inputs':{k:{'path':str(q),'sha256':sha(q)}for k,q in [('model',m),('blend',m.with_suffix('.blend')),('failure',a.failure.resolve())]},'old_positions_gltf':v.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':n.tolist(),'fit':{'part':a.part,'gltf_Z_offset_mm':a.offset_mm,'model_scale':a.model_scale,'original_root_domain_and_thresholds_unchanged':True},'formal_acceptance':False};out.mkdir();(out/'deformation.plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'ok':True,'plan':str(out/'deformation.plan.json')}))
