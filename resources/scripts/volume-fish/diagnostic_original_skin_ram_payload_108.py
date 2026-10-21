#!/usr/bin/env python3
"""Stdout-only RAM mesh for the stopped108 attempt2 diagnostic; no asset writes."""
import ast,json,hashlib,inspect
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from build_mouth_y_candidate_108 import map_faces,patch_representatives,normals_for_surface
from build_stage1_cdt_candidate_108 import position_key

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 root=Path(__file__).resolve().parents[3];b=root/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108';completion=b/'original-skin-cpu/completion.validation.json';failed=json.loads(completion.read_text());assert not failed['cpu_gate_passed'];params=b/'phase2-attempt2-parameters.validation.json';p=json.loads(params.read_text());script=Path(__file__).with_name('probe_mouth_attempt2_108.py');assert sha(params)==failed['input_sha256']and sha(script)==failed['frozen_field_sha256'];tree=ast.parse(script.read_text());ns={'__file__':str(script),'__name__':'attempt2_RAM_diagnostic','root':root,'b':b,'p':p,'report':{}};module=[x for x in tree.body if isinstance(x,(ast.Import,ast.ImportFrom))or isinstance(x,ast.FunctionDef)and x.name=='sha'];exec(compile(ast.Module(body=module,type_ignores=[]),str(script),'exec'),ns);mainast=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='main');req=next(x for x in mainast.body if isinstance(x,ast.FunctionDef)and x.name=='require');exec(compile(ast.Module(body=[req],type_ignores=[]),str(script),'exec'),ns);prefix=[]
 for node in next(x for x in mainast.body if isinstance(x,ast.Try)).body:
  prefix.append(node)
  if isinstance(node,ast.FunctionDef)and node.name=='evaluate':break
 exec(compile(ast.Module(body=prefix,type_ignores=[]),str(script),'exec'),ns);old=ns['old'];st=ns['st'];actual=ns['data'];cpu_positions={}
 for surface in range(2):
  q=ns['canvas'](st[surface]);m,_=ns['evaluate'](q);v=st[surface].copy();on=m[:,1]!=q[:,1];v[on,1]=(371-m[on,1])/2024
  for origin,dest in zip(old[surface],v.astype(np.float32)):
   key=position_key(origin)
   if key in cpu_positions:assert np.array_equal(cpu_positions[key],dest)
   else:cpu_positions[key]=dest
 ocfg=json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text());oret=json.loads((b/'cpu-upper-cdt/cdt-api-result.validation.json').read_text());source=Path(ocfg['raw_glb']);g,bin0=read_glb(source);mi=next(n['mesh']for n in g['nodes']if n.get('name')=='Closed_body');pr=g['meshes'][mi]['primitives'];raw=[{k:accessor(g,bin0,a)for k,a in x['attributes'].items()}for x in pr];rawfaces=[accessor(g,bin0,x['indices']).reshape(-1,3)for x in pr];mapped=[np.asarray([cpu_positions[position_key(v)]for v in r['POSITION']],np.float32)for r in raw];maps=[];signs=[]
 for r,f,a in zip(raw,rawfaces,actual):m,s=map_faces(r,f,a);maps.append(m);signs.append(s)
 skinfaces=rawfaces[0];ok=np.ones(len(rawfaces[1]),bool);ok[maps[1][ocfg['old_oral_triangle_ids']]]=False;ids=np.asarray([a['raw_glb_vertex_ids'][0]for a in ocfg['points']]);neworal=ids[np.asarray(oret['input_origin_faces'])]
 if signs[1]<0:neworal=neworal[:,::-1]
 count=len(raw[1]['POSITION']);oral_origins=np.r_[np.arange(count),neworal.ravel()];oralfaces=np.r_[rawfaces[1][ok],np.arange(count,count+291).reshape(-1,3)];positions=[mapped[0],mapped[1][oral_origins]];faces=[skinfaces,oralfaces];origins=[np.arange(len(mapped[0])),oral_origins];protected=[set(),set()]
 for group in p['base_eye_contract']['raw_corner_groups']:
  for side in group['raw_sides']:protected[side['surface']].add(position_key(side['POSITION'][0]))
 # Zero-newfaces needs an explicit guard: [-0:] would wrongly mark all faces.
 normal_source=inspect.getsource(normals_for_surface).replace('changed_faces[-new_faces_count:]=True','\n if new_faces_count:changed_faces[-new_faces_count:]=True');scope=dict(normals_for_surface.__globals__);exec(normal_source,scope);normal_method=scope['normals_for_surface']
 surfaces=[];statistics=[]
 for i in range(2):
  normal,stats,_,_=normal_method(raw[i],positions[i],faces[i],[0,97][i],origins[i],protected[i]);surfaces.append(dict(POSITION=positions[i].astype(float).tolist(),NORMAL=normal.astype(float).tolist(),indices=faces[i].ravel().tolist()));statistics.append({k:stats[k]for k in ['updated_count','unit_max_error','actual_face_corner_cosine_min','actual_face_corner_cosine_nonpositive','policy']})
 baseline=np.r_[raw[0]['POSITION'],raw[1]['POSITION']];bb=np.c_[baseline[:,0],-baseline[:,2],baseline[:,1]]
 print(json.dumps(dict(status='RAM_diagnostic_only_CPU_failed',accepted=False,candidate_written=False,global_crossing_not_run=True,failed_gate=failed['failures'],original_source=str(source),source_sha256=sha(source),field_sha256=sha(script),parameters_sha256=sha(params),cpu_failure_report_sha256=sha(completion),payload_script_sha256=sha(Path(__file__)),connectivity='originalskin22941+fixedoral97',normal_zero_newfaces_guard=True,normal_method_script_sha256=sha(Path(__file__).with_name('build_mouth_y_candidate_108.py')),baseline_body_bounds_Blender=[bb.min(0).astype(float).tolist(),bb.max(0).astype(float).tolist()],normal_statistics=statistics,surfaces=surfaces)))
if __name__=='__main__':main()
