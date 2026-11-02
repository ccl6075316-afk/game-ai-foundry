"""Dry-run/apply an exact reviewed Nile trial list after accepted source retention.

No recursive deletion, symlink traversal, or archive creation. Every file is
preflighted by absolute containment, size and SHA before any deletion begins.
"""
from pathlib import Path
import argparse,gzip,json,hashlib,subprocess,stat
ROOT=Path(__file__).resolve().parents[3];GAME=ROOT/'projects/fishing-2d'
RELEASE=GAME/'plans/reviews/nile-tilapia-release-20261103'
ALLOWED=[GAME/'experiments/nile-database-shape-20261102',GAME/'experiments/nile-dorsal-route-trial']
EXTRA={RELEASE/'accepted/fish.glb'}|{RELEASE/(a+'-'+b+'.png')for a in ['Swim','Turn','Ascend','Dive']for b in ['canonical','approved']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def safe(p):
 assert p.is_absolute() and (any(p.is_relative_to(a)for a in ALLOWED)or p in EXTRA),'Outside explicit cleanup scope: '+str(p)
 assert p.resolve()==p,'Resolved path changed: '+str(p)
 for a in [p,*p.parents]:
  assert not a.is_symlink() and not(a.stat().st_file_attributes&stat.FILE_ATTRIBUTE_REPARSE_POINT),'Reparse path: '+str(a)
  if a==ROOT:break
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 assert args.plan.resolve()==RELEASE/'cleanup-plan.json';plan=read(args.plan);assert plan['user_authorized'] is True
 assert read(RELEASE/'manifest.json')['user_acceptance'] and read(RELEASE/'sop.validation.json')['ok']
 for row in plan['protected']:
  path=Path(row['path']);assert path.is_file() and sha(path)==row['sha256'],'Protected source/evidence changed: '+str(path)
 index=RELEASE/'cleanup-files.json.gz';assert sha(index)==plan['index_sha256']
 rows=json.loads(gzip.decompress(index.read_bytes()))
 # Verify our scoped viewer is closed before retiring files it uses.
 result=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name LIKE 'Godot%'\" | Select-Object -ExpandProperty CommandLine"],capture_output=True,text=True,check=True)
 assert not any(str(a).replace('\\','/').lower()in result.stdout.replace('\\','/').lower()for a in ALLOWED),'Close the old trial viewer first'
 for row in rows:
  p=Path(row['path']);safe(p);assert p.is_file()and p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'Changed target: '+str(p)
 count=0;size=0
 if args.apply:
  for row in rows:
   p=Path(row['path']);assert sha(p)==row['sha256'];p.unlink();count+=1;size+=row['bytes']
  for a in ALLOWED+[RELEASE/'accepted']:
   if not a.exists():continue
   for p in sorted([p for p in a.rglob('*')if p.is_dir()],key=lambda p:len(p.parts),reverse=True):
    if not any(p.iterdir()):p.rmdir()
   if not any(a.iterdir()):a.rmdir()
  for row in plan['protected']:assert sha(Path(row['path']))==row['sha256']
 report={'ok':True,'apply':args.apply,'eligible_files':len(rows),'eligible_bytes':sum(r['bytes']for r in rows),'deleted_files':count,'deleted_bytes':size,'plan_sha256':sha(args.plan),'retained_source_and_evidence_verified':True,'no_whole_trial_archive_created':True}
 (RELEASE/('cleanup-execution.json'if args.apply else'cleanup-preflight.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
