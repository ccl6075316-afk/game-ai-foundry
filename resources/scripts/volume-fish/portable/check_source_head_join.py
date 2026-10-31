"""Actual exported whole head/body join versus frozen native-source targets.

Independent of any generated frontal image. Old rejected body must fail the
same predeclared pixel tolerance. Width/anatomy/mouth/visual gates stay separate.
"""
import argparse,json
from pathlib import Path
import numpy as np
from parts import packed_arrays,read,sha,BODY_ROLES
from fish_asset_spec import load_spec,resolve_ref


def envelope(triangles,x,aspect,H):
    points=[]
    for a,b in[(triangles[:,0],triangles[:,1]),(triangles[:,1],triangles[:,2]),(triangles[:,2],triangles[:,0])]:
        hit=(a[:,0]-x)*(b[:,0]-x)<0
        if hit.any():
            t=(x-a[hit,0])/(b[hit,0]-a[hit,0]);points.extend(a[hit]+t[:,None]*(b[hit]-a[hit]))
        points.extend(a[np.abs(a[:,0]-x)<1e-7])
    if not points:raise ValueError('Missing actual body cross section')
    y=np.asarray(points)[:,1];return np.array([.5-y.max()/aspect,.5-y.min()/aspect])*H


def check(spec_path,target):
    spec=load_spec(spec_path);model=resolve_ref(spec['model']);doc,blob,node,primitive,parts,values,indices,joints,actual=packed_arrays(model,spec)
    ids=np.concatenate([indices[p['index_range'][0]:p['index_range'][1]]for p in parts if p['role']in BODY_ROLES]).reshape(-1,3);triangles=values['POSITION'][ids];W,H=target['source_size'];rows=[]
    for row in target['samples']:
        expected=np.array([row['top_px'],row['bottom_px']]);observed=envelope(triangles,row['u']-.5,H/W,H);error=abs(expected-observed)
        rows.append({'u':row['u'],'target_px':expected.tolist(),'actual_px':observed.tolist(),'error_px':error.tolist()})
    maximum=max(max(r['error_px'])for r in rows)
    return {'ok':maximum<=target['tolerance_source_px'],'model':str(model),'model_sha256':sha(model),'spec_sha256':sha(spec_path),'maximum_error_source_px':maximum,'samples':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in['spec','target','rejected_spec','output']:p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    a=p.parse_args();target=read(a.target);assert sha(target['source'])==target['source_sha256'];current=check(a.spec,target);rejected=check(a.rejected_spec,target)
    report={'ok':current['ok']and not rejected['ok'],'kind':'native_source_whole_head_body_join','target_sha256':sha(a.target),'tolerance_source_px':target['tolerance_source_px'],'current':current,'rejected_original':rejected,'scope':'Actual GLB cross sections, whole declared join, source-derived vertical profile and rejected old candidate only. Separate transverse/head/mouth and real gray/source images remain required.'};assert not a.output.exists();a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':report['ok'],'current_max_px':current['maximum_error_source_px'],'rejected_max_px':rejected['maximum_error_source_px']}));raise SystemExit(0 if report['ok']else 1)
