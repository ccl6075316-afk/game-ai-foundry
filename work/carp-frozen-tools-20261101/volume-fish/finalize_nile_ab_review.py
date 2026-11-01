"""Freeze review evidence and remove only explicitly regenerable round4 outputs."""
import json,hashlib,io,struct
from pathlib import Path
from PIL import Image
repo=Path(__file__).resolve().parents[3];game=repo/'projects/fishing-2d'
out=game/'experiments/nile-dorsal-route-trial/round4-ab-textured'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bound(p):return {'path':str(p.relative_to(repo)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size}
def glb(p):
 b=p.read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);return j,b[28+n:]
assert out.resolve().is_relative_to(game.resolve())
baseline={'experiments/nile-tilapia-static-merge/nile_tilapia-static.blend':'32ed543993bfc3927c17f1bc19e1b3d91a8b95d9aeb9adcc7da0727ad88f2c6b','game/assets/models/fish/nile_tilapia.glb':'4ee2c552939b682463120b52e40f2f98e996c2dad8f91f9144ab7d6de51ad25a'}
for name,value in baseline.items():assert sha(game/name)==value,name+' original changed'
recipe=read(out/'comparison.plan.validation.json');cold=read(out/'cold-render.validation.json');assert cold['ok'] and not cold['static_construction_chain']
records={}
for route in ['A','B']:
 directory=out/(route+'-artifacts');build=read(directory/'validation.json');roots=read(directory/'fin-gate/completion.validation.json')
 assert roots['ok'] and roots['checks'][0]['poses']==177
 doc,binary=glb(directory/'fish.glb');texture={}
 for row in doc['materials']:
  if row['name']=='body_skin':
   assert row['alphaMode']=='OPAQUE';idx=row['pbrMetallicRoughness']['baseColorTexture']['index'];image=doc['images'][doc['textures'][idx]['source']];view=doc['bufferViews'][image['bufferView']];blob=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
   embedded=Image.open(io.BytesIO(blob)).convert('RGBA');expected=Image.open(out/'shared/body-atlas.png').convert('RGBA');assert embedded.size==expected.size and embedded.tobytes()==expected.tobytes(),'Exported skin differs'
   assert embedded.getchannel('A').getextrema()==(255,255)
   texture={'embedded_pixels_equal_shared_atlas':True,'size':list(embedded.size),'alpha_range':[255,255],'alpha_mode':'OPAQUE'}
 assert texture
 assert build['hashes']['fish.glb']==sha(directory/'fish.glb') and build['hashes']['fish.blend']==sha(directory/'fish.blend')
 model=next(row for row in cold['models'] if row['route']==route);assert model['model_sha256']==sha(directory/'fish.glb') and model['triangles']==build['triangles']
 records[route]={'triangles':build['triangles'],'parts':build['parts'],'body_closed':build['topology']['Closed_body' if route=='A' else 'Closed_body_B']['closed'],'fin_root_gate':{'poses':177,'fins':7,'numeric_report_pass':True,'closed_body_prerequisite_met':route=='B','certified_contact_pass':route=='B','qualification':'A has open-body boundaries, so signed nearest-distance results are diagnostic only despite numerical threshold pass.' if route=='A' else 'Closed B body prerequisite and177 discrete root-distance samples passed.','report':bound(directory/'fin-gate/completion.validation.json')},'body_texture':texture,'editable':bound(directory/'fish.blend'),'model':bound(directory/'fish.glb'),'build_report':bound(directory/'validation.json'),'successful_build_process_seconds':build['process_seconds']}
