"""Freeze one species-specific transverse experiment, never copy another fish's gains."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists()
 research=ROOT/'output/four-fish-width-study-20261031/pre-model-plan.json';allplans=json.loads(research.read_text(encoding='utf8'));c=allplans['species'][a.species]
 assert a.species in ['bluegill','crucian','grass_carp']
 source_model=Path(c['source_model']);assert sha(source_model)==c['source_model_sha256']
 source_blend=source_model.parent/'source/fish.blend';assert source_blend.is_file()
 baseline=json.loads((research.parent/'baseline.validation.json').read_text(encoding='utf8'));base=next(r for r in baseline['records']if r['species']==a.species)
 cutoff={'bluegill':.50,'crucian':.60,'grass_carp':.82}[a.species]
 targets=[(r['s'],r['target_width_cm'])for r in c['stations']if r['s']<cutoff]
 # Avoid introducing posterior narrowing from the exploratory report. Blend back to
 # actual current geometry; independently requested fin/artwork repair is deferred.
 if a.species=='bluegill':targets=[(s,w)for s,w in targets if s<=.40]
 if a.species=='crucian':targets=[(s,w)for s,w in targets if s<=.50]
 d,b=read_glb(source_model);pr=d['meshes'][0]['primitives'][0];pos=arrays(d,b,pr['attributes']['POSITION']);n=arrays(d,b,pr['attributes']['NORMAL'])
 lo,hi=pos[:,0].min(),pos[:,0].max();L=hi-lo;stations=[]
 for s,w in targets:
  measured=next(r['width_cm']for r in base['sections']if r['s_from_nose_over_visible_TL']==s);stations.append([s,w/measured])
 stations=[[0,stations[0][1]],*stations,[cutoff,1],[1,1]]
 gfield=PchipInterpolator(np.array(stations)[:,0],np.array(stations)[:,1]);s=(hi-pos[:,0])/L;g=gfield(s);dgdx=-gfield.derivative()(s)/L
 assert (g>0).all();new=pos.copy();new[:,2]=pos[:,2]*g
 nn=n.astype(float).copy();nn[:,0]-=pos[:,2]*dgdx/g*n[:,2];nn[:,2]/=g;nn/=np.linalg.norm(nn,axis=1)[:,None];nn=nn.astype('float32')
 keep=s>=cutoff;new[keep]=pos[keep];nn[keep]=n[keep]
 scale=base['model_scale_cm']/100;tl=c['length']/100
 inputs={k:{'path':str(v),'sha256':sha(v)}for k,v in {'model':source_model,'blend':source_blend,'research':research}.items()}
 parts=[]
 for part in d['extras']['geometry_parts']:
  j=part['vertex_start'];end=j+part['vertex_count'];parts.append({'name':part['name'],'role':part['role'],'changed_vertices':int(np.any(pos[j:end]!=new[j:end],axis=1).sum())})
 plan={'kind':'single_fish_transverse_width_trial','species':a.species,'label':c['label'],'inputs':inputs,'coordinate':'glTF X length/Yheight fixed; Z only; full widths in cm','source_evidence':c['sourceids'],'basis':c['basis'],'evidence_grade':'D-authored experimental targets/longitudinal matching, constrained by separately recorded same-species evidence','scope':'Width only. No new/split/deleted mesh, no fin boundary/artwork or mouth reconstruction. Existing fins in field follow continuous deformation; old physical reports invalid.','target_width_stations_cm':targets,'gain_stations':stations,'cutoff_s':cutoff,'display_TL_cm':c['length'],'model_scale':scale,'head_focus':[float((hi-.12*L)*scale),0,0],'whole_width':tl*1.4,'head_width':tl*.42,'front_width':tl*.75,'motion_width':tl*1.5,'parts':parts,'old_positions_gltf':pos.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':nn.tolist(),'formal_acceptance':False}
 dump(out/'deformation.plan.json',plan)
 dump(ROOT/f'resources/volume-fish/{a.species}-width-trial-20261031.json',{k:v for k,v in plan.items()if k not in ['old_positions_gltf','new_positions_gltf','new_normals_gltf']})
 dump(out/'manifest.json',{'kind':'species_width_trial','species':a.species,'status':'pending','next_action':'run','inputs':inputs,'scope':plan['scope'],'formal_acceptance':False,'installed':False})
 print(json.dumps({'ok':True,'species':a.species,'output':str(out),'target_stations':len(targets)}))
if __name__=='__main__':main()
