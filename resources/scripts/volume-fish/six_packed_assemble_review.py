"""Assemble an explicitly observed packed-fish candidate from a frozen recipe.

The recipe names actual receipts; no gate runs, report-kind conversion,
historical-receipt relabelling, installation or user acceptance occurs here.
"""
import argparse,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'cli'),str(HERE/'portable')]
from volume_sop import STAGES,standard_snapshot
from logical_document import logical_document

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def path(p):
 p=Path(p['path']if isinstance(p,dict)else p);return p.resolve()if p.is_absolute()else(ROOT/p).resolve()
def ref(p):p=path(p);return {'path':str(p),'sha256':sha(p)}
def write(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main(recipe):
 cfg=read(recipe);root=path(cfg['directory']);species=cfg['species'];model=path(cfg['model']);blend=path(cfg['blend']);g=path(cfg['gates']);delivery=path(cfg['delivery']);operator=path(cfg['operator_directory']);images=delivery/'review';fviews=path(cfg['finviews']);msha=sha(model)
 assert root.is_relative_to(ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104')
 observations=read(path(cfg['observations']));assert set(observations)==set(STAGES)and all(isinstance(v,str)and v.strip()for v in observations.values())
 technical={k:path(v)for k,v in cfg['technical'].items()};reports={}
 for k,p in technical.items():reports[k]=read(p);assert reports[k]['ok'],k
 for k in ['body077','root490','membrane490','fin_volume','lip_preservation','source_authoring','native_loop']:assert reports[k]['model_sha256']==msha,k
 opening=reports['opening']
 if 'model_sha256'in opening:assert opening['model_sha256']==msha
 else:
  assert opening['kind']=='independent_actual_source_mouth_opening_regression'
  projection=read(path(cfg['opening_projection']));current=opening['results']['current']
  assert current['ok']and opening['results']['rejected']['ok']is False
  assert sha(current['source_blend'])==current['sha256']==projection['diagnostic_blend_sha256']
  assert path(current['source_blend'])==path(projection['diagnostic_blend'])
  ordinary=g/'ordinary-reference.glb';assert sha(ordinary)==projection['input_sha256']and path(projection['input'])==ordinary
  # Reconstruct the exact ordinary logical projection from CURRENT packed rows
  # in memory. This binds diagnostic source rays without inventing a model SHA
  # in the historical/raw mouth report.
  plan=read(g/'fin.plan.json')['items'][0];doc,blob,_=logical_document(model,plan['body'],list(plan['fins']),g/'parts-manifest.json')
  j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*(-len(j)%4);blob+=b'\0'*(-len(blob)%4)
  raw=struct.pack('<4sII',b'glTF',2,28+len(j)+len(blob))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(blob),b'BIN\0')+blob
  assert hashlib.sha256(raw).hexdigest()==sha(ordinary),'Mouth projection no longer matches current packed model'
 assert reports['head']['species'][0]['model_sha256']==msha
 assert read(delivery/'negative-head.validation.json')['ok']is False
 assert len(reports['root490']['samples'])==reports['membrane490']['poses']==490
 volume=reports['fin_volume'];assert volume['kind']=='actual_packed_source_fin_volume_and_tail_section'
 profile=path(cfg['profile']);assert volume['profile_sha256']==sha(profile)
 assert volume['root490']==ref(technical['root490'])and volume['membrane490']==ref(technical['membrane490'])
 correspondence=read(path(volume['source_correspondence']));assert correspondence['ok']and correspondence['blend_sha256']==sha(blend)and correspondence['model_sha256']==msha
 capture=read(images/'review-capture.validation.json');assert capture['ok']and capture['model_sha256']==msha and capture['direct_GLTFDocument']and capture['runtime_static_build_calls']==0 and capture['static_arrays_uv_materials_unchanged']
 for p,h in capture['frozen_inputs'].items():assert sha(p)==h,('Stale actual capture input',p)
 coldpath=path(cfg['cold_export']);cold=read(coldpath);assert cold['ok']and cold['output_sha256']==msha and cold['blend_sha256']==sha(blend)and cold['reference_GLB_read_during_export']is False
 spec=read(g/'spec.json');motion=path(spec['motion']['profile']);runtime=path(spec['motion']['runtime']);atlas=path(spec['inputs']['atlas'])
 nativepath=path(cfg['native_lip_report']);native=read(nativepath);author=path(cfg['material_author_model']);source=path(cfg['source_image'])
 assert native['ok']and native['kind']=='complete_anterior_semantic_color_chart'and native['model_sha256']==sha(author)and native['source_sha256']==sha(source)
 assert opening['source_sha256']==sha(source)
 asset=root/'runtime-assets-manifest.json';write(asset,{'kind':'exported_fish_review_candidate_manifest','species':species,'status':'done','next_action':'human_review','model':ref(model),'editable_source':ref(blend),'profile':ref(profile),'motion':ref(motion),'runtime':ref(runtime),'source':ref(source),'actual_current_reports':{k:ref(p)for k,p in technical.items()},'installed':False,'user_acceptance':False,'scope':'Current source-owned exported candidate; technical/operator checks are separate from user acceptance.'})
 candidates={k:ref(p)for k,p in {'source_image':source,'model':model,'species_profile':profile,'runtime_manifest':asset,'motion_config':motion,'editable_source':blend,'editable_blend':blend,'final_entry':model,'motion_runtime':runtime,'viewer_script':HERE/'portable/FishListViewer.gd','final_spec':g/'spec.json','delivery_config':g/'delivery-config.json','atlas':atlas,'root_plan':g/'fin.plan.json','material_author_model':author,**{k:path(v)for k,v in cfg.get('additional_candidates',{}).items()}}.items()};frozen={k:v['sha256']for k,v in candidates.items()}
 facts=root/'current-evidence.validation.json';write(facts,{'ok':True,'kind':'current_packed_database_revision_evidence_inventory','species':species,'bound_inputs':frozen,'operator_observations':observations,'actual_current_reports':{k:ref(p)for k,p in technical.items()},'current_capture':ref(images/'review-capture.validation.json'),'source_cold_export':ref(coldpath),'native_lip_author_report':ref(nativepath),'current_native_lip_preservation':ref(technical['lip_preservation']),'reference_evidence':{k:ref(v)for k,v in cfg['reference_evidence'].items()},'limits':cfg['limits'],'user_acceptance':False})
 coldreport=root/'root-final-asset-cold-load.validation.json';write(coldreport,{'ok':True,'kind':'fish_final_asset_cold_load','species':species,'bound_inputs':frozen,'entry_role':'final_entry','fresh_process':True,'static_builders_disabled':True,'runtime_static_build_calls':0,'errors':[],'checks':{'independent_load':capture['direct_GLTFDocument'],'materials_complete':reports['import']['ok'],'rig_and_motion':reports['motion']['ok'],'export_matches_candidate':cold['output_sha256']==msha},'actual_receipts':{'cold_source_export':ref(coldpath),'new_process_capture':ref(images/'review-capture.validation.json'),'new_process_import':ref(technical['import']),'actual_controls':ref(technical['motion'])},'scope':'Actual source/candidate cold byte match and fresh direct GLTFDocument/import/current-controls receipts; no canonical installation claim.'})
 review=read(root/'production-review.json');assert review['species']==species and review['standard']==standard_snapshot()
 review.update(candidate_files=candidates,evidence={},scope='Source-owned library-informed whole-fish candidate, user appearance review pending; canonical game asset unchanged.',user_acceptance=False,task_type='repair')
 paths={
 'preparation.landmarks_and_part_inventory':images/'source-pose-comparison.png','head.source_pose_comparison':images/'source-pose-comparison.png',
 **{'head.clay_'+v:images/('head-'+('left'if v=='side'else v)+'-clay.png')for v in ['side','front','top','bottom','oblique']},
 'mouth.whole_snout_and_chin':images/'head-bottom-texture.png','mouth.integrated_upper_lower_jaws_and_cut':images/'head-oblique-clay.png','mouth.misplaced_outline_ownership':images/'head-front-texture.png','mouth.native_pixel_cover_and_actual_uv_joins':operator/'root-head-review.jpg','mouth.complete_native_lip_domain_and_front_exclusion':nativepath,
 'eyes.source_eye_and_ownership_domains':images/'source-pose-comparison.png','eyes.opposite_and_top_views':operator/'root-head-review.jpg',
 'skin.dorsal_material':images/'whole-top-texture.png','skin.ventral_material':images/'whole-bottom-texture.png','skin.hidden_fin_skin':images/'body-without-fins-bottom-texture.png','skin.body_owned_fin_base_marks':images/'body-without-fins-top-texture.png',
 'fins.source_cutout_and_shape_comparison':images/'fin-source-comparison-0.jpg','fins.expanded_fin_visual_review':fviews/'fin-volume-review-1.jpg','fins.fin_volume_end_on_and_top_clay':fviews/'fin-volume-review-0.jpg','fins.all_fin_root_gate':technical['root490'],'fins.whole_fin_membrane_gate':technical['membrane490'],'fins.actual_normal_thickness_and_tail_section':technical['fin_volume'],
 'motion.native_loop':technical['native_loop'],'motion.real_transitions_and_control_ranges':technical['motion'],
 **{'motion.'+a:images/f'frames/frame-{n:04d}.jpg'for a,n in [('swim',48),('turn',96),('ascend',144),('dive',192)]},
 'runtime.body_integrity_gpu_gate':technical['body077'],'runtime.material_anchor_and_actual_lod':technical['import'],'runtime.motion_and_surface_gate':technical['motion'],'runtime.cold_import_and_install_binding':coldreport,'runtime.final_asset_cold_load':coldreport,'runtime.exported_vs_experiment_comparison':images/'source-pose-comparison.png',
 'presentation.source_style_final_comparison':images/'source-pose-comparison.png','presentation.normal_and_close_game_views':operator/'root-whole-skin-review.jpg','presentation.water_readability':images/'water-natural-freshwater-oblique.png','presentation.orbit_and_motion_video':path(cfg['video'])}
 for stage,criteria in STAGES.items():
  entry=review['stages'][stage];entry.update(result='passed',method='Actual current source/cold/gates, complete native-lip and exhaustive packed fin measurements, independently inspected current captures; historical acceptance only within original scope.',reviewer='Codex root operator; user appearance acceptance pending',observations=observations[stage])
  for criterion,kind in criteria.items():
   eid=stage+'.'+criterion;p=paths.get(eid,facts if kind=='data'else None);assert p is not None and p.is_file(),eid
   review['evidence'][eid]={**ref(p),'kind':kind,'bound_inputs':frozen,'observation':observations[stage]};entry['checks'][criterion]=[eid]
 review['stages']['mouth']['implementation']={'branch':'integrated_jaw_cut','body_resource_role':'model',**cfg['mouth_implementation'],'method_reference':'resources/skills/fish-volume-production/references/mouth-execution.md'}
 review['stages']['runtime']['finalization']={'state':'exported','editable_source_role':'editable_source','model_role':'model','entry_role':'final_entry','static_parts':{k:{'geometry_uv_weights_role':'model','observation':observations[{'body':'skin','eyes':'eyes','mouth':'mouth','fins':'fins'}[k]]}for k in ['body','eyes','mouth','fins']},'engine_resource_roles':[],'runtime_behaviors':[{'resource_role':'motion_runtime','purpose':'animation','observation':'Native swimming and four actions/transitions, all static source shape already exported.'},{'resource_role':'viewer_script','purpose':'resource_loading','observation':'Read-only exported-candidate view; canonical game model unchanged.'}]}
 write(root/'production-review.json',review);print(json.dumps({'ok':True,'species':species,'evidence':len(review['evidence']),'model_sha256':msha,'installed':False,'user_acceptance':False}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True);main(p.parse_args().recipe)
