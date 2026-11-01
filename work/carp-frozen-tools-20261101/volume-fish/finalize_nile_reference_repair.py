"""Bind the measured-reference revision and clean rejected/rebuildable outputs."""
import json,hashlib,subprocess,ast
from pathlib import Path
repo=Path(__file__).resolve().parents[3];game=repo/'projects/fishing-2d';trial=game/'experiments/nile-dorsal-route-trial';out=trial/'round6-reference-repair';rejected=trial/'round5-user-review-fixes'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def bound(p):return {'path':str(p.relative_to(repo)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size}
plan=read(out/'repair.plan.validation.json');live=read(out/'three-live.validation.json');control=read(out/'three-interactive-input.validation.json')
assert live['ok'] and control['ok'] and control['synchronized_views']==3
routes={}
for route in ['A','B']:
 d=out/(route+'-artifacts');v=read(d/'validation.json');gate=read(d/'fin-gate/completion.validation.json');assert gate['ok'] and gate['checks'][0]['poses']==177
 for name,h in v['hashes'].items():assert sha(d/name)==h
 seen=next(row for row in live['models'] if row['route']==route);assert seen['model_sha256']==sha(d/'fish.glb') and seen['triangles']==v['triangles']
 routes[route]={'triangles':v['triangles'],'preferred_met':v['triangles']<=1500,'model':bound(d/'fish.glb'),'editable_source':bound(d/'fish.blend'),'body_closed':v['body_closed'],'all_fin_and_tail_geometry_uv_weights_unchanged':v['all_fin_geometry_uv_weights_unchanged'],'current_root_gate':bound(d/'fin-gate/completion.validation.json'),'root_certification':route=='B','A_root_limit':'A original open body invalidates closed-body contact certification despite numeric pass.' if route=='A' else None,'oral_construction':v['oral_trim']}
report={'kind':'nile_actual_reference_local_revision','ok':True,'status':'experimental_revision_for_user_review','next_action':'human_review','formal_acceptance':False,'user_visual_acceptance':'pending','routes':routes,'rejected_round5':{'user_visual_acceptance':'rejected','reasons':plan['rejected_round5'],'do_not_resume_previous_builder':True},'belly':{'cause':'Round5 donor_y minimum clamp collapsed a 2D patch to repeated source rows. Black-ray removal alone was not a visual pass.','current':'Native-scale 2D whole-skin donor follows ellipse arc; no y clamp, small patch scale-up or flat grey fill.','map':bound(out/'belly-donor-map.npz')},'mouth':{'reference':bound(out/'A-mouth-reference.validation.json'),'method':'Measure actual A projected jaw boundaries, full outer envelopes and transverse width; fit only B anterior sparse-cage stations and subtract the measured asymmetric oral volume. No A mesh topology graft or old-body reduction.','color':'Corresponding A actual skin triangle UVs and A actual oral role, not unrelated grey forehead/chin rectangles.','plan_cut_profile':plan['cut_profile_native'],'limits':'Sparse reconstruction, not an exact duplicate of every A triangle. A reference has open edges; B retains closed jaws and interior walls. User visual acceptance pending.'},'forehead':{'source':'Existing original chart112 dorsal source; original longitudinal and eye-protection blend restored offline.','eye_preservation':'Geometry beforeu.94 and both original painted eye domains retained; chart mask protects source eye ellipse.','mask':bound(out/'forehead-old-chart-mask.png')},'evidence':{name:bound(out/name) for name in ['belly-rejected-current.jpg','mouth-geometry-A-B.jpg','mouth-A-B-current.jpg','mouth-rejected-current.jpg','forehead-original-A-B.jpg','diagnostic-cold-render.validation.json','three-live.validation.json','three-interactive-input.validation.json']},'reproduce':['measure_nile_mouth_reference.py in Blender','prepare_nile_reference_repair.py in venv','build_nile_reference_repair.py in Blender','open_nile_ab_review.py in venv; defaultrevision6, --round4/--round5 historical only'],'remaining_formal_gates':['User acceptance of belly/mouth/forehead and visible fin thickness','Full490 fin membrane/native checks','Body/GPU/head final checks and full SOP'],'source_code':{name:sha(repo/'resources/scripts/volume-fish'/name) for name in ['measure_nile_mouth_reference.py','prepare_nile_reference_repair.py','build_nile_reference_repair.py','oral_jaws.py','preview_nile_three_live.gd']},'new_generation_calls':0,'new_generation_fees':0}
assert sha(game/'game/assets/models/fish/nile_tilapia.glb')=='4ee2c552939b682463120b52e40f2f98e996c2dad8f91f9144ab7d6de51ad25a'
write(out/'review.validation.json',report)
review=read(out/'sop-review.json');files={'source_image':trial/'round4-ab-textured/shared/body-side.png','model':out/'B-artifacts/fish.glb','species_profile':repo/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json','runtime_manifest':out/'review.validation.json','motion_config':repo/'resources/volume-fish/motion/nile_tilapia-082.json','editable_blend':out/'B-artifacts/fish.blend'}
review['candidate_files']={k:{'path':str(p),'sha256':sha(p)} for k,p in files.items()}
for stage in review['stages'].values():stage['observations']='Local actual-reference revision pending user visual review, not formal stage acceptance.'
write(out/'sop-review.json',review)
result=subprocess.run([str(repo/'.venv/Scripts/python.exe'),'cli/gamefactory.py','volume','sop-check','--review',str(out/'sop-review.json'),'--output',str(out/'sop-check.validation.json'),'--json'],cwd=repo,capture_output=True,text=True,encoding='utf8');assert not json.loads(result.stdout)['ok']

# Freeze failure explanations before deleting regenerable candidate binaries.
failure={'kind':'local_implementation_failures','rejected_round5':'Preserved screenshots, plans, hashes and scripts; model binaries reproducible from retained round4 sources.','local_diagnostic_rejections':['Initial envelope rays were restricted to the mouth ROI and clipped the true head crown; actual gray render exposed a false nose bump. Measurement now spans the entire head, and no such interim model is presented as current.','Blender process initially kept a material datablock across open_mainfile; it was invalidated and crashed. The source color is now frozen as plain numeric data.','Transported per-corner periodic UVs required destination triangle seam unwrapping.']}
write(out/'failure-notes.validation.json',failure)
to_delete=[]
for route in ['A','B']:
 for p in [out/f'{route}-artifacts/fish.blend1',out/f'{route}-artifacts/fin-gate/export.log',out/f'{route}-artifacts/fin-gate/nile_tilapia/check.log']:
  if p.exists():to_delete.append(p)
 for name in ['fish.blend','fish.glb']:
  p=rejected/f'{route}-artifacts/{name}'
  if p.exists():to_delete.append(p)
previous=read(out/'cleanup.validation.json') if (out/'cleanup.validation.json').exists() else {}
new_deleted=[bound(p) for p in to_delete];deleted=previous.get('deleted',[])+new_deleted
receipt={'ok':False,'status':'prepared','deleted':deleted,'scope':'Round6 intermediate backups/success logs and explicitly user-rejected round5 model binaries. Keep round4 immutable source, round5 unique failure figures/parameters/reports, current round6 editable/exported models and bounded donor data.'}
write(out/'cleanup.validation.json',receipt)
for p,row in zip(to_delete,new_deleted):
 assert p.resolve().is_relative_to(trial.resolve()) and sha(p)==row['sha256'];p.unlink()
receipt.update(ok=True,status='done',deleted_bytes=sum(r['bytes'] for r in deleted),retained=[bound(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ['cleanup.validation.json','three-navigation.validation.json']]);receipt['retained_bytes']=sum(r['bytes'] for r in receipt['retained']);receipt['volatile_excluded']=['three-navigation.validation.json: current live mouse state, not asset evidence'];write(out/'cleanup.validation.json',receipt)
old_cleanup=read(rejected/'cleanup.validation.json');old_cleanup['rejected_outputs_removed_in_round6']=[r for r in new_deleted if '/round5-' in r['path']];old_cleanup['current_user_rejection']=True;old_cleanup['retained']=[bound(p) for p in sorted(rejected.rglob('*')) if p.is_file() and p.name not in ['cleanup.validation.json','three-navigation.validation.json']];old_cleanup['retained_bytes_excluding_volatile']=sum(r['bytes'] for r in old_cleanup['retained']);write(rejected/'cleanup.validation.json',old_cleanup)
for p in (repo/'resources/scripts/volume-fish').glob('*nile*reference*.py'):ast.parse(p.read_text(encoding='utf8'))
print(json.dumps({'ok':True,'A':routes['A']['triangles'],'B':routes['B']['triangles'],'deleted_bytes':receipt['deleted_bytes'],'retained_bytes':receipt['retained_bytes'],'user_visual_acceptance':'pending'}))
