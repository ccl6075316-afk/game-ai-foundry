"""Collect actual final-candidate images/video; no visual verdict or acceptance."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True);p.add_argument('--revision',type=int,required=True);p.add_argument('--delivery',type=Path,required=True);p.add_argument('--godot',type=Path,required=True);a=p.parse_args();root=ROOT/f'projects/fishing-2d/experiments/five-fish-database-20261103/{a.species}';model=root/f'width-r{a.revision}/fish.glb';delivery=a.delivery.resolve();assert json.loads((delivery/'manifest.json').read_text()).get('specialized_checks_ok');logs=root/'view-logs';logs.mkdir(exist_ok=True)
def run(name,args):
 r=subprocess.run([str(x)for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=r.stdout.decode('utf8','replace');(logs/(name+'.log')).write_text(log,encoding='utf8');assert r.returncode==0 and not any(t in log for t in ['Traceback','SCRIPT ERROR','Parse Error']),name+':'+log[-1500:];print(json.dumps({'stage':name,'ok':True}),flush=True)
base=[a.godot,'--path',ROOT/'projects/fishing-2d/game','--rendering-method','gl_compatibility','--audio-driver','Dummy','--position','-3000,-3000','--script'];fv=root/f'fin-volume-r{a.revision}'
run('fins',base+[HERE/'portable/capture_fin_volume.gd','--',delivery/'review.plan.json',fv]);run('fin-sheets',[sys.executable,HERE/'portable/compose_fin_volume_review.py','--review',fv])
plan=json.loads((root/'width-r1/capture.plan.json').read_text());old=plan['models']['after'];plan['models']['after']=str(model);plan['bindings'].pop(old);plan['bindings'][str(model)]=sha(model);h=HERE/'capture_unlit_width_review.gd';plan['bindings'][str(h)]=sha(h);(root/'unlit.plan.json').write_text(json.dumps(plan,indent=2)+'\n')
run('unlit',base+[h,'--',root/'unlit.plan.json',root/'unlit-review'])
run('movie',['ffmpeg','-hide_banner','-loglevel','error','-framerate','12','-i',delivery/'review/frames/frame-%04d.jpg','-c:v','libx264','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',root/f'{a.species.replace("_","-")}-database-review.mp4'])
run('invariants-and-sheets',[sys.executable,HERE/'review_database_revision.py','--species',a.species,'--directory',root,'--model',model,'--delivery',delivery,'--mask',root/'ventral-bake-r2/patch-mask.png'])
