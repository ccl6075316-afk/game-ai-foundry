"""Actual finite cephalofoil leading-rim depth with the collapsed-rim negative."""
import argparse,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays,sha

def triangles(path):
    d,b=read_glb(path);node=next(n for n in d['nodes']if n.get('name')=='Reference_head_body');parts=[]
    for q in d['meshes'][node['mesh']]['primitives']:
        v=arrays(d,b,q['attributes']['POSITION']).astype(float)[:,[0,2,1]];v[:,1]*=-1;parts.extend(v[arrays(d,b,q['indices']).reshape(-1,3)])
    return np.array(parts)

def ray(tri,x,y,sign):
    origin=np.array([x,y,-2*sign]);direction=np.array([0.,0.,float(sign)]);a,b,c=tri.transpose(1,0,2);e1=b-a;e2=c-a;h=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-14;inverse=np.divide(1.,det,out=np.zeros_like(det),where=valid);s=origin-a;u=np.einsum('ij,ij->i',s,h)*inverse;q=np.cross(s,e1);v=q@direction*inverse;t=np.einsum('ij,ij->i',e2,q)*inverse;valid&=(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(t>0);assert valid.any();return float((origin+direction*t[valid].min())[2])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--config',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();assert not a.output.exists();c=json.loads(a.config.read_text());ref=json.loads(Path(c['reference']).read_text());head=ref['head_transverse_stations'];body=ref['body_stations'];rows=[]
    for key in ['model','negative']:
        assert sha(c[key])==c[key+'_sha256'];tri=triangles(c[key]);probes=[]
        for y in c['lateral_stations_m']:
            front=np.interp(y,[r['y_m']for r in head],[r['front_x_m']for r in head]);x=front-c['inset_from_front_m'];t=(ref['reference_body_axis_m']/2-x)/ref['reference_body_axis_m'];target=float(np.interp(t,[r['t']for r in body],[r['top_z_m']-r['bottom_z_m']for r in body]));top=ray(tri,x,y,-1);bottom=ray(tri,x,y,1);depth=top-bottom;probes.append(dict(x_m=float(x),y_m=y,actual_depth_m=depth,project_side_depth_m=target,depth_ratio=depth/target))
        rows.append(dict(ok=all(r['depth_ratio']>=c['minimum_side_depth_fraction']for r in probes),model_sha256=sha(c[key]),probes=probes))
    r=dict(ok=rows[0]['ok']and not rows[1]['ok'],kind='project_art_leading_rim_depth_and_collapsed_negative',current=rows[0],rejected_original=rows[1],reference_sha256=sha(c['reference']),config_sha256=sha(a.config),checker_sha256=sha(__file__),scope='Finite vertical rays just inside the own-project top outline, compared with the frozen own-side section. Engineering finite-rim requirement, not biological metrology or automatic appearance approval. Planform, mouth and source/clay checks remain separate.');a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=r['ok'],current=[x['depth_ratio']for x in rows[0]['probes']],negative=[x['depth_ratio']for x in rows[1]['probes']])));raise SystemExit(0 if r['ok']else 1)
