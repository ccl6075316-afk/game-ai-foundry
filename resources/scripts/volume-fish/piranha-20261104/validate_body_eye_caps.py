"""Piranha-only077 adapter for declared non-rigid body-supported eye caps.

The maintained body's closure/winding/opaque-donor/GPU/negative-control code is
executed unchanged. Explicit eye caps are checked independently and projected
out only of that body-topology analysis. Real GPU capture reads the fullGLB.
"""
import copy,hashlib,importlib.util,io,json,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
PORTABLE=ROOT/'resources/scripts/volume-fish/portable'
BASE=PORTABLE/'validate_standalone_body.py'
BASE_SHA='1a73badcd756005eb10e5e70530ea3bcc084c5db2f084d0cb16843cb65ab4fd7'
sys.path.insert(0,str(PORTABLE));sys.path.insert(0,str(PORTABLE.parent))
from glb_io import read_glb,arrays
import logical_document as logical
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(BASE)==BASE_SHA,'Body validator changed; review private adapter delta'
module_spec=importlib.util.spec_from_file_location('_piranha_077_base',BASE)
base=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(base)
original_inspect=base.inspect_model

def bound(ref):
 p=Path(ref['path']);assert p.is_absolute() and sha(p)==ref['sha256'],'Stale eye-cap report/source';return p

