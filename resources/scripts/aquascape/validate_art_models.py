"""Inspect actual GLB payloads, embedded textures and seam-welded edge incidence."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image


def inspect(path):
    raw=path.read_bytes();size=struct.unpack_from('<I',raw,12)[0]
    d=json.loads(raw[20:20+size]);binary=raw[28+size:]
    def read(index):
        a=d['accessors'][index];v=d['bufferViews'][a['bufferView']]
        offset=v.get('byteOffset',0)+a.get('byteOffset',0)
        n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
        return np.frombuffer(binary,dtype=dtype,count=a['count']*n,offset=offset).reshape(-1,n)
    meshes=[];alltri=[];failed=[]
    for mesh in d['meshes']:
        for prim in mesh['primitives']:
            v=read(prim['attributes']['POSITION']);uv=read(prim['attributes']['TEXCOORD_0']);normal=read(prim['attributes']['NORMAL'])
            tri=v.reshape(-1,3,3);alltri.append(tri)
            cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1)
            good=bool(np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(normal).all() and (area>1e-20).all())
            if not good:failed.append(mesh['name']+': invalid vertex/UV/normal or zero-area triangle')
            meshes.append({'name':mesh['name'],'triangles':len(tri),'finite_and_nonzero_area':good})
    triangles=np.concatenate(alltri)
    quantized=triangles.reshape(-1,3)
    _,ids=np.unique(quantized,axis=0,return_inverse=True);faces=ids.reshape(-1,3)
    edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);edges.sort(axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    boundary=int((counts==1).sum());nonmanifold=int((counts>2).sum())
    # Topology is reported separately; a technical pass does not hide open edges.
    if boundary:failed.append(f'{boundary} open edges after positional seam weld')
    textures=[]
    for im in d['images']:
        view=d['bufferViews'][im['bufferView']];offset=view.get('byteOffset',0)
        image=Image.open(io.BytesIO(binary[offset:offset+view['byteLength']])).convert('RGBA');a=np.asarray(image)
        opaque=bool((a[:,:,3]==255).all())
        textures.append({'name':im['name'],'size':list(image.size),'opaque':opaque})
        if not opaque:failed.append(im['name']+': unexpected transparency')
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'ok':not failed,'meshes':meshes,'textures':textures,'open_edges':boundary,'nonmanifold_edges':nonmanifold,'failures':failed}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    results=[inspect(f) for f in sorted(a.input.glob('*.glb'))]
    report={'command':'aquascape.validate-art-models','ok':bool(results) and all(r['ok'] for r in results),'status':'done','next_action':'human_review','outputs':results,'user_acceptance':'pending','scope':'Payload and closed-edge checks only. No style, contact or reconstruction-accuracy certification.'}
    if not report['ok']:report.update(status='failed',next_action='fix_input')
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='outputs'},ensure_ascii=False))
    print(json.dumps([{'file':r['path'],'open_edges':r['open_edges'],'nonmanifold_edges':r['nonmanifold_edges'],'failures':r['failures']} for r in results]))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
