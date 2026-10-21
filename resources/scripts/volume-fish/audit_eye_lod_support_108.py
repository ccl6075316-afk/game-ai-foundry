#!/usr/bin/env python3
"""108 read-only full-eye base/LOD support contract data. Never changes protection or assets."""
import argparse,json,hashlib,struct
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image
from audit_mouth_refinement_108 import load_frozen_field
from audit_mouth_y_failure_108 import polyclip,area

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parent;ns=load_frozen_field(Path(__file__).with_name('probe_mouth_monotone_108.py'),a.input);data=ns['data'][0];v=np.array(data['rest_xyz']);canvas=ns['canvas'];q=canvas(v);base=np.array(data['indices']).reshape(-1,3);lods=[('base',base)]+[('LOD'+str(k),np.array(l['indices']).reshape(-1,3)) for k,l in enumerate(data['lods'])];cfg=Path('projects/fish-107-zander-eye/game/assets/models/fish/motion/eye-107/eye-ownership-107.json');profile=json.loads(cfg.read_text())['profiles']['zander'];proj=profile['projection'];maskpath=cfg.parent/'eye-layer-mask.png';sourcepath=cfg.parent/'source-runtime.png';mask=np.array(Image.open(maskpath).convert('RGBA'))[:,:,0]>=128;mask&=np.array(Image.open(sourcepath).convert('RGBA'))[:,:,3]>0;yy,xx=np.nonzero(mask);runs=[]
 for y in sorted(set(yy)):
  xs=np.flatnonzero(mask[y]);gs=np.split(xs,np.flatnonzero(np.diff(xs)>1)+1)
  for g in gs:runs.append((int(g[0]),int(g[-1])+1,int(y),int(y)+1))
 anchor=np.array(proj['anchor_rest_xy']);pixel=np.array(proj['pixel_native_xy']);pupil=np.array(proj['source_pupil_px']);anchor[1]-=proj['downshift_native_pixels']*pixel[1];gap=proj['central_gap_abs_z'];result=[];union=set();frozen_triangles=[];normalperLOD=[]
 for name,faces in lods:
  sides=[];levelvertices=set();leveltri=[]
  for side,sign in [('left',1),('right',-1)]:
   touched=[]
   for tid,face in enumerate(faces):
    tri=v[face].copy();tri[:,2]*=sign
    if tri[:,2].max()<=gap:continue
    p=polyclip(tri,2,gap,True)
    if len(p)<3:continue
    xy=pupil+np.c_[(p[:,0]-anchor[0])/pixel[0],-(p[:,1]-anchor[1])/pixel[1]];xmin,ymin=xy.min(0);xmax,ymax=xy.max(0)
    if xmax<xx.min() or xmin>xx.max()+1 or ymax<yy.min() or ymin>yy.max()+1:continue
    for x0,x1,y0,y1 in runs:
     if xmax<x0 or xmin>x1 or ymax<y0 or ymin>y1:continue
     poly=xy.copy()
     for ax,z,greater in [(0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)]:
      if not len(poly):break
      poly=polyclip(poly,ax,z,greater)
     if area(poly)>0:touched.append(tid);break
   ids=set(map(int,np.unique(faces[touched])));levelvertices|=ids;leveltri.extend(touched);sides.append({'side':side,'feature_triangle_ids':touched,'feature_triangle_count':len(touched),'feature_vertex_ids':sorted(ids),'feature_vertex_count':len(ids),'support_native_bbox':[q[list(ids)].min(0).tolist(),q[list(ids)].max(0).tolist()] if ids else None})
  failed=name=='LOD5';result.append({'level':name,'triangles_total':len(faces),'historical_gate':'FAILED_LOD5_not_in_pass_union' if failed else 'previously_approved_level_support_only_not_new_pass','sides':sides,'union_vertex_ids':sorted(levelvertices),'union_vertex_count':len(levelvertices),'support_native_bbox':[q[list(levelvertices)].min(0).tolist(),q[list(levelvertices)].max(0).tolist()] if levelvertices else None})
  if not failed:union|=levelvertices;frozen_triangles.extend(faces[sorted(set(leveltri))].tolist())
 # Include exactly colocated actual vertices; original normal/UV attribute values remain distinct.
 positionkeys={tuple(v[i]) for i in union};duplicates={i for i,p in enumerate(v) if tuple(p) in positionkeys};normalfaces=np.flatnonzero(np.isin(base,list(duplicates)).any(1));normalverts=set(map(int,np.unique(base[normalfaces])));oldprotect=set(ns['eye']['surfaces'][0]['frozen_vertex_ids']);oral=np.array(ns['old'][1]);oral_shared=[i for i,p in enumerate(oral) if tuple(p) in positionkeys]
 # Map raw POSITION equivalence groups without choosing a representative NORMAL/UV group.
 oralcfg=json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text());glb=Path(oralcfg['raw_glb']);raw=glb.read_bytes();ln=struct.unpack_from('<I',raw,12)[0];gl=json.loads(raw[20:20+ln]);binary=raw[28+ln:];types={5126:'<f4',5123:'<u2',5121:'u1'};nums={'VEC2':2,'VEC3':3,'VEC4':4}
 def acc(ix):
  ac=gl['accessors'][ix];bv=gl['bufferViews'][ac['bufferView']];dt=np.dtype(types[ac['componentType']]);co=nums[ac['type']];return np.ndarray((ac['count'],co),dt,buffer=binary,offset=bv.get('byteOffset',0)+ac.get('byteOffset',0),strides=(bv.get('byteStride',co*dt.itemsize),dt.itemsize)).copy()
 prims=next(m for m in gl['meshes'] if m.get('name')=='Closed_body')['primitives'];attrs=[{k:acc(ix) for k,ix in prim['attributes'].items()} for prim in prims];groups=[]
 for at in attrs:
  group=defaultdict(list)
  for j,p in enumerate(at['POSITION']):group[tuple(p.astype(float))].append(j)
  groups.append(group)
 mappedgroups=[]
 for key in sorted(positionkeys):
  rawkey=tuple(np.array(key,dtype=np.float32).astype(float));record={'original_actual_POSITION':list(key),'skin_actual_ids':[i for i in sorted(duplicates) if tuple(v[i])==key],'raw_sides':[]}
  for surface in range(2):
   rid=groups[surface].get(rawkey,[])
   if rid:record['raw_sides'].append({'surface':surface,'raw_vertex_ids':rid,'POSITION':attrs[surface]['POSITION'][rid].astype(float).tolist(),'NORMAL':attrs[surface]['NORMAL'][rid].astype(float).tolist(),'TEXCOORD_0':attrs[surface]['TEXCOORD_0'][rid].astype(float).tolist(),'JOINTS_0':attrs[surface]['JOINTS_0'][rid].astype(int).tolist(),'WEIGHTS_0':attrs[surface]['WEIGHTS_0'][rid].astype(float).tolist()})
  assert record['raw_sides'];mappedgroups.append(record)
 # Local support bottom is a triangle-plane profile versusX, not global bbox maxY.
 supportfaces=np.array(frozen_triangles,int);supporttris=q[supportfaces];normtris=q[base[normalfaces]];S=452.62-1.02*742/2024*(q[:,0]-1894.464);vv=q[:,1]-S;lower=base[vv[base].min(1)>0];lowertri=q[lower]
 def bounds(tris,x):
  ys=[]
  for tri in tris:
   if tri[:,0].min()>x or tri[:,0].max()<x:continue
   for aa,bb in zip(tri,np.roll(tri,-1,axis=0)):
    if aa[0]==bb[0]:
     if aa[0]==x:ys.extend([aa[1],bb[1]])
    else:
     t=(x-aa[0])/(bb[0]-aa[0])
     if 0<=t<=1:ys.append(aa[1]+t*(bb[1]-aa[1]))
  return (float(min(ys)),float(max(ys))) if ys else None
 def slab_bounds(tris,x0,x1):
  ys=[]
  for tri in tris:
   if tri[:,0].min()>x1 or tri[:,0].max()<x0:continue
   pp=polyclip(tri,0,x0,True)
   if len(pp):pp=polyclip(pp,0,x1,False)
   if len(pp):ys.extend(pp[:,1].tolist())
  return [float(min(ys)),float(max(ys))] if ys else None
 xmin=float(q[list(duplicates),0].min());xmax=float(q[list(duplicates),0].max());rows=[]
 for x0 in np.arange(np.floor(xmin/4)*4,np.ceil(xmax/4)*4,4):
  samples=[]
  for x in [float(x0),float(x0+2),float(x0+4)]:
   sd=bounds(supporttris,x);nd=bounds(normtris,x);lb=bounds(lowertri,x)
   samples.append({'X':x,'direct_feature_triangle_support_bottomY':sd[1] if sd else None,'normal_incident_triangle_bottomY':nd[1] if nd else None,'old_actual_lowerlip_L':lb[0] if lb else None,'old_actual_chin_B':lb[1] if lb else None,'direct_support_to_L_gap':lb[0]-sd[1] if lb and sd else None,'direct_support_to_B_gap':lb[1]-sd[1] if lb and sd else None,'normal_incident_to_L_gap':lb[0]-nd[1] if lb and nd else None,'normal_incident_to_B_gap':lb[1]-nd[1] if lb and nd else None})
  sdslab=slab_bounds(supporttris,float(x0),float(x0+4));ndslab=slab_bounds(normtris,float(x0),float(x0+4));lbslab=slab_bounds(lowertri,float(x0),float(x0+4))
  rows.append({'direct_triangle_support_bottomY_max_over_full_slab':sdslab[1] if sdslab else None,'normal_incident_bottomY_max_over_full_slab':ndslab[1] if ndslab else None,'old_lowerlip_minY_over_full_slab':lbslab[0] if lbslab else None,'conservative_direct_to_lowerlip_interval_clearance':lbslab[0]-sdslab[1] if lbslab and sdslab else None,'X_interval':[float(x0),float(x0+4)],'endpoint_midpoint_samples':samples,'local_min_direct_to_L_gap':min((s['direct_support_to_L_gap'] for s in samples if s['direct_support_to_L_gap'] is not None),default=None)})
 out={'status':'read_only_base_LOD0_4_support_contract_data','accepted':False,'protection_changed':False,'field_or_candidate_generated':False,'complete_source_mask_pixels':int(mask.sum()),'projection':proj,'levels':result,'pass_level_union':{'levels':['base','LOD0','LOD1','LOD2','LOD3','LOD4'],'direct_feature_vertex_ids':sorted(union),'exact_same_POSITION_attribute_vertex_ids':sorted(duplicates),'direct_vertex_count':len(union),'same_position_vertex_count':len(duplicates),'native_bbox':[q[list(duplicates)].min(0).tolist(),q[list(duplicates)].max(0).tolist()],'outside_old659_ids':sorted(duplicates-oldprotect),'old659_extra_ids':sorted(oldprotect-duplicates),'normal_base_incident_triangle_ids':normalfaces.tolist(),'normal_base_incident_vertex_ids':sorted(normalverts),'normal_base_incident_vertex_count':len(normalverts),'normal_base_incident_native_bbox':[q[list(normalverts)].min(0).tolist(),q[list(normalverts)].max(0).tolist()],'shared_oral_actual_ids':oral_shared},'raw_position_normal_UV_groups':mappedgroups,'local_X_support_clearance':{'bin_native_pixels':4,'method':'supporttriangle clippingtofull4pxXslab yields exactpiecewise-linear maxY floatbound; lowerbranch intervalminY givesconservative clearance; sameX L/B also sampledendpoints+midpoint forreference, notfullcontinuousclearanceproof','rows':rows},'LOD5':'Original439tri failure reported separately, excluded frompassunion; noLODindex/geometrychanged.','limits':['Base+existingLOD0–4 union is input evidence, no permission to shrink protection.','NewimportcanregenerateLOD: allnewactualLOD and fragment+normal/eye remain freshmandatory.','Directtrianglevertex support and base-normalincident geometry are distinct contracts; original splitNORMAL/UV groups all retained, no arbitrary representative.','Finitefloat64 polygonclipping againstfullmaskpixelcells; no rastercenter-only approximation or pupil-onlymask.'],'dependencies_sha256':{str(p):sha(p) for p in [a.input,Path(__file__),Path(__file__).with_name('probe_mouth_monotone_108.py'),b.parent/'eye-rollout-107/zander-mesh-rest.json',b/'zander-oral-rest.json',cfg,maskpath,sourcepath,glb]}};a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'levels':[{'level':r['level'],'vertices':r['union_vertex_count'],'bbox':r['support_native_bbox']} for r in result],'union':{k:v for k,v in out['pass_level_union'].items() if k in ['direct_vertex_count','same_position_vertex_count','native_bbox','normal_base_incident_vertex_count','normal_base_incident_native_bbox','shared_oral_actual_ids','outside_old659_ids']},'old659_extra_count':len(oldprotect-duplicates)},indent=2))
if __name__=='__main__':main()
