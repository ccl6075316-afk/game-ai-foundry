"""Run the same finite-plane calibration on the independently failed bluegill plane."""
from pathlib import Path
p=Path(__file__).with_name('six_carp_bluegill_head_calibrate.py')
s=p.read_text(encoding='utf8').replace('/carp','/bluegill').replace("'species':'carp'","'species':'bluegill'")
s=s.replace("old=base/'width-r2';out=base/'width-r3'","old=base/'width-r1';out=base/'width-r2'")
s=s.replace("'delivery-r2/head.validation.json'","'delivery-r1/head.validation.json'").replace('brentq(error,1,1.6','brentq(error,.5,1.6')
exec(compile(s,str(p), 'exec'))
