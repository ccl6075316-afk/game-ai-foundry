"""Retain unique negative fixtures and independent source traces before retirement."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/five-fish-release-20261104';O=G/'experiments/five-fish-database-20261103';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf8'));inventory=read(R/'retention-manifest.json')
def keep(src,dst,expected=None):
 src=Path(src).resolve();dst=dst.resolve();assert src.is_file() and dst.is_relative_to(R)
 if expected:assert sha(src)==expected
 dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copy2(src,dst)
 assert sha(dst)==sha(src);inventory['files'].append({'old':str(src),'new':str(dst),'sha256':sha(dst),'bytes':dst.stat().st_size})
for record in read(R/'manifest.json')['records']:
 s=record['species'];d=O/s;ledger=read(d/'production-review.json');gates=Path(ledger['candidate_files']['final_spec']['path']).parent;v=read(gates/'volume.config.json');keep(v['input_blend'],R/s/'history/negative-fin-source.blend',v['input_blend_sha256']);m=read(gates/'mouth-opening.validation.json');bad=m['results']['rejected'];keep(bad['source_blend'],R/s/'history/negative-mouth-source.blend',bad['sha256']);trial=G/f'experiments/{s.replace("_","-")}-portable-trial-20261031';configs=[p for p in trial.glob('mouth-boundaries*.json')if sha(p)==m['config_sha256']];assert len(configs)==1;keep(configs[0],R/s/'references/mouth-boundaries.json');keep(trial/'cage-r3.handoff.json',R/s/'history/source-art-handoff.json');facts=read(d/'current-evidence.validation.json');delivery=Path(facts['actual_capture']['path']).parent.parent;negative=delivery/'negative-narrow-head.glb';keep(negative,R/s/'history/negative-narrow-head.glb')
(R/'retention-manifest.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'retained_mappings':len(inventory['files'])}))
