"""Block body holes: welded shell topology, opaque donor/bindings and real GPU coverage.

Run after freeze_body_opacity.py. Mouth cavities remain model geometry, not an
alpha exemption. Fins are excluded using the complete per-species inventory.
"""
import argparse,hashlib,json,subprocess,sys,re
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ['game','godot','output']:p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--species',action='append',help='Explicit species inventory for a local repair; default checks all fish.')
 p.add_argument('--source-body-plan',type=Path,help='Exact validated-baseline body arrays/material plus RGB-only attachment wrapper; requires the143 preservation/GPU capture contract.')
 p.add_argument('--mouth-runtime-report',type=Path,help='Fresh actual139 replacement mesh/material/GPU report; checks the replacement rather than the original GLB body.')
 p.add_argument('--mouth-candidate-plan',type=Path,help='Frozen139 geometry, skinning and resource bindings required with --mouth-runtime-report.')
 a=p.parse_args()
 if a.mouth_runtime_report:
  from validate_mouth_body139 import validate
  if not a.mouth_candidate_plan:raise ValueError('--mouth-candidate-plan is required for actual139 body validation')
  result=validate(a.game.resolve(),a.mouth_runtime_report.resolve(),a.output.resolve(),a.mouth_candidate_plan.resolve());print(json.dumps({'ok':result['ok'],'error':result.get('error'),'records':len(result.get('records',[]))}));return 0 if result['ok'] else 1
 a.game=a.game.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);records=[];capture_process={}
 try:
  for shader in ['FishBodyOpaque.gdshader','FishMouthPigment.gdshader']:
   code=(a.game/'scripts/aquarium'/shader).read_text(encoding='utf8')
   code=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',code)
   assert not re.search(r'\b(?:ALPHA|ALPHA_SCISSOR_THRESHOLD|ALPHA_HASH_SCALE|discard)\b',code),'Body shader can discard body coverage: '+shader
  models=a.game/'assets/models/fish';own=json.loads((models/'motion/surface-ownership.json').read_text());opaque=json.loads((models/'motion/body-opacity.json').read_text());files=sorted(models.glob('*.glb'));assert files,'No fish models';assert set(opaque['profiles'])=={x.stem for x in files},'Incomplete opacity species inventory'
  if a.species:
   assert len(a.species)==len(set(a.species)) and set(a.species)<={f.stem for f in files},'Unknown/duplicate requested body species'
   files=[f for f in files if f.stem in a.species]
  for f in files:
   sp=f.stem;d,b=read_glb(f);profile=opaque['profiles'][sp];assert sha(f)==profile['model_sha256'];bodies=[]
   for n in d['nodes']:
    if 'mesh' not in n or n['name'] in own['profiles'][sp]['fins']:continue
    if n['name'] in profile.get('decorative_overlays',{}):
     layer=profile['decorative_overlays'][n['name']]
     if sp=='zander' and n['name'] in {'Eye_relief112_-1_0','Eye_relief112_1_0'} and layer=={'underlying_body':'Closed_body','kind':'frozen_eye_relief160'}:
      # A native skinned eye cap overlays the separately validated closed body.
      assert len(d['meshes'][n['mesh']]['primitives'])==1 and n.get('skin')==0,'Invalid frozen eye overlay'
      continue
     assert sp=='arapaima' and n['name']=='Frontal_head_overlay' and layer['underlying_body']=='Closed_body','Unrecognized decorative layer'
     mats=[d['materials'][p['material']] for p in d['meshes'][n['mesh']]['primitives']]
     assert len(mats)==17 and all(m.get('alphaMode') in ['MASK','BLEND'] for m in mats),'Missing authored alpha fusion'
     assert [round(m.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])[3]*16) for m in mats]==list(range(17)),'Changed overlay alpha weights'
     continue
    if n['name'] in profile['suppressed_auxiliary']:
     assert n['name'].startswith('Textured_eye') and all(d['materials'][p['material']].get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])[3]==0 for p in d['meshes'][n['mesh']]['primitives']),'Invalid auxiliary exclusion'
     continue
    edges=Counter()
    for si,prim in enumerate(d['meshes'][n['mesh']]['primitives']):
     pos=accessor(d,b,prim['attributes']['POSITION']);tri=accessor(d,b,prim['indices']).reshape(-1,3);pts=[tuple(round(float(x),7) for x in v) for v in pos]
     for face in tri:
      q=[pts[x] for x in face];assert len(set(q))==3,'Degenerate body triangle'
      for x,y in zip(q,q[1:]+q[:1]):edges[tuple(sorted([x,y]))]+=1
     mat=d['materials'][prim['material']]
     if mat.get('pbrMetallicRoughness',{}).get('baseColorTexture') is not None:
      donor=profile['surfaces'][n['name']][str(si)];path=a.game/donor['texture'].removeprefix('res://');assert sha(path)==donor['texture_sha256'];assert np.all(np.asarray(Image.open(path).convert('RGBA'))[:,:,3]==255),'Transparent donor'
    assert edges and all(v==2 for v in edges.values()),'Open/nonmanifold body shell: '+sp+'/'+n['name']
    bodies.append(n['name'])
   assert all(v['underlying_body'] in bodies for v in profile.get('decorative_overlays',{}).values()),'Overlay lacks validated closed underlying skin'
   assert bodies,'Empty body selection';records.append({'species':sp,'model_sha256':sha(f),'closed_body_meshes':bodies})
  source_body_plan=None
  if a.source_body_plan:
   source_body_plan=json.loads(a.source_body_plan.read_text());assert source_body_plan['ok'] and a.species and set(source_body_plan['species'])<=set(a.species)
   for path,h in source_body_plan['frozen_inputs'].items():assert sha(path)==h,'Stale source-body preservation reference: '+path
   baseline=json.loads(Path(source_body_plan['baseline_body_gate']).read_text());assert baseline['ok'] and {x['species']for x in baseline['species']}>=set(a.species),'Unvalidated baseline body'
  capture=Path(__file__).with_name('capture_source_body143.gd' if source_body_plan else 'capture_body_coverage.gd');out=a.output/'captures'
  receipt=out/'capture.validation.json'
  if receipt.exists():receipt.unlink()
  import os
  capture_env=os.environ.copy()
  if source_body_plan:capture_env['FOUNDRY_SOURCE_BODY143_PLAN']=str(a.source_body_plan.resolve())
  run=subprocess.run([str(a.godot),'--path',str(a.game),'--quit-after','1200','--script',str(capture),'--',str(out),*(a.species or [])],env=capture_env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180);(a.output/'capture.log').write_text(run.stdout+run.stderr,encoding='utf8');capture_process={'returncode':run.returncode,'quit_after_frames':1200,'receipt_exists':receipt.exists(),'logged_error':'ERROR:' in run.stdout+run.stderr};assert run.returncode==0 and 'ERROR:' not in run.stdout+run.stderr and receipt.exists(),'GPU capture failed'
  data=json.loads(receipt.read_text());assert len(data['records'])==len(files)*2
  assert {(x['species'],x['pose']) for x in data['records']}=={(f.stem,pose) for f in files for pose in [0,1]},'Incomplete captured species/pose inventory'
  for record in data['records']:
   assert record['views']==8 and record['model_sha256']==sha(models/(record['species']+'.glb')),'Stale or incomplete body capture'
  for file,digest in data['files'].items():assert sha(a.game/file)==digest,'Changed runtime during capture'
  for row in records:
   row['views']=[]
   for pose in range(2):
    for view in range(8):
     stem=out/row['species']/f'p{pose}-v{view}';act=stem.with_name(stem.name+'-actual.png');ref=stem.with_name(stem.name+'-closed.png');x=np.asarray(Image.open(act));y=np.asarray(Image.open(ref));assert x.shape==y.shape and x.shape[-1]==4
     mask=y[:,:,3]>128;assert mask.sum()>30,'Empty reference body'
     missing=int((mask&(x[:,:,3]<128)).sum());row['views'].append({'pose':'neutral' if pose==0 else 'maximum_amplitude','view':view,'missing_body_pixels':missing,'actual_sha256':sha(act),'reference_sha256':sha(ref)})
   row['ok']=all(v['missing_body_pixels']==0 for v in row['views'])
  result={'ok':all(x['ok'] for x in records),'species':records,'capture_files':data['files'],'checker_sha256':sha(__file__),'capture_script_sha256':sha(capture),'body_opacity_sha256':sha(models/'motion/body-opacity.json'),'views_per_species':16,'method':'Closed welded non-fin shells; opaque donor inventory; actual GPU material alpha coverage compared with opaque double-sided render of identical body geometry. No mouth alpha exemption.','limits':'16 discrete views/poses per species, not exhaustive continuous visibility proof; actual geometry cavities retain their inner surfaces.'}
  if source_body_plan:
   assert all(sha(path)==h for path,h in source_body_plan['frozen_inputs'].items()),'Source body reference changed during capture'
   result['source_body_plan_sha256']=sha(a.source_body_plan);result['baseline_body_gate_sha256']=sha(source_body_plan['baseline_body_gate']);result['replacement_material_scope']='Exact baseline body arrays and all previous shader inputs/pixels, with only the frozen RGB attachment wrapper. Current16-pose/view GPU coverage retained without tolerances relaxed.'
 except Exception as e:result={'ok':False,'error':str(e),'species':records}
 result['capture_process']=capture_process
 (a.output/'completion.validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':result['ok'],'species':len(records),'error':result.get('error'),'capture_process':capture_process}));return 0 if result['ok'] else 1
if __name__=='__main__':sys.exit(main())
