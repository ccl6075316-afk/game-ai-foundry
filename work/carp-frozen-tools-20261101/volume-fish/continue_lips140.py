"""Continue native source clusters over a reprojected raised lip candidate."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from PIL import Image

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--prior-root',type=Path,required=True);p.add_argument('--species',required=True);p.add_argument('--blender',required=True);a=p.parse_args()
 dest=a.root/a.species/'lips';dest.mkdir(parents=True,exist_ok=True);old=a.prior_root/a.species/'lips';body=a.root/a.species/'geometry/body.bound.json';lip=a.root/a.species/'geometry/lips.raw.json';scripts=Path(__file__).resolve().parent
 band=a.root/a.species/'band140.plan.json'
 if not band.exists():band=old/'band.plan.json'
 plan={'species':a.species,'body_mesh':str(body),'lip_mesh':str(lip),'band_plan':str(band),'source_images_npz':str(old/'source-images.npz'),'source_image':str(old/'native-source.png'),'opaque_skin':read(old/'trial.plan.json')['opaque_skin'],'skin_selection_min':[.3,-.2,-.1],'skin_selection_max':[.51,.15,.1]}
 if a.species in ['bluegill','nile_tilapia']:plan['source_band_coordinate_override']=['upper']
 if read(old/'trial.plan.json').get('source_uv_repair'):plan['source_uv_repair']=read(old/'trial.plan.json')['source_uv_repair']
 plan['frozen_inputs']={str(x):sha(x) for x in [body,lip,band,old/'source-images.npz']}
 write(dest/'trial.plan.json',plan)
 def run(script):
  r=subprocess.run([a.blender,'-b','--python-exit-code','1','--python',str(scripts/script),'--',str(dest)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=300)
  (dest/(script+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0 and 'Traceback' not in r.stdout+r.stderr,(script,r.stdout[-1000:],r.stderr[-1000:])
 run('probe_source_lip_uv.py');probe=read(dest/'body-lip-correspondence.json');bands=read(band);joins={}
 for part in read(lip)['parts']:
  name=part['name'];v=np.array(part['vertices'])[1:-1].reshape(255,17,3);q=np.array(probe[name]['body_uv'])[1:-1].reshape(255,17,2)*bands['source_size'];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(v[:,16],axis=0),axis=1))];choices=[];target=bands['bands'][name]['central_source_column']-12
  for L in range(50,110):
   R=254-L;dl=np.array([np.polyfit(arc[L-5:L+1]-arc[L],q[L-5:L+1,j,0],1)[0] for j in range(17)]);dr=np.array([-np.polyfit(arc[R:R+6]-arc[R],q[R:R+6,j,0],1)[0] for j in range(17)])
   if np.all(dl>0) and np.all(dr>0):choices.append((abs(q[L,16,0]-target)+abs(q[R,16,0]-target),L,R))
  assert choices,('No valid source joins',name)
  _,L,R=min(choices);joins[name]=[L,R]
 plan['join_rows']=joins;write(dest/'trial.plan.json',plan);run('build_mouth_material_continuity.py')
 for name in ['upper','lower','skin']:Image.fromarray(np.load(dest/(name+'-continuation.rgba.npy'))).save(dest/(name+'-continuation.png'))
 write(dest/'continuity140.validation.json',{'ok':True,'species':a.species,'plan_sha256':sha(dest/'trial.plan.json'),'join_rows':joins,'lips_sha256':sha(dest/'aligned-lips.mesh.json'),'scope':'Complete original source pixel clusters and measured joins; visual/body/motion review required.'})
 print(a.species,joins,flush=True)
if __name__=='__main__':main()
