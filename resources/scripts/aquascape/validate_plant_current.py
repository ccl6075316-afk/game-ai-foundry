"""Validate the serialized skin and native loop, including actual pinned vertices."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rig_plant_current import read_glb,array


def slerp(a,b,t):
    dot=np.dot(a,b)
    if dot<0:b=-b;dot=-dot
    if dot>.9995:q=a+(b-a)*t;return q/np.linalg.norm(q)
    angle=np.arccos(np.clip(dot,-1,1));return (np.sin((1-t)*angle)*a+np.sin(t*angle)*b)/np.sin(angle)


def pose(doc,binary,time=None):
    animated={}
    if time is not None:
        anim=doc['animations'][0]
        for ch in anim['channels']:
            sampler=anim['samplers'][ch['sampler']];ts=array(doc,binary,sampler['input'])[:,0];qs=array(doc,binary,sampler['output'])
            i=int(np.clip(np.searchsorted(ts,time,side='right')-1,0,len(ts)-2));blend=float(np.clip((time-ts[i])/(ts[i+1]-ts[i]),0,1))
            animated[ch['target']['node']]=slerp(qs[i],qs[i+1],blend)
    parents={child:i for i,n in enumerate(doc['nodes']) for child in n.get('children',[])}
    world={}
    for i,node in enumerate(doc['nodes']):
        mat=np.eye(4);mat[:3,:3]=Rotation.from_quat(animated.get(i,node.get('rotation',[0,0,0,1]))).as_matrix();mat[:3,3]=node.get('translation',[0,0,0])
        world[i]=world[parents[i]]@mat if i in parents else mat
    skin=doc['skins'][0];inverse=array(doc,binary,skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
    return np.stack([world[i] for i in skin['joints']])@inverse


def deform(prim,doc,binary,matrices):
    attrs=prim['attributes'];v=array(doc,binary,attrs['POSITION']);j=array(doc,binary,attrs['JOINTS_0']);w=array(doc,binary,attrs['WEIGHTS_0'])
    result=np.zeros_like(v,dtype=float);h=np.c_[v,np.ones(len(v))]
    for influence in range(4):
        if not w[:,influence].any():continue
        transformed=np.einsum('vij,vj->vi',matrices[j[:,influence]],h)[:,:3]
        result+=transformed*w[:,influence,None]
    return result


def validate(path,source,spec,config):
    doc,binary=read_glb(path);original,original_bin=read_glb(source);failures=[]
    rest=pose(doc,binary);first=pose(doc,binary,0);last=pose(doc,binary,config['duration_s'])
    rest_error=0;anchor_error=0;loop_error=0;tips=0;images_identical=True;weights_valid=True;tip_samples=[]
    times=np.linspace(0,config['duration_s'],81)
    matrices=[pose(doc,binary,float(t)) for t in times]
    for im,old in zip(doc['images'],original['images']):
        a=doc['bufferViews'][im['bufferView']];b=original['bufferViews'][old['bufferView']]
        images_identical &= binary[a.get('byteOffset',0):a.get('byteOffset',0)+a['byteLength']]==original_bin[b.get('byteOffset',0):b.get('byteOffset',0)+b['byteLength']]
    for mesh,oldmesh in zip(doc['meshes'],original['meshes']):
        leaf=mesh['name'].startswith('traced_leaf_');leaf_peak=0
        for prim,oldprim in zip(mesh['primitives'],oldmesh['primitives']):
            attrs=prim['attributes'];v=array(doc,binary,attrs['POSITION']);uv=array(doc,binary,attrs['TEXCOORD_0'])
            for key in ['POSITION','NORMAL','TEXCOORD_0']:
                if not np.array_equal(array(doc,binary,attrs[key]),array(original,original_bin,oldprim['attributes'][key])):failures.append(mesh['name']+': source attribute changed: '+key)
            w=array(doc,binary,attrs['WEIGHTS_0']);j=array(doc,binary,attrs['JOINTS_0'])
            weights_valid &= bool(np.isfinite(w).all() and (w>=0).all() and np.allclose(w.sum(1),1,atol=1e-6) and j.max()<len(doc['skins'][0]['joints']))
            rest_error=max(rest_error,float(np.linalg.norm(deform(prim,doc,binary,rest)-v,axis=1).max()))
            loop_error=max(loop_error,float(np.linalg.norm(deform(prim,doc,binary,first)-deform(prim,doc,binary,last),axis=1).max()))
            pinned=(1-uv[:,1]<=config['root_pin_fraction']+1e-6) if leaf else np.ones(len(v),dtype=bool)
            distal=(1-uv[:,1]>.9) if leaf else np.zeros(len(v),dtype=bool)
            if leaf and (not pinned.any() or not distal.any()):failures.append(mesh['name']+': empty root/tip selection')
            for m in matrices:
                moved=deform(prim,doc,binary,m)-v
                if pinned.any():anchor_error=max(anchor_error,float(np.linalg.norm(moved[pinned],axis=1).max()))
                if distal.any():leaf_peak=max(leaf_peak,float(np.linalg.norm(moved[distal],axis=1).max()))
        if leaf:tip_samples.append(leaf_peak);tips=max(tips,leaf_peak)
    if not images_identical:failures.append('Original generated image bytes changed')
    if not weights_valid:failures.append('Invalid skin weights/joints')
    if rest_error>1e-6:failures.append('Bind pose changes original geometry')
    if anchor_error>1e-6:failures.append('Pinned root/rhizome vertices move')
    if loop_error>1e-6:failures.append('Loop has positional seam')
    low,high=spec['tip_displacement_range_m']
    if not low<tips<high:failures.append('Leaf tip amplitude outside species trial range')
    return {'id':spec['id'],'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'ok':not failures,'joint_count':len(doc['skins'][0]['joints']),'sampled_poses':len(times),'rest_error_m':rest_error,'max_pinned_vertex_motion_m':anchor_error,'loop_seam_m':loop_error,'max_tip_motion_from_rest_m':tips,'per_leaf_tip_motion_m':tip_samples,'original_image_bytes_identical':images_identical,'weights_valid':weights_valid,'failures':failures}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();cfg=json.loads(a.config.read_text(encoding='utf-8'))
    rows=[validate(a.input/(s['id']+'.glb'),a.root/cfg['source_models']/(s['id']+'.glb'),s,cfg) for s in cfg['plants']]
    okay=all(r['ok'] for r in rows)
    report={'schema_version':1,'command':'aquascape.validate-plant-current','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':rows,'failures':[f for r in rows for f in r['failures']],'scope':'Serialized CPU skinning and sampled loop. Must inspect actual Godot skeletal import and rendered motion; no full-time collision proof.','user_acceptance':'pending'}
    a.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));return 0 if okay else 1


if __name__=='__main__':raise SystemExit(main())
