"""Check a frozen transverse head envelope on actual GLB body triangles.

The envelope is a documented production assumption, never a universal biological
threshold. Texture, rig and fin checks remain separate. --baseline exercises the
old-model negative against the same frozen target; it must fail when too narrow.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from freeze_surface_ownership import read_glb, accessor


def cross_section(triangles, x):
    hits=[]
    for a,b in [(triangles[:,0],triangles[:,1]),
                (triangles[:,1],triangles[:,2]),
                (triangles[:,2],triangles[:,0])]:
        mask=(a[:,0]-x)*(b[:,0]-x)<0
        if mask.any():
            t=(x-a[mask,0])/(b[mask,0]-a[mask,0])
            hits.extend(a[mask]+t[:,None]*(b[mask]-a[mask]))
        # Include on-plane endpoints, including an explicitly authored front cap.
        hits.extend(a[np.abs(a[:,0]-x)<1e-7])
    if not hits:
        raise ValueError('Empty head section')
    points=np.asarray(hits)
    return float(np.ptp(points[:,2]))/2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text(encoding='utf8'));rows=[]
    for item in plan['items']:
        path=Path(item['source'] if args.baseline else item['target'])
        model_sha=hashlib.sha256(path.read_bytes()).hexdigest()
        expected_sha=item.get('source_sha256' if args.baseline else 'target_sha256')
        if expected_sha is not None:assert model_sha==expected_sha,'Stale head-envelope model'
        if item.get('packed_parts_manifest') and not args.baseline:
            from logical_document import logical_document
            assert hashlib.sha256(Path(item['packed_parts_manifest']).read_bytes()).hexdigest()==item['packed_parts_manifest_sha256']
            doc,blob,_=logical_document(path,item['body'],item['fins'],item['packed_parts_manifest'])
        else:doc,blob=read_glb(path)
        nodes=[n for n in doc['nodes'] if n.get('name')==item.get('body','Closed_body') and 'mesh' in n]
        assert len(nodes)==1,'Ambiguous/missing reviewed body mesh'
        assert not any(k in nodes[0] for k in ['matrix','translation','rotation','scale'])
        triangles=[]
        for primitive in doc['meshes'][nodes[0]['mesh']]['primitives']:
            positions=accessor(doc,blob,primitive['attributes']['POSITION'])
            indices=accessor(doc,blob,primitive['indices']).reshape(-1,3)
            triangles.append(positions[indices])
        triangles=np.concatenate(triangles)
        checks=[]
        tolerance=item['envelope_halfwidth_tolerance_native']
        for u,half_width in item['target_half_width_envelope']:
            try:measured=cross_section(triangles,u-.5)
            except ValueError as error:
                checks.append({'source_u':u,'target_half_width':half_width,'measured_half_width':None,'ok':False,'error':str(error)})
                continue
            checks.append({'source_u':u,'target_half_width':half_width,
                           'measured_half_width':measured,
                           'error_native':measured-half_width,
                           'ok':abs(measured-half_width)<=tolerance})
        rows.append({'species':item['species'],'model':str(path),
                     'model_sha256':model_sha,
                     'ok':all(x['ok'] for x in checks),'sections':checks})
    result={'ok':bool(rows) and all(x['ok'] for x in rows),'baseline_negative':args.baseline,
            'plan_sha256':hashlib.sha256(args.plan.read_bytes()).hexdigest(),
            'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'species':rows,'limits':'Frozen species-specific production envelope only; '
            'not a biological measurement or an automatic anatomical acceptance. '
            'Front/top clay and textured visual review remain required.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'ok':result['ok'],'baseline_negative':args.baseline,
                      'species':[(r['species'],r['ok']) for r in rows]}))
    return 0 if result['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())
