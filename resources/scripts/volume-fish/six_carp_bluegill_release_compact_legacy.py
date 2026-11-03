import json,hashlib
from pathlib import Path
R=Path('E:/game-ai-foundry');D=R/'projects/fishing-2d/plans/reviews/six-fish-release-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def compact(v):
 if isinstance(v,dict):return {k:compact(x)for k,x in v.items()}
 if isinstance(v,list):
  if len(v)<=64:return [compact(x)for x in v]
  failures=[compact(x)for x in v if isinstance(x,dict)and x.get('ok')is False];return {'raw_list_items_retired':len(v),'raw_list_canonical_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'explicit_failed_records_count':len(failures),'representative_failed_records':failures[:8],'scope':'Retired historical raw arrays/donor addresses; final accepted source and complete current physical conclusions remain separately preserved.'}
 return v
for s in ['carp','bluegill']:
 q=D/s;mp=q/'retention-manifest.json';m=json.loads(mp.read_text(encoding='utf8'));removed=[];summaries=[];remain=[]
 for row in m['files']:
  p=Path(row['new'])
  if not p.is_relative_to(q/'history/legacy-leaves')or p.suffix!='.json'or p.stat().st_size<250000:remain.append(row);continue
  source=json.loads(p.read_text(encoding='utf8'));dest=q/'history/legacy-conclusions'/p.relative_to(q/'history/legacy-leaves');out={'kind':'explicit_retired_historical_numeric_summary','original':row,'summary':compact(source),'statement':'This is a labelled summary of an obsolete nonfinal experiment, not a same-byte original report or current pass. Original original-path/SHA and conclusions/parameters kept; dense geometry/donor/sample arrays removed.'};dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');summaries.append({'original_path':row['old'],'original_sha256':row['sha256'],'summary':{'path':str(dest),'sha256':sha(dest)}});removed.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size});p.unlink()
 m['files']=remain;m.setdefault('retired_legacy_after_explicit_summary',[]).extend(summaries);mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8');receipt=q/'verification-cleanup.validation.json';v=json.loads(receipt.read_text(encoding='utf8'));v['files'].extend(removed);v['deleted_files']+=len(removed);v['deleted_bytes']+=sum(x['bytes']for x in removed);v['scope']+=' Verbose copied nonfinal legacy reports compacted into explicitly labelled numeric/conclusion summaries, with original SHA and summary maps; complete current technical reports unchanged.';receipt.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(s,'raw copied JSON removed',sum(x['bytes']for x in removed),'summaries',len(summaries))
