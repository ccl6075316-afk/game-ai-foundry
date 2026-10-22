"""Blender CPU preflight for the exact source-plane fin CDT used by build_fish.

Run: blender -b --python preflight_fin_polygons.py -- report.json profile.json ...
Does not build or approve a fish. Rejects planar pinches before solidification.
"""
import hashlib
import json
import math
from collections import Counter,defaultdict
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fish import fin_source_geometry
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


def check(profile):
    p=json.loads(profile.read_text());aspect=1/p['source_aspect_ratio'];records=[]
    for f in p['fins']:
        polygon,points=fin_source_geometry(f,aspect)
        dv,de,df,*_=delaunay_2d_cdt(points,[(i,(i+1)%len(polygon)) for i in range(len(polygon))],[list(range(len(polygon)))],1,1e-7)
        edges=Counter();used=set();links=defaultdict(list)
        for face in df:
            used.update(face)
            for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted([a,b]))]+=1
            for i,v in enumerate(face):links[v].append({face[i-1],face[(i+1)%len(face)]})
        boundary=Counter(v for e,n in edges.items() if n==1 for v in e)
        pinches=[]
        for v,groups in links.items():
            remaining=groups[:];components=0
            while remaining:
                connected=remaining.pop();components+=1
                while True:
                    matches=[g for g in remaining if g&connected]
                    if not matches:break
                    for g in matches:connected|=g;remaining.remove(g)
            if components!=1:pinches.append(v)
        bad={i:n for i,n in boundary.items() if n!=2}
        loose=len(dv)-len(used)
        ok=bool(df) and not bad and not pinches and not loose and max(edges.values())<=2
        records.append({'fin':f['name'],'ok':ok,'vertices':len(dv),'faces':len(df),'loose_vertices':loose,
                        'boundary_degree_abnormal':bad,'disconnected_face_fans':pinches,'max_edge_faces':max(edges.values())})
    return {'profile':str(profile),'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),'ok':all(r['ok'] for r in records),'fins':records}


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:];rows=[check(Path(s)) for s in args[1:]]
    result={'ok':all(r['ok'] for r in rows),'scope':'Exact source-plane CDT topology only. Projection/solidification/GLB, anatomy and fin/body runtime gates remain separate.','items':rows}
    Path(args[0]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    if not result['ok']:sys.exit(1)
