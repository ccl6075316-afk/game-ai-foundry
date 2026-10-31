"""Author, cold export and locally capture one fresh width experiment.

Does not grant physical, anatomical, visual or final SOP acceptance.
"""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['directory','blender','godot']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();out=a.directory.resolve();plan=json.loads((out/'deformation.plan.json').read_text(encoding='utf8'));manifest=out/'manifest.json';m=json.loads(manifest.read_text(encoding='utf8'))
 assert m['status']=='pending'and not(out/'fish.glb').exists()
 def save():manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 m.update(status='running',next_action='poll',stages=[]);save()
 stages=[('author',[str(a.blender),'--background','--python-exit-code','1','--python',str(HERE/'author_transverse_width_trial.py'),'--','--plan',str(out/'deformation.plan.json'),'--output',str(out/'fish.blend'),'--report',str(out/'source.validation.json')]),('cold-export',[str(a.blender),'--background','--python-exit-code','1','--python',str(HERE/'portable/export_source.py'),'--','--blend',str(out/'fish.blend'),'--output',str(out/'fish.glb'),'--report',str(out/'cold-export.validation.json')]),('invariants',[sys.executable,str(HERE/'validate_transverse_width_trial.py'),'--directory',str(out)]),('capture',[str(a.godot),'--path',str(ROOT/'projects/fishing-2d/game'),'--rendering-method','gl_compatibility','--script',str(HERE/'capture_transverse_width_trial.gd'),'--',str(out/'capture.plan.json'),str(out/'review')])]
 try:
  for name,args in stages:
   r=subprocess.run(args,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120);log=out/(name+'.log');log.write_text(r.stdout+'\n'+r.stderr,encoding='utf8')
   m['stages'].append({'stage':name,'exit_code':r.returncode,'log':str(log)});save()
   assert r.returncode==0 and all(x not in r.stdout+r.stderr for x in ['SCRIPT ERROR','ERROR:','Traceback (most recent call last)']),(name,r.stdout[-1000:],r.stderr[-500:])
   print(plan['species'],name,'ok',flush=True)
  report=json.loads((out/'review/capture.validation.json').read_text(encoding='utf8'));assert report['ok']
  assert all(r['snapshot']['action']==r['action_requested']and not r['snapshot']['pending_action']for r in report['motion'])
  m.update(status='done',next_action='human_review',scope='Local width comparison only',model=str(out/'fish.glb'),editable_source=str(out/'fish.blend'),capture_report=str(out/'review/capture.validation.json'),formal_acceptance=False,installed=False);save()
 except Exception as e:
  m.update(status='failed',next_action='fix_input',error=str(e));save();raise
if __name__=='__main__':main()
