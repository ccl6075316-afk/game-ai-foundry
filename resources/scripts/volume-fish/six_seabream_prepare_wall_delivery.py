"""Prepare true seabream gates for a guarded seven-fin closing-wall UV delta."""
import copy,json,hashlib,sys,shutil,argparse
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--species',choices=['red_seabream','black_seabream'],default='red_seabream');S=p.parse_args().species
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;G=ROOT/'projects/fishing-2d';D=G/'experiments/six-fish-database-20261104'/S;OLD=G/('experiments/red-seabream-lowpoly-sop-20261101'if S=='red_seabream'else'experiments/black-seabream-lowpoly-sop-20261102');R=D/'fin-wall-r1';O=D/'wall-gates-r1'
sys.path[:0]=[str(HERE/'portable'),str(HERE)]
from glb_io import read_glb,arrays
from parts import freeze
from logical_document import logical_document
from six_database_prepare_gates import write_glb
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
ref=lambda p:{'path':str(Path(p).resolve()),'sha256':sha(p)}
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert not O.exists();O.mkdir()
model=R/'fish.glb';blend=R/'fish.blend';wall=R/'wall-uv.validation.json';proof=read(wall);assert proof['ok'] and proof['non_wall_UV_exact'] and proof['geometry_normals_weights_parts_rig_actions_exact']
oldmodel=G/f'game/assets/models/fish/{S}.glb';doc,blob=read_glb(model);od,ob=read_glb(oldmodel);pr=doc['meshes'][0]['primitives'][0];op=od['meshes'][0]['primitives'][0]
for k in ['POSITION','NORMAL','JOINTS_0','WEIGHTS_0']:
 assert np.array_equal(arrays(doc,blob,pr['attributes'][k]),arrays(od,ob,op['attributes'][k])),k
assert np.array_equal(arrays(doc,blob,pr['indices']),arrays(od,ob,op['indices']))
spec=read(D/'final-spec.json');spec.pop('production',None);spec['model']=ref(model);spec['inputs']['source_blend']=ref(blend);spec['inputs']['reference_glb']=ref(model);spec['inputs']['wall_uv_repair']=ref(wall);spec['authoring_delta']={'kind':'native_cap_alpha_matched_fin_wall_uv_repair','report':str(wall),'sha256':sha(wall)}
spec['viewer']['model_scale']=read(ROOT/spec['motion']['profile']['path'])['real_length_cm']/100/float(np.ptp(arrays(doc,blob,pr['attributes']['POSITION'])[:,0]))
for role in ['runtime','profile']:spec['motion'][role]=ref(spec['motion'][role]['path'])
write(O/'spec.json',spec);freeze(model,spec,O/'parts-manifest.json')
plan=read(OLD/('release-20261101/formal-fin-gate-r3.plan.json'if S=='red_seabream'else'release-20261102/fin-gate.plan.json'));p=plan['items'][0];assert p['model_sha256']==sha(oldmodel)
helper=HERE/'portable/PackedFishParts.gd';canon=HERE/'portable/parts.py';exporter=HERE/'portable/export_fin_poses.gd'
p.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(O/'parts-manifest.json'),packed_parts_manifest_sha256=sha(O/'parts-manifest.json'),packed_helper_script=str(helper),packed_canonicalizer=str(canon),motion_profile=spec['motion']['profile']['path'],motion_profile_sha256=spec['motion']['profile']['sha256'],motion_runtime=spec['motion']['runtime']['path'],motion_runtime_sha256=spec['motion']['runtime']['sha256'],controller_script=spec['motion']['runtime']['path'])
p['frozen_inputs']={str(x):sha(x)for x in [model,blend,wall,O/'spec.json',O/'parts-manifest.json',helper,canon,exporter,Path(p['motion_runtime']),Path(p['motion_profile']),Path(__file__)]}
p['scope']='Complete own-species root banks retained verbatim under exact geometry/weight/index/rig identity; wall UV only. New physical runs required.';write(O/'fin.plan.json',plan)
ld,lb,_=logical_document(model,p['body'],list(p['fins']),O/'parts-manifest.json');write_glb(O/'ordinary-reference.glb',ld,lb)
config=read(OLD/('release-20261101/formal-delivery-r3.config.json'if S=='red_seabream'else'release-20261102/delivery.config.json'));config.pop('production',None);config.update(game=str(G/'game'),final_spec=str(O/'spec.json'),fin_plan=str(O/'fin.plan.json'),ordinary_reference=str(O/'ordinary-reference.glb'),fin_pose_exporter=str(exporter),review_capture_script=str(HERE/'portable/capture_fish_review.gd'))
config['review_sources']=[str((ROOT/x).resolve())for x in config['review_sources']]+[str(wall),str(D/('wall-source-compatibility.validation.json'if S=='red_seabream'else'wall-alpha.validation.json'))]
write(O/'delivery-config.json',config)
from run_delivery_checks import prepare
local=D/'wall-local-r1';local.mkdir();prepare(O/'delivery-config.json',local)
print(json.dumps({'ok':True,'new_model_sha256':sha(model),'source_sha256':sha(blend),'output':str(O),'local_review_plan':str(local/'review.plan.json')}))
