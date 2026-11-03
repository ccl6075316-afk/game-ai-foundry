"""Retire named superseded review/model caches after final whole-fish SOP pass."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];s=sys.argv[1];r=(ROOT/f'projects/fishing-2d/experiments/six-fish-database-20261104/{s}').resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf8'));assert read(r/'sop.validation.json')['ok'];latest='delivery-r6'if s=='crucian'else'delivery-r4';remove={}
def add(p,reason):
 if p.is_file():
  assert p.resolve().is_relative_to(r) and not p.is_symlink();remove[str(p.resolve())]={'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size,'reason':reason}
for d in r.glob('delivery-*'):
 if d.name==latest:continue
 for p in (d/'review').glob('**/*'):
  if p.suffix.lower()in ['.jpg','.png']and p.name not in ['whole-left-texture.png','head-bottom-texture.png','mouth-front-texture.png']:add(p,'Superseded capture; complete numeric reports and three source/mouth/bottom representative images retained. Current full capture is separate.')
 add(d/'negative-narrow-head.glb','Duplicate generated head negative; current actual head negative and old numeric rejection retained.')
for d in r.glob('gates-*'):
 if d.name!='gates-r7':add(d/'ordinary-reference.glb','Superseded derived ordinary GLB; source authoring/numeric receipts retained, current ordinary GLB kept.')
for version in ([2,3]if s=='crucian'else[4]):
 for name in ['fish.glb','fish.blend','cold-fish.glb']:add(r/f'width-r{version}'/name,'Rejected unadopted wrong-V or split-seam candidate; final source chain does not consume it. Failure reports and representative image retained.')
if s=='crucian':
 for p in [r/'native-lips-r2/atlas.png',r/'chin-bake-r2/atlas.png',r/'crucian-database-review.mp4',r/'crucian-database-r5-review.mp4']:add(p,'Rejected or superseded color preview; final native chart/current video and exact failure hashes retained.')
 for p in (r/'fin-volume-views').glob('*.png'):add(p,'Superseded fin capture; current full112 captures and both comparison sheets retained.')
# Byte-identical cold models are redundant after actual source-only cold receipts.
for p in r.glob('width-*/cold-fish.glb'):
 canonical=p.parent/'fish.glb'
 if canonical.is_file()and sha(p)==sha(canonical):add(p,'Exact duplicate cold export; current canonical source/model and real cold receipt remain.')
receipt=r/'retired-cache-cleanup.validation.json';assert not receipt.exists();records=list(remove.values());receipt.write_text(json.dumps({'ok':True,'scope':'Only explicitly named superseded derived caches/unadopted outputs. Latest source/model/SOP/profile/native-lip author/raw donor receipts/complete numeric results and original external baseline/negative untouched. Historical cache files are intentionally retired, not current evidence.','deleted':records,'deleted_bytes':sum(q['bytes']for q in records)},indent=2)+'\n',encoding='utf8')
for row in records:
 p=Path(row['path']);assert p.resolve().is_relative_to(r)and sha(p)==row['sha256'];p.unlink()
print(json.dumps({'ok':True,'deleted_files':len(records),'deleted_bytes':sum(q['bytes']for q in records),'retained_bytes':sum(p.stat().st_size for p in r.rglob('*')if p.is_file())}))