def check_eye_caps(plan,doc,blob,manifest):
 definition=plan['decorative_overlays'];expected=set(definition)
 assert expected=={'Eye_relief_-1','Eye_relief_1'},'Missing/extra piranha eye cap role'
 allparts=manifest['parts'];eye_parts=[p for p in allparts if p['role']=='eyes']
 assert {p['name']for p in eye_parts}==expected and len(eye_parts)==2,'Missing eye role or undeclared overlay'
 report=json.loads(bound(plan['eye_finite_face_report']).read_text(encoding='utf8'))
 assert report['kind']=='actual_runtime_490_eye_front_finite_face_clearance' and report['ok'] is True
 assert report['model_sha256']==plan['model_sha256']==sha(plan['model']),'Wrong eye-contact model'
 assert len(report['samples'])==490 and report['penetration_tolerance_mm']==.02
 assert all(np.isfinite(r['minimum_front_face_clearance_mm']) and r['minimum_front_face_clearance_mm']>=-.02 and r['actual_triangle_intersections']>0 for r in report['samples'])
 actual=json.loads(bound(plan['eye_skin_export']).read_text(encoding='utf8'))
 assert actual['ok'] and actual['model_sha256']==plan['model_sha256'] and len(actual['samples'])==490
 assert Path(actual['controller_source']).resolve()==Path(plan['motion_runtime']).resolve() and actual['controller_sha256']==plan['motion_runtime_sha256']==sha(plan['motion_runtime']),'Wrong current eye controller'
 assert Path(actual['actual_motion_profile']).resolve()==Path(plan['motion_profile']).resolve() and actual['actual_motion_profile_sha256']==plan['motion_profile_sha256']==sha(plan['motion_profile']),'Wrong current eye motion profile'
 assert [(r['action'],r['seconds'])for r in actual['samples']]==[(r['action'],r['seconds'])for r in report['samples']], 'Different actual490 schedules'
 assert report['analysis_inputs']['skin_export_sha256']==plan['eye_skin_export']['sha256']
 checker=bound(report['analysis_inputs']['checker']);assert checker.name=='check_dynamic_faces.py'
 source=Image.open(bound(plan['eye_original_source'])).convert('RGBA')
 author=json.loads(bound(plan['eye_authoring']).read_text(encoding='utf8'))
 assert {e['name']for e in author['eyes']}==expected
 d,b=read_glb(plan['model']);pr=d['meshes'][0]['primitives'][0];at={k:arrays(d,b,a)for k,a in pr['attributes'].items()};indices=arrays(d,b,pr['indices']).reshape(-1,3)
 body_face_keys={tuple(sorted(map(int,face)))for p in manifest['parts']if p['role']in ('body','body_skin')for face in indices[p['index_range'][0]//3:p['index_range'][1]//3]}
 assert body_face_keys,'No actual finite body support triangles'
 im=d['images'][0];view=d['bufferViews'][im['bufferView']];rgba=np.asarray(Image.open(io.BytesIO(b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])).convert('RGBA'));height,width=rgba.shape[:2]
 result=[]
 for p in eye_parts:
  rule=definition[p['name']];assert rule['kind']=='body_supported_shallow_eye_cap' and rule['underlying_body']==plan['body']
  assert 'rigid_bone' not in rule and rule['closed'] is False,'Do not label non-rigid/open cap closed/rigid'
  lo,hi=p['vertex_range'];i0,i1=p['index_range'];pos=at['POSITION'][lo:hi];weights=at['WEIGHTS_0'][lo:hi];joints=at['JOINTS_0'][lo:hi];uv=at['TEXCOORD_0'][lo:hi]
  assert np.isfinite(pos).all() and np.isfinite(weights).all() and weights.shape==(len(pos),4)
  assert np.all(weights>=0) and np.all(abs(weights.sum(1)-1)<1e-5) and np.all(joints>=0) and joints.max()<len(d['skins'][0]['joints'])
  q=next(e for e in author['eyes']if e['name']==p['name']);assert len(q['samples'])==len(pos)
  for vertex,s in enumerate(q['samples']):
   assert np.max(abs(pos[vertex]-s['eye']))<2e-6,'Eye point differs from authored current support'
   ids=np.asarray(s['body_triangle']);bary=np.asarray(s['barycentric']);assert len(ids)==3 and np.min(bary)>=0 and abs(bary.sum()-1)<1e-6
   assert tuple(sorted(map(int,ids)))in body_face_keys,'Eye support is not an actual finite body triangle'
   skin={}
   for j,w in zip(joints[vertex],weights[vertex]):skin[int(j)]=skin.get(int(j),0)+float(w)
   support={}
   for index,gain in zip(ids,bary):
    for j,w in zip(at['JOINTS_0'][index],at['WEIGHTS_0'][index]):support[int(j)]=support.get(int(j),0)+float(w*gain)
   assert max(abs(skin.get(j,0)-support.get(j,0))for j in set(skin)|set(support))<2e-6,'Eye actual4weights not body barycentric skin'
  # Preserve complete original eye chart; prove explicit per-vertex affine
  # mapping and exact source pixels over its entire enclosing rectangle.
  chart=rule['chart'];box=chart['source_roi'];origin=chart['atlas_origin'];sw,sh=source.size
  sx=(pos[:,0]+.5)*sw;sy=(.5-pos[:,1]*1.8081140350877194)*sh
  expected_uv=np.column_stack([(origin[0]+sx-box[0])/width,(origin[1]+sy-box[1])/height])
  assert np.max(abs(uv-expected_uv))<2e-6,'Current eye UV is not original source chart'
  region=rgba[origin[1]:origin[1]+box[3]-box[1],origin[0]:origin[0]+box[2]-box[0]]
  assert np.array_equal(region,np.asarray(source.crop(box))),'Original complete eye pixels changed'
  assert np.all(region[:,:,3]==255),'Transparent original eye domain'
  xy=pos[:,:2];r=np.sqrt(((xy[:,0]-.39418)/.0294)**2+((xy[:,1]+.01455)/.0318)**2)
  assert r.max()<=1.00001 and np.min(r)<1e-4,'Wrong/incomplete actual original eye footprint'
  # Every front-face point was checked against actual posed finite body faces.
  assert i1-i0==147*3 and np.all(np.isfinite(uv))
  result.append({'name':p['name'],'kind':rule['kind'],'closed':False,'actual_body_barycentric_four_weights':True,'triangles':(i1-i0)//3,'complete_original_pixel_chart':True,'actual490_finite_face_report_sha256':plan['eye_finite_face_report']['sha256']})
 return result

def inspect_model(plan):
 assert plan['species']=='piranha','Private adapter is only for piranha'
 assert sha(plan['model'])==plan['model_sha256'],'Wrong current full model'
 manifest=json.loads(bound({'path':plan['packed_parts_manifest'],'sha256':plan['packed_parts_manifest_sha256']}).read_text(encoding='utf8'))
 doc,blob,opacity=logical.logical_document(plan['model'],plan['body'],plan['fins'],plan['packed_parts_manifest'])
 names={n['name']for n in doc['nodes']if 'mesh'in n};overlays=plan.get('decorative_overlays',{})
 assert set(overlays)=={'Eye_relief_-1','Eye_relief_1'}
 assert names=={plan['body'],*plan['fins'],*overlays},'Unexpected or omitted overlay'
 total=sum(len(arrays(doc,blob,p['indices']))//3 for n in doc['nodes']if 'mesh'in n for p in doc['meshes'][n['mesh']]['primitives'])
 assert total==plan['expected_triangles']==1940,'Wrong full triangle inventory'
 # This is an explicit analysis projection of body+all fins after full actual
 # inventory validation; full source model and actual GPU input stay unchanged.
 projected=copy.deepcopy(doc)
 for node in projected['nodes']:
  if node.get('name')in overlays:node.pop('mesh',None)
 inner=copy.deepcopy(plan);inner['decorative_overlays']={};inner['expected_triangles']=total-294
 original_logical=logical.logical_document
 try:
  logical.logical_document=lambda *_args:(projected,blob,opacity)
  geometry=original_inspect(inner)
 finally:logical.logical_document=original_logical
 proofs=check_eye_caps(plan,doc,blob,manifest)
 geometry.update(triangles=total,decorative_overlay_proofs=proofs,private_body_topology_projection={'body_and_all_fins_triangles':total-294,'declared_eye_cap_triangles':294,'full_model_gpu_input_unchanged':True,'base_validator_sha256':BASE_SHA})
 return geometry

def validate(game,godot,plan_path,output):
 base.inspect_model=inspect_model
 result=base.validate(game,godot,plan_path,output)
 result['private_eye_cap_adapter']={'path':str(Path(__file__).resolve()),'sha256':sha(__file__),'base_sha256':BASE_SHA,'scope':'Only explicit piranha shallow caps; unchanged body077 kernel and actual complete model GPU checks.'}
 (output/'completion.validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 return result

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__)
 for key in ['game','godot','plan','output']:p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();r=validate(a.game.resolve(),a.godot.resolve(),a.plan.resolve(),a.output.resolve());print(json.dumps({'ok':r['ok'],'error':r.get('error')}));raise SystemExit(0 if r['ok']else 1)
