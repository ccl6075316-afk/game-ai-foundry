"""Freeze explicit own-species width targets on an existing finite packed source."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())

def prepare(config_path,out):
    c=read(config_path);out=out.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists()
    for row in c['inputs'].values():assert sha(row['path'])==row['sha256']
    baseline=read(c['inputs']['baseline_audit']['path']);spec=read(c['inputs']['spec']['path']);assert baseline['species']==spec['species']==c['species']
    assert baseline['model_sha256']==c['inputs']['model']['sha256'];assert c['evidence_grade'].startswith('D')
    d,b=read_glb(c['inputs']['model']['path']);assert len(d['meshes'])==1 and len(d['meshes'][0]['primitives'])==1
    pr=d['meshes'][0]['primitives'][0];pos=arrays(d,b,pr['attributes']['POSITION']);n=arrays(d,b,pr['attributes']['NORMAL']);lo,hi=pos[:,0].min(),pos[:,0].max();L=hi-lo
    targets=c['target_width_stations_cm'];cutoff=c['cutoff_s'];stations=[]
    assert all(0<s<cutoff and w>0 for s,w in targets)and np.all(np.diff(np.array(targets)[:,0])>0)
    for s,w in targets:
        measured=next(r['width_cm']for r in baseline['sections']if abs(r['s_from_nose_over_visible_TL']-s)<1e-9);stations.append([s,w/measured])
    stations=[[0,stations[0][1]],*stations,[cutoff,1],[1,1]]
    field=PchipInterpolator(np.array(stations)[:,0],np.array(stations)[:,1]);s=(hi-pos[:,0])/L;g=field(s);dgdx=-field.derivative()(s)/L
    assert np.isfinite(g).all()and .5<g.min()and g.max()<2.5,'Inspect extreme gains instead of extrapolating'
    new=pos.copy();new[:,2]=pos[:,2]*g;nn=n.astype(float).copy();nn[:,0]-=pos[:,2]*dgdx/g*n[:,2];nn[:,2]/=g;nn/=np.linalg.norm(nn,axis=1)[:,None];nn=nn.astype('float32');keep=s>=cutoff;new[keep]=pos[keep];nn[keep]=n[keep]
    scale=spec['viewer']['model_scale'];tl=baseline['display_length_cm']/100;parts=[]
    for part in d['extras']['geometry_parts']:
        j=part['vertex_start'];end=j+part['vertex_count'];parts.append({'name':part['name'],'role':part['role'],'changed_vertices':int(np.any(pos[j:end]!=new[j:end],axis=1).sum())})
    runtime={k:spec['motion'][k]for k in ['profile','runtime']}
    plan={**c,'kind':'single_fish_transverse_width_trial','config_sha256':sha(config_path),'gain_stations':stations,'display_TL_cm':baseline['display_length_cm'],'model_scale':scale,'head_focus':[float((hi-.12*L)*scale),0,0],'whole_width':tl*1.4,'head_width':tl*.42,'front_width':tl*.75,'motion_width':tl*1.5,'runtime_bindings':runtime,'parts':parts,'old_positions_gltf':pos.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':nn.tolist(),'formal_acceptance':False}
    out.mkdir();write(out/'deformation.plan.json',plan);write(out/'manifest.json',{'kind':'species_width_trial','species':c['species'],'status':'pending','next_action':'run','inputs':c['inputs'],'scope':c['scope'],'formal_acceptance':False,'installed':False})
    return {'ok':True,'species':c['species'],'stations':len(targets),'gain_min_max':[float(g.min()),float(g.max())],'output':str(out)}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();print(json.dumps(prepare(a.config,a.output)))
