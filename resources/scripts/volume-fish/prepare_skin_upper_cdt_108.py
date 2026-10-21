#!/usr/bin/env python3
"""Freeze upper-only108 destination XY CDT input. Read-only; never invokes CDT."""
import argparse,json,hashlib,struct
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from scipy.spatial import cKDTree
from audit_mouth_refinement_108 import load_frozen_field
from audit_mouth_skin_chart_108 import intersect,cross

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parent;charts=json.loads(a.input.read_text());script=Path(__file__).with_name('probe_mouth_monotone_108.py');fr=json.loads((b/'cpu-y-uv-monotone/monotone-frozen.validation.json').read_text());assert sha(script)==next(v for k,v in fr['dependencies_sha256'].items() if k.endswith('/probe_mouth_monotone_108.py'));ns=load_frozen_field(script,b/'source-mouth-alignment.validation.json');stage=ns['st'][0];old=ns['old'][0];data=ns['data'][0];faces=np.array(data['indices']).reshape(-1,3);q=ns['canvas'](stage);mq=ns['evaluate'](q)[0];mapped=stage.copy();on=mq[:,1]!=q[:,1];mapped[on,1]=(371-mq[on,1])/2024
 cfg=json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text());glb=Path(cfg['raw_glb']);raw=glb.read_bytes();ln=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+ln]);binary=raw[28+ln:];types={5126:'<f4',5123:'<u2',5121:'u1'};nums={'VEC2':2,'VEC3':3,'VEC4':4}
 def acc(ix):
  ac=gltf['accessors'][ix];bv=gltf['bufferViews'][ac['bufferView']];dt=np.dtype(types[ac['componentType']]);co=nums[ac['type']];return np.ndarray((ac['count'],co),dt,buffer=binary,offset=bv.get('byteOffset',0)+ac.get('byteOffset',0),strides=(bv.get('byteStride',co*dt.itemsize),dt.itemsize)).copy()
 primitive=next(m for m in gltf['meshes'] if m.get('name')=='Closed_body')['primitives'][0];attrs={k:acc(v) for k,v in primitive['attributes'].items()};groups=defaultdict(list)
 for i,p in enumerate(attrs['POSITION']):groups[tuple(p.astype(float))].append(i)
 inputs=[]
 for chart in charts['sheets'][:2]:
  faceids=np.array(chart['triangle_ids']);actualids=np.unique(faces[faceids]);keys=sorted(set(tuple(stage[i]) for i in actualids));lut={p:i for i,p in enumerate(keys)};ids=[next(int(i) for i in actualids if tuple(stage[i])==key) for key in keys];local=np.array([[lut[tuple(stage[i])] for i in face] for face in faces[faceids]]);points=[]
  for j,i in enumerate(ids):
   rawids=groups[tuple(old[i].astype(np.float32).astype(float))];ref=rawids[0]
   for attr in ['JOINTS_0','WEIGHTS_0','TEXCOORD_0']:
    assert all(np.array_equal(attrs[attr][ref],attrs[attr][k]) for k in rawids),'nonidenticalattribute '+attr
   normals=[]
   for k in rawids:
    if attrs['NORMAL'][k].astype(float).tolist() not in normals:normals.append(attrs['NORMAL'][k].astype(float).tolist())
   points.append({'input_point_id':j,'actual_vertex_id':i,'original_actual_xyz':old[i].tolist(),'stage1_xyz':stage[i].tolist(),'mapped_xyz_float64':mapped[i].tolist(),'mapped_xyz_float32':mapped[i].astype(np.float32).astype(float).tolist(),'input_xy':mapped[i,:2].astype(np.float32).astype(float).tolist(),'raw_glb_vertex_ids':rawids,'raw_POSITION':attrs['POSITION'][ref].astype(float).tolist(),'JOINTS_0':attrs['JOINTS_0'][ref].astype(int).tolist(),'WEIGHTS_0':attrs['WEIGHTS_0'][ref].astype(float).tolist(),'TEXCOORD_0':attrs['TEXCOORD_0'][ref].astype(float).tolist(),'raw_normal_groups':normals,'actual_original_normal':data['rest_normals'][i]})
  ct=Counter(tuple(sorted((int(i),int(j)))) for tri in local for i,j in zip(tri,np.roll(tri,-1)));boundary=sorted(e for e,c in ct.items() if c==1);directed=[(int(i),int(j)) for tri in local for i,j in zip(tri,np.roll(tri,-1)) if ct[tuple(sorted((int(i),int(j))))]==1];xy=np.array([p['input_xy'] for p in points]);xyz=np.array([p['mapped_xyz_float32'] for p in points]);distance=cKDTree(xy).query(xy,k=2)[0][:,1];areas=(xy[local[:,1],0]-xy[local[:,0],0])*(xy[local[:,2],1]-xy[local[:,0],1])-(xy[local[:,1],1]-xy[local[:,0],1])*(xy[local[:,2],0]-xy[local[:,0],0]);normal=np.cross(xyz[local[:,1]]-xyz[local[:,0]],xyz[local[:,2]]-xyz[local[:,0]]);samexy=defaultdict(list)
  for j,point in enumerate(xy):samexy[tuple(point)].append(j)
  mult=[{'point_ids':v,'Z_values':xyz[v,2].tolist()} for v in samexy.values() if len(v)>1];floatdiag={'minimum_distinct_XY_distance_rest':float(distance.min()),'minimum_distinct_XY_distance_native_pixels':float(distance.min()*2024),'same_XY_groups':mult,'zero_area_old_triangles_after_float32':int((areas==0).sum()),'zero_3d_area_old_triangles_after_float32':int((np.linalg.norm(normal,axis=1)==0).sum()),'max_float32_writeback_distance_rest':float(np.linalg.norm(xyz-np.array([p['mapped_xyz_float64'] for p in points]),axis=1).max()),'old_projected_area_sign_counts':{'positive':int((areas>0).sum()),'negative':int((areas<0).sum())},'input_epsilon_rest':1e-9,'input_epsilon_less_than_minimum_spacing':bool(1e-9<distance.min())}
  boundary_cross=[];through=[]
  for e,(u,v) in enumerate(boundary):
   for w,z in boundary[e+1:]:
    if len({u,v,w,z})==4 and intersect(xy[u],xy[v],xy[w],xy[z]):boundary_cross.append([[u,v],[w,z]])
   dd=xy[v]-xy[u];len2=dd@dd
   for k in range(len(xy)):
    if k in [u,v]:continue
    t=((xy[k]-xy[u])@dd)/len2
    if 0<t<1 and abs(cross(dd,xy[k]-xy[u]))/np.sqrt(len2)<1e-12:through.append([u,v,k])
  floatdiag['boundary_strict_crossings']=boundary_cross;floatdiag['constraint_edges_through_other_points']=through
  assert not boundary_cross and not through
  assert not mult and not floatdiag['zero_area_old_triangles_after_float32'] and not floatdiag['zero_3d_area_old_triangles_after_float32'];assert floatdiag['input_epsilon_less_than_minimum_spacing']
  inputs.append({'sheet':chart['sheet'],'points':points,'boundary_edges':[list(e) for e in boundary],'directed_boundary_edges':[list(e) for e in directed],'old_skin_triangle_ids':faceids.tolist(),'old_local_faces':local.tolist(),'expected_faces_euler':2*len(points)-len(boundary)-2,'float32_preflight':floatdiag,'all_point_raw_JWUV_groups_compatible':True,'all_point_normal_group_counts':[len(p['raw_normal_groups']) for p in points]})
 out={'status':'upper_skin_CDT_input_proposal_not_executed','accepted':False,'CDT_executed':False,'assets_written':False,'epsilon':1e-9,'coordinate_units':'actual mapped float32 REST XY, not native2000px absolute coordinates','output_type':1,'need_ids':True,'sheets':inputs,'preserved':'all lower229/266 original connections and both UV groups;15crossZ;46lowerYZcap;mouth upper97 previousCDT;everyothermesh/source/rig/motion unchanged','return_contract':'Returned coords diagnostic only, discarded. orig_verts must singleton1:1; exact input origin->mapped float32 XYZ/JWUV. No new/merged/unused/split boundary points. Same exact directed boundary.','normal_contract':'Input raw original normal groups frozen; no cross-group welding. For new upper faces retain provenance and future independently approved face/corner normals. Negative transported-normal cosine is diagnostic, not a topology flip veto. Actual nonzero3D, uniform directed projected area, boundary closure, all-pairs crossing and coplanar area zero are mandatory.','parameters_unchanged':'Stage1+F2 source targets/Hermite/window/UV chart fixed; no further deformation or subdivision','dependencies_sha256':{str(p):sha(p) for p in [a.input,script,Path(__file__),glb,b/'cpu-y-uv-monotone/monotone-frozen.validation.json',b/'cpu-upper-cdt/cdt-api-result.validation.json']}};out['orientation_contract']='One uniform chart winding fixed from original directed boundary: left-upper REST XY negative, right-upper positive. No per-face correction based on transported-normal cosine.'
 for sh in inputs:sh['required_uniform_directed_XY_area_sign']=-1 if sh['sheet']=='left-upper' else 1
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'sheets':[{'sheet':sh['sheet'],'points':len(sh['points']),'boundary':len(sh['boundary_edges']),'expected_faces':sh['expected_faces_euler'],'float32':sh['float32_preflight']} for sh in inputs],'input_sha256':sha(a.output)},indent=2))
if __name__=='__main__':main()
