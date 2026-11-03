"""Install two user-accepted fish and retain only explicit release inputs/evidence."""
import argparse,copy,json,hashlib,shutil,sys,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb
from parts import freeze
from check_frozen_fish_static import fingerprint
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();ref=lambda p:{'path':str(Path(p).resolve()),'sha256':sha(p)}
def write(p,d):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main(s):
 assert s in ['crucian','grass_carp'];old=G/f'experiments/six-fish-database-20261104/{s}';R=G/f'plans/reviews/six-fish-release-20261104/{s}';source=G/f'assets/source/fish/{s}';assert not (R/'release-inputs.json').exists();R.mkdir(parents=True,exist_ok=True);source.mkdir(parents=True,exist_ok=True);mapping=[]
 def retain(src,dst):
  src=Path(src).resolve();dst=Path(dst).resolve();assert src.is_file()and dst.is_relative_to(G);dst.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists():assert sha(src)==sha(dst),str(dst)
  else:shutil.copy2(src,dst)
  row={'old':str(src),'new':str(dst),'sha256':sha(dst),'bytes':dst.stat().st_size}
  if row not in mapping:mapping.append(row)
  return dst
 m=read(old/'manifest.json');prior=read(old/'production-review.json');assert read(old/'sop.validation.json')['ok'];c=prior['candidate_files'];g=Path(c['final_spec']['path']).parent;delivery=Path(m['delivery_manifest']['path']).parent;rev=6 if s=='crucian' else 7
 for row in c.values():assert sha(row['path'])==row['sha256']
 canonical=G/f'game/assets/models/fish/{s}.glb';previous=sha(canonical);shutil.copyfile(c['model']['path'],canonical);assert sha(canonical)==c['model']['sha256'];mapping.append({'old':c['model']['path'],'new':str(canonical.resolve()),'sha256':sha(canonical),'bytes':canonical.stat().st_size})
 blend=retain(c['editable_source']['path'],source/'fish.blend');art=retain(c['source_image']['path'],source/'source.png');atlas=retain(c['atlas']['path'],source/'atlas.png');author=retain(c['material_author_model']['path'],source/'material-author-native-lips.glb');profile=ROOT/f'resources/volume-fish/database-revision-20261104/{s}.profile.json';assert sha(profile)==c['species_profile']['sha256']
 # Original complete native donor input, without keeping another whole fish.
 d,b=read_glb(old/'width-r1/fish.glb');iv=d['bufferViews'][d['images'][0]['bufferView']];baseline_atlas=source/'source-atlas-before-native.png';baseline_atlas.write_bytes(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']]);write(source/'source-atlas-provenance.json',{'kind':'exact_original_packed_image_payload','original_model_sha256':sha(old/'width-r1/fish.glb'),'original_model_path':str(old/'width-r1/fish.glb'),'embedded_image_sha256':sha(baseline_atlas),'scope':'Exact original pre-native embedded PNG retained; original body positions/UV equal current body. No duplicate historical whole-fish material input required.'})
 retain(old/'production-review.json',R/'history/reviewed-production-review.json');retain(old/'sop.validation.json',R/'history/reviewed-sop.validation.json');retain(old/'HANDOFF.md',R/'history/authoring-HANDOFF.md');retain(old/'manifest.json',R/'history/reviewed-manifest.json');retain(old/f'observations-r{rev}.json',R/'operator-observations.json');retain(old/'runtime-assets-manifest.json',R/'history/reviewed-runtime-manifest.json');retain(c['final_spec']['path'],R/'history/reviewed-spec.json')
 byold={};evidence={}
 for eid,row in prior['evidence'].items():
  p=Path(row['path']).resolve();assert sha(p)==row['sha256']
  if str(p)not in byold:byold[str(p)]=retain(p,R/'evidence'/p.relative_to(old))
  evidence[eid]={**ref(byold[str(p)]),'kind':row['kind'],'observation':row.get('observation','')}
 # Entire numeric physical evidence, exact original bytes, with no dense poses.
 for p in [old/'revision-invariants.validation.json',old/'database-preflight.validation.json',old/'library-hierarchy.validation.json',g/'root-domain-preservation.validation.json',g/'head-reference-coverage.validation.json',g/'packing-continuity.validation.json',g/'mouth-opening-raw.validation.json',g/'mouth-opening.validation.json',g/'lip-preservation.validation.json',g/'fin.plan.json',g/'native-loop.validation.json',g/'head-envelope.profile.json',delivery/'manifest.json',delivery/'fin490/completion.validation.json',delivery/'root072/completion.validation.json',delivery/'head.validation.json',delivery/'negative-head.validation.json',delivery/'import.validation.json',delivery/'motion.validation.json',delivery/'body077/completion.validation.json',delivery/'body077/capture.validation.json',delivery/'review/review-capture.validation.json',delivery/'cache-cleanup.validation.json',old/'cleanup-summary.validation.json',old/'retired-cache-cleanup.validation.json']:
  if p.is_file():retain(p,R/'history'/p.relative_to(old))
 vol=read(g/'fin-volume.validation.json')
 for role in ['source_correspondence','rejected_original','raw_measurement']:
  p=Path(vol[role]['path']);retain(p,R/'history'/p.relative_to(old))
 for p in (old/'native-lips-r3').glob('*.json'):retain(p,source/'native-lips'/p.name)
 chin='chin-bake-r3'if s=='crucian'else'chin-bake-r1';skin='chin-skin-r3'if s=='crucian'else'chin-skin-r1'
 for dirname,names in [(chin,['material.validation.json','actual-chin-donors.npz']),(skin,['skin.png','material.validation.json','native-donors.npz'])]:
  for name in names:retain(old/dirname/name,source/'chin-material'/dirname/name)
 cfg=ROOT/f'resources/volume-fish/{s.replace("_","-")}-central-material-20261031.json';retain(cfg,R/'references/mouth-boundaries-original.json')
 for p in (old/'source-cutouts').glob('*.png'):retain(p,source/'fin-cutouts'/p.name)
 meta=read(old/'database-preflight.validation.json');base=Path(meta['baseline']['candidate_directory']);tail=read(base/'author/tail-donors.validation.json');earlier=Path(tail['baseline']).parent.parent;auth=read(earlier/'author/author.validation.json');retain(base/'author/packing.validation.json',R/'references/original-packing.validation.json');retain(earlier.parent/'audit/audit.validation.json',R/'references/original-fin-source-audit.validation.json');retain(auth['input_masks']['path'],R/'references/original-native-masks.validation.json')
 mouth=read(g/'mouth-opening-raw.validation.json')['results']['rejected'];retain(mouth['source_blend'],R/'negatives/original-mouth.blend');retain(tail['baseline'],R/'negatives/original-constant-fin.glb');retain(delivery/'negative-narrow-head.glb',R/'negatives/narrow-head.glb')
 if s=='crucian':
  retain(old/'width-r5/fish.glb',R/'negatives/original-buried-dorsal-fold.glb');retain(old/'packed-volume-r5b/raw.validation.json',R/'negatives/dorsal-fold-measurement.validation.json');retain(old/'width-r6/xy-authoring.validation.json',R/'parameters/dorsal-XY-repair.validation.json')
 else:
  retain(old/'width-r1/fish.glb',R/'negatives/original-pectoral-gap.glb')
  for v in [1,2,3]:
   for n in ['roots','membranes']:retain(old/f'delivery-r{v}/fin490/{s}/{n}.validation.json',R/f'negatives/pectoral-r{v}-{n}.validation.json')
 # Scalar authoring records and explicit final arrays are retained, no old worktrees.
 params={'species':s,'corrections':[],'scope':'All actual scalar/source/failure parameters; full current static arrays live in canonical blend/GLB. Historical paths denote retired authoring locations.'}
 for p in sorted(old.glob('width-*/deformation.plan.json')):
  value=read(p);small={k:v for k,v in value.items()if k not in ['old_positions_gltf','new_positions_gltf','new_normals_gltf']};params['corrections'].append({'old_path':str(p),'sha256':sha(p),'parameters':small})
 write(R/'parameters.json',params)
 for version in range(1,rev+1):
  for name in ['source-authoring.validation.json','geometry-authoring.validation.json','combined-authoring.validation.json']:
   p=old/f'width-r{version}'/name
   if p.exists():retain(p,R/'history'/p.relative_to(old))
 # Root/SOP's source art and original accepted cutout scope remain explicit.
 original_manifest=G/'experiments/three-fish-fin-detail-20261031/manifest.json';entry=next(x for x in read(original_manifest)['species']if x['species']==s);write(R/'references/original-local-acceptance.json',{'original_manifest_sha256':sha(original_manifest),'original_species_record':entry,'scope':'Original local fin/tail acceptance only. Whole current appearance explicitly accepted separately2026-11-04.'})
 frozen=source/'frozen-static.json';write(frozen,{'kind':'accepted_fish_static_freeze','static':fingerprint(canonical),'future_scope':'Motion/controller/animation only by default. Explicit user reopening required for geometry, complete fins, UV/pixels, skin or skeleton/rest changes.'})
 spec=copy.deepcopy(read(c['final_spec']['path']));spec.pop('production',None);spec['model']=ref(canonical);spec['inputs']={k:ref(p)for k,p in [('source_blend',blend),('reference_glb',canonical),('atlas',atlas),('packing_report',R/'history'/g.relative_to(old)/'packing-continuity.validation.json')]};write(R/'spec.json',spec);parts=R/'parts-manifest.json';staging=ROOT/f'output/six-cyprinid-release-20261104/{s}/parts-manifest.json'
 if not staging.exists():freeze(canonical,spec,staging)
 retain(staging,parts)
 fp=read(g/'fin.plan.json');item=fp['items'][0];item.update(model=str(canonical),model_sha256=sha(canonical),packed_parts_manifest=str(parts),packed_parts_manifest_sha256=sha(parts));motion=Path(c['motion_config']['path']);runtime=Path(c['motion_runtime']['path']);item['frozen_inputs']={str(p):sha(p)for p in [canonical,blend,atlas,parts,motion,runtime]};write(R/'recheck-fin.plan.json',fp)
 ep=read(delivery/'review.plan.json');ep.update(model=str(canonical),model_sha256=sha(canonical),packed_parts_manifest=str(parts),packed_parts_manifest_sha256=sha(parts),frozen_inputs={str(p):sha(p)for p in [canonical,parts,motion,runtime]},review_sources=[]);write(R/'entry.plan.json',ep)
 runtime_manifest=R/'runtime-assets-manifest.json';write(runtime_manifest,{'species':s,'status':'running','next_action':'canonical_source_export_and_entry_verification','installed':True,'user_acceptance':True,'model':ref(canonical),'editable_source':ref(blend),'static_freeze':ref(frozen)})
 metadata=ROOT/f'resources/volume-fish/{s.replace("_","-")}-final-20261104.json';write(metadata,{'species':s,'real_length_cm':read(profile)['real_length_cm'],'accepted_model':ref(canonical),'accepted_source':ref(blend),'accepted_model_sha256':sha(canonical),'accepted_source_sha256':sha(blend),'appearance_and_rig_frozen':True,'future_scope':'Motion only by default; all static geometry/complete fins/UV/material/skin/skeleton rest data frozen unless explicitly reopened by user.','user_acceptance':{'date':'2026-11-04','scope':'User explicitly accepted all current six fish as finished assets, authorized installation, retirement of related experiments, commit and push. No biological measurement claim.','authorization':'Explicit user authorization communicated by root for this release; exact user wording maintained in root batch handoff.'},'shape_profile':ref(profile),'parameters':ref(R/'parameters.json'),'static_freeze':ref(frozen),'reference':ref(R/'history/database-preflight.validation.json'),'release_handoff':str(R/'HANDOFF.md')})
 roles={**c,'source_image':ref(art),'model':ref(canonical),'species_profile':ref(profile),'editable_source':ref(blend),'editable_blend':ref(blend),'atlas':ref(atlas),'material_author_model':ref(author),'final_entry':ref(canonical),'runtime_manifest':ref(runtime_manifest),'final_spec':ref(R/'spec.json'),'root_plan':ref(R/'recheck-fin.plan.json'),'static_freeze':ref(frozen),'release_metadata':ref(metadata)};roles.pop('delivery_config',None)
 # No current role may continue pointing at the retired experimental tree.
 assert not any('/experiments/'in v['path'].replace('\\','/')for v in roles.values())
 write(R/'release-inputs.json',{'species':s,'roles':roles,'evidence':evidence,'old_ledger':ref(R/'history/reviewed-production-review.json'),'previous_installed_sha256':previous,'accepted_model_sha256':sha(canonical),'accepted_source_sha256':sha(blend),'history_contract':ref(R/'evidence'/Path(prior['evidence']['fins.actual_normal_thickness_and_tail_section']['path']).relative_to(old)),'technical_report_reuse':'Same model/source/profile/native runtime/motion bytes, original physical reports copied byte-exact. No old pass attached to relocated plan SHA; fresh canonical/source/cache checks required.'})
 write(R/'retention-manifest.json',{'kind':'explicit_byte_exact_release_retention_mapping','species':s,'files':mapping,'scope':'Only listed current sources, actual original donors, unique negatives, complete numeric evidence and SOP representative images/video retained. Old report internal paths are historical, not current dependencies.'})
 targets=[G/f'experiments/{s.replace("_","-")}-portable-trial-20261030',G/f'experiments/{s.replace("_","-")}-static-merge',G/f'experiments/three-fish-fin-detail-20261031/{s}',G/f'experiments/four-fish-width-trial-20261031/{s}',old,G/f'experiments/blender-fish/models/{s}']
 if s=='crucian':targets.append(G/'experiments/crucian-head-review-20261031')
 write(R/'cleanup-plan.json',{'species':s,'state':'planned_not_deleted','target_roots':[str(p.resolve())for p in targets if p.exists()],'estimated_bytes':sum(x.stat().st_size for p in targets if p.exists()for x in p.rglob('*')if x.is_file()),'retention_manifest':ref(R/'retention-manifest.json'),'precondition':'Current source/GLB accepted exact bytes, unique donors/negative/evidence migrated; fresh canonical/SOP finalization must pass before deleting. Shared three-fish/four-fish siblings untouched. Check outside current references before per-file SHA deletion.'})
 write(R/'manifest.json',{'species':s,'status':'running','next_action':'canonical_source_export_and_entry_verification','installed':True,'user_acceptance':True,'appearance_and_rig_frozen':True,'model':ref(canonical),'source':ref(blend),'metadata':ref(metadata),'spec':ref(R/'spec.json'),'retention':ref(R/'retention-manifest.json'),'cleanup_plan':ref(R/'cleanup-plan.json')});print(json.dumps({'ok':True,'species':s,'canonical':str(canonical),'model_sha256':sha(canonical),'source_sha256':sha(blend),'retained_files':len(mapping),'planned_delete_bytes':read(R/'cleanup-plan.json')['estimated_bytes']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--species',required=True);main(p.parse_args().species)
