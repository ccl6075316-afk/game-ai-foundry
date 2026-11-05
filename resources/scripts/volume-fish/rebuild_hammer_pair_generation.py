"""Run explicit source-based pair stages; visual approvals remain separate.

Each stage verifies expected outputs (Blender may exit zero on Python errors).
Nothing is installed and no acceptance is invented. Existing outputs are never
overwritten. Native source paths and species parameters are per-fish inputs.
"""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];SCRIPTS=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--blender',type=Path,required=True);p.add_argument('--suffix',required=True);p.add_argument('--stage',choices=['geometry','appearance','rig'],required=True);a=p.parse_args();B=a.base.resolve();s=a.suffix
 assert '/experiments/hammer-pair-rebuild-'in str(B)and s.startswith('-r')
 def run(script,args,output,label,blender=False):
  assert not output.exists(),output
  log=B.parent/'logs'/(B.name+s+'-'+label+'.log');cmd=([str(a.blender),'-b','--python',str(SCRIPTS/script),'--']if blender else[sys.executable,str(SCRIPTS/script)])+list(map(str,args))
  with log.open('w')as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
  assert result.returncode==0 and output.exists(),str(log)
  print(label,str(output),flush=True)
 if a.stage=='geometry':
  prep=B/('preparation'+s);ref=B/('shape'+s)/'reference.input.json';body=B/('body'+s);fins=B/('fins'+s)
  run('prepare_project_art_shark.py',['--config',prep/'config.json','--output',ref.parent],ref,'shape')
  bc=B/('body'+s+'.config.json');run('prepare_continuous_shark_head_patch.py',['--reference',ref,'--output',bc],bc,'cage')
  run('build_continuous_shark_head_patch.py',[bc,body],body/'fish.glb','body',True)
  fc=B/('fins'+s+'.config.json');run('prepare_reference_shark_fin_lofts.py',['--config',ref.parent/'fin-layout.config.json','--output',fc],fc,'fin-layout')
  run('build_reference_shark_fin_lofts.py',[fc,fins],fins/'fish.glb','fins',True)
  skin=B/('skin-input'+s);run('prepare_hammerhead_native_skin.py',['--base',B,'--generation-suffix='+s,'--output',skin],skin/'preparation.validation.json','skin-preflight')
 elif a.stage=='appearance':
  src=B/('skin-input'+s);skin=B/('skin'+s);finmat=B/('fin-material'+s)
  run('author_project_shark_skin.py',[src/'skin.config.json',skin],skin/'fish.glb','skin',True)
  run('author_reference_shark_fin_materials.py',[skin,B/'fin-charts',finmat],finmat/'fish.glb','fin-material',True)
  ec=read(B/('eyes-r2.config.json'if B.name=='smooth'else'eyes.config.json'));ec.update(baseline=str(finmat),reference=str(B/('shape'+s)/'reference.input.json'));ep=B/('eyes'+s+'.config.json');write(ep,ec)
  eye=B/('eyes'+s+'-art');run('author_reference_shark_eyes.py',[ep,eye],eye/'fish.glb','eyes',True)
 else:
  eye=B/('eyes'+s+'-art');rc=read(B/'rig.config.json');rc.update(baseline=str(eye),baseline_sha256=sha(eye/'fish.glb'),reference=str(B/('shape'+s)/'reference.input.json'));rp=B/('rig'+s+'.config.json');write(rp,rc);candidate=B/('candidate'+s+'-source')
  run('rig_reference_shark.py',[rp,candidate],candidate/'fish.glb','rig',True)
if __name__=='__main__':main()
