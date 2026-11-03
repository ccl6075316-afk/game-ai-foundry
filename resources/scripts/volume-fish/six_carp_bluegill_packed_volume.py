"""Bluegill adapter of the frozen shared exhaustive packed four-probe method.
Only source resolution differs; all thresholds/probes/negative methods remain.
"""
from pathlib import Path
p=Path(__file__).with_name('six_cyprinid_packed_volume.py');s=p.read_text(encoding='utf8')
s=s.replace("meta=read(r/'database-preflight.validation.json');candidate=Path(meta['baseline']['candidate_directory'])", "candidate=ROOT/'projects/fishing-2d/experiments/three-fish-fin-detail-20261031/bluegill/tail-root-skin-r2'")
assert 'database-preflight.validation.json'not in s
exec(compile(s,str(Path(__file__).resolve()),'exec'))
