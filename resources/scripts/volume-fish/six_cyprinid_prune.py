"""Prune only hash-verified numeric pose/frame caches after full reports are retained."""
import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();s=sys.argv[1];r=ROOT/f'projects/fishing-2d/experiments/six-fish-database-20261104/{s}';records=[];kept=[]
for folder in r.glob('delivery-*/fin490/'+s):
 receipt=folder.parent.parent/'cache-cleanup.validation.json'
 if receipt.exists():continue
 def read(n):return json.loads((folder/n).read_text(encoding='utf8'))
 roots=read('roots.validation.json');mem=read('membranes.validation.json');exp=read('export.validation.json');assert len(roots['samples'])==len(mem['samples'])==len(exp['samples'])==490;keep={0}
 for fin in roots['summary']:
  for key in ['min_signed_distance_cm','max_signed_distance_cm']:
   values=[x['fins'][fin][key]for x in roots['samples']];keep.update([min(range(490),key=values.__getitem__),max(range(490),key=values.__getitem__)])
  values=[x['fins'][fin]['min_signed_distance_mm']for x in mem['samples']];keep.add(min(range(490),key=values.__getitem__))
 remove=[];retain=[]
 for i,row in enumerate(exp['samples']):
  p=Path(row['posed_mesh_json']);assert p.parent.resolve()==folder.resolve();assert sha(p)==row['sha256'];entry={'path':str(p),'sha256':row['sha256'],'bytes':p.stat().st_size};(retain if i in keep else remove).append(entry)
 for p in (folder.parent.parent/'review/frames').glob('frame-*.jpg'):
  entry={'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size};(retain if int(p.stem.split('-')[1])in[0,24,48,96,144,192,240,264,287]else remove).append(entry)
 data={'ok':True,'scope':'Full numeric reports retained, including actual failures; keep rest and all per-fin root/min/max/membrane worst samples plus9 representative movie phases. No source/model/report/still/video removed.','roots_passed':roots['ok'],'membranes_passed':mem['ok'],'deleted':remove,'retained':retain,'deleted_bytes':sum(x['bytes']for x in remove)};receipt.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
 for x in remove:
  p=Path(x['path']);assert p.resolve().is_relative_to(r.resolve())and sha(p)==x['sha256'];p.unlink()
 records.append({'receipt':str(receipt),'files':len(remove),'bytes':data['deleted_bytes']});kept.extend(retain)
print(json.dumps({'ok':True,'rounds':records,'deleted_bytes':sum(x['bytes']for x in records),'remaining_bytes':sum(p.stat().st_size for p in r.rglob('*')if p.is_file())}))
