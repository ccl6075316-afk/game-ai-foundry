"""Verify cold width-only export and write a species-bound local capture plan."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def section(pos,idx,x,scale):
 pts=[]
 for tri in pos[idx.reshape(-1,3)]:
  for i,j in [(0,1),(1,2),(2,0)]:
   a,b=tri[i],tri[j]
   if abs(a[0]-x)<1e-9:pts.append(a)
   if (a[0]-x)*(b[0]-x)<0:pts.append(a+(b-a)*(x-a[0])/(b[0]-a[0]))
 return float(np.ptp(np.array(pts)[:,2])*scale*100)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();out=a.directory.resolve()
 plan=json.loads((out/'deformation.plan.json').read_text(encoding='utf8'));oldpath=Path(plan['inputs']['model']['path']);newpath=out/'fish.glb'
 old,ob=read_glb(oldpath);new,nb=read_glb(newpath);op=old['meshes'][0]['primitives'][0];np_=new['meshes'][0]['primitives'][0]
 before={k:arrays(old,ob,v)for k,v in op['attributes'].items()};after={k:arrays(new,nb,v)for k,v in np_['attributes'].items()}
 assert set(before)==set(after)
 for k in before:
  if k not in ['POSITION','NORMAL']:assert np.array_equal(before[k],after[k]),k
 idx=arrays(old,ob,op['indices']).reshape(-1);assert np.array_equal(idx,arrays(new,nb,np_['indices']).reshape(-1))
 assert np.array_equal(before['POSITION'][:,:2],after['POSITION'][:,:2])
 pe=float(np.max(np.abs(np.array(plan['new_positions_gltf'])-after['POSITION'])));ne=float(np.max(np.abs(np.array(plan['new_normals_gltf'])-after['NORMAL'])))
 assert pe<1e-7 and ne<1e-6
 assert old['nodes']==new['nodes']
 assert old['skins'][0]['joints']==new['skins'][0]['joints']
 assert np.array_equal(arrays(old,ob,old['skins'][0]['inverseBindMatrices']),arrays(new,nb,new['skins'][0]['inverseBindMatrices']))
 assert len(old['animations'])==len(new['animations']);ae=0.
 for oa,na in zip(old['animations'],new['animations']):
  assert oa['channels']==na['channels']
  for x,y in zip(oa['samplers'],na['samplers']):
   for k in ['input','output']:ae=max(ae,float(np.max(np.abs(arrays(old,ob,x[k])-arrays(new,nb,y[k])))))
 assert ae<1e-7
 def image(d,b):
  v=d['bufferViews'][d['images'][0]['bufferView']];return b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
 assert image(old,ob)==image(new,nb)
 skin=np.concatenate([idx[r['index_start']:r['index_start']+r['index_count']]for r in new['extras']['geometry_parts']if r['role']in ['body_skin','mouth']])
 hi=before['POSITION'][:,0].max();L=np.ptp(before['POSITION'][:,0]);rows=[]
 for s,w in plan['target_width_stations_cm']:
  x=hi-s*L;rows.append({'s':s,'target_cm':w,'old_cm':section(before['POSITION'],skin,x,plan['model_scale']),'exported_cm':section(after['POSITION'],skin,x,plan['model_scale'])})
 proof={'ok':True,'kind':'width_trial_export_invariants','species':plan['species'],'model_sha256':sha(newpath),'source_model_sha256':sha(oldpath),'triangles':len(idx)//3,'mesh_count':1,'surface_count':1,'new_parts':0,'topology_UV_skin_rig_animation_image_preserved':True,'all_XY_exactly_unchanged':True,'position_vs_authored_max_error':pe,'normal_vs_authored_max_error':ne,'animation_max_error':ae,'actual_widths_cm':rows,'formal_acceptance':False}
 dump(out/'export-invariants.validation.json',proof)
 sp=plan['species']
 if plan.get('runtime_bindings'):
  refs=plan['runtime_bindings']
  for row in refs.values():assert sha(row['path'])==row['sha256']
  runtime=(ROOT/refs['runtime']['path']).resolve();motion=(ROOT/refs['profile']['path']).resolve()
 else:
  catalog=json.loads((ROOT/'projects/fishing-2d/experiments/four-fish-central-review-20261031/viewer/catalog.json').read_text(encoding='utf8'));v=next(r['viewer']for r in catalog['entries']if r['id']==sp);runtime=Path(v['controller']['runtime']);motion=Path(v['controller']['profile'])
 capture=HERE/'capture_transverse_width_trial.gd';paths=[oldpath,newpath,runtime,motion,capture,HERE/'portable/ReviewCaptureBase.gd']
 cap={'models':{'before':str(oldpath),'after':str(newpath)},'model_scale':plan['model_scale'],'motion_runtime':str(runtime),'motion_profile':str(motion),'bindings':{str(f):sha(f)for f in paths},**{k:plan[k]for k in ['head_focus','whole_width','head_width','front_width','motion_width']}}
 dump(out/'capture.plan.json',cap)
 print(json.dumps({'ok':True,'species':sp,'triangles':len(idx)//3,'position_error':pe,'normal_error':ne,'animation_error':ae}))
if __name__=='__main__':main()
