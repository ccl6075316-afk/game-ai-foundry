"""Assemble the observed November 4 carp candidate; never installs or accepts it.

Historical source/native-color evidence retains its original hashes. Current
geometry, physical gates, direct captures and cold export have their own proofs.
Only run after the explicitly recorded operator inspection and video encoding.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'cli'),str(Path(__file__).parent/'portable')]
from volume_sop import STAGES,standard_snapshot
from glb_io import read_glb,arrays
import numpy as np

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):p=Path(p).resolve();return {'path':str(p),'sha256':sha(p)}
def write(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def checked(p):
 d=read(p);assert d['ok'],str(p);return d
def path(r):
 p=Path(r['path']if isinstance(r,dict)else r);return p if p.is_absolute()else ROOT/p

def main():
 root=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/carp';g=root/'gates-r4';delivery=root/'delivery-r4';images=delivery/'review';model=root/'width-r4/fish.glb';blend=model.with_suffix('.blend');msha=sha(model)
 oldroot=ROOT/'projects/fishing-2d/experiments/carp-lowpoly-sop-20261031';old=read(oldroot/'generated-underside-material-20261101/final/sop-review.json')
 observations=read(root/'root-operator-observations.json');assert set(observations)==set(STAGES)and all(isinstance(x,str)and x.strip()for x in observations.values())
 technical={k:root/v for k,v in {
  'budget':'delivery-r4/budget.validation.json','import':'delivery-r4/import.validation.json','motion':'delivery-r4/motion.validation.json','body077':'delivery-r4/body077/completion.validation.json','head':'delivery-r4/head.validation.json','root490':'delivery-r4/fin490/carp/roots.validation.json','membrane490':'delivery-r4/fin490/carp/membranes.validation.json','fin072':'delivery-r4/root072/completion.validation.json','fin_volume':'fin-volume-current-profile.validation.json','opening':'mouth-opening-r4.validation.json','lip_preservation':'lip-transport.validation.json','source_authoring':'width-r4/source-authoring.validation.json','source_projection':'width-r4/validation-source.validation.json','packing':'gates-r4/packing-continuity.validation.json','root_domain':'gates-r4/root-domain-preservation.validation.json','native_loop':'native-loop.validation.json','composition':'delivery-r4/review/source-composition.validation.json'}.items()}
 reports={k:checked(p)for k,p in technical.items()}
 for k in ['body077','root490','membrane490','fin_volume','lip_preservation','source_authoring','source_projection','native_loop']:assert reports[k]['model_sha256']==msha,k
 assert reports['head']['species'][0]['model_sha256']==msha
 assert read(delivery/'negative-head.validation.json')['ok']is False
 assert len(reports['root490']['samples'])==reports['membrane490']['poses']==490
 assert reports['fin_volume']['profile_sha256']==sha(g/'head-envelope.profile.json')
 assert reports['fin_volume']['current']['blend_sha256']==sha(root/'width-r4/validation-source.blend')
 capture=checked(images/'review-capture.validation.json');assert capture['model_sha256']==msha and capture['direct_GLTFDocument']and capture['runtime_static_build_calls']==0 and capture['static_arrays_uv_materials_unchanged']
 for p,h in capture['frozen_inputs'].items():assert sha(p)==h,('Stale actual capture input',p)
 cold=checked(root/'width-r4/cold-export.validation.json');assert cold['output_sha256']==msha and cold['blend_sha256']==sha(blend)and cold['reference_GLB_read_during_export']is False
 assert cold['triangles']==1494
 profile=ROOT/'resources/volume-fish/database-revision-20261104/carp.profile.json'
 if profile.exists():assert sha(profile)==sha(g/'head-envelope.profile.json')
 else:profile.parent.mkdir(parents=True,exist_ok=True);profile.write_bytes((g/'head-envelope.profile.json').read_bytes())
 # Keep original source provenance and native-color author evidence immutable.
 original_roles=['source_image','material_author_model','generated_skin_image','generated_skin_source_review','water_renderer','water_profile','water_shader']
 historical={k:path(old['candidate_files'][k])for k in original_roles}
 for k,p in historical.items():assert sha(p)==old['candidate_files'][k]['sha256'],k
 native=oldroot/'head-material-r5/authoring.validation.json';nr=checked(native)
 assert nr['model_sha256']==sha(historical['material_author_model'])and nr['source_sha256']==sha(historical['source_image'])
 preservation=reports['lip_preservation'];assert preservation['all_actual_RGBA_exact']and all(preservation['checks'].values())and preservation['native_lip_ownership_original_report']==ref(native)
 spec=read(g/'spec.json');motion=path(spec['motion']['profile']);runtime=path(spec['motion']['runtime']);atlas=path(spec['inputs']['atlas'])
 asset=root/'runtime-assets-manifest.json';write(asset,{'kind':'exported_fish_review_candidate_manifest','species':'carp','status':'done','next_action':'human_review','model':ref(model),'editable_source':ref(blend),'profile':ref(profile),'motion':ref(motion),'runtime':ref(runtime),'source':ref(historical['source_image']),'actual_current_reports':{k:ref(p)for k,p in technical.items()},'installed':False,'user_acceptance':False,'scope':'Exported whole-fish operator candidate. Prior underside appearance acceptance is retained only as source history; new whole appearance requires user review.'})
 candidates={k:ref(p)for k,p in {**historical,'model':model,'species_profile':profile,'runtime_manifest':asset,'motion_config':motion,'editable_source':blend,'final_entry':model,'motion_runtime':runtime,'viewer_script':Path(__file__).parent/'portable/FishListViewer.gd','final_spec':g/'spec.json','delivery_config':g/'delivery-config.json','atlas':atlas,'root_plan':g/'fin.plan.json','source_projection':root/'width-r4/validation-source.blend'}.items()};frozen={k:v['sha256']for k,v in candidates.items()}
 facts=root/'current-evidence.validation.json';write(facts,{'ok':True,'kind':'current_database_revision_evidence_inventory','species':'carp','bound_inputs':frozen,'operator_observations':observations,'library_comparison':ref(root/'reference-comparison.validation.json'),'unity_transform_audit':ref(root/'unity-reference-transform.validation.json'),'actual_current_reports':{k:ref(p)for k,p in technical.items()},'historical_source_audit':ref(oldroot/'source-audit/validation-report.json'),'historical_preparation':ref(oldroot/'preparation.validation.json'),'native_fin_masks':ref(oldroot/'native-fins-r5/masks.validation.json'),'historical_complete_native_chart':ref(native),'historical_skin_source_review':ref(historical['generated_skin_source_review']),'current_lip_transport':ref(technical['lip_preservation']),'head_reference_coverage':ref(g/'head-reference-coverage.validation.json'),'enumerated_XY_correction':ref(root/'width-r4/xy-preservation.validation.json'),'source_cold_export':ref(root/'width-r4/cold-export.validation.json'),'actual_capture':ref(images/'review-capture.validation.json'),'fin_capture':ref(root/'fin-views/fin-volume-capture.validation.json'),'limits':['CommonCarp is named third-party game art, not a biological measurement; identity/age/sex remain unknown.','Only mouth is an intentional body opening; 077 includes actual same-pose GPU coverage.','Discrete490/contact rays and viewed representative images do not certify all continuous times.','Original pixels and all UV/index/skin remain; mouth Y, transverse envelope and five erroneous custom normals are actual source edits.','No new mouth articulation; native swimming and existing four controls/transitions only.','Standalone exported candidate, no canonical game replacement and no new whole-fish user acceptance.'],'user_acceptance':False})
 coldreport=root/'root-final-asset-cold-load.validation.json';write(coldreport,{'ok':True,'kind':'fish_final_asset_cold_load','species':'carp','bound_inputs':frozen,'entry_role':'final_entry','fresh_process':True,'static_builders_disabled':True,'runtime_static_build_calls':0,'errors':[],'checks':{'independent_load':capture['direct_GLTFDocument'],'materials_complete':reports['import']['ok'],'rig_and_motion':reports['motion']['ok'],'export_matches_candidate':cold['output_sha256']==msha},'actual_receipts':{'cold_source_export':ref(root/'width-r4/cold-export.validation.json'),'new_process_capture':ref(images/'review-capture.validation.json'),'new_process_import':ref(technical['import']),'actual_controls':ref(technical['motion'])},'scope':'New process source export equals exact candidate; independent direct GLTFDocument GPU/import/motion receipts use this candidate without static builders. No installation claim.'})
 review=read(root/'production-review.json');assert review['species']=='carp'and review['standard']==standard_snapshot()
 review.update(candidate_files=candidates,evidence={},scope='Current library-informed carp whole-fish review candidate; prior game asset unchanged; user review pending.',user_acceptance=False,task_type='repair')
 paths={
 'preparation.landmarks_and_part_inventory':images/'source-pose-comparison.png','head.source_pose_comparison':images/'source-pose-comparison.png',
 **{'head.clay_'+v:images/('head-'+('left'if v=='side'else v)+'-clay.png')for v in ['side','front','top','bottom','oblique']},
 'mouth.whole_snout_and_chin':images/'head-bottom-texture.png','mouth.integrated_upper_lower_jaws_and_cut':images/'head-oblique-clay.png','mouth.misplaced_outline_ownership':images/'head-front-texture.png','mouth.native_pixel_cover_and_actual_uv_joins':root/'root-head-review.jpg','mouth.complete_native_lip_domain_and_front_exclusion':native,
 'eyes.source_eye_and_ownership_domains':images/'source-pose-comparison.png','eyes.opposite_and_top_views':root/'root-head-review.jpg',
 'skin.dorsal_material':images/'whole-top-texture.png','skin.ventral_material':images/'whole-bottom-texture.png','skin.hidden_fin_skin':images/'body-without-fins-bottom-texture.png','skin.body_owned_fin_base_marks':images/'body-without-fins-top-texture.png',
 'fins.source_cutout_and_shape_comparison':images/'fin-source-comparison-0.jpg','fins.expanded_fin_visual_review':root/'fin-views/fin-volume-review-1.jpg','fins.fin_volume_end_on_and_top_clay':root/'fin-views/fin-volume-review-0.jpg','fins.all_fin_root_gate':technical['root490'],'fins.whole_fin_membrane_gate':technical['membrane490'],'fins.actual_normal_thickness_and_tail_section':technical['fin_volume'],
 'motion.native_loop':technical['native_loop'],'motion.real_transitions_and_control_ranges':technical['motion'],
 **{'motion.'+a:images/f'frames/frame-{n:04d}.jpg'for a,n in [('swim',48),('turn',96),('ascend',144),('dive',192)]},
 'runtime.body_integrity_gpu_gate':technical['body077'],'runtime.material_anchor_and_actual_lod':technical['import'],'runtime.motion_and_surface_gate':technical['motion'],'runtime.cold_import_and_install_binding':coldreport,'runtime.final_asset_cold_load':coldreport,'runtime.exported_vs_experiment_comparison':images/'source-pose-comparison.png',
 'presentation.source_style_final_comparison':images/'source-pose-comparison.png','presentation.normal_and_close_game_views':root/'root-whole-skin-review.jpg','presentation.water_readability':images/'water-natural-freshwater-oblique.png','presentation.orbit_and_motion_video':root/'carp-database-r4-review.mp4'}
 for stage,criteria in STAGES.items():
  entry=review['stages'][stage];entry.update(result='passed',method='Actual current source/cold binding, inspected current captures and unchanged historical provenance/native chart with separately measured transport; specialized current gates distinct from visual review.',reviewer='Codex root operator; whole-fish user review pending',observations=observations[stage])
  for criterion,kind in criteria.items():
   eid=stage+'.'+criterion;p=paths.get(eid,facts if kind=='data'else None);assert p is not None and p.is_file(),eid
   review['evidence'][eid]={**ref(p),'kind':kind,'bound_inputs':frozen,'observation':observations[stage]};entry['checks'][criterion]=[eid]
 review['stages']['mouth']['implementation']={'branch':'integrated_jaw_cut','body_resource_role':'model','cut_line':'Own original upper/lower lip traces at five independent stations; actual BVH hits preserve native lip chart while correcting a too-narrow oral gap.','upper_jaw':'Connected native roof/upper jaw, four original barbels retained.','lower_jaw':'Connected original lower jaw and chin, oral floor retained; no independent lip layers.','method_reference':'resources/skills/fish-volume-production/references/mouth-execution.md'}
 review['stages']['runtime']['finalization']={'state':'exported','editable_source_role':'editable_source','model_role':'model','entry_role':'final_entry','static_parts':{k:{'geometry_uv_weights_role':'model','observation':observations[{'body':'skin','eyes':'eyes','mouth':'mouth','fins':'fins'}[k]]}for k in ['body','eyes','mouth','fins']},'engine_resource_roles':[],'runtime_behaviors':[{'resource_role':'motion_runtime','purpose':'animation','observation':'Native animation plus existing four actions/control transitions; static source shape is already exported.'},{'resource_role':'viewer_script','purpose':'resource_loading','observation':'Read-only exported-candidate viewer; canonical installed model unchanged.'}]}
 write(root/'production-review.json',review);print(json.dumps({'ok':True,'species':'carp','evidence':len(review['evidence']),'model_sha256':msha,'installed':False,'user_acceptance':False}))

if __name__=='__main__':main()
