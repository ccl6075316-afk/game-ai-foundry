"""Attach true glTF skin/bone animation to existing generated-art leaf shells.

Original mesh attributes and embedded paintings remain byte-identical. Only
JOINTS/WEIGHTS, rest bones, inverse binds and native animation are appended.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from build_from_art import Glb,rotation,split_leaves,foreground


def read_glb(path):
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
    return doc,binary[:doc['buffers'][0]['byteLength']]


def array(doc,binary,index):
    acc=doc['accessors'][index];view=doc['bufferViews'][acc['bufferView']]
    components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[acc['type']]
    dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[acc['componentType']]
    return np.frombuffer(binary,dtype=dtype,count=acc['count']*components,offset=view.get('byteOffset',0)+acc.get('byteOffset',0)).reshape(-1,components)


def append(g,values,kind,component=5126,target=None):
    values=np.ascontiguousarray(values,dtype='<f4' if component==5126 else '<u2')
    idx=len(g.doc['accessors'])
    acc={'bufferView':g.view(values.tobytes(),target),'componentType':component,'count':len(values),'type':kind}
    if kind=='SCALAR':acc.update(min=values.min(0).tolist(),max=values.max(0).tolist())
    g.doc['accessors'].append(acc);return idx


def motion_quats(spec,leaf,segment,times,duration):
    phase=spec['plant_phase']+leaf*.67
    wave=2*np.pi*times/duration
    # Shared slow current plus weaker independent harmonic, both exactly periodic.
    bend=(.78*np.sin(wave+phase-segment*.16)+.22*np.sin(2*wave+leaf*1.73-segment*.38))
    sideways=np.sin(wave+phase+.7-segment*.21)*spec['sideways_ratio']
    twist=np.sin(2*wave+phase*.8+segment*.31)*spec['twist_ratio']
    amplitude=spec['bend_degrees'][segment-1]*(.92+.12*math.sin(leaf*1.4))
    xyz=np.c_[bend,twist,sideways]*amplitude
    quat=Rotation.from_euler('xyz',xyz,degrees=True).as_quat()
    # Pin the serialized loop endpoint, avoiding floating-point phase residue.
    quat[-1]=quat[0]
    for i in range(1,len(quat)):
        if np.dot(quat[i],quat[i-1])<0:quat[i]*=-1
    return quat.astype('float32')


def rig(root,config,spec,output):
    source=root/config['source_models']/(spec['id']+'.glb')
    doc,binary=read_glb(source);g=Glb();g.doc=copy.deepcopy(doc);g.bin=bytearray(binary)
    profile_path=root/config['source_profile'];profile=json.loads(profile_path.read_text(encoding='utf-8'))
    plant=next(p for p in profile['plants'] if p['id']==spec['id'])
    images=split_leaves(root/profile['sources'][plant['parts']])
    root_node=len(g.doc['nodes']);g.doc['nodes'].append({'name':'FixedRhizome','children':[]})
    g.doc['scenes'][g.doc.get('scene',0)]['nodes'].append(root_node)
    joints=[root_node];inverse_binds=[np.eye(4)]
    duration=config['duration_s'];times=np.linspace(0,duration,round(duration*config['sample_fps'])+1,dtype='float32')
    time_accessor=append(g,times[:,None],'SCALAR')
    anim={'name':config['clip'],'samplers':[],'channels':[],'extras':{'loop':True,'duration_s':duration,'root_pinned':True}}
    leaves=[]
    for mesh_node in g.doc['nodes'][:root_node]:
        if 'mesh' not in mesh_node:continue
        mesh=g.doc['meshes'][mesh_node['mesh']];mesh_node['skin']=0
        is_leaf=mesh['name'].startswith('traced_leaf_')
        leaf_id=int(mesh['name'].rsplit('_',1)[1])-1 if is_leaf else -1
        if is_leaf:
            length=plant['lengths_m'][leaf_id];im=images[leaf_id%len(images)];m=foreground(im);h,w=m.shape
            stem=m[max(0,h-4):].nonzero()[1].mean();tip=m[:4].nonzero()[1].mean()
            dx=(tip-stem)*length/max(1,h-1)
            axis_angle=math.atan2(dx,length)
            base_rotation=np.asarray(plant['rotation_matrices'][leaf_id]) if 'rotation_matrices' in plant else rotation(plant['pitch_degrees'][leaf_id],plant['depth_rotations_degrees'][leaf_id],-plant['angles_degrees'][leaf_id])
            alignment=rotation(0,0,math.degrees(axis_angle));basis=base_rotation@alignment
            at=np.asarray(plant['attachments_m'][leaf_id]) if 'attachments_m' in plant else np.array([(leaf_id/(len(plant['lengths_m'])-1)-.5)*plant['rhizome_length_m'],plant['base_y_m'],.003*math.sin(leaf_id*2.4)])
            bend=plant.get('rest_bend_ratio',.025)
            chain=[];centers=[]
            for segment,t in enumerate(config['joints_at_leaf_fraction']):
                local=np.array([dx*t,length*t,bend*length*t*t+math.sin(math.pi*t)*length*.025])
                center=basis@local+at;centers.append(center)
                node={'name':f'Leaf{leaf_id+1:02d}_'+('PinnedBase' if segment==0 else f'Flex{segment}'),'children':[]}
                if segment==0:
                    node.update(translation=center.tolist(),rotation=Rotation.from_matrix(basis).as_quat().tolist())
                    parent=root_node
                else:
                    node['translation']=(basis.T@(center-centers[-2])).tolist();parent=chain[-1]
                index=len(g.doc['nodes']);g.doc['nodes'].append(node);g.doc['nodes'][parent]['children'].append(index)
                chain.append(index);joints.append(index)
                inverse=np.eye(4);inverse[:3,:3]=basis.T;inverse[:3,3]=-basis.T@center;inverse_binds.append(inverse)
                if segment:
                    q=motion_quats(spec,leaf_id,segment,times,duration)
                    sampler=len(anim['samplers']);anim['samplers'].append({'input':time_accessor,'output':append(g,q,'VEC4'),'interpolation':'LINEAR'})
                    anim['channels'].append({'sampler':sampler,'target':{'node':index,'path':'rotation'}})
            joint_ids=np.arange(len(joints)-len(chain),len(joints))
            leaves.append({'mesh':mesh['name'],'chain_nodes':chain,'skin_joints':joint_ids.tolist(),'length_m':length,'pinned_uv_fraction':config['root_pin_fraction']})
        for primitive in mesh['primitives']:
            vertices=array(doc,binary,primitive['attributes']['POSITION']);count=len(vertices)
            ids=np.zeros((count,4),dtype='uint16');weights=np.zeros((count,4),dtype='float32');weights[:,0]=1
            if is_leaf:
                uv=array(doc,binary,primitive['attributes']['TEXCOORD_0']);t=np.clip(1-uv[:,1],0,1)
                knots=np.asarray(config['weight_fraction']);low=np.clip(np.searchsorted(knots,t,side='right')-1,0,len(knots)-2);high=low+1
                alpha=np.clip((t-knots[low])/(knots[high]-knots[low]),0,1)
                ids[:,0]=joint_ids[low];ids[:,1]=joint_ids[high];weights[:,0]=1-alpha;weights[:,1]=alpha
            primitive['attributes']['JOINTS_0']=append(g,ids,'VEC4',5123,34962)
            primitive['attributes']['WEIGHTS_0']=append(g,weights,'VEC4',5126,34962)
    matrices=np.array([m.flatten(order='F') for m in inverse_binds],dtype='float32')
    g.doc['skins']=[{'name':'AnchoredAquaticPlant','joints':joints,'skeleton':root_node,'inverseBindMatrices':append(g,matrices,'MAT4')}]
    g.doc['animations']=[anim]
    g.doc['asset']['generator']='Foundry native skeletal aquatic micro-current'
    g.doc['extras']={'species':spec['scientific_name'],'current_profile':str(config),'root_pin_fraction':config['root_pin_fraction'],'duration_s':duration}
    path=output/(spec['id']+'.glb');g.save(path)
    return {'id':spec['id'],'scientific_name':spec['scientific_name'],'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'joint_count':len(joints),'leaf_count':len(leaves),'leaves':leaves,'native_clip':config['clip'],'duration_s':duration,'unchanged':'Original positions, normals, UVs, topology, material images and nearest samplers retained byte-for-byte.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    config=json.loads(a.input.read_text(encoding='utf-8'));a.output.mkdir(parents=True,exist_ok=True)
    rows=[rig(a.root,config,s,a.output) for s in config['plants']]
    report={'schema_version':1,'command':'aquascape.rig-plant-current','ok':True,'status':'done','next_action':'human_review','outputs':rows,'failures':[],'config_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'visual_review':'pending','user_acceptance':'pending','scope':'Native plant bones and animation only. No new artwork, fish or static scenery changes.'}
    (a.output/'rig.handoff.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='outputs'}));print([(r['id'],r['joint_count']) for r in rows])


if __name__=='__main__':main()
