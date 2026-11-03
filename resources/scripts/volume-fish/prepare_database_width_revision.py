"""Prepare one source-owned transverse revision from an inspected local reference.

Preserves project XY, topology, UV, skin, rig and clips. A width proposal is not
physical or visual acceptance; finite fin/body and source/cold gates remain due.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays
from audit_transverse_width import section
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n',encoding='utf8')
def main(a):
    out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and (not out.exists() or not any(out.iterdir()))
    report=json.loads(a.comparison.read_text(encoding='utf8'));species=report['species'];assert species!='red_emperor' or a.allow_related
    game=ROOT/report['installed']['path'];ref=ROOT/report['reference']['path'];assert sha(game)==report['installed']['sha256'] and sha(ref)==report['reference']['sha256']
    d,b=read_glb(game);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);norm=arrays(d,b,pr['attributes']['NORMAL']);idx=arrays(d,b,pr['indices']).reshape(-1)
    body=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']] for p in d['extras']['geometry_parts'] if p['role'] in ['body_skin','mouth']]);lo,hi=v[body,0].min(),v[body,0].max();L=hi-lo
    refrows=report['sections']['reference'];rt=np.array([r['s'] for r in refrows]);rw=np.array([r['width_over_body_axis'] for r in refrows]);target=PchipInterpolator(rt,rw)
    # A modest longitudinal set fits the inspected reference without inheriting
    # each low-poly ripple. Preserve the final peduncle/tail interface in a
    # declared smooth posterior transition, rather than copying external topology.
    installed_record=json.loads((ROOT/'output/five-fish-database-20261103/restored'/species/'frozen/delivery-config.json').read_text())
    head_stations=[float((hi-(u-.5))/L) for u in installed_record['head_stations']]
    stations=np.array(sorted(set([.005,.015,.03,.05,.08,.12,.18,.24,.30,.36,.42,.48,.55,.62,.70,.76,.82,.88,.94,.98]+[s for s in head_stations if .005<=s<=.82])))
    gains=[];source=[]
    for t in stations:
        w=float(np.ptp(section(v,body,hi-t*L)[:,2]));desired=float(target(t)*L)
        blend=np.clip((.98-t)/.16,0,1);blend=blend*blend*(3-2*blend)
        desired=w+(desired-w)*blend
        gains.append(desired/w);source.append({'s_body':float(t),'reference_width_over_body_axis':float(target(t)),'baseline_width':w,'proposed_width':desired,'posterior_reference_weight':float(blend)})
    tt=np.r_[0,stations,1];gg=np.r_[gains[0],gains,1.];field=PchipInterpolator(tt,gg);t=np.clip((hi-v[:,0])/L,0,1)
    # The reference target is independent of the sparse construction field.
    # Preflight original named head planes on actual finite triangles, and only
    # calibrate the field if needed; do not alter the curve or its tolerance.
    head=[]
    for u in installed_record['head_stations']:
        s=float((hi-(u-.5))/L)
        if .005<=s<=.82:head.append((s,float(target(s)*L)))
    test_stations=sorted(set(stations.tolist()+[s for s,w in head]));target_rows=[]
    for s in test_stations:
        oldw=float(np.ptp(section(v,body,hi-s*L)[:,2]));blend=np.clip((.98-s)/.16,0,1);blend=blend*blend*(3-2*blend);target_rows.append((s,oldw+(float(target(s)*L)-oldw)*blend))
    def finite_errors(values):
        f=PchipInterpolator(tt,values);vv=v.copy();vv[:,2]*=f(t)
        return np.array([float(np.ptp(section(vv,body,hi-s*L)[:,2]))-w for s,w in target_rows])
    initial_errors=finite_errors(gg);head_ids=[i for i,(s,w)in enumerate(target_rows) if any(abs(s-h[0])<1e-9 for h in head)];tolerance=installed_record['head_tolerance'];calibration={'performed':False,'head_halfwidth_tolerance_native':tolerance,'initial_head_halfwidth_errors':[float(initial_errors[i]/2) for i in head_ids]}
    if head_ids and max(abs(initial_errors[i]/2) for i in head_ids)>tolerance:
        start=gg.copy();weights=np.ones(len(target_rows));weights[head_ids]=20
        def residual(values):return np.r_[finite_errors(np.r_[values,1])*weights,.0002*(values-start[:-1])]
        solved=least_squares(residual,start[:-1],bounds=(.500001,2.499999),max_nfev=100,xtol=1e-10,ftol=1e-10,gtol=1e-10);gg=np.r_[solved.x,1];field=PchipInterpolator(tt,gg);actual=finite_errors(gg);calibration.update(performed=True,parameter_evaluations=solved.nfev,final_head_halfwidth_errors=[float(actual[i]/2) for i in head_ids],target_unchanged=True,tolerance_unchanged=True)
        if max(abs(actual[i]/2) for i in head_ids)>tolerance:
            out.parent.mkdir(parents=True,exist_ok=True);write(out.parent/'preflight-failure.validation.json',{'ok':False,'species':species,'status':'blocked','next_action':'fix_input','calibration':calibration,'head_target_rows':[target_rows[i] for i in head_ids],'solved_gain_stations':np.c_[tt,gg].tolist(),'model_modified':False})
            raise AssertionError('Finite head target still unresolved; see preflight-failure.validation.json; do not author or relax it')
    g=field(t);dgdx=-field.derivative()(t)/L
    assert .5<float(g.min())<float(g.max())<2.5
    new=v.copy();new[:,2]*=g
    n=norm.astype(float).copy();n[:,0]-=v[:,2]*dgdx/g*norm[:,2];n[:,2]/=g;n/=np.linalg.norm(n,axis=1)[:,None]
    tris=body.reshape(-1,3);fn=np.cross(new[tris[:,1]]-new[tris[:,0]],new[tris[:,2]]-new[tris[:,0]]);fn/=np.maximum(np.linalg.norm(fn,axis=1)[:,None],1e-30)
    badbefore=int(((fn*n[tris].mean(1)).sum(1)<=0).sum())
    for _ in range(500):
        dots=(fn*n[tris].mean(1)).sum(1);bad=np.flatnonzero(dots<=1e-5)
        if not len(bad):break
        for i in bad:
            ids=tris[i];n[ids]+=max(0,1e-4-float(n[ids].mean(0)@fn[i]))*fn[i];n[ids]/=np.linalg.norm(n[ids],axis=1)[:,None]
    assert np.all((fn*n[tris].mean(1)).sum(1)>0)
    motion=ROOT/f'projects/fishing-2d/game/assets/models/fish/motion/width20261101/{species}.json';runtime=ROOT/'projects/fishing-2d/game/scripts/aquarium/FoundryFishMotion.gd';table=json.loads((motion.parent/'manifest.json').read_text())['profiles'][species];scale=table['model_scale'];visibleL=np.ptp(v[:,0]);TL=visibleL*scale
    inp={'model':game,'blend':a.blend.resolve(),'comparison':a.comparison.resolve(),'reference':ref,'motion':motion,'runtime':runtime}
    plan={'kind':'single_fish_transverse_width_trial','stage':'database-reference-width-r1','species':species,'inputs':{k:{'path':str(p),'sha256':sha(p)} for k,p in inp.items()},'scope':'Transverse artistic shape reference only; project XY/art, exact UV/material/alpha, topology, weights, rig and animation preserved. Old affected physical gates invalid.','evidence_grade':'Third-party game shape, biological identity/precision/age unknown','normalization':'Matched visible body nose-to-peduncle body-mesh axis, fin and detached-eye components excluded; not biological SL/TL','reference_stations':source,'finite_head_preflight':calibration,'gain_stations':np.c_[tt,gg].tolist(),'finite_body_normal_failures_before':badbefore,'finite_body_normal_failures_after':0,'gain_range':[float(g.min()),float(g.max())],'model_scale':scale,'display_TL_cm':TL*100,'head_focus':[float((hi-.12*visibleL)*scale),0,0],'whole_width':TL*1.35,'head_width':TL*.45,'front_width':TL*.70,'motion_width':TL*1.4,'runtime_bindings':{k:{'path':str(p),'sha256':sha(p)} for k,p in [('profile',motion),('runtime',runtime)]},'target_width_stations_cm':[[float((hi-(hi-s*L))/visibleL),float(w['proposed_width']*scale*100)] for s,w in zip(stations,source)],'old_positions_gltf':v.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':n.astype('float32').tolist(),'formal_acceptance':False}
    out.mkdir(parents=True,exist_ok=True);write(out/'deformation.plan.json',plan);write(out/'manifest.json',{'kind':'database_reference_width_revision','species':species,'status':'pending','next_action':'author_then_local_mouth_review','formal_acceptance':False,'installed':False,'inputs':plan['inputs'],'gain_range':plan['gain_range']})
    print(json.dumps({'ok':True,'species':species,'output':str(out),'gain_range':plan['gain_range'],'finite_normal_failures_before':badbefore}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['comparison','blend','output']:p.add_argument('--'+k,required=True,type=Path)
    p.add_argument('--allow-related',action='store_true');main(p.parse_args())
