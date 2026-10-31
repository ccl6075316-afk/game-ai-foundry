"""Write truthful scoped review records and a confined cleanup plan, no deletes."""
import copy,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import sha
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 root=ROOT/'projects/fishing-2d/experiments/three-fish-fin-detail-20261031';current=load(root/'current-candidates.validation.json');settings_path=ROOT/'resources/volume-fish/fin-detail-cage-20261031.json';settings=load(settings_path);ann=ROOT/'resources/volume-fish/fin-detail-20261031.json'
 for rec in current['records']:
  out=Path(rec['candidate']);review=load(out/'production-review.json');auth=load(out/'author/author.validation.json');mask=load(auth['input_masks']['path']);runtime=load(out/'fin-review.plan.json');files={'source_image':Path(mask['source_image']),'model':Path(rec['model']),'species_profile':settings_path,'runtime_manifest':out/'fin-review.plan.json','motion_config':Path(runtime['motion_profile']),'editable_blend':Path(rec['editable_blend'])};review['candidate_files']={k:{'path':str(p),'sha256':sha(p)}for k,p in files.items()};bound={k:sha(p)for k,p in files.items()};evidence={}
  def ev(key,path,kind,observation):evidence[key]={'path':str(path),'sha256':sha(path),'kind':kind,'bound_inputs':bound,'observation':observation}
  ev('preservation',out/'preservation-source.validation.json','report','All protected part attributes/directed indices/sampledRGBA unchanged; native alpha coverage and finite new shells verified.');ev('cold_source',out/'source-run/validation-report.json','report','Editable source with original rig; complete semantic parity and independent process cold export.');ev('roots',out/'fin-root-gate/completion.validation.json','report','Current complete490 root report includes177; no invented duplicate177 run.');ev('membranes',out/'fin490/completion.validation.json','report','Every applicable fin at490 current native/controller/range poses, original limits.');ev('fin_compare',out/'review/fin-before-after.png','image','Actual same-camera cold GLBs; visible rounded source edges and retained accepted width.');ev('mouth_compare',out/'review/mouth-preservation.png','image','Viewed lower lip, true opening, upper/lower jaw and source colors from side/front/oblique; unchanged source geometry and actual material.');ev('all_fins',out/'fin-volume/all-fins-overview.png','image','Viewed all applicable fin source texture and oblique finite clay; separate root/body and end/top views retained.');ev('controls',out/'motion.validation.json','report','Native controller controls/actions/transitions checked on actual candidate, original rig unchanged.')
  if rec['body077']:ev('body077',out/'body077/completion.validation.json','report','Current closed body, opaque donors and GPU coverage with transparent negative control.')
  review['evidence']=evidence
  for stage in review['stages'].values():stage['observations']=['Scoped fin-repair review candidate. Complete whole-fish acceptance is pending; no historical pass copied.']
  review['stages']['mouth']['observations']=['Mouth remains exactly on accepted-width baseline; actual side/front/oblique lower lip/opening/jaw/color reviewed. No mouth reconstruction or new mouth acceptance.']
  fins=review['stages']['fins'];fins['method']='Independent original-pixel masks → low-poly cage → full finite source root band on actual body → editable source/cold GLB → current490 and GPU views.';fins['observations']=['All applicable fins checked, including retained dorsal/caudal. NativeRGB and alpha support verified. User fin appearance acceptance still pending.']
  mapping={'complete_species_fin_inventory_and_roots':['preservation','roots'],'source_cutout_and_shape_comparison':['preservation','fin_compare'],'all_fin_root_gate':['roots'],'whole_fin_membrane_gate':['membranes'],'expanded_fin_visual_review':['all_fins','fin_compare'],'actual_normal_thickness_and_tail_section':['all_fins'],'fin_volume_end_on_and_top_clay':['all_fins']}
  for k,v in mapping.items():
   if k in fins['checks']:fins['checks'][k]=v
  review['stages']['runtime']['observations']=['Cold editable-source export and standalone viewer verified. Formal installation/water presentation pending. '+('Current077 passed.'if rec['body077']else '077 blocked by pre-existing accepted-width body normal/winding mismatch; same baseline reproduces it. Body not modified to conceal it.')];review['scope']='User requested method archive and fin refinement. Standalone current candidate; not formal whole-fish delivery, not user fin acceptance.';save(out/'production-review.json',review)
  rec.update(specific_settings=settings[rec['species']],specific_settings_sha256=hashlib.sha256(json.dumps(settings[rec['species']],sort_keys=True).encode()).hexdigest(),original_annotation={'path':str(ann),'sha256':sha(ann)},proofs={name:{'path':str(out/path),'sha256':sha(out/path)}for name,path in [('source','source-run/validation-report.json'),('preservation','preservation-source.validation.json'),('roots','fin-root-gate/completion.validation.json'),('membranes','fin490/completion.validation.json'),('motion','motion.validation.json'),('body077','body077/completion.validation.json')]})
 current['production_tools']={str(p):sha(p)for p in [HERE/name for name in ['prepare_native_fin_detail.py','refine_native_fin_cages.py','conform_native_fin_roots.py','prepare_native_fin_review.py','validate_native_fin_detail.py']]};save(root/'current-candidates.validation.json',current)
 manifest=load(root/'manifest.json');manifest.update(status='done',next_action='human_review',scope='Fin-specific revision and method archive completed for review. Whole-fish formal gates not all passed; installed=false.',formal_acceptance=False,current_candidates={'path':str(root/'current-candidates.validation.json'),'sha256':sha(root/'current-candidates.validation.json')},handoff={'path':str(root/'HANDOFF.md'),'sha256':sha(root/'HANDOFF.md')},species=current['records']);save(root/'manifest.json',manifest)
 # Preserve static plus every recorded worst failure pose before pruning raw
 # rejected490 samples. Existing reports stay historical and are not rewritten.
 delete=set();rejected=[]
 for sp,rev in [('bluegill','candidate-r4'),('bluegill','candidate-r5'),('crucian','candidate-r3')]:
  folder=root/sp/rev/'fin490'/sp;exp=load(folder/'export.validation.json');mem=load(folder/'membranes.validation.json');wanted={('Static',0.)}
  for row in mem['summary'].values():
   if row['worst_pose']:wanted.add((row['worst_pose']['action'],row['worst_pose']['seconds']))
  kept=[]
  for row in exp['samples']:
   path=Path(row['posed_mesh_json']);assert path.resolve().parent==folder.resolve()and sha(path)==row['sha256']
   if (row['action'],row['seconds'])in wanted:kept.append(row)
   else:delete.add(path)
  rejected.append({'species':sp,'revision':rev,'export_report':str(folder/'export.validation.json'),'export_sha256':sha(folder/'export.validation.json'),'kept_minimal_counterexamples':kept,'historical_full_report_coverage':490,'dense_other_samples_pruned':True})
 # Exact lists of unadopted candidates; preserve the author inputs referenced
 # by the final candidates (blue4, crucian1, grass4) and unique failed models.
 obsolete=['bluegill/candidate-r1','bluegill/candidate-r2','bluegill/candidate-r3','bluegill/candidate-r6','crucian/candidate-r2','grass_carp/candidate-r1','grass_carp/candidate-r2','grass_carp/candidate-r3']
 historical=[]
 for relative in obsolete:
  path=(root/relative).resolve();assert path.is_relative_to(root)and path!=root
  historical.append({'directory':str(path),'reason':'Unadopted intermediate or duplicate; unique failure conclusions copied into handoff/method.','files':[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}for p in path.rglob('*')if p.is_file()]})
  delete.update(p for p in path.rglob('*')if p.is_file())
 for path in delete:assert path.resolve().is_relative_to(root)and path.is_file()
 plan={'ok':True,'kind':'explicit_experiment_cleanup_plan','root':str(root),'current_models':[r['model']for r in current['records']],'rejected_pose_archives':rejected,'obsolete_candidates':historical,'delete_files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(delete)],'passing_dense_samples':'Pruned only via validate_fin_completion.discard_passing_samples after complete current490/root passes.','preserve':'Final editable source/GLBs, current masks, independent source/context, all current GPU and binding reports, unique failed models/minimal poses, width baselines and full research archive.'};save(root/'cleanup.plan.json',plan);print(json.dumps({'ok':True,'planned_files':len(delete),'planned_MB':round(sum(r['bytes']for r in plan['delete_files'])/1024**2,2)}))
if __name__=='__main__':main()
