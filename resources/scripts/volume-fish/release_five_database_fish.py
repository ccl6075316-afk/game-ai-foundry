"""Promote the explicitly user-accepted five fish, preserving report provenance.

Historical technical reports are copied byte-exact, never relabelled as reruns.
Fresh source export and actual canonical/cache checks are separate release steps.
"""
import copy,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];GAME=ROOT/'projects/fishing-2d';OLD=GAME/'experiments/five-fish-database-20261103';RELEASE=GAME/'plans/reviews/five-fish-release-20261104'
sys.path[:0]=[str(Path(__file__).parent),str(Path(__file__).parent/'portable')]
from check_frozen_fish_static import fingerprint
from parts import freeze
NAMES={'rainbow_trout':'虹鳟','brown_trout':'褐鳟','atlantic_salmon':'大西洋鲑','sea_bass':'海鲈','red_emperor':'红皇帝鱼'}
QUOTE='非常好，完美，把它们直接归类到跟罗飞鱼一样，就是彻底把它定下来。然后如果你还没有完成表B导出，呃GiaoB导出的话，把它们也导出来，替换游戏里的角色。它们其他一些跟这几条鱼有关的一些实验都可以去掉了，这个就可以作为成品了。然后把它提交上去就行了。'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def ref(p):p=Path(p).resolve();return {'path':str(p),'sha256':sha(p)}
def main():
 assert not RELEASE.exists() or '--resume' in sys.argv
 RELEASE.mkdir(parents=True,exist_ok=True);mapping=[];rows=[]
 def retain(src,dst):
  src=Path(src).resolve();dst=dst.resolve();assert src.is_file() and dst.is_relative_to(GAME)
  dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists():shutil.copy2(src,dst)
  assert sha(src)==sha(dst);mapping.append({'old':str(src),'new':str(dst),'sha256':sha(dst),'bytes':dst.stat().st_size});return dst
 tablepath=GAME/'game/assets/models/fish/motion/width20261101/manifest.json';previous_table=RELEASE/'history/previous-runtime-table.json'
 if not previous_table.exists():retain(tablepath,previous_table)
 table=read(previous_table)
 for s,label in NAMES.items():
  old=OLD/s;ledger=read(old/'production-review.json');assert read(old/'sop-after-final-cleanup.validation.json')['ok'];c=ledger['candidate_files'];release=RELEASE/s;source=GAME/f'assets/source/fish/{s}';source.mkdir(parents=True,exist_ok=True)
  for key in ['model','editable_source','source_image','atlas','source_projection','material_author_model']:assert sha(c[key]['path'])==c[key]['sha256']
  model=GAME/f'game/assets/models/fish/{s}.glb';oldsha=table['profiles'][s]['model_sha256'];assert sha(model) in [oldsha,c['model']['sha256']];shutil.copyfile(c['model']['path'],model);assert sha(model)==c['model']['sha256'];mapping.append({'old':c['model']['path'],'new':str(model),'sha256':sha(model),'bytes':model.stat().st_size})
  blend=retain(c['editable_source']['path'],source/'fish.blend');art=retain(c['source_image']['path'],source/'source.png');atlas=retain(c['atlas']['path'],source/'atlas.png');projection=retain(c['source_projection']['path'],source/'validation-source.blend');author=retain(c['material_author_model']['path'],release/'history/material-author-original.glb')
  oldspec=read(c['final_spec']['path']);retain(c['final_spec']['path'],release/'history/reviewed-spec.json');retain(old/'production-review.json',release/'history/reviewed-production-review.json');retain(old/'operator-observations.json',release/'operator-observations.json');retain(old/'HANDOFF.md',release/'history/authoring-HANDOFF.md');retain(old/'runtime-assets-manifest.json',release/'history/reviewed-runtime-manifest.json')
  # Preserve the exact reports and images used by the operator ledger. Multiple
  # criteria sharing the same file share one retained copy.
  evidence={};by_old={}
  for eid,record in ledger['evidence'].items():
   src=Path(record['path']).resolve();assert sha(src)==record['sha256']
   if str(src)not in by_old:
    if src.is_relative_to(old):dest=release/'evidence'/src.relative_to(old)
    else:dest=release/'history'/(src.parent.name+'-'+src.name)
    by_old[str(src)]=retain(src,dest)
   evidence[eid]=ref(by_old[str(src)])|{'kind':record['kind'],'observation':record.get('observation','')}
  facts=read(old/'current-evidence.validation.json');delivery=Path(facts['actual_capture']['path']).parent.parent;gates=Path(c['final_spec']['path']).parent
  # Complete numerical receipts and original input domains remain immutable.
  for p in [old/'revision-invariants.validation.json',old/'native-loop.validation.json',old/'sop-after-final-cleanup.validation.json',gates/'root-domain-preservation.validation.json',gates/'head-reference-coverage.validation.json',gates/'volume.config.json',gates/'volume.validation.json',gates/'volume-source.validation.json',gates/'mouth-opening.validation.json',gates/'fin.plan.json',delivery/'fin490/completion.validation.json',delivery/'root072/completion.validation.json',delivery/'head.validation.json',delivery/'negative-head.validation.json',delivery/'import.validation.json',delivery/'motion.validation.json',delivery/'body077/completion.validation.json',delivery/'body077/capture.validation.json',Path(c['editable_source']['path']).parent/'cold-export.validation.json']:
   if p.exists():retain(p,release/'history'/p.relative_to(old))
  for pattern in ['width-*/source-authoring.validation.json','width-*/skin-*.validation.json','width-*/xy-*.validation.json','gates-*/volume.validation.json','delivery-*/fin490/*/membranes.validation.json','*donor*/material.validation.json','ventral-bake-*/material.validation.json','ventral-*.json','skin-fit/fit.validation.json','skin-fit/bindings.validation.json']:
   for p in old.glob(pattern):
    if p.is_file():retain(p,release/'history'/p.relative_to(old))
  for p in [old/'current-visual-review.jpg',old/'source-final-side-comparison.jpg',old/'motion-review.jpg',old/'unlit-review/after-whole-left-texture.png',old/'unlit-review/after-whole-right-texture.png',old/'unlit-review/after-head-bottom-texture.png',old/'ventral-native-roi.png']:
   if p.exists():retain(p,release/'evidence'/p.relative_to(old))
  generated=GAME/f'experiments/{s.replace("_","-")}-portable-trial-20261031/body-generated.png';retain(generated,source/'body-generated.png')
  for p in old.glob('ventral-donor*/native-donors.npz'):retain(p,release/'history'/p.relative_to(old))
  # Keep all scalar parameters/corrections, not repeated dense vertex arrays.
  params={'species':s,'width':{},'corrections':[],'scope':'Actual authoring values and rejected alternatives; full final static arrays live in current GLB/blend. Historical failure reports keep original hashes, not new passes.'}
  for p in sorted(old.glob('*/deformation.plan.json')):
   value=read(p);small={k:v for k,v in value.items()if k not in ['old_positions_gltf','new_positions_gltf','new_normals_gltf']};params['corrections'].append({'original_plan_sha256':sha(p),'original_path':str(p),'parameters':small})
  params['width']=params['corrections'][0] if params['corrections'] else {};write(release/'parameters.json',params)
  preflight=ROOT/'output/five-fish-database-20261103/body-preflight'
  for name in [s+'.validation.json',s+'-transform.validation.json']:retain(preflight/name,release/'references'/name)
  accepted_old=ROOT/f'output/five-fish-database-20261103/restored/{s}/accepted-head-envelope.profile.json'
  if accepted_old.exists():retain(accepted_old,release/'references/previous-accepted-head-envelope.profile.json')
  oldprofile=Path(c['species_profile']['path']);metadata=ROOT/f'resources/volume-fish/{s.replace("_","-")}-final-20261104.json';freeze_file=source/'frozen-static.json';write(freeze_file,{'kind':'accepted_fish_static_freeze','static':fingerprint(model),'future_scope':'Motion/controller/animation only by default. Explicit user reopening required for geometry/UV/material/skin/skeleton changes.'})
  write(metadata,{'species':s,'scientific_name':oldspec.get('scientific_name',read(oldprofile).get('scientific_name')),'real_length_cm':table['profiles'][s]['real_length_cm'],'accepted_model':ref(model),'accepted_source':ref(blend),'accepted_model_sha256':sha(model),'accepted_source_sha256':sha(blend),'appearance_and_rig_frozen':True,'future_scope':'Motion/controller/animation only by default; preserve all static geometry, complete fins, UV/pixels, weights and skeleton/rest data unless user explicitly reopens.','user_acceptance':{'date':'2026-11-04','quote':QUOTE,'scope':'Whole current five-fish preview accepted as finished assets, authorized installation, cleanup, commit and push. Not biological measurement.'},'shape_profile':ref(oldprofile),'parameters':ref(release/'parameters.json'),'static_freeze':ref(freeze_file),'reference':ref(release/'references'/f'{s}.validation.json'),'release_handoff':str(RELEASE/'HANDOFF.md')})
  spec=copy.deepcopy(oldspec);spec.pop('production',None);spec['model']=ref(model);spec['inputs']={k:ref(p)for k,p in [('source_blend',blend),('reference_glb',model),('atlas',atlas)]};write(release/'spec.json',spec);parts=release/'parts-manifest.json';staging=ROOT/f'output/five-fish-release-20261104/staging/{s}/parts-manifest.json'
  if not staging.exists():freeze(model,spec,staging)
  assert read(staging)['model_sha256']==sha(model);retain(staging,parts)
  # This is a new repeat-check plan only. No old technical pass is attributed to
  # its new path hash; immutable reports are reused solely by byte/pose identity.
  fp=read(gates/'fin.plan.json');item=fp['items'][0];item.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(parts),packed_parts_manifest_sha256=sha(parts));motion=ROOT/spec['motion']['profile']['path'];runtime=ROOT/spec['motion']['runtime']['path'];item['frozen_inputs']={str(p):sha(p)for p in [model,blend,atlas,parts,motion,runtime]};write(release/'recheck-fin.plan.json',fp)
  entryplan=read(delivery/'review.plan.json');entryplan.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(parts),packed_parts_manifest_sha256=sha(parts),frozen_inputs={str(p):sha(p)for p in [model,parts,motion,runtime]},review_sources=[]);write(release/'entry.plan.json',entryplan)
  manifest=release/'runtime-assets-manifest.json';write(manifest,{'species':s,'status':'running','next_action':'verify_canonical_entry','user_acceptance':True,'installed':True,'model':ref(model),'editable_source':ref(blend),'static_freeze':ref(freeze_file)})
  roles={**c,'source_image':ref(art),'model':ref(model),'editable_source':ref(blend),'atlas':ref(atlas),'source_projection':ref(projection),'material_author_model':ref(author),'final_entry':ref(model),'runtime_manifest':ref(manifest),'final_spec':ref(release/'spec.json'),'root_plan':ref(release/'recheck-fin.plan.json'),'static_freeze':ref(freeze_file),'release_metadata':ref(metadata),'loader':ref(GAME/'game/scripts/aquarium/FinalizedWidthBatch20261101.gd'),'exhibit':ref(GAME/'game/scripts/aquarium/VolumeFishExhibit.gd')}
  write(release/'release-inputs.json',{'species':s,'roles':roles,'old_ledger':ref(release/'history/reviewed-production-review.json'),'evidence':evidence,'previous_installed_sha256':oldsha,'source_shape_unchanged':True,'technical_report_reuse':'GLB/editable-source identical to accepted review. Existing physical reports copied byte-exact with original historical paths/hashes; no fabricated reruns. New canonical source export/cache/entry checks required before completion.','user_quote':QUOTE})
  table['profiles'][s].update(model_sha256=sha(model),appearance_and_rig_frozen=True,user_accepted_date='2026-11-04',release_metadata=metadata.relative_to(ROOT).as_posix());rows.append({'species':s,'name':label,'model':ref(model),'source':ref(blend),'metadata':ref(metadata),'status':'installed_pending_canonical_check'})
 write(tablepath,table);retain(OLD/'review/five-fish-overview.jpg',RELEASE/'five-fish-overview.jpg');retain(OLD/'completion.validation.json',RELEASE/'history/authoring-batch-completion.validation.json')
 for p in (OLD/'reproduction').glob('*.py'):retain(p,RELEASE/'methods'/p.name)
 write(RELEASE/'retention-manifest.json',{'kind':'byte_exact_retained_evidence_and_source_migration','files':mapping,'historical_paths':'Old report internal paths are historical. Mapping locates identical retained bytes; retired intermediates are not fabricated as current files.','new_archive_created':False});write(RELEASE/'manifest.json',{'status':'running','next_action':'canonical_source_export_and_entry_check','user_acceptance':True,'appearance_and_rig_frozen':True,'records':rows});print(json.dumps({'ok':True,'installed':len(rows),'retained_files':len(mapping),'release':str(RELEASE)}))
if __name__=='__main__':main()
