"""Bind explicit authored full root bands to a portable model, without granting passes."""
import argparse,hashlib,json
from pathlib import Path
from fish_asset_spec import ROOT,load_spec,resolve_ref,artifact_output,require
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--root-plan',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--parts-manifest',type=Path,required=True);p.add_argument('--mesh-renames',type=Path,required=True);p.add_argument('--root-collar-mm',type=float,required=True);p.add_argument('--penetration-tolerance-mm',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
spec=load_spec(a.spec);model=resolve_ref(spec['model']);profile=resolve_ref(spec['motion']['profile']);runtime=resolve_ref(spec['motion']['runtime'])
authored=read(a.root_plan);require(len(authored['items'])==1,'One explicit authored species required');item=authored['items'][0]
require(item['species']==spec['species'],'Species mismatch')
require(sha(item['profile'])==item['profile_sha256'],'Stale authored geometry profile')
renames=read(a.mesh_renames)['mesh_node_renames']
item['fins']={renames.get(name,name):root for name,root in item['fins'].items()}
declared={part.get('logical_name',part['name'])for part in spec['parts']if part['role']=='fin'}
require(declared==set(item['fins']),'Every explicit anatomical fin must have its own full authored band')
manifest=read(a.parts_manifest);require(manifest['model_sha256']==sha(model),'Stale portable part manifest')
require(all(root['rest_points_gltf'] and root['source_baseline'] for root in item['fins'].values()),'No empty root bands')
require(0<=a.root_collar_mm<=1 and 0<=a.penetration_tolerance_mm<=.02,'Freeze bounded physical limits; do not weaken them')
out=artifact_output(a.output,[model,profile,runtime,a.root_plan,a.spec,a.parts_manifest,a.mesh_renames])
helper=Path(__file__).with_name('PackedFishParts.gd');canonicalizer=Path(__file__).with_name('parts.py')
item.update(model=str(model),model_sha256=sha(model),motion_profile=str(profile),motion_profile_sha256=sha(profile),motion_runtime=str(runtime),packed_parts_manifest=str(a.parts_manifest.resolve()),packed_parts_manifest_sha256=sha(a.parts_manifest),packed_helper_script=str(helper),packed_canonicalizer=str(canonicalizer),membrane_clearance={'root_collar_mm':a.root_collar_mm,'penetration_tolerance_mm':a.penetration_tolerance_mm},scope='Source full-band selection and actual portable part adapter. No prior physical passes transferred; same177/490 schedule and original collision kernels.')
dependencies=[model,profile,runtime,a.root_plan,a.spec,a.parts_manifest,a.mesh_renames,helper,canonicalizer,Path(__file__).with_name('export_fin_poses.gd')]
item['frozen_inputs']={str(x.resolve()):sha(x)for x in dependencies}
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'kind':'portable_authored_fin_validation_plan','items':[item]},indent=2)+'\n',encoding='utf8')
print(json.dumps({'ok':True,'output':str(out),'fins':len(item['fins'])}))
