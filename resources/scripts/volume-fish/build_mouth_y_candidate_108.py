#!/usr/bin/env python3
"""108 authorized isolated geometry only: original -> Stage1 -> frozen Y, three CDT patches.
No UV/material change, runtime install or acceptance. Normals use actual float32
final triangles within exact original POS/NORMAL/UV/JW islands; no seam welding.
"""
import argparse,copy,json,hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
from audit_mouth_refinement_108 import load_frozen_field
from build_stage1_cdt_candidate_108 import face_key,orientation,position_key,sha

def map_faces(raw,rawf,actual):
 v=np.asarray(actual['rest_xyz'],np.float32);faces=np.asarray(actual['indices']).reshape(-1,3);lut=defaultdict(list)
 for i,f in enumerate(rawf):lut[face_key(raw['POSITION'][f])].append(i)
 mapping=[];signs=[]
 for f in faces:
  hits=lut[face_key(v[f])];assert len(hits)==1;idx=hits[0];mapping.append(idx);signs.append(orientation(v[f],raw['POSITION'][rawf[idx]]))
 assert len(set(mapping))==len(rawf) and len(set(signs))==1
 return np.asarray(mapping),signs[0]
def island_key(attrs,i):
 # Exact original attribute identity. UV seams, hard normals and skin/oral
 # primitives remain distinct; original joints/weights also prevent welding.
 return tuple(float(x)for k in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']for x in attrs[k][i])
def patch_representatives(points,raw,mapped):
 ids=[]
 for p in points:
  members=p['raw_glb_vertex_ids'];ref=int(members[0]);assert all(position_key(raw['POSITION'][i])==position_key(p['raw_POSITION'])for i in members)
  for k in ['JOINTS_0','WEIGHTS_0','TEXCOORD_0']:assert all(np.array_equal(raw[k][ref],raw[k][i])for i in members)
  if 'mapped_xyz_float32'in p:assert np.array_equal(mapped[ref],np.asarray(p['mapped_xyz_float32'],np.float32))
  ids.append(ref)
 return np.asarray(ids)
def normals_for_surface(raw,positions,faces,new_faces_count,origin_ids,protected_keys):
 # origin_ids: every output attribute vertex points to original raw attrs.
 original_keys=[island_key(raw,int(i))for i in origin_ids];group_ids={};groups=[]
 for k in original_keys:
  if k not in group_ids:group_ids[k]=len(group_ids)
  groups.append(group_ids[k])
 groups=np.asarray(groups);# each new oral face is its own hard island
 if len(origin_ids)>len(raw['POSITION']):
  for face in faces[-new_faces_count:]:
   for vertex in face:groups[vertex]=len(group_ids);group_ids[('new_oral_hard_corner',int(vertex))]=len(group_ids)
 tri=positions[faces].astype(float);area=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);assert np.all(np.linalg.norm(area,axis=1)>0)
 oldpos=raw['POSITION'][origin_ids];geom_changed=np.any(positions!=oldpos,axis=1);changed_faces=geom_changed[faces].any(1);changed_faces[-new_faces_count:]=True
 active_groups=set(groups[faces[changed_faces]].ravel().tolist());protected_groups={groups[i]for i,j in enumerate(origin_ids)if position_key(raw['POSITION'][int(j)])in protected_keys};active_groups-=protected_groups
 direct_incident=np.zeros(len(positions),bool);direct_incident[faces[changed_faces].ravel()]=True
 sums=np.zeros((len(group_ids),3))
 for corner in range(3):np.add.at(sums,groups[faces[:,corner]],area)
 original=raw['NORMAL'][origin_ids];out=original.copy();allowed=np.array([int(g)in active_groups for g in groups])&direct_incident;length=np.linalg.norm(sums,axis=1);assert np.all(length[list(active_groups)]>0);out[allowed]=sums[groups[allowed]]/length[groups[allowed],None]
 # Unit face flat normals for appended oral corners, never averaged with other faces.
 assert np.isfinite(out).all();assert np.max(abs(np.linalg.norm(out.astype(float),axis=1)-1))<1e-5
 delta=np.any(out!=original,axis=1);angle=np.degrees(np.arccos(np.clip((out.astype(float)*original.astype(float)).sum(1)/(np.linalg.norm(out,axis=1)*np.linalg.norm(original,axis=1)),-1,1)));incident=np.zeros(len(positions),bool);incident[faces[changed_faces].ravel()]=True
 # A seam-island member shares contributions only with the exact same original
 # POS/NORMAL/UV/JW identity; record all updated attribute IDs explicitly.
 face_norm=area/np.linalg.norm(area,axis=1)[:,None];cos=(out[faces]*face_norm[:,None,:]).sum(2)
 report=dict(updated_attribute_vertex_ids=np.flatnonzero(delta).tolist(),geometry_or_topology_incident_vertex_ids=np.flatnonzero(incident).tolist(),eligible_normal_update_vertex_ids=np.flatnonzero(allowed).tolist(),changed_face_ids=np.flatnonzero(changed_faces).tolist(),updated_count=int(delta.sum()),maximum_normal_angle_degrees=float(angle[delta].max())if delta.any()else 0.,finite=True,unit_max_error=float(np.max(abs(np.linalg.norm(out.astype(float),axis=1)-1))),actual_face_corner_cosine_min=float(cos.min()),actual_face_corner_cosine_nonpositive=int((cos<=0).sum()),protected_groups_skipped=len(protected_groups),policy='actual finalfloat32 face area weighted inside exact original POS/NORMAL/UV/JW island; all incident contributions; eye islands exact; neworal97 hard corners separate',normal_angle_degrees_by_updated_id=[[int(i),float(angle[i])]for i in np.flatnonzero(delta)])
 return out,report,delta,incident

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True,help='Phase3f skin CDT API result');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=Path(__file__).resolve().parents[3];ret=json.loads(a.input.read_text());inp=Path(ret['input']);cfg=json.loads(inp.read_text());b=inp.parent;completion=a.input.with_name('cdt-completion.validation.json');complete=json.loads(completion.read_text());assert complete['cpu_topology_gate_passed']and complete['all209_newfaces_selected'];assert sha(inp)==ret['input_sha256']
 for p,h in complete['dependencies_sha256'].items():assert sha(p)==h,('staleCPU',p)
 script=Path(__file__).with_name('probe_mouth_monotone_108.py');ns=load_frozen_field(script,b/'source-mouth-alignment.validation.json');actual=ns['data'];old=ns['old'];stage=ns['st'];evaluate=ns['evaluate'];frozen=json.loads((b/'cpu-y-uv-monotone/monotone-frozen.validation.json').read_text());assert sha(script)==next(v for k,v in frozen['dependencies_sha256'].items()if k.endswith('/probe_mouth_monotone_108.py'))
 ocfg_path=b/'cpu-upper-cdt/cdt-input-frozen.validation.json';oret_path=b/'cpu-upper-cdt/cdt-api-result.validation.json';ocfg=json.loads(ocfg_path.read_text());oret=json.loads(oret_path.read_text());assert sha(ocfg_path)==oret['input_sha256'];source=Path(ocfg['raw_glb']);assert sha(source)==ocfg['raw_glb_sha256'];d,bin0=read_glb(source);original=copy.deepcopy(d);mi=next(n['mesh']for n in d['nodes']if n.get('name')=='Closed_body');pr=d['meshes'][mi]['primitives'];raw=[{k:accessor(d,bin0,ix)for k,ix in p['attributes'].items()}for p in pr];rawfaces=[accessor(d,bin0,p['indices']).reshape(-1,3)for p in pr];maps=[];signs=[]
 for attrs,faces,ac in zip(raw,rawfaces,actual):m,s=map_faces(attrs,faces,ac);maps.append(m);signs.append(s)
 mapped=[];actual_mapped=[];canonical_positions={}
 for surface in range(2):
  v=stage[surface];q=ns['canvas'](v);mq=evaluate(q)[0];out=v.copy();on=mq[:,1]!=q[:,1];out[on,1]=(371-mq[on,1])/2024;out=out.astype(np.float32);actual_mapped.append(out);lut={}
  for orig,p in zip(old[surface],out):
   k=position_key(orig)
   if k in lut:assert np.array_equal(lut[k],p)
   else:lut[k]=p
  for k,p in lut.items():
   if k in canonical_positions:assert np.array_equal(canonical_positions[k],p),('CPU f32 origin mismatch across surfaces',k)
   else:canonical_positions[k]=p
 for surface in range(2):mapped.append(np.asarray([canonical_positions[position_key(v)]for v in raw[surface]['POSITION']],np.float32))
 # Skin: replace only two upper sheets, retain all lower/crossZ/cap connections.
 skin_keep=np.ones(len(rawfaces[0]),bool);skin_new=[];mapping_report=[]
 for sh,api in zip(cfg['sheets'],ret['sheets']):
  assert sh['sheet']==api['sheet']and api['origins_one_to_one']and not api['unused_input_point_ids'];ids=patch_representatives(sh['points'],raw[0],mapped[0]);local=np.asarray(api['input_origin_faces']);new=ids[local]
  if signs[0]<0:new=new[:,::-1]
  selected=maps[0][sh['old_skin_triangle_ids']];skin_keep[selected]=False;skin_new.append(new);mapping_report.append(dict(sheet=sh['sheet'],old_actual_face_ids=sh['old_skin_triangle_ids'],old_raw_face_ids=selected.tolist(),new_faces=len(new),existing_raw_origins=ids.tolist(),returned_coordinates_used=False))
 skinfaces=np.concatenate([rawfaces[0][skin_keep],*skin_new]);# Oral: upper97 only, preserve lower+rear original raw order.
 oral_keep=np.ones(len(rawfaces[1]),bool);oral_keep[maps[1][ocfg['old_oral_triangle_ids']]]=False;ids=patch_representatives(ocfg['points'],raw[1],mapped[1]);neworal=ids[np.asarray(oret['input_origin_faces'])]
 if signs[1]<0:neworal=neworal[:,::-1]
 count=len(raw[1]['POSITION']);oral_origins=np.r_[np.arange(count),neworal.ravel()];oralpositions=mapped[1][oral_origins];oralfaces=np.r_[rawfaces[1][oral_keep],np.arange(count,count+291).reshape(-1,3)];attrs=[{k:v.copy()for k,v in r.items()}for r in raw];attrs[0]['POSITION']=mapped[0];attrs[1]={k:v[oral_origins].copy()for k,v in raw[1].items()};attrs[1]['POSITION']=oralpositions
 eye=ns['eye'];normal_reports=[];deltas=[];incidents=[];protectchecks=[]
 for surface,(positions,faces,origins,nnew)in enumerate([(mapped[0],skinfaces,np.arange(len(mapped[0])),209),(oralpositions,oralfaces,oral_origins,97)]):
  protected={position_key(old[surface][i])for i in eye['surfaces'][surface]['frozen_vertex_ids']};normal,report,delta,incident=normals_for_surface(raw[surface],positions,faces,nnew,origins,protected);attrs[surface]['NORMAL']=normal;normal_reports.append(report);deltas.append(delta);incidents.append(incident);pids=np.array([i for i in range(len(raw[surface]['POSITION']))if position_key(raw[surface]['POSITION'][i])in protected]);assert len(pids)==[659,231][surface];assert all(np.array_equal(attrs[surface][k][pids],raw[surface][k][pids])for k in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']);protectchecks.append(dict(surface=surface,protected_vertices=len(pids),POS_NORMAL_UV_JW_exact=True))
  assert np.array_equal(attrs[surface]['POSITION'][:,2],raw[surface]['POSITION'][origins,2]);assert all(np.array_equal(attrs[surface][k],raw[surface][k][origins])for k in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0'])
 # Rear interface/unknown references are matched by exact origin, with ID-level
 # disclosure of allowed incident normal changes rather than false exact claims.
 alignment=json.loads((b/'source-mouth-alignment.validation.json').read_text());rearsets={'rear640':set(),'unknown704':set()}
 for edge in alignment['actual_interface']:
  p=np.asarray(edge['rest_xyz']);q=ns['canvas'](p);sq=ns['stage1'](q)[0]
  for k,qq,ss in zip(p,q,sq):
   if qq[0]<=1988:rearsets['rear640'].add(position_key(k))
   if ss[0]<=2000.5:rearsets['unknown704'].add(position_key(k))
 rear_reports={}
 for name,keys in rearsets.items():
  entries=[]
  for surface in range(2):
   ids=np.array([i for i,p in enumerate(raw[surface]['POSITION'])if position_key(p)in keys]);assert len(ids)>0
   # Stage1 may move unknown forward band; F2 must not move its interface.
   reference=np.asarray([stage[surface][next(j for j,p in enumerate(old[surface])if position_key(p)==position_key(raw[surface]['POSITION'][i]))]for i in ids],np.float32);assert np.array_equal(attrs[surface]['POSITION'][ids],reference)
   changedids=ids[deltas[surface][ids]];nonincident=ids[~incidents[surface][ids]];assert np.array_equal(attrs[surface]['NORMAL'][nonincident],raw[surface]['NORMAL'][nonincident]);entries.append(dict(surface=surface,raw_vertex_ids=ids.tolist(),position_against_frozen_stage1_exact=True,UV_JW_exact=all(np.array_equal(attrs[surface][k][ids],raw[surface][k][ids])for k in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']),updated_normal_ids=changedids.tolist(),updated_normal_count=len(changedids),updated_normal_angles_degrees=[[int(i),dict(normal_reports[surface]['normal_angle_degrees_by_updated_id'])[int(i)]]for i in changedids],reason='incident real final face changed, same original POS/NORMAL/UV/JW island; no positional orUV permission inferred'))
  rear_reports[name]=entries
 # A final geometry contribution may involve unknownrear normal islands while
 # source POS andUV remain identity. No nonincident normal is changed.
 binary=bytearray(bin0)
 def add(arr,oldac,target):
  arr=np.ascontiguousarray(arr);binary.extend(b'\0'*(-len(binary)%4));off=len(binary);binary.extend(arr.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=off,byteLength=arr.nbytes,target=target));ix=len(d['accessors']);ac=dict(bufferView=vi,componentType=oldac['componentType'],count=len(arr),type=oldac['type'])
  if ac['type']!='SCALAR':ac.update(min=arr.min(0).tolist(),max=arr.max(0).tolist())
  d['accessors'].append(ac);return ix
 for surface in range(2):
  for k in (['POSITION','NORMAL']if surface==0 else list(attrs[1])):pr[surface]['attributes'][k]=add(attrs[surface][k],original['accessors'][original['meshes'][mi]['primitives'][surface]['attributes'][k]],34962)
  faces=[skinfaces,oralfaces][surface];oldac=original['accessors'][original['meshes'][mi]['primitives'][surface]['indices']];dt={5121:'u1',5123:'<u2',5125:'<u4'}[oldac['componentType']];assert faces.max()<=np.iinfo(np.dtype(dt)).max;pr[surface]['indices']=add(faces.astype(dt).ravel(),oldac,34963)
 assert all(original[k]==d[k]for k in ['nodes','skins','animations','images','materials']);assert all(mesh==d['meshes'][i]for i,mesh in enumerate(original['meshes'])if i!=mi);assert np.array_equal(skinfaces[:skin_keep.sum()],rawfaces[0][skin_keep])and np.array_equal(oralfaces[:oral_keep.sum()],rawfaces[1][oral_keep])
 a.output.mkdir(parents=True,exist_ok=True);target=a.output/'zander.glb';assert not target.exists(),'Refuse overwrite candidate';write(target,d,binary);_,nb=read_glb(target);assert bytes(nb[:len(bin0)])==bytes(bin0)
 report=dict(ok=True,status='isolated_fullY_geometry_candidate_not_accepted',accepted=False,source=str(source),source_sha256=sha(source),model_sha256=sha(target),inputs={str(p):sha(p)for p in [a.input,inp,completion,b/'cpu-y-uv-monotone/monotone-frozen.validation.json',script,ocfg_path,oret_path,Path(__file__)]},actual_to_raw=dict(skin_faces_unique=len(maps[0]),oral_faces_unique=len(maps[1]),winding_signs=signs,skin_patches=mapping_report,kept_raw_skin_faces_same_order_exact=True,kept_raw_oral_faces_same_order_exact=True),topology_replaced_surfaces=[dict(surface=0,new_tail_faces=209),dict(surface=1,new_tail_faces=97)],normals=normal_reports,eye=protectchecks,rear_unknown_normal_disclosure=rear_reports,original_BIN_prefix_exact=True,other_meshes_rig_animation_source_materials_exact=True,skin_UV_exact=True,oral_UV_origin_copy_only=True,Stage2_geometry_done_not_accepted=True,Stage2_UV_RGB_done=False,limits=['No Godot import/runtime install or freshLOD claims.','Area weighted normals actual finalfloat32 faces within original seamislands; unknownrear incidentnormal changes disclosed, not false exactnormal claim.','Native sourceUV intentionally unchanged; color/material/source correspondence pending independently reviewed UV step.'])
 (a.output/'build.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(model=str(target),sha256=report['model_sha256'],eye=protectchecks,normal_updated=[x['updated_count']for x in normal_reports])))
if __name__=='__main__':main()
