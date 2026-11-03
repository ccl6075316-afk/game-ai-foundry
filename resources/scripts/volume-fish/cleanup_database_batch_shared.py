"""Retire this batch's exact temporary parser install after all five SOPs pass."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];work=(ROOT/'work/five-fish-database-20261103').resolve();out=ROOT/'output/five-fish-database-20261103';batch=ROOT/'projects/fishing-2d/experiments/five-fish-database-20261103';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for species in ['rainbow_trout','brown_trout','atlantic_salmon','sea_bass','red_emperor']:assert json.loads((batch/species/'sop-postcleanup.validation.json').read_text(encoding='utf8'))['ok']
assert work.is_relative_to(ROOT/'work') and work.name=='five-fish-database-20261103' and not work.is_symlink();retained=[];recipes=batch/'reproduction';recipes.mkdir(exist_ok=True)
for p in work.glob('*.py'):
 q=recipes/p.name;assert not q.exists();shutil.copy2(p,q);assert sha(q)==sha(p);retained.append({'path':str(q),'sha256':sha(q),'bytes':q.stat().st_size})
rows=[]
for p in work.rglob('*'):
 if not p.is_file():continue
 assert p.resolve().is_relative_to(work) and not p.is_symlink();rows.append({'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size})
plan={'kind':'exact_temporary_parser_and_recipe_cleanup','root':str(work),'scope':'UnityPy1.25.4 task-local parser install and duplicate task recipes only. Every Python recipe copied byte-exact to project reproduction folder. Library raw bundles/OBJ, restored required inputs, candidate sources/models, numeric and visual evidence retained. No archive.','retained_recipes':retained,'delete':rows,'delete_bytes':sum(x['bytes']for x in rows)};(out/'shared-cleanup.plan.json').write_text(json.dumps(plan,indent=2)+'\n')
for row in rows:
 p=Path(row['path']);assert p.resolve().is_relative_to(work) and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
for row in rows:Path(row['path']).unlink()
for p in sorted([p for p in work.rglob('*')if p.is_dir()],key=lambda p:len(p.parts),reverse=True):
 assert p.resolve().is_relative_to(work) and not p.is_symlink();p.rmdir()
work.rmdir();receipt={'ok':True,'deleted_files':len(rows),'deleted_bytes':plan['delete_bytes'],'retained_recipe_files':len(retained),'retained_recipe_bytes':sum(x['bytes']for x in retained),'original_work_directory_removed':not work.exists(),'new_archives':0,'plan_sha256':sha(out/'shared-cleanup.plan.json')};(out/'shared-cleanup-execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
