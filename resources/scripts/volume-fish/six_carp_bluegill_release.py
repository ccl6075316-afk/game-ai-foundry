"""Install the two explicitly accepted static assets; retain compact provenance.

No shared table/loader/registry or Git mutations. Old reports stay byte-exact.
Canonical entry validation/final release SOP is a separate step.
"""
import copy,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];GAME=ROOT/'projects/fishing-2d'
OLD=GAME/'experiments/six-fish-database-20261104';RELEASE=GAME/'plans/reviews/six-fish-release-20261104'
sys.path[:0]=[str(Path(__file__).parent),str(Path(__file__).parent/'portable')]
from check_frozen_fish_static import fingerprint
from parts import freeze
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def ref(p):p=Path(p).resolve();return {'path':str(p),'sha256':sha(p)}

def main(s):
 old=OLD/s;release=RELEASE/s;source=GAME/f'assets/source/fish/{s}'
 assert not(release/'release-inputs.json').exists()
 ledger=read(old/'production-review.json');assert read(old/'root-sop.validation.json')['ok'];c=ledger['candidate_files'];facts=read(old/'current-evidence.validation.json')
 mapping=[];destinations={};seen_json=set()
 def retain(src,dst):
  src=Path(src).resolve();dst=dst.resolve();assert src.is_file()and dst.is_relative_to(GAME)
  if str(src)in destinations:return Path(destinations[str(src)])
  dst.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists():assert sha(dst)==sha(src),(src,dst)
  else:shutil.copy2(src,dst)
  assert sha(src)==sha(dst);destinations[str(src)]=str(dst);mapping.append({'old':str(src),'new':str(dst),'sha256':sha(dst),'bytes':dst.stat().st_size});return dst
 def history(src):
  src=Path(src).resolve()
  if src.is_relative_to(GAME):dst=release/'history'/src.relative_to(GAME)
  else:dst=release/'history'/'foundry'/src.relative_to(ROOT)
  return retain(src,dst)
 def numeric_tree(src):
  src=Path(src).resolve()
  if str(src)in seen_json:return
  seen_json.add(str(src));history(src)
  try:data=read(src)
  except (ValueError,UnicodeError):return
  def scan(v):
   if isinstance(v,dict):
    if isinstance(v.get('path'),str)and v.get('sha256'):
     p=Path(v['path']);p=p if p.is_absolute()else ROOT/p
     if p.is_file()and p.suffix=='.json'and p.resolve().is_relative_to(GAME):
      assert sha(p)==v['sha256'];numeric_tree(p)
    for x in v.values():scan(x)
   elif isinstance(v,list):
    for x in v:scan(x)
  scan(data)
 for k,v in c.items():assert sha(v['path'])==v['sha256'],k
 model=GAME/f'game/assets/models/fish/{s}.glb';previous=sha(model)if sha(model)!=c['model']['sha256']else None;shutil.copyfile(c['model']['path'],model);assert sha(model)==c['model']['sha256'];destinations[c['model']['path']]=str(model.resolve());mapping.append({'old':c['model']['path'],'new':str(model.resolve()),'sha256':sha(model),'bytes':model.stat().st_size})
 blend=retain(c['editable_source']['path'],source/'fish.blend');art=retain(c['source_image']['path'],source/'source.png');atlas=retain(c['atlas']['path'],source/'atlas.png')
 author=retain(c['material_author_model']['path'],release/'history/material-author-original.glb')
 role_paths={k:Path(v['path'])for k,v in c.items()}
 role_paths.update(model=model,editable_source=blend,source_image=art,atlas=atlas,material_author_model=author,final_entry=model)
 if 'editable_blend'in c:role_paths['editable_blend']=blend
 for k,name in [('source_projection','validation-source.blend'),('generated_skin_image','head-underside-generated.png'),('body_skin','body-source.png')]:
  if k in c:role_paths[k]=retain(c[k]['path'],source/name)
 for k in ['generated_skin_source_review','water_renderer','water_profile','water_shader']:
  if k in c:role_paths[k]=history(c[k]['path'])
 for name in ['production-review.json','current-evidence.validation.json','root-sop.validation.json','runtime-assets-manifest.json','operator-observations.json','HANDOFF.md','manifest.json','completion.validation.json','reference-comparison.validation.json','unity-reference-transform.validation.json']:
  if(old/name).is_file():history(old/name)
 evidence={}
 for eid,v in ledger['evidence'].items():
  p=Path(v['path']);assert sha(p)==v['sha256']
  target=retain(p,release/'evidence'/p.relative_to(old))if p.is_relative_to(old)else history(p)
  evidence[eid]={**ref(target),'kind':v['kind'],'observation':v.get('observation','')}
  if p.suffix=='.json':numeric_tree(p)
 for v in facts['actual_current_reports'].values():numeric_tree(v['path'])
 for k in ['historical_source_audit','historical_preparation','native_fin_masks','historical_complete_native_chart','historical_skin_source_review','head_reference_coverage','enumerated_XY_correction','source_cold_export','actual_capture','current_capture','fin_capture','native_lip_author_report','current_native_lip_preservation']:
  if k in facts:numeric_tree(facts[k]['path'])
 for v in facts.get('reference_evidence',{}).values():
  if Path(v['path']).suffix=='.json':numeric_tree(v['path'])
 gates=Path(c['final_spec']['path']).parent;delivery=Path(facts.get('actual_capture',facts.get('current_capture'))['path']).parent.parent
 for p in gates.glob('*.json'):numeric_tree(p)
 for name in ['manifest.json','body077/capture.validation.json','fin490/completion.validation.json','root072/completion.validation.json','negative-head.validation.json','review/review-capture.validation.json','review/movie-frames.validation.json']:
  if(delivery/name).is_file():numeric_tree(delivery/name)
 for folder in ['native-lips-r1','chin-bake-r1','chin-skin-r1','fin-volume-r6']:
  for p in (old/folder).glob('*.json'):numeric_tree(p)
  for p in (old/folder).glob('*.npz'):history(p)
 if s=='bluegill':
  history(old/'chin-skin-r1/skin.png');history(old/'chin-quilt.config.json')
  tail=read(GAME/'experiments/three-fish-fin-detail-20261031/bluegill/tail-root-skin-r2/author/tail-donors.validation.json')
  retain(tail['baseline'],release/'history/negative-fin-original.glb')
  mouth=read(old/'mouth-opening-r6.validation.json');bad=mouth['results']['rejected'];retain(bad['source_blend'],release/'history/negative-mouth-source.blend')
  history(ROOT/'resources/volume-fish/bluegill-mouth-source-boundaries-20261031.json')
 else:
  negative=GAME/'experiments/carp-lowpoly-sop-20261031/fin-cages-r1/fish.blend';assert sha(negative)==read(old/'fin-volume-current-profile.validation.json')['rejected_original']['blend_sha256'];retain(negative,release/'history/negative-fin-source.blend')
  mouth=read(old/'mouth-opening-r4.validation.json');bad=mouth['results']['rejected'];retain(bad['source_blend'],release/'history/negative-mouth-source.blend')
  history(ROOT/'resources/volume-fish/carp-sop-front-material-r5-20261031.json')
 for p in [delivery/'negative-narrow-head.glb']:
  if p.exists():history(p)
 # Keep only numeric correction parameters; final arrays live in accepted source.
 parameters=[]
 for p in sorted(old.glob('width-*/deformation.plan.json')):
  value=read(p);small={k:v for k,v in value.items()if k not in ['old_positions_gltf','new_positions_gltf','new_normals_gltf']};parameters.append({'original_path':str(p),'original_plan_sha256':sha(p),'parameters':small})
 write(release/'parameters.json',{'species':s,'corrections':parameters,'scope':'Actual own-species parameters and rejected alternatives; full accepted static arrays retained in canonical GLB/editable source, not repeated dense plans.'})
 freeze_file=source/'frozen-static.json';write(freeze_file,{'kind':'accepted_fish_static_freeze','static':fingerprint(model),'future_scope':'Motion/controller/animation only by default. Static geometry, complete fins, UV/pixels, skin and skeleton/rest data require explicit user reopening.'})
 spec=copy.deepcopy(read(c['final_spec']['path']));spec.pop('production',None);spec['model']=ref(model);spec['inputs'].update(source_blend=ref(blend),reference_glb=ref(model),atlas=ref(atlas),packing_report=ref(history(spec['inputs']['packing_report']['path'])));write(release/'spec.json',spec)
 parts=release/'parts-manifest.json';staging=ROOT/f'output/six-fish-release-20261104/carp-bluegill/{s}/parts-manifest.json'
 if not staging.exists():freeze(model,spec,staging)
 assert read(staging)==freeze(model,spec);retain(staging,parts)
 plan=read(c['root_plan']['path']);item=plan['items'][0];motion=Path(c['motion_config']['path']);runtime=Path(c['motion_runtime']['path']);item.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(parts),packed_parts_manifest_sha256=sha(parts),frozen_inputs={str(p.resolve()):sha(p)for p in [model,blend,atlas,parts,motion,runtime]});write(release/'recheck-fin.plan.json',plan)
 entry=read(delivery/'review.plan.json');entry.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(parts),packed_parts_manifest_sha256=sha(parts),frozen_inputs={str(p.resolve()):sha(p)for p in [model,parts,motion,runtime]},review_sources=[]);write(release/'entry.plan.json',entry)
 runtime_manifest=release/'runtime-assets-manifest.json';write(runtime_manifest,{'species':s,'status':'running','next_action':'verify_canonical_entry','user_acceptance':True,'installed':True,'model':ref(model),'editable_source':ref(blend),'static_freeze':ref(freeze_file)})
 metadata=ROOT/f'resources/volume-fish/{s}-final-20261104.json';write(metadata,{'species':s,'real_length_cm':read(c['species_profile']['path'])['real_length_cm'],'accepted_model':ref(model),'accepted_source':ref(blend),'accepted_model_sha256':sha(model),'accepted_source_sha256':sha(blend),'appearance_and_rig_frozen':True,'future_scope':'Default motion/controller/animation only; explicit user reopening needed for static geometry, complete fins, UV/material, skin and skeleton/rest changes.','user_acceptance':{'date':'2026-11-04','instruction_summary':'User explicitly accepts all six current database revisions as finished fish, authorizes canonical installation, retirement of old experiments and commit+push.','scope':'Whole current appearance; third-party game art remains artistic reference, not biological measurement.'},'shape_profile':c['species_profile'],'parameters':ref(release/'parameters.json'),'static_freeze':ref(freeze_file),'release_handoff':str(release/'HANDOFF.md')})
 role_paths.update(final_spec=release/'spec.json',root_plan=release/'recheck-fin.plan.json',runtime_manifest=runtime_manifest,static_freeze=freeze_file,release_metadata=metadata)
 # Original delivery config is historical and remains a receipt, not a rerun plan.
 role_paths['delivery_config']=history(c['delivery_config']['path'])
 write(release/'release-inputs.json',{'species':s,'roles':{k:ref(v)for k,v in role_paths.items()},'old_ledger':ref(history(old/'production-review.json')),'evidence':evidence,'previous_installed_sha256':previous,'source_shape_unchanged':True,'technical_report_reuse':'Reviewed GLB and source migrated byte-exact. Existing physical reports retain original bytes/path/SHA meanings; fresh canonical/cache/direct/source checks are separate.','user_acceptance':True,'static_frozen':True})
 write(release/'retention-manifest.json',{'kind':'byte_exact_retained_evidence_and_source_migration','species':s,'files':mapping,'historical_paths':'Immutable old reports retain original internal paths and source hashes. Map locates retained identical bytes. Retired intermediate binaries are intentionally not reconstructed or falsely marked current.','new_archive_created':False})
 write(release/'manifest.json',{'species':s,'status':'running','next_action':'canonical_source_export_and_entry_check','user_acceptance':True,'installed':True,'static_frozen':True,'model':ref(model),'source':ref(blend),'metadata':ref(metadata),'retention':ref(release/'retention-manifest.json')})
 print(json.dumps({'ok':True,'species':s,'retained_files':len(mapping),'model':ref(model),'source':ref(blend)}))

if __name__=='__main__':
 for species in ['carp','bluegill']:main(species)
