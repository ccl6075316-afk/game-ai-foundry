"""Freeze the standalone blacktip cage's actual inventory, roots and viewer."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 root=ROOT/'projects/fishing-2d/experiments/blacktip-lowpoly-20261101';folder=(ROOT/sys.argv[1]).resolve();model=folder/'fish.glb';d,b=read_glb(model);author=json.loads((folder/'fin-authoring.json').read_text());points=[];triangles=0
 for n in d['nodes']:
  if 'mesh'not in n:continue
  for p in d['meshes'][n['mesh']]['primitives']:points.extend(arrays(d,b,p['attributes']['POSITION']));triangles+=len(arrays(d,b,p['indices']))//3
 length=float(np.ptp(np.asarray(points)[:,0]));motion=json.loads((ROOT/'resources/volume-fish/motion/blacktip_reef_shark.json').read_text());motion['base_clip']='Swim';motion['notes'].append('2026-11-01 standalone source cage. Inherited shark motion uses C. limbatus proxy data, not direct C. melanopterus kinematics. Species visual/action review pending.');mp=root/'native-motion.json';save(mp,motion);runtime=ROOT/'projects/fishing-2d/game/scripts/aquarium/FoundryFishMotion.gd'
 fins={f['name']:{'ids':f['root_ids'],'rest_points_gltf':[[q[0],q[2],-q[1]]for q in f['root_points_native']],'rule':'Entire own-species original basal contour, both finite layers and all connecting caps; no old source band narrowed. Actual surface barycentric skin at full root.'}for f in author['fins']}
 body=next(n for n in d['nodes']if n.get('name')=='Closed_body');surfaces=len(d['meshes'][body['mesh']]['primitives']);inputs={str(p):sha(p)for p in[folder/'fish.blend',folder/'fin-authoring.json',ROOT/'resources/volume-fish/blacktip-complete-source-cage-20261101.json',ROOT/'resources/volume-fish/blacktip-fin-cages-20261101.json']};plan=dict(species='blacktip_reef_shark',model=str(model),model_sha256=sha(model),body='Closed_body',fins=fins,length_native=length,model_scale=1.5/length,motion_profile=str(mp),motion_profile_sha256=sha(mp),motion_runtime=str(runtime),motion_runtime_sha256=sha(runtime),controller_script='res://scripts/aquarium/FoundryFishMotion.gd',frozen_inputs=inputs,expected_triangles=triangles,expected_body_surfaces=surfaces,membrane_clearance={'root_collar_mm':.5,'penetration_tolerance_mm':.02,'targets':list(fins)},head_focus_u=.93,whole_camera_size=1.8,head_camera_size=.46,maximum_amplitude=2.5,pose_time=3.75)
 save(folder/'candidate.plan.json',plan);save(folder/'fin.plan.json',{'items':[plan]});save(folder/'diagnostic-fin.plan.json',{'items':[dict(plan,diagnostic_pose_filter=[{'action':'Swim','seconds':0.},{'action':'Turn','seconds':0.},{'action':'Ascend','seconds':0.},{'action':'Dive','seconds':0.}])]})
 ref=lambda p:{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
 spec={'kind':'fish_asset_finalization_spec','version':2,'species':'blacktip_reef_shark','game':'projects/fishing-2d/game','model':ref(model),'motion':{'api':'foundry_motion_v1','runtime':ref(runtime),'profile':ref(mp),'action':'Swim'},'viewer':{'model_scale':1.5/length,'native_clip':'Swim','focuses':{'head':{'mode':'bbox_relative','position':[.93,.50,.50]},'mouth':{'mode':'bbox_relative','position':[.93,.36,.50]}},'captures':[{'name':'side','yaw_degrees':0,'pitch_degrees':0,'time_seconds':0},{'name':'oblique','yaw_degrees':35,'pitch_degrees':15,'time_seconds':0},{'name':'top','yaw_degrees':0,'pitch_degrees':85,'time_seconds':0},{'name':'front','yaw_degrees':90,'pitch_degrees':0,'time_seconds':0},{'name':'bottom','yaw_degrees':0,'pitch_degrees':-85,'time_seconds':0}]},'camera':{'yaw_degrees':15,'pitch_degrees':12}}
 save(folder/'viewer-spec.json',spec);print(json.dumps({'triangles':triangles,'bones':len(d['skins'][0]['joints']),'mesh_count':len(fins)+1,'surfaces':surfaces,'length_native':length}))
if __name__=='__main__':main()
