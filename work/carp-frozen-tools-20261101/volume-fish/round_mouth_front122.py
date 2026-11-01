"""C1 anterior lip crown on frozen upper/lower transverse branches.

This is an explicit artistic trial, not a universal biological mouth shape.
All non-body geometry and original UV/rig/animation/image streams are retained.
"""
import argparse, copy, hashlib, json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb, accessor
from patch_existing_fin_meshes import write

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def field(p, flags, row):
    p=np.asarray(p,dtype=float)
    radius=np.where(flags>.5,row['radius_upper'],row['radius_lower'])
    t=np.clip((p[:,0]+.5-row['start_u'])/(row['plateau_u']-row['start_u']),0.,1.)
    f=t*t*(3-2*t)
    df=np.where((t>0)&(t<1),6*t*(1-t)/(row['plateau_u']-row['start_u']),0.)
    q=p[:,2]/radius; inside=abs(q)<1
    h=np.where(inside,(1-q*q)**2,0.)
    dh=np.where(inside,-4*q*(1-q*q)/radius,0.)
    return row['sag']*f*h, 1+row['sag']*df*h, row['sag']*f*dh

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--report',type=Path,required=True)
    a=ap.parse_args(); records=[]
    for row in json.loads(a.plan.read_text())['items']:
        source,target=Path(row['source']),Path(row['target'])
        assert source.resolve()!=target.resolve() and sha(source)==row['source_sha256']
        assert 0<row['sag']<min(row['radius_upper'],row['radius_lower'])
        assert row['start_u']<row['plateau_u']
        d,b=read_glb(source);old=copy.deepcopy(d);binary=bytearray(b)
        node=next(n for n in d['nodes'] if n.get('name')==row['mesh'])
        assert not any(k in node for k in ['matrix','translation','rotation','scale'])
        parts=d['meshes'][node['mesh']]['primitives'];assert len(parts)==2
        def add(values,template):
            data=np.asarray(values,dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));off=len(binary);binary.extend(data.tobytes())
            vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':data.nbytes,'target':34962})
            ac=copy.deepcopy(template);ac.update(bufferView=vi,byteOffset=0,count=len(data),componentType=5126,min=data.min(0).tolist(),max=data.max(0).tolist())
            ai=len(d['accessors']);d['accessors'].append(ac);return ai
        counts=[]
        for part in parts:
            at=part['attributes'];p=accessor(old,b,at['POSITION']).astype(float)
            flags=accessor(old,b,at['TEXCOORD_1'])[:,1]
            assert np.all(np.isin(flags[p[:,0]+.5>row['start_u']],[0,1]))
            dx,jxx,jxz=field(p,flags,row);mask=dx>0;assert mask.any() and np.all(jxx>=1)
            q=p.copy();q[:,0]+=dx
            n=accessor(old,b,at['NORMAL']).astype(float);nn=n.copy();nn[:,0]=n[:,0]/jxx;nn[:,2]=n[:,2]-jxz*n[:,0]/jxx
            nn/=np.maximum(np.linalg.norm(nn,axis=1),1e-12)[:,None];nn[~mask]=n[~mask]
            at['POSITION']=add(q,d['accessors'][at['POSITION']]);at['NORMAL']=add(nn,d['accessors'][at['NORMAL']])
            if 'TANGENT' in at:
                t=accessor(old,b,at['TANGENT']).astype(float);nt=t.copy();nt[:,0]=jxx*t[:,0]+jxz*t[:,2]
                nt[:,:3]/=np.maximum(np.linalg.norm(nt[:,:3],axis=1),1e-12)[:,None];nt[~mask]=t[~mask]
                at['TANGENT']=add(nt,d['accessors'][at['TANGENT']])
            counts.append(int(mask.sum()))
        assert bytes(binary[:len(b)])==b
        for key in ['nodes','skins','animations','images','textures','materials','samplers']:assert d.get(key)==old.get(key)
        target.parent.mkdir(parents=True,exist_ok=True);write(target,d,binary)
        records.append({'species':row['species'],'source_sha256':row['source_sha256'],'model_sha256':sha(target),'changed_vertices':counts})
    a.report.write_text(json.dumps({'ok':True,'items':records,'plan_sha256':sha(a.plan),'builder_sha256':sha(__file__)},indent=2)+'\n')
    print(json.dumps({'ok':True,'species':[r['species'] for r in records]}))
if __name__=='__main__':main()
