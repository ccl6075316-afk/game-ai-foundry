"""Inspect frozen game-fish and local-library references without mutating assets."""
import csv, hashlib, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent / 'portable'))
from glb_io import read_glb, arrays

SPECIES = ['rainbow_trout', 'brown_trout', 'atlantic_salmon', 'sea_bass', 'red_emperor']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def inspect():
    database = ROOT / 'resources/fish-database'
    with (database / 'catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.csv').open(encoding='utf-8-sig') as f:
        catalog = list(csv.DictReader(f))
    for row in catalog:
        values = list(row.values())
        if values[1] in ['Rainbowtrout', 'BrownTrout', 'AtlanticSalmon', 'EuropeanSeabass', 'RedSnapper', 'ShortTailRedSnapper']:
            p = database / values[7]
            verts=[]; groups={}; group='default'
            for line in p.read_text().splitlines():
                q=line.split()
                if not q: continue
                if q[0]=='v': verts.append(list(map(float,q[1:4])))
                if q[0] in ['g','usemtl']: group=' '.join(q[1:]);groups.setdefault(group,[])
                if q[0]=='f': groups.setdefault(group,[]).append([int(x.split('/')[0])-1 for x in q[1:]])
            v=np.array(verts)
            group_info={}
            for k,x in groups.items():
                if x:
                    vv=v[np.unique(np.array(x))]
                    group_info[k]={'triangles':len(x),'bounds':[vv.min(0).tolist(),vv.max(0).tolist()]}
            print(json.dumps({'reference':values[:2],'path':str(p.relative_to(ROOT)),'sha256':sha(p), 'groups':group_info},ensure_ascii=False))
    for species in SPECIES:
        p=ROOT/f'projects/fishing-2d/game/assets/models/fish/{species}.glb'
        d,b=read_glb(p)
        pr=d['meshes'][0]['primitives'][0]; v=arrays(d,b,pr['attributes']['POSITION'])
        print(json.dumps({'species':species,'sha256':sha(p),'parts':[(x['name'],x['role'],x['index_count']//3) for x in d['extras']['geometry_parts']], 'bounds':[v.min(0).tolist(),v.max(0).tolist()], 'animations':[x.get('name') for x in d.get('animations',[])]},ensure_ascii=False))

if __name__=='__main__': inspect()
