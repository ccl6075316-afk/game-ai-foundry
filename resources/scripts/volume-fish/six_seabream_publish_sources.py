"""Publish this pair's guarded wall-only sources; preserve compact provenance."""
import copy,json,hashlib,sys,shutil,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;G=ROOT/'projects/fishing-2d';B=G/'experiments/six-fish-database-20261104';RELEASE=G/'plans/reviews/six-fish-release-20261104'
sys.path[:0]=[str(HERE/'portable'),str(HERE)]
from glb_io import read_glb,arrays
from parts import freeze
from check_frozen_fish_static import fingerprint
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text(encoding='utf8'));ref=lambda p:{'path':str(Path(p).resolve()),'sha256':sha(p)}
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sheet(paths,dest,cols=3):
 out=Image.new('RGB',(cols*400,((len(paths)+cols-1)//cols)*300),(35,50,58));draw=ImageDraw.Draw(out)
 for i,p in enumerate(paths):
  im=Image.open(p).convert('RGB');im.thumbnail((395,270));x=(i%cols)*400;y=(i//cols)*300;out.paste(im,(x,y+24));draw.text((x+6,y+4),p.stem,fill='white')
 out.save(dest,quality=94)
for S in ['red_seabream','black_seabream']:
 D=B/S;O=RELEASE/S;A=G/'assets/source/fish'/S;C=G/f'game/assets/models/fish/{S}.glb'
 if(O/'release-inputs.json').exists():continue
 O.mkdir(parents=True,exist_ok=True);A.mkdir(parents=True,exist_ok=True)
 mapping=[]
 def retain(source,dest):
  source=Path(source);dest=Path(dest);assert source.is_file();dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(source,dest)
  assert sha(source)==sha(dest);mapping.append({'old_path':str(source.resolve()),**ref(dest),'bytes':dest.stat().st_size});return dest
 ledger=read(D/'production-review.json');spec=read(D/'wall-gates-r1/spec.json');proof=read(D/'fin-wall-r1/wall-uv.validation.json');assert read(D/'wall-delivery-r1/manifest.json')['specialized_checks_ok']
 retain(D/'production-review.json',O/'history/pre-wall-production-review.json')
 if not(O/'history/pre-wall-model.glb').exists():retain(C,O/'history/pre-wall-model.glb')
 retain(D/'fin-wall-r1/fish.blend',A/'fish.blend');retain(ledger['candidate_files']['source_image']['path'],A/'source.png');retain(spec['inputs']['atlas']['path'],A/'atlas.png');retain(spec['inputs']['packing_report']['path'],A/'packing-history.validation.json')
 anatomy=(G/'experiments/red-seabream-lowpoly-sop-20261101/neck-transition-20261101/candidate-r2/anatomical-witness/fish.blend')if S=='red_seabream'else(G/'experiments/black-seabream-lowpoly-sop-20261102/thickness-symmetry-20261102/width-source-r3/fish.blend');retain(anatomy,A/'anatomical-source.blend')
 retain(ledger['candidate_files']['material_author_model']['path'],O/'history/material-author-original.glb')
 domains=next(Path(v['path'])for v in ledger['evidence'].values()if 'masks.validation.json'in v['path']);dd=read(domains)
 for f in dd['fins']:
  if Path(f['image']).is_file():retain(f['image'],A/'native-fins'/Path(f['image']).name)
 retain(domains,A/'native-fin-domains.history.json')
 # Immutable historical ledger evidence stays in its original reporting scope.
 ev={}
 for eid,v in ledger['evidence'].items():
  p=Path(v['path']);q=O/'history/evidence'/(sha(p)[:16]+p.suffix);retain(p,q);ev[eid]={'kind':v['kind'],**ref(q),'original_path':str(p),'original_observation':v['observation']}
 retain(D/'fin-wall-r1/wall-uv.validation.json',O/'wall-uv.validation.json')
 for name in ['library-comparison.json','library-decision.validation.json','library-source.validation.json','library-body-comparison.png','library-renderer.validation.json','wall-source-compatibility.validation.json','wall-alpha.validation.json']:
  if(D/name).exists():retain(D/name,O/name)
 # Keep aggregate complete numeric results, not dense per-pose serialized geometry.
 for p in (D/'wall-delivery-r1').rglob('*.json'):
  if p.name.startswith('sample-')or'membrane-parts'in p.parts:continue
  retain(p,O/'measured-gates'/p.relative_to(D/'wall-delivery-r1'))
 review=D/'wall-delivery-r1/review';images=O/'images';images.mkdir(exist_ok=True)
 for mode in ['texture','clay']:
  sheet(sorted(review.glob('fin-*-oblique-'+mode+'.png')),images/('seven-fin-'+mode+'.jpg'))
 sheet([review/('head-'+v+'-'+m+'.png')for v in ['left','right','front','top','bottom','oblique']for m in ['texture','clay']],images/'head-mouth.jpg')
 sheet([review/('whole-'+v+'-'+m+'.png')for v in ['left','right','top','bottom']for m in ['texture','clay']],images/'whole-skin.jpg')
 sheet([review/'frames'/('frame-%04d.jpg'%i)for i in [0,32,60,110,160,220,246,258,270,282]],images/'motion.jpg')
 for name in ['water-natural-freshwater-left.png','water-natural-freshwater-oblique.png','fin-Pelvic_right_mesh-oblique-texture.png','fin-Pectoral_right_mesh-oblique-texture.png']:retain(review/name,images/name)
 # Prove oral/body material history transports under actual unchanged part arrays.
 nd,nb=read_glb(D/'fin-wall-r1/fish.glb');od,ob=read_glb(O/'history/pre-wall-model.glb');np_=nd['meshes'][0]['primitives'][0];op=od['meshes'][0]['primitives'][0];unchanged={}
 for key in ['POSITION','NORMAL','JOINTS_0','WEIGHTS_0']:
  unchanged[key]=bool(np.array_equal(arrays(nd,nb,np_['attributes'][key]),arrays(od,ob,op['attributes'][key])))
 unchanged['indices']=bool(np.array_equal(arrays(nd,nb,np_['indices']),arrays(od,ob,op['indices'])))
 uv=arrays(nd,nb,np_['attributes']['TEXCOORD_0']);ouv=arrays(od,ob,op['attributes']['TEXCOORD_0']);parts=[]
 for p in nd['extras']['geometry_parts']:
  if p['role']=='fin':continue
  start=p['vertex_start'];stop=start+p['vertex_count'];same=bool(np.array_equal(uv[start:stop],ouv[start:stop]));assert same;parts.append({'name':p['logical_name'],'role':p['role'],'UV_exact':same,'vertices':p['vertex_count']})
 def rgba(d,b):
  v=d['bufferViews'][d['images'][0]['bufferView']];return np.array(Image.open(io.BytesIO(b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGBA'))
 assert all(unchanged.values())and np.array_equal(rgba(nd,nb),rgba(od,ob))
 assert sha(C)in[sha(O/'history/pre-wall-model.glb'),sha(D/'fin-wall-r1/fish.glb')];shutil.copy2(D/'fin-wall-r1/fish.glb',C);retain(D/'fin-wall-r1/fish.glb',C)
 spec.pop('production',None);spec.update(model=ref(C),authoring_delta={'kind':'native_cap_alpha_matched_fin_wall_uv_repair','report':str(O/'wall-uv.validation.json'),'sha256':sha(O/'wall-uv.validation.json')})
 spec['inputs'].update(source_blend=ref(A/'fish.blend'),reference_glb=ref(C),atlas=ref(A/'atlas.png'),packing_report=ref(A/'packing-history.validation.json'),wall_uv_repair=ref(O/'wall-uv.validation.json'))
 write(O/'spec.json',spec)
 temp=D/'publish-parts.json'
 if not temp.exists():freeze(C,spec,temp)
 retain(temp,O/'parts-manifest.json')
 plan=read(D/'wall-gates-r1/fin.plan.json');p=plan['items'][0];p.update(model=str(C),model_sha256=sha(C),packed_parts_manifest=str(O/'parts-manifest.json'),packed_parts_manifest_sha256=sha(O/'parts-manifest.json'))
 p['frozen_inputs']={str(x):sha(x)for x in [C,A/'fish.blend',A/'atlas.png',O/'spec.json',O/'parts-manifest.json',O/'wall-uv.validation.json',Path(p['motion_profile']),Path(p['motion_runtime']),HERE/'portable/PackedFishParts.gd',HERE/'portable/parts.py',HERE/'portable/export_fin_poses.gd']};p['scope']='Recheck recipe for canonical same-byte reviewed wall repair. Historical run plan remains immutable; this migrated plan has not itself been given that historical plan SHA pass.';write(O/'recheck-fin.plan.json',plan)
 config=read(D/'wall-gates-r1/delivery-config.json');config.update(final_spec=str(O/'spec.json'),fin_plan=str(O/'recheck-fin.plan.json'),ordinary_reference=str(O/'history/material-author-original.glb'),review_sources=[str(A/'source.png'),str(O/'wall-uv.validation.json')]);write(O/'delivery-config.json',config)
 entry=read(D/'wall-local-r1/review.plan.json');entry.update(model=str(C),model_sha256=sha(C),packed_parts_manifest=str(O/'parts-manifest.json'),packed_parts_manifest_sha256=sha(O/'parts-manifest.json'),frozen_inputs=p['frozen_inputs']);write(O/'entry.plan.json',entry)
 write(A/'frozen-static.json',{'kind':'accepted_fish_static_freeze','static':fingerprint(C),'future_scope':'Motion only by default. Explicit user reopening required for geometry/UV/material/skin/skeleton changes.'})
 write(O/'unchanged-domain-transport.validation.json',{'ok':True,'species':S,'model':ref(C),'baseline':ref(O/'history/pre-wall-model.glb'),'editable_source':ref(A/'fish.blend'),'actual_unchanged_arrays':unchanged,'non_fin_parts':parts,'embedded_decoded_RGBA_exact':True,'wall_source_guard':ref(O/'wall-uv.validation.json'),'historical_scope':'Native-lip material author report and fin-volume report remain historical. Their relevant unchanged geometry/normal/UV/RGBA domains are independently measured here for current model. New490/072/077/head/motion separately executed on new SHA; no report SHA relabeling.'})
 write(O/'release-inputs.json',{'species':S,'historical_evidence':ev,'retention':mapping,'previous_ledger':ref(O/'history/pre-wall-production-review.json'),'user_quote':'先修真鲷鳍悬空细框，然后本轮六鱼全收成品、安装/清理旧实验大截图/提交push。','static_change':'Closing-wall UV only; atlas RGBA, natural native fin silhouette/rays and all non-fin UV unchanged.','new_model':ref(C),'editable_source':ref(A/'fish.blend'),'final_spec':ref(O/'spec.json'),'release_source_ready':True})
 print(json.dumps({'species':S,'model':ref(C),'source':ref(A/'fish.blend'),'spec':ref(O/'spec.json'),'ready_for_canonical':True}),flush=True)
