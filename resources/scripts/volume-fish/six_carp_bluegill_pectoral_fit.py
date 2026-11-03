"""Author the measured static minimax inward translation, keeping complete root domains."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
base=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/bluegill';old=base/'width-r2';out=base/'width-r3';out.mkdir();d,b=read_glb(old/'fish.glb');p=d['meshes'][0]['primitives'][0];v=arrays(d,b,p['attributes']['POSITION']);n=arrays(d,b,p['attributes']['NORMAL']);new=v.copy();spec=json.loads((base/'gates-r2/spec.json').read_text());scale=spec['viewer']['model_scale'];shift=.0011/scale
for part in d['extras']['geometry_parts']:
 if part['role']=='fin' and part['logical_name']in ['Pectoral_left_mesh','Pectoral_right_mesh']:
  ids=np.arange(part['vertex_start'],part['vertex_start']+part['vertex_count']);sign=np.sign(v[ids,2].mean());new[ids,2]-=sign*shift
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs={'model':old/'fish.glb','blend':old/'fish.blend','finite_static_probe':base/'pectoral-static-fit-probe.validation.json','failed_full_roots':base/'delivery-r2/fin490/bluegill/roots.validation.json'};plan={'kind':'single_fish_transverse_width_trial','stage':'measured_bilateral_pectoral_fit_r3','species':'bluegill','inputs':{k:{'path':str(p),'sha256':sha(p)}for k,p in inputs.items()},'scope':'Both complete pectorals translated1.1mm inward along transverse axis, selected by actual posed static-body BVH and previous490 extrema; original complete root domains/tolerances retained. Actual new490 required. No other static data changed.','fit_mm':1.1,'old_positions_gltf':v.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':n.tolist(),'formal_acceptance':False};(out/'deformation.plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8')
