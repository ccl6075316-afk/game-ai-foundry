"""Actual ArrayMesh positions/UV/bones/UNORM16 plus untouched accepted body."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from validate_mouth_body139 import binding_matches
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def adapted(f):return {'skin_bind_names':f['skin_joint_names'],'parts':[{**p,'bones':p['joints']} for p in f['parts']]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();r=a.root;rows=[]
 try:
  plan=json.loads(a.plan.read_text());candidate=Path(plan['output']);geometry=candidate/('fins.final.json' if(candidate/'fins.final.json').exists()else'fins.bound.json');expected=json.loads(geometry.read_text());actual=json.loads(a.runtime.read_text());original=json.loads(Path(plan['source_mesh']).read_text());assert actual['source_model_sha256']==expected['source_model_sha256']==original['source_model_sha256'];byname={f['name']:f for f in actual['fins']};assert set(byname)=={f['name']for f in original['fins']},'Applicable fin inventory changed'
  if geometry.name=='fins.final.json':
   frozen=json.loads((candidate/'fin.plan.json').read_text())['items'][0]['mouth_candidate']['frozen_inputs'];assert frozen[str(geometry.resolve())]==sha(geometry),'Unfrozen final geometry'
  for f in expected['fins']:
   got=byname[f['name']];binding_matches(adapted(got),f['parts'],f['skin_joint_names'])
   for pp,gg in zip(f['parts'],got['parts']):
    assert np.array_equal(np.asarray(pp['uv'],np.float32),np.asarray(gg['uv'],np.float32)),'Actual UV differs';im=np.asarray(Image.open(gg['texture']['path']).convert('RGBA'));ref=np.asarray(Image.open(f['texture']).convert('RGBA'));assert np.array_equal(im,ref),'Actual native source image differs'
   rows.append({'name':f['name'],'ok':True,'actual_positions_uv_bones_weights_exact':True,'native_rgba_identical':True})
  replaced={f['name']for f in expected['fins']}
  for old in original['fins']:
   if old['name']in replaced:continue
   got=byname[old['name']];assert got['skin_joint_names']==old['skin_joint_names']and len(got['parts'])==len(old['parts'])
   for pp,gg in zip(old['parts'],got['parts']):
    for field in ['vertices','normals','uv','joints','weights','triangles']:assert np.array_equal(np.asarray(pp[field]),np.asarray(gg[field])),'Retained fin changed: '+old['name']+'/'+field
    assert np.array_equal(np.asarray(Image.open(pp['texture']['path']).convert('RGBA')),np.asarray(Image.open(gg['texture']['path']).convert('RGBA'))),'Retained fin texture changed'
  assert len(actual['body'])==len(original['body'])
  override=plan.get('body_geometry_override');desired=json.loads(Path(override['path']).read_text()) if override else None
  for old,got in zip(original['body'],actual['body']):
   assert old['name']==got['name'] and old['skin_joint_names']==got['skin_joint_names'],'Body skin table changed';assert len(old['parts'])==len(got['parts'])
   # Both sides here are already decoded actual-engine arrays. Do not apply
   # the raw-generator floor encoder a second time to preserved UNORM16 values.
   if desired:binding_matches(adapted(got),desired['parts'],override['skin_joint_names'])
   for si,(pp,gg) in enumerate(zip(old['parts'],got['parts'])):
    for field in ['vertices','normals','uv','joints','weights','triangles']:
     dtype=np.int64 if field in ['joints','triangles'] else np.float32
     if field=='vertices' and override:
      oldv=np.asarray(pp[field],dtype);newv=np.asarray(gg[field],dtype);assert np.array_equal(oldv[oldv[:,0]>=0],newv[oldv[:,0]>=0]),'Accepted anterior half/head changed'
     else:assert np.array_equal(np.asarray(pp[field],dtype),np.asarray(gg[field],dtype)),'Accepted body array changed: '+field
  result={'ok':len(rows)==len(expected['fins']),'records':rows,'retained_fins_arrays_native_rgba_exact':len(original['fins'])-len(rows),'accepted_body_positions_uv_skin_unchanged':not bool(override),'accepted_anterior_half_and_all_nonposition_body_arrays_unchanged':True,'local_anal_basal_fit':override,'input_plan_sha256':sha(a.plan),'geometry_sha256':sha(geometry),'runtime_sha256':sha(a.runtime),'scope':'Actual new fin resource arrays and native RGBA; preserved140 anterior half/head and nonposition arrays. Only declared posterior ventral basal fit may move body positions. Posed contact, body GPU and visual/source checks remain separate.'}
 except Exception as e:result={'ok':False,'error':str(e),'records':rows}
 target=a.output or candidate/'runtime-binding.validation.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2));print(json.dumps({'ok':result['ok'],'fins':len(rows),'error':result.get('error')}));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
