"""Run fresh177 roots, complete490 export/roots and unrelaxed membrane kernels."""
import argparse,concurrent.futures,json,subprocess,sys,hashlib,re
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--godot',required=True);p.add_argument('--blender',required=True);p.add_argument('--species',nargs='*');p.add_argument('--workers',type=int,default=2,help='Parallel membrane checker processes; same complete samples and limits.');p.add_argument('--fish-workers',type=int,default=2,help='Concurrent independent species; same complete poses/fins and limits.');p.add_argument('--revision-tag',default='',help='Keep a fresh named set of full reports without overwriting earlier failures.');a=p.parse_args();assert 1<=a.workers<=8 and 1<=a.fish_workers<=4;scripts=Path(__file__).resolve().parent;rows=json.loads(a.batch.read_text())['items'];results=[]
 if a.species:rows=[r for r in rows if r['species'] in a.species]
 tag=a.revision_tag
 if tag:assert re.fullmatch('[a-z0-9-]{1,32}',tag)
 def run(row):
  s=row['species'];plan=Path(row['plan']);base=plan.parent;exporter=scripts/row['exporter']
  def call(cmd,log,timeout=1200):
   with log.open('w',encoding='utf8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
   assert r.returncode==0,(s,str(log))
  try:
   root=base/('root177'+('-'+tag if tag else''));call([sys.executable,'-X','utf8',str(scripts/'validate_fin_completion.py'),'--plan',str(plan),'--game',str(a.game),'--godot',a.godot,'--blender',a.blender,'--output',str(root),'--exporter',str(exporter),'--checker-timeout','900'],base/(root.name+'.log'))
   assert json.loads((root/'completion.validation.json').read_text())['ok'];print('ROOT140',s,'177 passed',flush=True)
   full=base/('full490'+('-'+tag if tag else''));full.mkdir();folder=full/s;folder.mkdir();exp=folder/'export.validation.json'
   call([a.godot,'--headless','--path',str(a.game),'--quit-after','120','--script',str(exporter),'--',str(plan),str(full),'full-fin',s,'--membranes'],full/'export.log',900)
   log=(full/'export.log').read_text(encoding='utf8');assert 'ERROR:' not in log and exp.exists();d=json.loads(exp.read_text());assert len(d['samples'])==490
   roots=folder/'roots.validation.json';call([a.blender,'-b','--python-exit-code','1','--python',str(scripts/'check_runtime_fin_attachment.py'),'--','--export',str(exp),'--output',str(roots),'--tolerance-cm','.10','--max-penetration-cm','.60'],folder/'roots.log',900)
   assert json.loads(roots.read_text())['ok'];print('ROOT140',s,'490 passed',flush=True)
   parallel=base/('membrane490'+('-'+tag if tag else''));call([sys.executable,'-X','utf8',str(scripts/'validate_parallel_fin_membranes139.py'),'--plan',str(plan),'--game',str(a.game),'--blender',a.blender,'--export',str(exp),'--roots',str(roots),'--output',str(parallel),'--species',s,'--workers',str(a.workers),'--partitions','8'],base/(parallel.name+'.log'),3600)
   assert json.loads((parallel/'completion.validation.json').read_text())['ok'];return {'species':s,'ok':True,'root_report':str(root/'completion.validation.json'),'full_report':str(parallel/'completion.validation.json'),'plan_sha256':sha(plan)}
  except Exception as e:return {'species':s,'ok':False,'error':str(e)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=getattr(a,'fish_workers',2)) as pool:
  for result in pool.map(run,rows):results.append(result);print('FISH140',json.dumps(result),flush=True)
 output=a.batch.parent/('fin-completion140'+('-'+tag if tag else'')+('-'+'-'.join(a.species) if a.species else '')+'.validation.json');output.write_text(json.dumps({'ok':all(x['ok'] for x in results),'records':results},indent=2));return 0 if all(x['ok'] for x in results) else 1
if __name__=='__main__':raise SystemExit(main())
