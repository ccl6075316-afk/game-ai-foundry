import json,hashlib
from pathlib import Path
q=Path('E:/game-ai-foundry/projects/fishing-2d/plans/reviews/six-fish-release-20261104/bluegill');p=q/'extra-leaf-cleanup-plan.json';data=json.loads(p.read_text(encoding='utf8'));old_sha=hashlib.sha256(p.read_bytes()).hexdigest();rows=list({x['path']:x for x in data['files']}.values());roots=sorted(set(data['target_roots']));already=sum(not Path(x['path']).exists()for x in rows);data.update(files=rows,target_roots=roots,total_bytes=sum(x['bytes']for x in rows),directory_alias_deduplication={'original_aliased_plan_sha256':old_sha,'original_root_entries':len(data['target_roots']),'unique_resolved_roots':len(roots),'unique_file_paths':len(rows),'files_already_deleted_before_duplicate_alias_detected':already,'explanation':'Legacy eye150 experiment directories alias the same plans/reviews/eye-volume150 species leaves. First duplicate path interrupted exact unlink after earlier valid deletions; resume deduplicates resolved paths, verifies every remaining existing file SHA and deletes each physical file exactly once. No mixed parent deleted.'});p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for row in rows:
 f=Path(row['path']);assert any(f.resolve().is_relative_to(Path(r))for r in roots)
 if f.exists():assert hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'];f.unlink()
for root in sorted([Path(x)for x in roots],key=lambda x:len(x.parts),reverse=True):
 if root.exists():
  for d in sorted([x for x in root.rglob('*')if x.is_dir()],key=lambda x:len(x.parts),reverse=True):d.rmdir()
  root.rmdir()
receipt={'ok':True,'species':'bluegill','deleted_files':len(rows),'deleted_bytes':data['total_bytes'],'roots':roots,'exact_SHA_plan':{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},'directory_alias_resume':data['directory_alias_deduplication'],'scope':data['species_verification'],'new_archive_created':False};(q/'extra-leaf-cleanup.validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('bluegill',len(roots),len(rows),data['total_bytes'])
