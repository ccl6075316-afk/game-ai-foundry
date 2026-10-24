"""Freeze original closed-body attributes for a species-specific curvature study."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb, accessor

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();d,b=read_glb(a.model)
    node=next(n for n in d['nodes'] if n.get('name')=='Closed_body')
    assert not any(k in node for k in ['matrix','translation','rotation','scale'])
    rows={k:[] for k in ['vertices','normals','uv','uv2','triangles','surface']};offset=0
    for si,prim in enumerate(d['meshes'][node['mesh']]['primitives']):
        attrs=prim['attributes'];v=accessor(d,b,attrs['POSITION']);t=accessor(d,b,prim['indices']).reshape(-1,3)
        rows['vertices'].append(v);rows['normals'].append(accessor(d,b,attrs['NORMAL']))
        rows['uv'].append(accessor(d,b,attrs['TEXCOORD_0']))
        rows['uv2'].append(accessor(d,b,attrs['TEXCOORD_1']) if 'TEXCOORD_1' in attrs else np.zeros((len(v),2)))
        rows['triangles'].append(t+offset);rows['surface'].append(np.full(len(t),si));offset+=len(v)
    rows={k:np.concatenate(v) for k,v in rows.items()}
    a.output.mkdir(parents=True,exist_ok=True)
    source=a.output/'source-attributes.npz';np.savez_compressed(source,**rows)
    # Preserve exact source positions. Rounding may collapse small valid faces.
    v,inv=np.unique(rows['vertices'].astype(float),axis=0,return_inverse=True)
    t=inv[rows['triangles']]
    area=np.linalg.norm(np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]),axis=1)
    empty=np.flatnonzero(area==0)
    # These source faces have no surface area (e.g. a collinear oral seam).
    # Exclude only exact zero-area faces from voxel input; original attributes,
    # face numbering and correspondence donor arrays stay untouched.
    t=t[area>0]
    assert len(t)>0 and np.all(area[area>0]>1e-20)
    shell=a.output/'source-shell.npz';np.savez_compressed(shell,vertices=v,triangles=t)
    result={'ok':True,'status':'done','next_action':'human_review','model':str(a.model.resolve()),'model_sha256':sha(a.model),
            'outputs':[{ 'path':str(x.resolve()),'sha256':sha(x)} for x in [source,shell]],
            'zero_area_source_faces_excluded_from_voxel_input':empty.tolist(),
            'source_attributes_unchanged':True,
            'scope':'Source attributes only. No anatomy, curvature or full-fish acceptance.'}
    (a.output/'source.validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))

if __name__=='__main__':main()
