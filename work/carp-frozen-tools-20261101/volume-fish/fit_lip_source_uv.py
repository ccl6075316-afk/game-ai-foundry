"""Fit source lip artwork to an existing wide mouth, preserving all geometry."""
import argparse,copy,json,hashlib,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
sys.path.insert(0,str(Path(__file__).resolve().parents[3]));from cli.volume_mouth import slit_v
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();reports=[]
 for row in json.loads(a.plan.read_text())['items']:
  assert sha(row['source'])==row['source_sha256'];d,b=read_glb(Path(row['source']));old=copy.deepcopy(d);n=next(n for n in d['nodes']if n.get('name')=='Closed_body');pr=d['meshes'][n['mesh']]['primitives'];v=accessor(d,b,pr[0]['attributes']['POSITION']);uv=accessor(d,b,pr[0]['attributes']['TEXCOORD_0']);before=uv.copy();path=np.array(row['source_gap_path']);upper=PchipInterpolator(path[:,0],path[:,1],extrapolate=False);lower=PchipInterpolator(path[:,0],path[:,2],extrapolate=False);start=row['old_path'][0][0];aspect=row['aspect'];binary=bytearray(b)
  for i,pos in enumerate(v):
   u=float(pos[0])+.5
   if u<=start:continue
   oldcenter=slit_v({'slit_path':row['old_path']},u);ou=oldcenter-row['old_gap']/aspect/2;ol=oldcenter+row['old_gap']/aspect/2;sample=np.clip(u,path[0,0],path[-1,0]);nu=float(upper(sample));nl=float(lower(sample));fade=np.clip((u-start)/.012,0,1);fade=fade*fade*(3-2*fade)
   if uv[i,1]<=ou:distance=ou-uv[i,1];delta=nu-ou
   elif uv[i,1]>=ol:distance=uv[i,1]-ol;delta=nl-ol
   else:
    distance=0;target=nu+(uv[i,1]-ou)/(ol-ou)*(nl-nu);delta=target-uv[i,1]
   uv[i,1]+=delta*max(0,1-distance/.12)**2*fade
  binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(uv.astype('<f4').tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=uv.nbytes,target=34962));ac=len(d['accessors']);d['accessors'].append(dict(bufferView=vi,componentType=5126,count=len(uv),type='VEC2',min=uv.min(0).tolist(),max=uv.max(0).tolist()));pr[0]['attributes']['TEXCOORD_0']=ac
  for i in range(2):
   for key in ['POSITION','NORMAL','JOINTS_0','WEIGHTS_0','TEXCOORD_1']:assert pr[i]['attributes'].get(key)==old['meshes'][n['mesh']]['primitives'][i]['attributes'].get(key)
  target=Path(row['uv_target']);target.parent.mkdir(parents=True,exist_ok=True);write(target,d,binary);reports.append(dict(species=row['species'],source_sha256=row['source_sha256'],model_sha256=sha(target),body_geometry_normals_rig_animation_fins_unchanged=True,changed_uv_vertices=int(np.any(before!=uv,axis=1).sum()),max_v_shift=float(np.max(np.abs(uv-before)))))
 a.report.write_text(json.dumps(dict(ok=True,items=reports,script_sha256=sha(__file__),plan_sha256=sha(a.plan)),indent=2));print('Fitted lip source UVs:',len(reports))
if __name__=='__main__':main()
