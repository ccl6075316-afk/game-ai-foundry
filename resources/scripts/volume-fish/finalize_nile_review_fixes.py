"""Freeze user-review repair evidence and clean exact round5 disposable files."""
import json,hashlib,subprocess,ast
from pathlib import Path
repo=Path(__file__).resolve().parents[3];game=repo/'projects/fishing-2d';out=game/'experiments/nile-dorsal-route-trial/round5-user-review-fixes'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def bound(p):return {'path':str(p.relative_to(repo)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size}
live=read(out/'three-live.validation.json');controls=read(out/'three-interactive-input.validation.json');assert live['ok'] and controls['ok'] and controls['synchronized_views']==3
assert sha(game/'game/assets/models/fish/nile_tilapia.glb')=='4ee2c552939b682463120b52e40f2f98e996c2dad8f91f9144ab7d6de51ad25a'
routes={}
for route in ['A','B']:
 d=out/(route+'-artifacts');build=read(d/'validation.json');root=read(d/'fin-gate/completion.validation.json');assert root['ok'] and root['checks'][0]['poses']==177
 for name in ['fish.blend','fish.glb']:assert sha(d/name)==build['hashes'][name]
 observed=next(row for row in live['models'] if row['route']==route);assert observed['model_sha256']==sha(d/'fish.glb') and observed['triangles']==build['triangles']
 routes[route]={'model':bound(d/'fish.glb'),'editable_source':bound(d/'fish.blend'),'triangles':build['triangles'],'body_closed':build['body_closed'],'tail_and_all_fins_geometry_uv_weights_unchanged':build['all_fin_geometry_uv_weights_unchanged'],'thickness':build['fin_thickness'],'root_numeric_check':bound(d/'fin-gate/completion.validation.json'),'root_contact_certification':route=='B','root_qualification':'A open-body prerequisite still fails; numeric diagnostic only.' if route=='A' else 'Current closed B,7fins177poses pass.','oral_trim':build['oral_trim']}
report={'kind':'nile_user_review_local_repair','ok':True,'status':'experimental_revision_ready_for_visual_review','next_action':'human_review','formal_acceptance':False,'user_visual_acceptance':'pending','routes':routes,'findings':{'pectoral_black_rays':'Hidden-fin GPU views locate the mark on the body. It came from the old directional ventral chart, not the office whole-body clean skin. A/B reused that chart in the offline atlas; current bounded repair samples the continuous office donor and excludes its lower outline.','mouth_black_inward_lips':'Round4 combined dark source outline wrap with uniform darkest-source cavity material on outward-visible inward jaw faces. Current B uses a tapered actual oral cut, source-bound same-jaw lining and bounded removal of inward outline pixels.','fin_thickness':'Actual solid front/back surfaces and walls exist. Pectoral0.08-0.40mm,dorsal0.10-0.55mm; most normal-size edges are subpixel. Existing thickness has NOT been arbitrarily increased or declared visually accepted.','tail':'User says current tail is acceptable; every fin/tail vertex,UV,weight/topology digest unchanged.','original_column':'Original116994 retained with its old saved materials as a baseline; its old belly pollution remains visible for comparison. A/B are the repaired columns.'},'controls':{'live_launcher':'.venv/Scripts/python.exe resources/scripts/volume-fish/open_nile_ab_review.py','previous_round_option':'--round4','new_button':'鳍厚度（放大）','return_button':'完整鱼','input_smoke_report':bound(out/'three-interactive-input.validation.json'),'live_report':bound(out/'three-live.validation.json')},'evidence':{name:bound(out/name) for name in ['pectoral-before-after.jpg','mouth-before-after.jpg','B-fin-thickness-edge.png','diagnostic-cold-render.validation.json','diagnostic-cold-render-after.validation.json']},'pending':['User review of repaired belly and inward lip shape/material','User judgment of visible fin thickness','Complete formal body/GPU and490whole-fin/native gates and SOP remain unapproved.'],'script_inputs':{name:sha(repo/'resources/scripts/volume-fish'/name) for name in ['prepare_nile_review_fixes.py','build_nile_review_fixes.py','oral_jaws.py','preview_nile_three_live.gd','diagnose_nile_review.gd']},'generation_calls':0,'new_external_generation_fees':0}
write(out/'review.validation.json',report)
review=read(out/'sop-review.json')
files={'source_image':out.parent/'round4-ab-textured/shared/body-side.png','model':out/'B-artifacts/fish.glb','species_profile':repo/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json','runtime_manifest':out/'review.validation.json','motion_config':repo/'resources/volume-fish/motion/nile_tilapia-082.json','editable_blend':out/'B-artifacts/fish.blend'}
review['candidate_files']={k:{'path':str(p),'sha256':sha(p)} for k,p in files.items()}
for stage in review['stages'].values():stage['observations']='Local user-review revision only. Read review.validation.json; no complete formal or user acceptance asserted.'
write(out/'sop-review.json',review)
check=subprocess.run([str(repo/'.venv/Scripts/python.exe'),'cli/gamefactory.py','volume','sop-check','--review',str(out/'sop-review.json'),'--output',str(out/'sop-check.validation.json'),'--json'],cwd=repo,capture_output=True,text=True,encoding='utf8');assert not json.loads(check.stdout)['ok']
files=[]
for route in ['A','B']:
 for p in [out/f'{route}-artifacts/fish.blend1',out/f'{route}-artifacts/fin-gate/export.log',out/f'{route}-artifacts/fin-gate/nile_tilapia/check.log']:
  if p.exists():files.append(p)
previous=read(out/'cleanup.validation.json') if (out/'cleanup.validation.json').exists() else {}
new_deleted=[bound(p) for p in files];deleted=previous.get('deleted',[])+new_deleted
receipt={'ok':False,'status':'prepared','deleted':deleted,'scope':'Only local intermediate Blender backups and successful checker logs. Keep old round4 inputs and current editable/exported assets, donor maps and unique before/after evidence.'}
write(out/'cleanup.validation.json',receipt)
for p,row in zip(files,new_deleted):assert p.resolve().is_relative_to(out.resolve()) and sha(p)==row['sha256'];p.unlink()
volatile={'three-navigation.validation.json','cleanup.validation.json'}
receipt.update(ok=True,status='done',deleted_bytes=sum(r['bytes'] for r in deleted),retained=[bound(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in volatile],volatile_files=['three-navigation.validation.json: live navigation diagnostics only; intentionally not a frozen asset hash'])
receipt['retained_bytes_excluding_volatile']=sum(r['bytes'] for r in receipt['retained']);write(out/'cleanup.validation.json',receipt)
for name in ['prepare_nile_review_fixes.py','build_nile_review_fixes.py','finalize_nile_review_fixes.py','open_nile_ab_review.py']:ast.parse((repo/'resources/scripts/volume-fish'/name).read_text(encoding='utf8'))
print(json.dumps({'ok':True,'A':routes['A']['triangles'],'B':routes['B']['triangles'],'deleted_bytes':receipt['deleted_bytes'],'retained_bytes':receipt['retained_bytes_excluding_volatile'],'formal_acceptance':False}))
