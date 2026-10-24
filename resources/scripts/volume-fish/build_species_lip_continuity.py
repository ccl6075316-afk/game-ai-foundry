"""Build independent, explicitly planned source lip candidates and evidence.

No install or acceptance. A failing species remains failed while independent
species can build; the batch returns nonzero if any species failed.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,d):Path(p).write_text(json.dumps(d,indent=2),encoding='utf8')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--parameters',type=Path,required=True);ap.add_argument('--blender',type=Path,required=True);ap.add_argument('--species',nargs='*');ap.add_argument('--reuse-geometry',action='store_true');a=ap.parse_args()
 scripts=Path(__file__).resolve().parent;results=[]
 for row in read(a.parameters)['items']:
  species=row['species']
  if a.species and species not in a.species:continue
  root=Path(row['output']).resolve();dest=root/'lips'
  def run(name,args,blender=False):
   cmd=[str(a.blender),'-b','--python',str(scripts/name),'--',*args] if blender else [sys.executable,'-X','utf8',str(scripts/name),*args]
   r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1200)
   (dest/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf8')
   assert r.returncode==0 and 'Traceback' not in r.stdout+r.stderr,(name,r.stderr[-700:],r.stdout[-700:])
  try:
   plan=dest/'band.plan.json';assert read(plan)['species']==species
   run('prepare_source_lips.py',['--plan',str(plan)])
   geometry=dest/'geometry.validation.json'
   reusable=a.reuse_geometry and geometry.exists() and read(geometry).get('ok') and read(geometry)['inputs']['plan_sha256']==sha(plan) and sha(dest/'lip-band.mesh.json')==read(geometry)['outputs'][0]['sha256']
   if not reusable:run('build_source_lips.py',[str(plan)],True)
   inspection=read(dest/'source-inspection.json');source=dest/'native-source.png';opaque=Path(inspection['opaque'])
   np.savez_compressed(dest/'source-images.npz',source=np.asarray(Image.open(source).convert('RGBA')),opaque=np.asarray(Image.open(opaque).convert('RGBA')))
   body=root/'localized/body.bound.json';lip=dest/'lip-band.mesh.json'
   assert body.exists()
   trial={'species':species,'body_mesh':str(body),'lip_mesh':str(lip),'band_plan':str(plan),'source_images_npz':str(dest/'source-images.npz'),
    'source_image':str(source),'opaque_skin':str(opaque),'skin_selection_min':[.3,-.2,-.1],'skin_selection_max':[.51,.15,.1]}
   if row.get('source_uv_repair'):trial['source_uv_repair']=row['source_uv_repair']
   trial['frozen_inputs']={str(p):sha(p) for p in [body,lip,plan,dest/'source-images.npz']}
   save(dest/'trial.plan.json',trial)
   run('probe_source_lip_uv.py',[str(dest)],True)
   probe=read(dest/'body-lip-correspondence.json');mesh=read(lip);joins={};width=read(plan)['source_size'][0]
   for part in mesh['parts']:
    name=part['name'];v=np.asarray(part['vertices'])[1:-1].reshape(255,17,3);q=np.asarray(probe[name]['body_uv'])[1:-1].reshape(255,17,2)*read(plan)['source_size'];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(v[:,16],axis=0),axis=1))];choices=[]
    target=read(plan)['bands'][name]['central_source_column']-12
    for L in range(50,110):
     R=254-L
     dl=np.array([np.polyfit(arc[L-5:L+1]-arc[L],q[L-5:L+1,j,0],1)[0] for j in range(17)])
     dr=np.array([-np.polyfit(arc[R:R+6]-arc[R],q[R:R+6,j,0],1)[0] for j in range(17)])
     if np.all(dl>0) and np.all(dr>0):choices.append((abs(q[L,16,0]-target)+abs(q[R,16,0]-target),L,R))
    assert choices,('No valid real UV joins',name)
    _,L,R=min(choices);joins[name]=[L,R]
   trial['join_rows']=joins;save(dest/'trial.plan.json',trial)
   run('build_mouth_material_continuity.py',[str(dest)],True)
   for name in ['upper','lower','skin']:
    Image.fromarray(np.load(dest/(name+'-continuation.rgba.npy'))).save(dest/(name+'-continuation.png'))
   aligned=dest/'aligned-lips.mesh.json';skinplan={'species':species,'source_model':row['model'],'mesh':'Closed_body','body':str(body),'lips':str(aligned),'output':str(dest/'bound'),
    'reuse_body_binding':True,'maximum_source_projection_distance':5e-6,'maximum_lip_projection_distance':.001,'maximum_discarded_weight':1e-5,
    'frozen_inputs':{str(p):sha(p) for p in [Path(row['model']),body,aligned]}}
   save(dest/'skinning.plan.json',skinplan);run('transfer_mouth_skinning.py',['--plan',str(dest/'skinning.plan.json')],True)
   preview=read(root/'preview.plan.json');cfg={'lips':str(dest/'bound/lips.bound.json'),'source':str(source),'opaque':str(opaque),'skin_records':str(dest/'skin-chart-records.json'),
    'atlases':{name:str(dest/(name+'-continuation.png')) for name in ['upper','lower','skin']}}
   cfg['frozen_inputs']={p:sha(p) for p in [cfg['lips'],cfg['source'],cfg['opaque'],cfg['skin_records'],*cfg['atlases'].values()]}
   preview['material_continuity']=cfg;save(root/'material-preview.plan.json',preview)
   result={'ok':True,'species':species,'plan_sha256':sha(plan),'joins':joins,'production_installed':False}
  except Exception as e:result={'ok':False,'species':species,'error':str(e),'production_installed':False}
  save(dest/'build.validation.json',result);results.append(result);print('SOURCE_LIPS',json.dumps(result),flush=True)
 return 0 if all(r['ok'] for r in results) else 1
if __name__=='__main__':sys.exit(main())
