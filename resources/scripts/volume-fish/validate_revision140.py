"""Verify the seven-fish140 delta, without promoting it to user acceptance."""
import argparse,json,hashlib
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--game',type=Path,required=True);a=p.parse_args();r=a.root;rows=[]
 try:
  plan=read(r/'install140.plan.json');selected=set(plan['changed_species']);assert len(selected)==7 and not any(s.endswith('hammerhead') for s in selected);cfg=a.game/'assets/models/fish/motion/mouth-repair139.json';assert read(cfg)==plan['config'];cfgsha=sha(cfg)
  assert read(r/'runtime-final2/completion.validation.json')['ok'];body=read(r/'runtime-final2/body-integrity/completion.validation.json');assert body['ok'] and body['candidate_plan_sha256']==sha(r/'install140.plan.json') and {x['species'] for x in body['records']}==selected
  controls=read(r/'controls-final2.validation.json');assert controls['ok'] and controls['config_sha256']==cfgsha and len(controls['checks'])==14
  lips=read(r/'lip-runtime-final/completion.validation.json');assert lips['ok'] and lips['candidate_plan_sha256']==sha(r/'install140.plan.json');assert read(r/'lip-contact140.validation.json')['ok']
  capture=read(r/'delivery-final2/capture.validation.json');video=read(r/'delivery-final2/video.validation.json');assert capture['ok'] and video['ok'] and capture['config_sha256']==cfgsha and video['capture_sha256']==sha(r/'delivery-final2/capture.validation.json');assert {x['species'] for x in capture['rows']}==selected
  source=read(r/'source-canvas-final/capture.validation.json');assert source['ok'] and source['config_sha256']==cfgsha and {x['species'] for x in source['rows']}==selected
  visual=read(r/'visual-review140.validation.json');assert visual['ok'] and visual['config_sha256']==cfgsha and set(visual['records'])==selected
  for dep in [r/'delivery-final2.stderr.log',r/'source-canvas-final.log',r/'controls-final2.log',r/'lip-runtime-final.log']:assert 'ERROR:' not in dep.read_text(encoding='utf8'),'Engine error: '+str(dep)
  for item in plan['items']:
   s=item['species']
   if s not in selected:continue
   assert sha(a.game/f'assets/models/fish/{s}.glb')==item['profile']['source_model_sha256']
   for src,rel in item['copies'].items():assert sha(src)==sha(a.game/rel)
   for role in ['geometry','skinning_report']:assert sha(item[role]['path'])==item[role]['sha256']
   for field in ['revision140_appearance_inputs','revision140_final_chart_inputs']:
    for path,digest in item.get(field,{}).items():assert sha(path)==digest,('Stale source input',path)
   fp=r/s/'fin.plan.json';spec=read(fp)['items'][0];roots=read(r/s/'root177/completion.validation.json');full=read(r/s/'membrane490/completion.validation.json');export=read(r/s/f'full490/{s}/export.validation.json')
   assert roots['ok'] and roots['plan_sha256']==sha(fp) and roots['checks'][0]['poses']==177
   assert full['ok'] and full['poses']==490 and full['plan_sha256']==sha(fp)
   expected={item['geometry']['path']:item['geometry']['sha256'],item['skinning_report']['path']:item['skinning_report']['sha256']}
   if s=='peacock_bass':expected[item['fin_geometry']['path']]=item['fin_geometry']['sha256']
   assert spec['mouth_candidate']['frozen_inputs']==export['candidate_input_sha256']==expected
   assert export['exhibit_sha256']==sha(a.game/'scripts/aquarium/VolumeFishExhibit.gd') and export['controller_sha256']==sha(a.game/export['controller_source'][6:])
   for check in full['checks']:assert check['ok'] and sha(check['report'])==check['sha256']
   if s in ['red_seabream','black_seabream']:
    skin=read(r/s/'skin/skin.validation.json');assert skin['ok'] and skin['donors_outside_safe_domain']==0 and skin['source_modified'] is False and skin['builder_sha256']==sha(Path(__file__).with_name('build_source_skin140.py'))
    for name,digest in skin['outputs'].items():assert sha(r/s/'skin'/name)==digest
   if item.get('candidate_lips'):assert sha(item['candidate_lips']['path'])==item['candidate_lips']['sha256']
   if item.get('retained_lower_report'):assert read(item['retained_lower_report']['path'])['ok'] and sha(item['retained_lower_report']['path'])==item['retained_lower_report']['sha256']
   rows.append({'species':s,'ok':True,'root_poses':177,'membrane_poses':490,'body_resource_sha256':item['profile']['body']['sha256'],'lip_resource_sha256':item['profile'].get('lips',{}).get('sha256'),'fin_plan_sha256':sha(fp),'root_report':str(r/s/'root177/completion.validation.json'),'full_report':str(r/s/'membrane490/completion.validation.json')})
  result={'ok':len(rows)==7,'revision_ready':len(rows)==7,'whole_fish_acceptance':False,'install_plan_sha256':sha(r/'install140.plan.json'),'records':rows,'runtime_sha256':sha(r/'runtime-final2/completion.validation.json'),'controls_sha256':sha(r/'controls-final2.validation.json'),'lip_binding_sha256':sha(r/'lip-runtime-final/completion.validation.json'),'media_sha256':sha(r/'delivery-final2/capture.validation.json'),'visual_review_sha256':sha(r/'visual-review140.validation.json'),'checker_sha256':sha(__file__),'scope':'Authorized140 local repair/regression only. New upper/head or named chin changes, original accepted/tolerated lower lips retained as recorded, two body texture repairs. Not user visual approval or whole-fish acceptance.'}
 except Exception as e:result={'ok':False,'revision_ready':False,'error':str(e),'records':rows}
 (r/'delivery140.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps({'ok':result['ok'],'fish':len(rows),'error':result.get('error')}));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
