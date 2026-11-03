"""Verify final six-fish manifests and audit exact cleanup receipts; no installs."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
GAME=ROOT/'projects/fishing-2d';BATCH=GAME/'plans/reviews/six-fish-database-20261104';FISH=GAME/'experiments/six-fish-database-20261104'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def path(p):
 p=Path(p['path']if isinstance(p,dict)else p);return p.resolve()if p.is_absolute()else(ROOT/p).resolve()
def ref(p):p=path(p);return {'path':str(p),'sha256':sha(p)}
def verify(r):p=path(r);assert p.is_file()and sha(p)==r['sha256'],str(p);return p

def main():
 manifest=BATCH/'manifest.json';batch=read(manifest)
 for row in batch['records']:
  species=row['species'];state=FISH/species/'manifest.json';m=read(state);assert m['status']=='done'and m['next_action']=='human_review'
  for role in ['model','editable_source','final_spec','production_review','sop_report']:verify(m[role]);row[role]=m[role]
  sop=read(path(m['sop_report']));assert sop['ok']and sop['review_sha256']==m['production_review']['sha256']
  row.update(status='done',next_action='human_review',production_manifest=ref(state),static_changed=m.get('static_changed',m['model']['sha256']!=row['installed_before']['sha256']),triangles=read(path(m['final_spec']))['expected']['triangles'],user_acceptance_of_new_candidate=False)
  if species in ['crucian','grass_carp']:row['completion_scope']='Source-owned library envelope, complete native lip/underside material, inherited normal and actual own fin repair. All current physical/cold/full4probe and54-evidence nine-stage SOP plus cleanup done; independently inspected by root. No canonical replacement.'
  old=row['installed_before'];p=verify(old);assert p.stat().st_size==old['bytes']
  if row['static_changed']:
   profile=ROOT/f'resources/volume-fish/database-revision-20261104/{species}.profile.json';assert profile.exists()
 for r in batch['protected_installed_models'].values():p=verify(r);assert p.stat().st_size==r['bytes']
 # Read only per-event receipts, not summary totals, so no round is double-counted.
 receipts=list(FISH.rglob('*cleanup.validation.json'))+[BATCH/'temporary-unity-deps-cleanup.validation.json',BATCH/'failed-list-smoke-cleanup.validation.json']
 seen=set();events=[];total=0;absent=0
 for receipt in sorted(set(receipts)):
  d=read(receipt);assert d['ok'],str(receipt)
  rows=next((d[k]for k in ['files','deleted_files','deleted']if isinstance(d.get(k),list)),None)
  if rows is None:
   plan=read(verify(d['plan']));rows=plan['files']
  assert sum(r['bytes']for r in rows)==d['deleted_bytes'],str(receipt)
  for r in rows:
   p=path(r);assert p.is_relative_to(ROOT),str(p);assert not p.exists(),('Deleted target recreated',str(p))
   key=(str(p).casefold(),r['sha256'],r['bytes']);assert key not in seen,('Duplicate deletion event',str(p));seen.add(key);absent+=1
  total+=d['deleted_bytes'];events.append({'receipt':ref(receipt),'files':len(rows),'deleted_bytes':d['deleted_bytes']})
 sizes={r['species']:sum(p.stat().st_size for p in (FISH/r['species']).rglob('*')if p.is_file())for r in batch['records']}
 cleanup=BATCH/'cleanup-summary.validation.json';write(cleanup,{'ok':True,'kind':'six_fish_exact_cleanup_audit','deletion_events':events,'deleted_files':absent,'deleted_bytes':total,'all_declared_deleted_paths_absent':True,'retained_new_experiment_bytes_by_species':sizes,'retained_new_experiment_bytes':sum(sizes.values()),'scope':'Actual deleted experiment outputs and isolated dependencies created during this batch. This is not a claim that pre-existing repository size shrank by this amount. Existing original inputs/accepted fish and current frozen chains retained. Retained totals exclude this batch planning directory, output viewer captures, original sources outside six-fish folder, and Git/LFS.'})
 batch.update(status='done',next_action='human_review',completed_count=6,completion_scope='All six library/SOP technical upgrades complete. Two exact accepted static assets retained; four new whole-fish appearance candidates require user review. No canonical replacement, commit or push.',completed_at=datetime.datetime.now().astimezone().isoformat(),protected_canonical_models_verified=28,cleanup_summary=ref(cleanup),viewer_launcher='resources/scripts/volume-fish/review_six_database_fish.py')
 write(manifest,batch);print(json.dumps({'ok':True,'completed':6,'canonical_models_unchanged':28,'deleted_bytes':total,'retained_experiment_bytes':sum(sizes.values()),'triangles':{r['species']:r['triangles']for r in batch['records']}}))

if __name__=='__main__':main()
