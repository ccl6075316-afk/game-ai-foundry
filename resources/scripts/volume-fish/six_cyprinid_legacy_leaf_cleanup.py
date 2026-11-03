"""Retire only explicitly named, unreferenced old crucian/grass-carp leaves."""
import argparse,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';sys.path.insert(0,str(ROOT/'cli'));from volume_sop import check
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main(s):
 assert s in ['crucian','grass_carp'];R=G/f'plans/reviews/six-fish-release-20261104/{s}';assert check(R/'production-review.json')['ok'];assert read(R/'manifest.json')['installed'];base=[G/'experiments/blender-fish',G/'plans/reviews'];targets=[];archives=[]
 for root in base:
  for p in root.rglob('*'):
   if not p.is_file()or'six-fish-release-20261104'in p.parts:continue
   named=any(s==part.lower()or part.lower()=='full-fin-'+s for part in p.parts)or p.stem.lower()==s or p.name.lower().startswith(s+'-')
   if not named:continue
   if p.suffix.lower()in ['.gz','.zip','.7z','.rar','.tar']:archives.append(str(p));continue
   actual=p.resolve();assert any(actual.is_relative_to(q.resolve())for q in base)and not p.is_symlink();
   if actual not in targets:targets.append(actual)
 current=list((G/f'assets/source/fish/{s}').rglob('*.json'))+list(R.rglob('*.json'))+[ROOT/f'resources/volume-fish/{s.replace("_","-")}-final-20261104.json',ROOT/f'resources/volume-fish/database-revision-20261104/{s}.profile.json'];texts=[]
 for p in current:
  try:texts.append((str(p),json.dumps(read(p),ensure_ascii=False).replace('\\\\','/').replace('\\','/').lower()))
  except (OSError,ValueError):pass
 for p in targets:
  needle=p.relative_to(ROOT).as_posix().lower();matches=[f for f,t in texts if needle in t];assert not matches,('Current source/report reference, retain',str(p),matches)
 rows=[];numbers=[]
 for p in targets:
  row={'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size};rows.append(row)
  if p.suffix.lower()=='.json':
   try:
    d=read(p);top={k:v for k,v in d.items()if isinstance(v,(str,int,float,bool))or v is None};detail={k:d[k]for k in ['summary','failures','checks','limits','parameters']if k in d};numbers.append({'original':row,'top_level_scalars':top,'numeric_conclusions':detail})
   except (ValueError,AttributeError):pass
 summary=R/'history/supplemental-legacy-conclusions.json';receipt=R/'history/supplemental-legacy-cleanup.validation.json';assert not summary.exists()and not receipt.exists();write(summary,{'species':s,'kind':'retired_named_leaf_numeric_conclusions','records':numbers,'scope':'Exact original top-level statuses/scalars and numeric summary/failure/check/parameter conclusions from superseded named fish leaves. Final current54/9 report, original donor/negative fixtures and complete current numerical evidence remain separate; old screenshot/model iterations retired.'});write(receipt,{'ok':True,'kind':'supplemental_named_fish_leaf_cleanup','species':s,'deleted':rows,'deleted_files':len(rows),'deleted_bytes':sum(r['bytes']for r in rows),'current_dependency_files_checked':len(texts),'literal_current_references_found':0,'excluded_archives':archives,'numeric_conclusions':{'path':str(summary.resolve()),'sha256':sha(summary)},'scope':'Only individually enumerated files under explicitly crucian/grass_carp/full-fin-species leaf or exact species filename/prefix. No mixed parent, compressed archive, other fish, canonical source/asset or existing release record modified.'})
 for p,row in zip(targets,rows):assert p.resolve().is_relative_to(G.resolve())and sha(p)==row['sha256']and p.stat().st_size==row['bytes'];p.unlink()
 # Only empty directories whose own name identifies this exact fish.
 for root in base:
  for d in sorted([p for p in root.rglob('*')if p.is_dir()and(p.name.lower()==s or p.name.lower()=='full-fin-'+s)and'six-fish-release-20261104'not in p.parts],key=lambda p:len(p.parts),reverse=True):
   if d.resolve().is_relative_to(root.resolve())and not list(d.iterdir()):d.rmdir()
 assert check(R/'production-review.json')['ok'];print(json.dumps({'ok':True,'species':s,'deleted_files':len(rows),'deleted_bytes':sum(r['bytes']for r in rows),'retained_new_conclusion_bytes':summary.stat().st_size+receipt.stat().st_size,'excluded_archives':len(archives)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--species',required=True);main(p.parse_args().species)
