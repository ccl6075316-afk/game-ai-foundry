"""Check measured jaw tip motion relative to head, independently of body action."""
import argparse,hashlib,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--export',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=json.loads(a.export.read_text(encoding='utf-8'))
assert sha(report['model'])==report['model_sha256'],'Stale model'
groups={};failures=[]
for row in report['samples']:
    assert sha(row['posed_mesh_json'])==row['sha256'],'Stale sample'
    data=json.loads(Path(row['posed_mesh_json']).read_text(encoding='utf-8'))
    points=data['jaw_tip_head_local'];assert points and all(math.isfinite(x) for q in points for x in q)
    center=[sum(q[i] for q in points)/len(points) for i in range(3)]
    groups.setdefault(row['action'],{}).setdefault(round(data['jaw_open_fraction'],5),[]).append(center)
distance=lambda a,b:math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
rows=[]
for action,states in groups.items():
    assert sorted(states)==[0,.33333,.66667,1],'Missing opening state'
    closed=states[0][0];travel=[]
    for amount,centers in sorted(states.items()):
        spread=max(distance(centers[0],q) for q in centers)
        if spread>1e-4:failures.append('Jaw varies relative to head for repeated same opening: '+action)
        travel.append(distance(closed,centers[0]))
    ok=all(b>a+1e-4 for a,b in zip(travel,travel[1:])) and .01<travel[-1]<.04
    if not ok:failures.append('Missing or nonmonotonic jaw motion: '+action)
    rows.append({'action':action,'tip_travel_head_local_native':travel,'repeated_closed_error_native':max(distance(closed,q) for q in states[0]),'ok':ok})
if len(report['samples'])!=32 or set(groups)!={'Swim','Turn','Ascend','Dive'}:failures.append('Incomplete four-action evidence')
result={'ok':not failures,'model_sha256':report['model_sha256'],'export_sha256':sha(a.export),'scope':'32 actual Godot CPU-skin samples; tip moves monotonically relative to head for 0,1/3,2/3,1 and returns on repeated closed samples. Not continuous collision testing, exact occlusion or biological gape acceptance. Native coordinate length is source image width, not meters.','samples':rows,'failures':failures}
a.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));raise SystemExit(bool(failures))
