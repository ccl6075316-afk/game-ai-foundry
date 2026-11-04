"""Validate current source-art channels and explicit full root transport.

Geometry and fin pivot translations may change; appearance/pose acceptance is
separate. This never rewrites an old report to claim current clearance.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from portable.glb_io import read_glb, arrays
from measure_hammerhead_head_field import load_candidate, vertical


def main():
    ap=argparse.ArgumentParser()
    for k in ['baseline','candidate','fin_plan','mouth_probes','output','new_fin_plan']:ap.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    ap.add_argument('--eye-rebuild-config',type=Path,help='Explicit closed-ellipsoid rebuild; other parts keep exact topology/UV/skin guards.')
    a=ap.parse_args();old,ob=read_glb(a.baseline);new,nb=read_glb(a.candidate);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    def parts(d):return {n['name']:d['meshes'][n['mesh']]['primitives']for n in d['nodes']if 'mesh'in n}
    om,nm=parts(old),parts(new);assert set(om)==set(nm);points={};changes=[]
    for name in om:
        ov,nv=[],[]
        eye_rebuild=bool(a.eye_rebuild_config and name in ['Eye_left','Eye_right'])
        if eye_rebuild:
            config=json.loads(a.eye_rebuild_config.read_text());assert config['eye_mode']=='closed_ellipsoid' and config['protected_eye_radius']==1.0
            assert len(om[name])==len(nm[name])==1
        for x,y in zip(om[name],nm[name]):
            if eye_rebuild:
                assert len(arrays(new,nb,y['indices']))==len(arrays(old,ob,x['indices']))==192
                ou,nu=arrays(old,ob,x['attributes']['TEXCOORD_0']),arrays(new,nb,y['attributes']['TEXCOORD_0'])
                assert np.max(abs(ou.min(0)-nu.min(0)))<1e-6 and np.max(abs(ou.max(0)-nu.max(0)))<1e-6,'Changed complete native eye chart bounds'
                npos=arrays(new,nb,y['attributes']['POSITION']);design=np.column_stack([npos[:,0],npos[:,1],np.ones(len(npos))]);fit=np.linalg.lstsq(design,nu,rcond=None)[0];assert np.max(abs(design@fit-nu))<1e-6,'Non-affine original eye source chart'
            else:assert np.array_equal(arrays(old,ob,x['indices']),arrays(new,nb,y['indices']))
            for k in x['attributes']:
                u,v=arrays(old,ob,x['attributes'][k]),arrays(new,nb,y['attributes'][k]);assert u.shape==v.shape and np.isfinite(v).all()
                if k not in ['POSITION','NORMAL'] and not(eye_rebuild and k=='TEXCOORD_0'):assert np.array_equal(u,v),(name,k)
                if k=='POSITION':
                    ov.append(u);nv.append(v)
                    if not eye_rebuild:
                        if a.eye_rebuild_config and name=='Reference_head_body' and json.loads(a.eye_rebuild_config.read_text()).get('posterior_rim_rounding',{}).get('rear_fillet_forward_m'):
                            cap=json.loads(a.eye_rebuild_config.read_text())['posterior_rim_rounding']['rear_fillet_forward_m'];delta=v[:,0]-u[:,0];assert delta.min()>=-1e-7 and delta.max()<=cap+1e-7
                            moved=abs(delta)>1e-7;assert np.all(u[moved,0]>.64) and np.all(abs(u[moved,2])>.16),'Rear fillet left declared head domain'
                        else:assert np.array_equal(u[:,0],v[:,0])
        u,v=np.concatenate(ov),np.concatenate(nv);points[name]=(u,v);changes.append({'mesh':name,'maximum_delta_m':float(np.linalg.norm(u-v,axis=1).max())})
    for key in ['materials','textures','samplers']:assert old[key]==new[key],key
    images=[]
    for x,y in zip(old['images'],new['images']):
        def rgba(d,b,im):
            v=d['bufferViews'][im['bufferView']];return Image.open(io.BytesIO(b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGBA')
        u,v=rgba(old,ob,x),rgba(new,nb,y);assert u.size==v.size and u.tobytes()==v.tobytes();images.append(hashlib.sha256(v.tobytes()).hexdigest())
    def channels(d,b):
        result={}
        for anim in d['animations']:
            for ch in anim['channels']:
                key=(d['nodes'][ch['target']['node']]['name'],ch['target']['path']);s=anim['samplers'][ch['sampler']];result[key]=(arrays(d,b,s['input']),arrays(d,b,s['output']))
        return result
    oc,nc=channels(old,ob),channels(new,nb);assert set(oc)==set(nc);translations=[];rotations=[];scales=[]
    for k in oc:
        t,v=oc[k];nt,nv=nc[k];assert np.array_equal(t,nt)
        if k[1]=='translation':
            delta=nv-v;assert np.max(np.ptp(delta,axis=0))<1e-6,'Changed dynamic translation curve'
            if np.max(abs(delta))>1e-7:translations.append({'bone':k[0],'constant_delta':delta[0].tolist()})
        elif k[1]=='rotation':
            # Rest-bone translation rewrites float32 orthogonal frames in the
            # exporter. Compare unit rotations up to quaternion sign, in an
            # explicitly recorded eight-float32-epsilon angular envelope.
            u=v.astype(float);w=nv.astype(float);u/=np.linalg.norm(u,axis=1)[:,None];w/=np.linalg.norm(w,axis=1)[:,None]
            sign=np.where(np.sum(u*w,axis=1)<0,-1,1);distance=np.linalg.norm(u-w*sign[:,None],axis=1)
            angle=float(np.max(4*np.arcsin(np.minimum(1.,distance/2))))
            assert angle<=8*np.finfo(np.float32).eps,(k,angle,'rotation exceeds float32 frame roundoff')
            rotations.append({'bone':k[0],'maximum_rotation_difference_rad':angle})
        else:
            delta=nv.astype(float)-v.astype(float)
            # Parent and child rest frames are both rebuilt in float32; the
            # static frame round-trip has the same eight-epsilon budget as the
            # unit-rotation check. A time-varying scale delta is still rejected.
            assert np.max(abs(delta))<=8*np.finfo(np.float32).eps and np.max(np.ptp(delta,axis=0))==0,(k,'dynamic scale or non-quantization frame change')
            scales.append({'bone':k[0],'constant_maximum_float32_difference':float(np.max(abs(delta)))})
    # Repeat all nine actual first-hit oral rays; same finite mouth is required.
    def hit(d,b,x,y):
        ts=[];m=[]
        for p in parts(d)['Reference_head_body']:
            v=arrays(d,b,p['attributes']['POSITION']);f=arrays(d,b,p['indices']).reshape(-1,3);ts.append(v[f]);m += [d['materials'][p['material']]['name']]*len(f)
        t=np.concatenate(ts);aa,bb,cc=t[:,0],t[:,1],t[:,2];z=-y;den=(bb[:,2]-cc[:,2])*(aa[:,0]-cc[:,0])+(cc[:,0]-bb[:,0])*(aa[:,2]-cc[:,2]);valid=abs(den)>1e-12;u=np.zeros(len(t));v=u.copy();u[valid]=((bb[valid,2]-cc[valid,2])*(x-cc[valid,0])+(cc[valid,0]-bb[valid,0])*(z-cc[valid,2]))/den[valid];v[valid]=((cc[valid,2]-aa[valid,2])*(x-cc[valid,0])+(aa[valid,0]-cc[valid,0])*(z-cc[valid,2]))/den[valid];w=1-u-v;ids=np.flatnonzero(valid&(u>=-1e-7)&(v>=-1e-7)&(w>=-1e-7));hs=u*aa[:,1]+v*bb[:,1]+w*cc[:,1];i=ids[np.argmin(hs[ids])];return {'height_m':float(hs[i]),'material':m[i]}
    probes=[]
    for p in json.loads(a.mouth_probes.read_text())['probes']:
        u=hit(old,ob,p['x_m'],p['y_m']);v=hit(new,nb,p['x_m'],p['y_m']);assert u==v and v['material']=='Actual finite oral lining';probes.append(v)
    plan=json.loads(a.fin_plan.read_text());root_rows=[]
    for item in plan['items']:
        item['model']=str(a.candidate.resolve());item['model_sha256']=sha(a.candidate)
        for name,config in item['fins'].items():
            u,v=points[name];queries=np.array(config['rest_points_gltf']);dist,ix=cKDTree(u).query(queries);assert dist.max()<1e-7,(name,'root identity drift')
            config['rest_points_gltf']=v[ix].tolist();root_rows.append({'fin':name,'complete_root_count':len(ix),'maximum_original_lookup_error_m':float(dist.max())})
    a.new_fin_plan.write_text(json.dumps(plan,indent=2)+'\n')
    result={'ok':True,'kind':'hammerhead_head_body_form_semantic_transport','baseline_sha256':sha(a.baseline),'model_sha256':sha(a.candidate),'complete_topology_UV_skin_and_pixels_preserved':True,'source_rotation_scale_and_timing_preserved':True,'constant_native_translation_deltas':translations,'rotation_quantization_differences':rotations,'constant_scale_quantization_differences':scales,'images_RGBA_exact':images,'mouth_first_hit_rays':probes,'full_root_transport':root_rows,'geometry_changes':changes,'formal_acceptance':False,'scope':'Exact retained semantic inputs and explicit current complete root locations. Not fin contact/body/head-form acceptance.'};
    if a.eye_rebuild_config:
        result.update(complete_topology_UV_skin_and_pixels_preserved=False,body_and_all_fin_topology_UV_skin_preserved=True,eye_reconstruction=dict(config_sha256=sha(a.eye_rebuild_config),whole_triangles_per_eye=64,complete_original_affine_source_chart=True,same_rigid_bone_weights=True),scope='Body/fin topology UV skin and all16 RGBA exact; eyes independently rebuilt closed64-triangle ellipsoids using full original affine source eye chart, same rigid weights. No claim eye positions/topology stayed identical. Mouth rays and full root identities current; visual/clearance checks separate.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':True,'images':len(images),'mouth_rays':len(probes),'roots':root_rows,'translated_channels':len(translations)}))


if __name__=='__main__':main()
