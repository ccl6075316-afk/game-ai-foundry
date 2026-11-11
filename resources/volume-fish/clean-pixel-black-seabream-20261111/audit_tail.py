"""Measure closed caudal geometry and normal-ray thickness on the actual export."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'resources/scripts/volume-fish/portable'))
from glb_io import read_glb,arrays

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(path,scale):
    d,b=read_glb(path)
    pr=d['meshes'][0]['primitives'][0]
    P=arrays(d,b,pr['attributes']['POSITION']).astype(float)
    I=arrays(d,b,pr['indices']).reshape(-1).astype(int)
    part=next(row for row in d['extras']['geometry_parts'] if row['logical_name']=='Caudal_mesh')
    T=I[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3)
    ids=np.unique(T)
    points,inv=np.unique(np.round(P[ids],7),axis=0,return_inverse=True)
    mapping={int(i):int(j) for i,j in zip(ids,inv)}
    triangles=np.array([[mapping[int(i)] for i in tri] for tri in T])
    edges=np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]])
    _,counts=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
    tree=BVHTree.FromPolygons([Vector(q) for q in P],T.tolist(),all_triangles=True,epsilon=0)
    probes=[]
    for index,tri in enumerate(T):
        xyz=P[tri]
        cross=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])
        length=np.linalg.norm(cross)
        if length<1e-13:
            probes.append(dict(face=index,degenerate=True))
            continue
        normal=Vector(cross/length)
        for weights in ((1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)):
            origin=Vector(np.array(weights)@xyz)
            hit,hn,face,distance=tree.ray_cast(origin-normal*1e-8,-normal,2)
            probes.append(dict(face=index,weights=weights,hit_face=face,
                               thickness_mm=None if hit is None else (distance+1e-8)*scale))
    missing=[row for row in probes if row.get('thickness_mm') is None]
    signed_volume=sum(np.dot(P[t[0]],np.cross(P[t[1]],P[t[2]])) for t in T)/6
    central=[]
    for y in sorted(set(np.round(P[ids,1],6)),key=abs):
        row=P[ids][np.abs(P[ids,1]-y)<1e-6]
        x=row[:,0].min()
        edge=row[np.abs(row[:,0]-x)<1e-6]
        if x<-.39 and abs(y)<.025 and len(edge)>1:
            central.append(dict(y=float(y),x=float(x),width_mm=float(np.ptp(edge[:,2])*scale)))
    return dict(model_sha256=sha(path),triangles=len(T),closed_two_faces_per_edge=bool(np.all(counts==2)),
                minimum_incident_faces=int(counts.min()),maximum_incident_faces=int(counts.max()),
                signed_volume=signed_volume,normal_rays=len(probes),missing_rays=missing,
                normal_thickness_min_mm=min(row['thickness_mm'] for row in probes if row.get('thickness_mm') is not None),
                central_trailing_edge=central,probes=probes)
p=argparse.ArgumentParser()
p.add_argument('--work',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
w=a.work.resolve()
plan=json.loads((w/'tail-r3/review.plan.json').read_text())
old=audit(w/'source-r1/fish.glb',plan['model_scale']*1000)
new=audit(w/'tail-r3/fish.glb',plan['model_scale']*1000)
ok=new['closed_two_faces_per_edge'] and not new['missing_rays'] and new['signed_volume']>0 and max(r['width_mm'] for r in new['central_trailing_edge'])<.451
result=dict(ok=ok,model_sha256=new['model_sha256'],before=old,after=new,
            scope='Actual finite caudal shell, four inward normal rays per face and matched trailing-edge stations. Rest geometry only; current root/membrane pose gates are separate.')
(w/'tail-r3/tail-volume.validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(ok=ok,old_closed=old['closed_two_faces_per_edge'],new_closed=new['closed_two_faces_per_edge'],old_missing=len(old['missing_rays']),new_missing=len(new['missing_rays']),rays=new['normal_rays'],central_before=old['central_trailing_edge'],central_after=new['central_trailing_edge'])))
sys.exit(0 if ok else 1)
