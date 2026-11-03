"""Retire only exact carp/bluegill legacy leaves, never mixed archives."""
import hashlib,json,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];G=R/'projects/fishing-2d';D=G/'plans/reviews/six-fish-release-20261104';labels={'carp','bluegill'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
leaves={s:[]for s in labels}
for start in [G/'experiments',G/'plans/reviews']:
 stack=[start]
 while stack:
  p=stack.pop()
  if p==D or 'local-cleanup'in p.parts or 'history-curation'in p.parts:continue
  for q in p.iterdir():
   if not q.is_dir():continue
   if q.name in labels:leaves[q.name].append(q.resolve())
   else:stack.append(q)
for s in sorted(labels if len(sys.argv)==1 else {sys.argv[1]}):
 leaves[s]=sorted(set(leaves[s]))
 d=D/s;assert read(d/'sop.validation.json')['ok']and read(d/'canonical-load.validation.json')['ok'];manifest=read(d/'retention-manifest.json');known={r['old']for r in manifest['files']};rows=[];retained=[];conclusions=[]
 for leaf in sorted(leaves[s]):
  assert leaf.name==s and not leaf.is_relative_to(D)and(leaf.is_relative_to(G/'experiments')or leaf.is_relative_to(G/'plans/reviews'))
  for p in sorted(x for x in leaf.rglob('*')if x.is_file()):
   assert not p.is_symlink();h=sha(p);size=p.stat().st_size;rows.append({'path':str(p.resolve()),'sha256':h,'bytes':size,'species':s,'leaf':str(leaf)})
   # Preserve complete scalar/numerical validation conclusions and parameters,
   # not geometry samples, logs, repeated images or obsolete model copies.
   if p.suffix=='.json'and not p.name.startswith(('sample-','pose-')):
    try:value=read(p)
    except(ValueError,UnicodeError):continue
    if size<=8_000_000:
     if str(p.resolve())not in known:
      dest=d/'history/legacy-leaves'/p.relative_to(G);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(dest)==h;record={'old':str(p.resolve()),'new':str(dest.resolve()),'sha256':h,'bytes':size};manifest['files'].append(record);retained.append(record);known.add(str(p.resolve()))
    else:
     compact={k:v for k,v in value.items()if not isinstance(v,list)or len(v)<200}if isinstance(value,dict)else{'list_items':len(value)};conclusions.append({'original_path':str(p.resolve()),'original_sha256':h,'original_bytes':size,'conclusions_and_parameters':compact,'scope':'Large raw arrays retired; full final accepted geometry retained in canonical GLB/source, this is an explicit summary rather than a byte-exact copy.'})
 plan={'species':s,'target_roots':[str(x)for x in sorted(leaves[s])],'files':rows,'total_bytes':sum(x['bytes']for x in rows),'species_verification':'Every selected root basename equals this exact species. Shared parent trees, mixed aggregate archives and local-cleanup/history-curation are excluded.','conclusions':conclusions};write(d/'extra-leaf-cleanup-plan.json',plan);write(d/'retention-manifest.json',manifest)
 for row in rows:
  p=Path(row['path']);assert any(p.resolve().is_relative_to(x)for x in leaves[s])and sha(p)==row['sha256'];p.unlink()
 for leaf in sorted(leaves[s],key=lambda p:len(p.parts),reverse=True):
  for p in sorted([p for p in leaf.rglob('*')if p.is_dir()],key=lambda p:len(p.parts),reverse=True):p.rmdir()
  leaf.rmdir()
 write(d/'extra-leaf-cleanup.validation.json',{'ok':True,'species':s,'deleted_bytes':plan['total_bytes'],'deleted_files':len(rows),'roots':plan['target_roots'],'exact_SHA_plan':{'path':str(d/'extra-leaf-cleanup-plan.json'),'sha256':sha(d/'extra-leaf-cleanup-plan.json')},'preserved_numeric_files':len(retained),'large_raw_summaries':len(conclusions),'scope':plan['species_verification'],'new_archive_created':False})
 print(json.dumps({'species':s,'leaves':len(leaves[s]),'deleted_files':len(rows),'deleted_bytes':plan['total_bytes'],'numeric_retained':len(retained)}),flush=True)
