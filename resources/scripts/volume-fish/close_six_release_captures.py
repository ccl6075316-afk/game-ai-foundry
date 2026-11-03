"""Retire root-owned duplicate verification captures, retaining numeric proof."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/six-fish-release-20261104'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 receipt=R/'root-capture-cleanup.validation.json'
 if receipt.exists():print(receipt.read_text(encoding='utf8'));return
 src=ROOT/'output/six-fish-release-20261104/protected/nile-source/source-export.validation.json';dst=R/'protected/nile_tilapia/source-export.validation.json';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 roots=[ROOT/'output/six-fish-review-20261104',ROOT/'output/six-fish-release-20261104/protected',ROOT/'output/six-fish-release-20261104/canonical']
 files=[p for root in roots if root.exists() for p in root.rglob('*') if p.is_file()]
 # The protected checks retain the zero-difference results and a four-action
 # montage. Their raw matched GPU pairs carry no unique visual information.
 files += [p for p in (R/'protected').rglob('*.png')]
 assert all(p.resolve().is_relative_to(ROOT.resolve()) for p in files)
 rows=[{'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size}for p in files]
 write(R/'root-capture-cleanup.plan.json',{'files':rows,'scope':'Root-owned old read-only viewer and canonical/protected duplicate captures/logs; complete numeric proof, bindings, four-action montages and Nile exact-source export report retained. Species-agent outputs excluded.'})
 for row in rows:
  p=Path(row['path']);assert sha(p)==row['sha256'];p.unlink()
 for root in roots:
  if root.exists():
   for d in sorted([p for p in root.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):d.rmdir()
   root.rmdir()
 write(receipt,{'ok':True,'deleted_files':len(rows),'deleted_bytes':sum(r['bytes'] for r in rows),'retained_nile_source_export':{'path':str(dst),'sha256':sha(dst)},'scope':'Duplicate root-owned captures and verification scratch only; not species cleanup, not prior rounds.'})
 print(receipt.read_text(encoding='utf8'))
if __name__=='__main__':main()