report={'kind':'nile_AB_textured_comparison','status':'experimental_comparison_ready','next_action':'human_review','ok':True,'formal_acceptance':False,'user_visual_acceptance':'pending','scope':'User-authorized A frozen1492 geometry + material and B new whole sparse cage + same material. Experimental outputs, not installed production fish.','routes':records,'budget':{'unit':'triangles','preferred_max':1500,'hard_max':2000,'all_body_mouth_fins_both_faces_walls_and_eyes_included':True,'raised_eye_meshes':0,'eyes':'Original painted eyes on both body sides'},'B_method_evidence':{'method_reference':'resources/skills/fish-volume-production/references/reference-cage-body.md','profile':bound(repo/recipe['profile']),'control_cage':bound(out/'B-artifacts/control-cage.validation.json'),'body_loops':25,'radial_points':16,'control_vertices':400,'old_dense_mesh_topology_read':False,'dense_mesh_reduction_used':False,'rig':'Shared existing accepted rig/clip only; no old skin read in B.','fin_method':'Native per-part outline/complete basal polyline cages; shared fin topology recipe with A.'},'static_asset_freeze':{'geometry_uv_weights':'Saved in editable blend and exported GLB','materials':'Ordinary embedded GLB nearest PBR textures; opaque body, alpha-scissor fins','godot_static_model_builders_called':0,'godot_runtime_behavior':'Existing FoundryFishMotion controller and native clip','cold_render_report':bound(out/'cold-render.validation.json'),'original_assets_unchanged':baseline},'visual_observations':['Actually inspected side, reverse side, front, top, oblique, clay/textured, action and transition images.','A/B side silhouettes and common-skin appearances are close. B has fewer triangles and a closed body; A existing collapsed body has open/nonmanifold boundaries.','B snout is integrated with real oral roof/floor, not an added pointed lip; flat source eyes are visible on both sides.','142 protected pectoral connector remains visible. New shared skin uses the office whole body-clean donor rather than seven hard patches.','Front/upper texture remains a static artistic projection with directional donors; no new biological transverse measurement or user visual approval claimed.'],'cost':{'new_image_or_model_service_calls':0,'new_image_or_model_service_fee':0,'currency':'No added external generation charge; this is NOT a statement about Codex subscription/token cost.','historical_A_body_reduction_and_shared_B_fins_time':'unknown','Codex_tokens_and_total_agent_time_cost':'not measured; no percentage savings claimed','common_preparation_process_seconds':recipe['common_preparation_seconds'],'successful_script_process_seconds_only':{r:records[r]['successful_build_process_seconds'] for r in records},'comparability_limit':'A already includes earlier B fin-cage work; B reuses the same rig, material preparation and fin-cage recipe. Script times exclude development/debugging, retries, review and historical costs.','implementation_rework':['Blender5 default node names required explicit node creation.','Blender-only process lacks PIL: accepted archive source verification delegated to existing venv.','All JSON reads now specify UTF-8 on Windows.','Rig-only export must remove skinned children in disposable process; importer custom bone shapes excluded.','A original body closure failure recorded without changing frozen A geometry.','Godot viewport captures center-cropped without rescaling model pixels; movie initially top-cropped, corrected before review.']},'remaining_formal_gates':['User visual selection/approval','Full490 fin membrane/body and native-cycle absolute checks','Body integrity/GPU alpha coverage and head transverse final checks','All applicable final SOP and actual game installation review'],'source_gate_receipt_note':'B.json is the immutable accepted-source planning receipt. It is NOT the execution queue for this custom experimental builder. Read this comparison validation as current state; do not invoke generic volume build on its body-only profile.','reproduce':{'prepare':'.venv/Scripts/python.exe resources/scripts/volume-fish/prepare_nile_ab_trial.py (only before freezing inputs)','build_A':'blender --background --python resources/scripts/volume-fish/build_nile_ab_textured.py -- --route A','build_B':'blender --background --python resources/scripts/volume-fish/build_nile_ab_textured.py -- --route B','live_view':'.venv/Scripts/python.exe resources/scripts/volume-fish/open_nile_ab_review.py','capture':'godot --path projects/fishing-2d/game --rendering-method gl_compatibility --script resources/scripts/volume-fish/preview_nile_ab_textured.gd -- <absolute round4 directory> --movie','package':'.venv/Scripts/python.exe resources/scripts/volume-fish/package_nile_ab_review.py'},'evidence':{name:bound(out/name) for name in ['comparison-texture.jpg','comparison-clay.jpg','comparison-other-views.jpg','comparison-motion.mp4','B-control-cage.jpg']}}
write(out/'comparison.validation.json',report)

# Keep original inputs, both current editable/exported models, current reports,
# source references and representative images/video. Delete exact candidates only.
delete=[]
for directory in ['movie-frames','movie-labeled']:
 folder=out/directory
 if folder.exists():
  for p in sorted(folder.iterdir()):
   assert p.is_file() and p.name.startswith('frame-') and p.suffix=='.jpg'
   delete.append(p)
delete.extend(p for p in [out/'review-contact.jpg',out/'A-artifacts/fish.blend1',out/'B-artifacts/fish.blend1'] if p.exists())
for route in ['A','B']:
 for p in [out/f'{route}-artifacts/fin-gate/export.log',out/f'{route}-artifacts/fin-gate/nile_tilapia/check.log']:
  if p.exists():delete.append(p)
previous=read(out/'cleanup.validation.json') if (out/'cleanup.validation.json').exists() else {}
deleted=previous.get('deleted',[])+[bound(p) for p in delete]
receipt={'ok':False,'status':'prepared','scope':'Only current-round regenerable frame sequences, successful debug logs, duplicate contact sheet and Blender backup; source/current models/reports kept.','deleted':deleted}
write(out/'cleanup.validation.json',receipt)
for p in delete:
 assert p.resolve().is_relative_to(out.resolve()) and sha(p)==next(row['sha256'] for row in deleted if row['path']==str(p.relative_to(repo)).replace('\\','/'))
 p.unlink()
for directory in ['movie-frames','movie-labeled']:
 folder=out/directory
 if folder.exists():assert not list(folder.iterdir());folder.rmdir()
receipt.update(ok=True,status='done',deleted_bytes=sum(row['bytes'] for row in deleted),deleted_files=len(deleted),retained=[bound(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='cleanup.validation.json'])
receipt['retained_bytes_excluding_receipt']=sum(row['bytes'] for row in receipt['retained'])
write(out/'cleanup.validation.json',receipt)
print(json.dumps({'ok':True,'A':records['A']['triangles'],'B':records['B']['triangles'],'deleted_files':len(deleted),'deleted_bytes':receipt['deleted_bytes'],'retained_bytes':receipt['retained_bytes_excluding_receipt']}))
