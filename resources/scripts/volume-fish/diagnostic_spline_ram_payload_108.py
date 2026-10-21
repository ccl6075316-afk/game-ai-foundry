#!/usr/bin/env python3
"""Approved attempt3 RAM ONLY. Loads frozen coefficients; NEVER calls production solve."""
import ast,json,hashlib,inspect
from pathlib import Path
from fractions import Fraction as F
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from build_mouth_y_candidate_108 import map_faces,normals_for_surface
from build_stage1_cdt_candidate_108 import position_key
from continuous_spline_exact_108 import Spline

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build_payload():
 root=Path(__file__).resolve().parents[3];b=root/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108';completion=b/'continuous-spline-cpu/completion.validation.json';assert sha(completion)=='bf90691c0ea89775b806f869b55cd60ba2aaabba0f80f3d195cab48281d11cc6';cpu=json.loads(completion.read_text());assert cpu['cpu_gate_passed'];freeze=b/'continuous-spline-cpu/execution-freeze.validation.json';assert sha(freeze)==cpu['execution_freeze_sha256'];fr=json.loads(freeze.read_text());phase2=b/'phase2-continuous-spline-package.validation.json';assert sha(phase2)==cpu['phase2_authorization_package_sha256']
 for path,h in json.loads(phase2.read_text())['inputs_sha256'].items():assert sha(root/path)==h
 for path,h in fr['implementation_sha256'].items():assert sha(root/path)==h
 params=b/'phase2-attempt2-parameters.validation.json';p=json.loads(params.read_text());script=Path(__file__).with_name('probe_continuous_spline_108.py');assert sha(script)==cpu['script_sha256']and sha(params)==cpu['input_sha256'];solver=cpu['solver'];assert solver['exact_KKT_gradient_equalities_and_all_constraints'];s=dict(knots=list(map(F,map(str,solver['knots']))),Y=list(map(F,solver['node_Y_rational'])),M=list(map(F,solver['second_derivatives_rational'])),polys=[list(map(F,row))for row in solver['piece_coefficients_native_rational']]);spline=Spline(s);solve_calls=0
 def forbidden_solve(*args,**kwargs):
  nonlocal solve_calls
  solve_calls+=1;raise RuntimeError('FORBIDDEN: production solver not authorized in RAM')
 tree=ast.parse(script.read_text());ns={'__file__':str(script),'__name__':'frozen_spline_RAM_only','root':root,'b':b,'p':p,'report':{},'load_rt':lambda:spline};imports=[x for x in tree.body if isinstance(x,(ast.Import,ast.ImportFrom))or isinstance(x,ast.FunctionDef)and x.name=='sha'];exec(compile(ast.Module(body=imports,type_ignores=[]),str(script),'exec'),ns);ns['solve']=forbidden_solve;mainast=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='main');req=next(x for x in mainast.body if isinstance(x,ast.FunctionDef)and x.name=='require');exec(compile(ast.Module(body=[req],type_ignores=[]),str(script),'exec'),ns);prefix=[];start=False
 for node in next(x for x in mainast.body if isinstance(x,ast.Try)).body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='ns'for t in node.targets):start=True
  if not start:continue
  prefix.append(node)
  if isinstance(node,ast.FunctionDef)and node.name=='evaluate':break
 class Loader(ast.NodeTransformer):
  def __init__(self):self.replaced=0
  def visit_Call(self,node):
   if isinstance(node.func,ast.Name)and node.func.id=='solve':self.replaced+=1;return ast.copy_location(ast.Call(func=ast.Name(id='load_rt',ctx=ast.Load()),args=[],keywords=[]),node)
   return self.generic_visit(node)
 loader=Loader();prefix=loader.visit(ast.Module(body=prefix,type_ignores=[]));assert loader.replaced==1;ast.fix_missing_locations(prefix);exec(compile(prefix,str(script),'exec'),ns);assert solve_calls==0;old=ns['old'];stage=ns['st'];actual=ns['data'];cache={}
 for surface in range(2):
  q=ns['canvas'](stage[surface]);m,_=ns['evaluate'](q);v=stage[surface].copy();on=m[:,1]!=q[:,1];v[on,1]=(371-m[on,1])/2024
  for origin,dest in zip(old[surface],v.astype(np.float32)):
   k=position_key(origin)
   if k in cache:assert np.array_equal(cache[k],dest)
   else:cache[k]=dest
 ocfg=json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text());oret=json.loads((b/'cpu-upper-cdt/cdt-api-result.validation.json').read_text());source=Path(ocfg['raw_glb']);g,bin0=read_glb(source);mi=next(n['mesh']for n in g['nodes']if n.get('name')=='Closed_body');pr=g['meshes'][mi]['primitives'];raw=[{k:accessor(g,bin0,a)for k,a in pp['attributes'].items()}for pp in pr];rf=[accessor(g,bin0,pp['indices']).reshape(-1,3)for pp in pr];mapped=[np.array([cache[position_key(v)]for v in r['POSITION']],dtype='<f4')for r in raw];pointchecks=[]
 for i,v in enumerate(mapped):
  expected=cpu['frozen_package_checks']['new_continuous_lip_raw_f32_points_hashes'][i];h=hashlib.sha256(v.tobytes()).hexdigest();assert len(v)==expected['count']and h==expected['sha256'];pointchecks.append(dict(surface=i,count=len(v),actual_f32_sha256=h,CPU_f32_hash_exact=True))
 maps=[];signs=[]
 for r,f,a in zip(raw,rf,actual):m,sn=map_faces(r,f,a);maps.append(m);signs.append(sn)
 keep=np.ones(len(rf[1]),bool);keep[maps[1][ocfg['old_oral_triangle_ids']]]=False;ids=np.asarray([v['raw_glb_vertex_ids'][0]for v in ocfg['points']]);neworal=ids[np.array(oret['input_origin_faces'])]
 if signs[1]<0:neworal=neworal[:,::-1]
 count=len(raw[1]['POSITION']);oral_origins=np.r_[np.arange(count),neworal.ravel()];faces=[rf[0],np.r_[rf[1][keep],np.arange(count,count+291).reshape(-1,3)]];positions=[mapped[0],mapped[1][oral_origins]];origins=[np.arange(len(mapped[0])),oral_origins];protected=[set(),set()]
 for group in p['base_eye_contract']['raw_corner_groups']:
  for side in group['raw_sides']:protected[side['surface']].add(position_key(side['POSITION'][0]))
 # Exactly the reviewed method with explicit zero-newfaces slicing guard.
 method=inspect.getsource(normals_for_surface).replace('changed_faces[-new_faces_count:]=True','\n if new_faces_count:changed_faces[-new_faces_count:]=True');scope=dict(normals_for_surface.__globals__);exec(method,scope);normal_method=scope['normals_for_surface'];surfaces=[];statistics=[]
 for i in range(2):
  normal,stats,delta,incident=normal_method(raw[i],positions[i],faces[i],[0,97][i],origins[i],protected[i]);protected_ids=np.array([j for j,k in enumerate(origins[i])if position_key(raw[i]['POSITION'][k])in protected[i]],int);assert np.array_equal(normal[protected_ids],raw[i]['NORMAL'][origins[i][protected_ids]]);assert np.array_equal(positions[i][protected_ids],raw[i]['POSITION'][origins[i][protected_ids]]);assert not(delta&~incident).any();surfaces.append(dict(POSITION=positions[i].astype(float).tolist(),NORMAL=normal.astype(float).tolist(),indices=faces[i].ravel().tolist()));statistics.append({k:stats[k]for k in ['updated_count','unit_max_error','actual_face_corner_cosine_min','actual_face_corner_cosine_nonpositive','policy']});statistics[-1].update(eye_position_normal_exact=True,eye_protected_raw_attributes=len(protected_ids),nonincident_exterior_NORMAL_exact=True,nonincident_changed_count=int((delta&~incident).sum()),updated_attribute_ids=np.flatnonzero(delta).tolist(),incident_attribute_ids=np.flatnonzero(incident).tolist())
 baseline=np.r_[raw[0]['POSITION'],raw[1]['POSITION']];bb=np.c_[baseline[:,0],-baseline[:,2],baseline[:,1]];payload=dict(status='RAM_CPU_pass_pending_visual_NOT_DELIVERY',fish='梭鲈 / Zander',accepted=False,candidate_written=False,production_solver_call_count=solve_calls,coefficients_loaded_from_completion=True,CPU_completion_sha256=sha(completion),execution_freeze_sha256=sha(freeze),field_sha256=sha(script),parameters_sha256=sha(params),payload_script_sha256=sha(Path(__file__)),normal_method_script_sha256=sha(Path(__file__).with_name('build_mouth_y_candidate_108.py')),normal_zero_newfaces_guard=True,original_source=str(source),source_sha256=sha(source),point_hash_checks=pointchecks,baseline_body_bounds_Blender=[bb.min(0).tolist(),bb.max(0).tolist()],CPU_global_crossing=cpu['actual_f32_global_crossing'],normal_statistics=statistics,surfaces=surfaces)
 evidence=dict(ns=ns,raw=raw,rawfaces=rf,mapped=mapped,actual=actual,old=old,stage=stage)
 return payload,evidence

def main():print(json.dumps(build_payload()[0]))
if __name__=='__main__':main()
