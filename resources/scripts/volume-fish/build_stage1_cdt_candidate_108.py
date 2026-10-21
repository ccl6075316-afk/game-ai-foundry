#!/usr/bin/env python3
"""Emit an isolated 108 Stage1+upper97 candidate, never install/accept it.

Stage1 field is imported unchanged. CDT origins determine exact existing raw
positions and JWUV; glTF face winding is recovered from actual/raw geometry.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
from probe_mouth_slit_stage1_108 import field,canvas

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def position_key(v):return tuple(np.asarray(v,dtype=np.float32).astype(float))
def face_key(v):return tuple(sorted(position_key(p)for p in v))
def orientation(a,b):
 a=list(map(position_key,a));b=list(map(position_key,b))
 if any(a==b[k:]+b[:k]for k in range(3)):return 1
 b=b[::-1]
 if any(a==b[k:]+b[:k]for k in range(3)):return -1
 raise ValueError('nonmatching oriented triangle')
def deform(v):
 q=canvas(v.astype(float));mapped,J=field(q);active=q[:,0]>1988.;out=v.copy();out[active,0]=mapped[active,0]/2024.-.5;out[active,1]=(371.-mapped[active,1])/2024.
 return out,J,active

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True,help='Frozen CDT API result');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();api=json.loads(a.input.read_text());frozen=Path(api['input']);cfg=json.loads(frozen.read_text());completion=a.input.with_name('cdt-completion.validation.json');done=json.loads(completion.read_text());package=a.input.with_name('phase3c-package.validation.json');pack=json.loads(package.read_text())
 assert done['base_cpu_gate_passed'] and done['all97newfaces_selected'];assert done['xz_domain']['directed_boundary_exact'];assert pack['base_cpu_gate_passed'];assert pack.get('version')=='selection_v2_includes_all97newfaces',pack.get('version');assert sha(frozen)==api['input_sha256']
 for p,h in done['inputs'].items():assert sha(p)==h,('stale completed CPU input',p)
 source=Path(cfg['raw_glb']);assert sha(source)==cfg['raw_glb_sha256'];root=Path(__file__).resolve().parents[3];base=a.input.resolve().parents[1];actual=json.loads((base/'zander-oral-rest.json').read_text());actual_skin=json.loads((base.parent/'eye-rollout-107/zander-mesh-rest.json').read_text());prot=json.loads((base/'eye-protection-proposal.validation.json').read_text())
 d,b=read_glb(source);old=copy.deepcopy(d);mi=next(n['mesh']for n in d['nodes']if n.get('name')=='Closed_body');pr=d['meshes'][mi]['primitives'];raw=[{k:accessor(d,b,ac)for k,ac in p['attributes'].items()}for p in pr];raw_faces=[accessor(d,b,p['indices']).reshape(-1,3)for p in pr]
 # Map actual triangle IDs to raw glTF by exact float32 geometric keys.
 av=np.asarray(actual['rest_xyz'],dtype=np.float32);af=np.asarray(actual['indices']).reshape(-1,3);lookup=defaultdict(list)
 for i,f in enumerate(raw_faces[1]):lookup[face_key(raw[1]['POSITION'][f])].append(i)
 mapping=[];signs=[]
 for f in af:
  matches=lookup[face_key(av[f])];assert len(matches)==1,('nonunique actual/raw face',matches);idx=matches[0];mapping.append(idx);signs.append(orientation(av[f],raw[1]['POSITION'][raw_faces[1][idx]]))
 assert len(set(mapping))==len(raw_faces[1]) and len(set(signs))==1
 selected_raw=np.asarray([mapping[i]for i in cfg['old_oral_triangle_ids']],int);assert len(selected_raw)==97 and len(set(selected_raw))==97
 keep=np.ones(len(raw_faces[1]),bool);keep[selected_raw]=False;kept=raw_faces[1][keep].copy()
 changed=[];mapped=[];jac=[]
 for attrs in raw:
  v,J,active=deform(attrs['POSITION']);mapped.append(v);jac.append(J);changed.append(active)
 updated=[{k:v.copy()for k,v in attrs.items()}for attrs in raw];updated[0]['POSITION']=mapped[0];updated[1]['POSITION']=mapped[1]
 # Only active skin normals are transported. Kept oral attributes retain raw
 # normals and JWUV, as frozen for this reach-only candidate.
 Jrest=jac[0].copy();Jrest[:,0,1]*=-1;Jrest[:,1,0]*=-1;J3=np.tile(np.eye(3),(len(Jrest),1,1));J3[:,:2,:2]=Jrest;n=raw[0]['NORMAL'];active=changed[0];nn=n.copy();nn[active]=np.einsum('nij,nj->ni',np.linalg.inv(J3[active]).transpose(0,2,1),n[active]);nn[active]/=np.linalg.norm(nn[active],axis=1)[:,None];updated[0]['NORMAL']=nn
 newlocal=np.asarray(api['input_origin_faces'],int);assert newlocal.shape==(97,3);assert len(np.unique(newlocal))==68;representatives=[]
 for p in cfg['points']:
  ids=np.array(p['raw_glb_vertex_ids'],int);assert all(position_key(raw[1]['POSITION'][i])==position_key(p['raw_POSITION'])for i in ids)
  for k in ['JOINTS_0','WEIGHTS_0','TEXCOORD_0']:
   assert all(np.array_equal(raw[1][k][ids[0]],raw[1][k][i])for i in ids);assert np.array_equal(raw[1][k][ids[0]],np.asarray(p[k],dtype=raw[1][k].dtype))
  # Stage1 is evaluated on raw float32 positions. Rounded API coordinates are
  # diagnostic only, never used in the asset.
  assert np.array_equal(mapped[1][ids[0]],np.asarray(p['stage1_xyz'],dtype=np.float32));representatives.append(int(ids[0]))
 newraw=np.asarray(representatives)[newlocal]
 if signs[0]<0:newraw=newraw[:,::-1]
 append={k:[]for k in raw[1]};flat_normals=[]
 for face in newraw:
  positions=mapped[1][face].astype(float);normal=np.cross(positions[1]-positions[0],positions[2]-positions[0]);assert np.linalg.norm(normal)>1e-14;normal/=np.linalg.norm(normal);flat_normals.append(normal.tolist())
  for vertex in face:
   for k in append:append[k].append(normal if k=='NORMAL'else mapped[1][vertex]if k=='POSITION'else raw[1][k][vertex])
 offset=len(raw[1]['POSITION']);oral_indices=np.concatenate([kept,np.arange(offset,offset+291).reshape(-1,3)])
 for k in append:updated[1][k]=np.concatenate([updated[1][k],np.asarray(append[k],dtype=raw[1][k].dtype)])
 # Preserve original BIN bytes and every unaffected accessor/primitive/node.
 binary=bytearray(b)
 def add_array(arr,kind,component,target):
  arr=np.ascontiguousarray(arr);binary.extend(b'\0'*(-len(binary)%4));off=len(binary);binary.extend(arr.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=off,byteLength=arr.nbytes,target=target));ac=len(d['accessors']);doc=dict(bufferView=vi,componentType=component,count=len(arr),type=kind)
  if kind!='SCALAR':doc.update(min=arr.min(0).tolist(),max=arr.max(0).tolist())
  d['accessors'].append(doc);return ac
 for k in ['POSITION','NORMAL']:
  oldac=old['accessors'][pr[0]['attributes'][k]];pr[0]['attributes'][k]=add_array(updated[0][k],oldac['type'],oldac['componentType'],34962)
 for k,arr in updated[1].items():
  oldac=old['accessors'][pr[1]['attributes'][k]];pr[1]['attributes'][k]=add_array(arr,oldac['type'],oldac['componentType'],34962)
 oldix=old['accessors'][pr[1]['indices']];dtype={5121:'u1',5123:'<u2',5125:'<u4'}[oldix['componentType']];assert oral_indices.max()<np.iinfo(np.dtype(dtype)).max;pr[1]['indices']=add_array(oral_indices.astype(dtype).ravel(),'SCALAR',oldix['componentType'],34963)
 checks=[]
 for i,actual_data in enumerate([actual_skin,actual]):
  actual_v=np.asarray(actual_data['rest_xyz'],dtype=np.float32);protected={position_key(actual_v[j])for j in prot['surfaces'][i]['frozen_vertex_ids']};ids=np.array([j for j,v in enumerate(raw[i]['POSITION'])if position_key(v)in protected]);assert len(ids)>0
  checks.append(dict(surface=i,protected_raw_vertices=len(ids),protected_position_normal_uv_exact=all(np.array_equal(raw[i][k][ids],updated[i][k][ids])for k in ['POSITION','NORMAL','TEXCOORD_0']),inactive_positions_exact=bool(np.array_equal(raw[i]['POSITION'][~changed[i]],updated[i]['POSITION'][:len(raw[i]['POSITION'])][~changed[i]])),z_original_vertices_exact=bool(np.array_equal(raw[i]['POSITION'][:,2],updated[i]['POSITION'][:len(raw[i]['POSITION']),2]))))
 assert all(c['protected_position_normal_uv_exact']and c['inactive_positions_exact']and c['z_original_vertices_exact']for c in checks)
 assert np.array_equal(oral_indices[:len(kept)],raw_faces[1][keep]);assert np.array_equal(updated[0]['TEXCOORD_0'],raw[0]['TEXCOORD_0']);assert all(np.array_equal(updated[1][k][:offset],raw[1][k])for k in ['NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']);assert old['nodes']==d['nodes']and old['skins']==d['skins']and old['animations']==d['animations']and old['images']==d['images']and old['materials']==d['materials'];assert all(m==d['meshes'][i]for i,m in enumerate(old['meshes'])if i!=mi)
 a.output.mkdir(parents=True,exist_ok=True);target=a.output/'zander.glb';assert not target.exists(),'Refuse overwrite frozen candidate';write(target,d,binary);nd,nb=read_glb(target);assert bytes(nb[:len(b)])==bytes(b)
 report=dict(ok=True,status='isolated_stage1_geometry_candidate_not_accepted',accepted=False,source=str(source),source_sha256=sha(source),model_sha256=sha(target),inputs={str(p):sha(p)for p in [a.input,frozen,completion,package,Path(__file__),Path(__file__).with_name('probe_mouth_slit_stage1_108.py')]},actual_raw_mapping=dict(actual_faces=len(af),unique_raw_face_matches=len(set(mapping)),same_triangle_order=mapping==list(range(len(mapping))),actual_relative_raw_winding=signs[0],all_same_winding=True,selected_actual_ids=cfg['old_oral_triangle_ids'],selected_raw_ids=selected_raw.tolist(),kept_raw_faces_count=len(kept),kept_raw_faces_same_order_exact=True),new_upper=dict(geometric_points=68,new_geometric_points=0,triangles=97,appended_attribute_vertices=291,flat_normals_from_actual_float32_3d=True,source_origin_raw_vertex_ids=representatives,new_input_origin_faces=newlocal.tolist(),winding_reversed_for_raw=signs[0]<0),preservation=checks,original_bin_prefix_exact=True,other_primitives_nodes_rig_animations_images_materials_exact=True,uv_original_and_origin_copy_only=True,lower_connections_unchanged=True,stage2_chin_front_lip_y_uv_done=False,limits=['Stage1 reach plus upper CDT only; chin and front-lipY/UV remain unfinished.','No production,106 or107 changes. No regenerated/accepted importedLOD tables.','Raw active kept oral normals retained; only new upper faces use new flat normals.','Grey visual review and actual emitted float32 geometry checks still required; CPU field approval does not accept an asset.'])
 (a.output/'build.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(model=str(target),sha256=report['model_sha256'],protected=checks)))
if __name__=='__main__':main()
