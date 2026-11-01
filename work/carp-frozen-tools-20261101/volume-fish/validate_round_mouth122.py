"""Verify frozen anterior crowns, exact side-rim preservation and original GLB streams."""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from round_mouth_front122 import field,sha

def validate(row,baseline=False):
    sd,sb=read_glb(Path(row['source']));td,tb=read_glb(Path(row['source'] if baseline else row['target']))
    assert sha(row['source'])==row['source_sha256'];assert tb[:len(sb)]==sb
    for key in ['nodes','skins','animations','images','textures','materials','samplers']:assert sd.get(key)==td.get(key),key
    assert len(sd['meshes'])==len(td['meshes'])
    curves=[];side_count=0;changed=0;all_points=defaultdict(list)
    for node in sd['nodes']:
        if 'mesh' not in node:continue
        mi=node['mesh'];sm,tm=sd['meshes'][mi],td['meshes'][mi]
        assert {k:v for k,v in sm.items() if k!='primitives'}=={k:v for k,v in tm.items() if k!='primitives'}
        assert len(sm['primitives'])==len(tm['primitives'])
        for si,(sp,tp) in enumerate(zip(sm['primitives'],tm['primitives'])):
            assert {k:v for k,v in sp.items() if k!='attributes'}=={k:v for k,v in tp.items() if k!='attributes'}
            aa={k:accessor(sd,sb,v) for k,v in sp['attributes'].items()};bb={k:accessor(td,tb,v) for k,v in tp['attributes'].items()};assert aa.keys()==bb.keys()
            if node['name']!=row['mesh']:
                assert all(np.array_equal(aa[k],bb[k]) for k in aa);continue
            p=aa['POSITION'].astype(float);q=bb['POSITION'];flags=aa['TEXCOORD_1'][:,1]
            assert np.array_equal(p[:,1:],q[:,1:]),'Y/Z changed'
            for k in aa:
                if k not in ['POSITION','NORMAL','TANGENT']:assert np.array_equal(aa[k],bb[k]),'Changed '+k
            dx,jxx,jxz=field(p,flags,row);active=dx>0
            if not baseline:
                assert np.array_equal(q[:,0],(p[:,0]+dx).astype('<f4')),'Incorrect X field'
                assert np.array_equal(q[~active],aa['POSITION'][~active]),'Frozen position changed'
                n=aa['NORMAL'].astype(float);nn=n.copy();nn[:,0]/=jxx;nn[:,2]-=jxz*n[:,0]/jxx;nn/=np.maximum(np.linalg.norm(nn,axis=1),1e-12)[:,None];nn[~active]=n[~active]
                assert np.max(abs(bb['NORMAL']-nn))<2e-6,'Normal transport'
                assert np.array_equal(bb['NORMAL'][~active],aa['NORMAL'][~active]),'Frozen normals changed'
            assert np.isfinite(q).all() and np.isfinite(bb['NORMAL']).all()
            idx=accessor(sd,sb,sp['indices']).reshape(-1,3)
            on=np.cross(p[idx[:,1]]-p[idx[:,0]],p[idx[:,2]]-p[idx[:,0]])
            new=q.astype(float);nn=np.cross(new[idx[:,1]]-new[idx[:,0]],new[idx[:,2]]-new[idx[:,0]])
            assert np.all(np.sum(on*nn,axis=1)>0),'Flipped/degenerate face'
            changed+=int(np.any(aa['POSITION']!=q,axis=1).sum())
            for v,newv,flag in zip(p,q,flags):
                if v[0]+.5>row['start_u']:all_points[tuple(v)].append((float(flag),tuple(newv)))
            if si!=1:continue
            # Each actual oral row contributes both lateral endpoints per branch.
            for x in np.unique(p[:,0]):
                for flag in [0,1]:
                    ids=np.flatnonzero((p[:,0]==x)&(flags==flag))
                    if not len(ids):continue
                    maximum=abs(p[ids,2]).max();sides=ids[abs(p[ids,2])>=maximum-1e-12]
                    assert np.array_equal(aa['POSITION'][sides],q[sides]),'Actual lateral lip moved'
                    side_count+=len(sides)
            for test in row['curve_tests']:
                flag=test['upper_flag'];rad=row['radius_upper'] if flag else row['radius_lower']
                ids=np.flatnonzero((p[:,0]==p[:,0].max())&(flags==flag));order=np.argsort(p[ids,2]);ids=ids[order];z=p[ids,2]/rad
                actual=np.interp(test['q'],z,q[ids,0].astype(float))-(float(q[ids[0],0])+float(q[ids[-1],0]))/2
                error=float(np.max(abs(actual-test['expected_bow'])));curves.append({'upper_flag':flag,'maximum_bow_error':error,'tolerance':test['tolerance'],'ok':error<=test['tolerance']})
    assert all(len({f for f,v in values})==1 and len({v for f,v in values})==1 for values in all_points.values()),'Split common skin/oral point'
    if not baseline:assert changed>0
    return {'species':row['species'],'ok':all(x['ok'] for x in curves),'curves':curves,'lateral_lip_points_exact':side_count,'changed_vertices':changed,'model_sha256':sha(row['source'] if baseline else row['target'])}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',action='store_true');a=p.parse_args();rows=[]
    try:
        for r in json.loads(a.plan.read_text())['items']:rows.append(validate(r,a.baseline))
        result={'ok':all(r['ok'] for r in rows),'expected_negative':a.baseline,'items':rows}
    except Exception as e:result={'ok':False,'items':rows,'error':str(e),'expected_negative':a.baseline}
    result.update(plan_sha256=sha(a.plan),checker_sha256=sha(__file__),builder_sha256=sha(Path(__file__).with_name('round_mouth_front122.py')))
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':result['ok'],'error':result.get('error'),'species':[(r['species'],r['ok']) for r in rows]}))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
