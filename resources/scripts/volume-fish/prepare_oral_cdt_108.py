#!/usr/bin/env python3
"""Freeze one108upper CPU-only CDT input. No asset writes."""
import argparse,json,hashlib,struct
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from probe_mouth_slit_stage1_108 import field,canvas
EPSILON=1e-9

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();proposal=json.loads(a.input.read_text());b=a.input.resolve().parent;root=Path(__file__).resolve().parents[3];path=b/'zander-oral-rest.json';d=json.loads(path.read_text());v=np.array(d['rest_xyz']);f=np.array(d['indices']).reshape(-1,3);patch=next(x for x in proposal['patches'] if x['sheet']=='upper');selected=np.array(patch['selected_triangle_ids']);keys=sorted(set(tuple(v[i]) for i in np.unique(f[selected])));pointid={k:i for i,k in enumerate(keys)};representative={}
 for i,p in enumerate(v):representative.setdefault(tuple(p),i)
 ids=[representative[k] for k in keys];faces=np.array([[pointid[tuple(v[i])] for i in tri] for tri in f[selected]]);count=Counter(tuple(sorted(e)) for face in faces for e in zip(face,np.roll(face,-1)));edges=[[int(x) for x in e] for e,n in count.items() if n==1];adj=defaultdict(set)
 for i,j in edges:adj[i].add(j);adj[j].add(i)
 loop=[min(adj)];previous=None
 while True:
  nxt=min(j for j in adj[loop[-1]] if j!=previous);previous=loop[-1]
  if nxt==loop[0]:break
  loop.append(nxt)
  if len(loop)>len(adj):raise ValueError('not simple loop')
 assert len(keys)==68 and len(edges)==37 and len(selected)==97 and len(loop)==37
 glb=root/'projects/fish-107-zander-eye/game/assets/models/fish/zander.glb';raw=glb.read_bytes();n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);start=20+n;binary=raw[start+8:];typ={5126:'<f4',5123:'<u2',5121:'u1'};num={'VEC2':2,'VEC3':3,'VEC4':4}
 def accessor(i):
  ac=g['accessors'][i];bv=g['bufferViews'][ac['bufferView']];dt=np.dtype(typ[ac['componentType']]);co=num[ac['type']];return np.ndarray((ac['count'],co),dtype=dt,buffer=binary,offset=bv.get('byteOffset',0)+ac.get('byteOffset',0),strides=(bv.get('byteStride',co*dt.itemsize),dt.itemsize)).copy()
 primitive=next(m for m in g['meshes'] if m.get('name')=='Closed_body')['primitives'][1];attrs={k:accessor(i) for k,i in primitive['attributes'].items()};groups=defaultdict(list)
 for i,p in enumerate(attrs['POSITION']):groups[tuple(p.astype(float))].append(i)
 mapped,_=field(canvas(np.array(keys)));original=np.array(keys);new=original.copy();active=canvas(original)[:,0]>1988;new[active,0]=mapped[active,0]/2024-.5;new[active,1]=(371-mapped[active,1])/2024
 points=[]
 for k,(pos,transformed,actualid) in enumerate(zip(keys,new,ids)):
  rawids=groups[tuple(np.asarray(pos,dtype=np.float32).astype(float))]
  if not rawids:raise ValueError('actualpoint has no exact rawGLB position')
  for attribute in ['JOINTS_0','WEIGHTS_0','TEXCOORD_0']:
   if any(not np.array_equal(attrs[attribute][rawids[0]],attrs[attribute][i]) for i in rawids[1:]):raise ValueError('raw geometricgroup attribute conflict '+attribute)
  points.append({'input_point_id':k,'oral_actual_vertex_id':actualid,'original_xyz':list(pos),'stage1_xyz':transformed.tolist(),'input_xz':[float(transformed[0]),float(transformed[2])],'raw_glb_vertex_ids':rawids,'raw_POSITION':attrs['POSITION'][rawids[0]].astype(float).tolist(),'actual_json_recovers_identical_raw_float32_position':bool(np.array_equal(np.asarray(pos,dtype=np.float32),attrs['POSITION'][rawids[0]])),'JOINTS_0':attrs['JOINTS_0'][rawids[0]].tolist(),'WEIGHTS_0':attrs['WEIGHTS_0'][rawids[0]].tolist(),'TEXCOORD_0':attrs['TEXCOORD_0'][rawids[0]].tolist(),'normal_policy':'originalsplit NORMAL maydiffer; newactiveface CPU flatnormal, kept rawattrs unchanged'})
 out={'status':'frozen_cpu_cdt_input','accepted':False,'epsilon':EPSILON,'output_type':1,'need_ids':True,'no_tuning':'single frozen epsilon, no retry with changed parameters','sheet':'upper_only','points':points,'edges':edges,'loop':loop,'old_oral_triangle_ids':selected.tolist(),'expected_faces_euler':2*len(points)-len(edges)-2,'expected_boundary_edges':37,'raw_glb_sha256':sha(glb),'raw_glb':str(glb),'input_hashes':{str(p):sha(p) for p in [a.input.resolve(),path,root/'resources/scripts/volume-fish/probe_mouth_slit_stage1_108.py',root/'resources/scripts/volume-fish/prepare_oral_cdt_108.py',b/'phase2c-oral-triangulation-proposal.md']},'forbidden':'No GLB/UV/runtime write, lower indices not replaced, Stage1 unchanged, Stage2 notimplemented'};a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'frozen':str(a.output),'points':len(points),'edges':len(edges),'expected_faces':out['expected_faces_euler'],'epsilon':EPSILON}))
if __name__=='__main__':main()
