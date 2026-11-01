"""Prepare one existing-fish trial: measured maximum W/SL first, referenced local envelope second."""
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import median_filter,binary_fill_holes
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays
from audit_transverse_width import section
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ref(p):return {'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def prepare(cp,out,dry_run=False):
 c=read(cp);out=out.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists()
 for r in c['inputs'].values():assert ref(r['path'])['sha256']==r['sha256']
 old=read(c['inputs']['baseline_config']['path']);spec=read(old['inputs']['spec']['path']);model=Path(old['inputs']['model']['path']);d,b=read_glb(model);p=d['meshes'][0]['primitives'][0];v=arrays(d,b,p['attributes']['POSITION']);n=arrays(d,b,p['attributes']['NORMAL']);ix=arrays(d,b,p['indices']).flatten();body=np.concatenate([ix[q['index_start']:q['index_start']+q['index_count']]for q in d['extras']['geometry_parts']if q['role']in ['body_skin','mouth']]);ids=np.unique(body);hi=float(v[:,0].max());L=float(np.ptp(v[:,0]));scale=spec['viewer']['model_scale']*100;LB=c['body_axis_cm'];assert abs(LB/scale-np.ptp(v[ids,0]))<.015,'Check tail-base ownership/axis before SL-like matching'
 samples=[]
 for row in csv.DictReader(open(c['inputs']['csv']['path'],encoding='utf-8-sig')):
  if row['Tree_name']==c['scientific_name'].replace(' ','_'):samples.append({'specimen_id':row['SpecimenID'],'SL_mm':float(row['Standard_length']),'max_width_mm':float(row['Max_fish_width']),'W_over_SL':float(row['Max_fish_width'])/float(row['Standard_length'])})
 assert samples;ratio=float(np.median([r['W_over_SL']for r in samples]));maximum=ratio*LB
 image=Image.open(c['inputs']['reference']['path']).convert('RGB');a=np.asarray(image);import cv2
 hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV);mask=(a.max(axis=2)<155)|(hsv[:,:,1]>25);count,labels,stats,centers=cv2.connectedComponentsWithStats(mask.astype('uint8'));mask=binary_fill_holes(labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA])));axis=c['reference_axis'];start,end=c['reference_axis_pixels'];lo,up=c['corridor'];source=[];draw=ImageDraw.Draw(image)
 for k in range(min(start,end)+2,max(start,end)-1):
  t=(k-start)/(end-start)
  if not .002<=t<=.92:continue
  bounds=[lo,up]
  for cut in c['fin_exclusion_corridors']:
   if cut['axis_range'][0]<=k<=cut['axis_range'][1]:bounds=cut['body_bounds']
  line=mask[k,:]if axis=='y'else mask[:,k];q=np.flatnonzero(line[bounds[0]:bounds[1]])+bounds[0]
  if len(q)<3:continue
  source.append({'t':t,'axis_pixel':k,'bounds':[int(q.min()),int(q.max())],'width_px':int(np.ptp(q))})
  if k%12==0:draw.line([(q.min(),k),(q.max(),k)]if axis=='y'else[(k,q.min()),(k,q.max())],fill='#ff9b00',width=1)
 source.sort(key=lambda q:q['t']);tt=np.array([q['t']for q in source]);w=median_filter(np.array([q['width_px']for q in source],float),size=9,mode='nearest');wmax=float(w.max());curve=PchipInterpolator(tt,w/wmax)
 def native(t):return float(np.ptp(section(v,body,hi-t*LB/scale)[:,2])*scale)
 join=PchipInterpolator([.7,.8,.9],[float(curve(.7)*maximum),(float(curve(.8)*maximum)+native(.8))/2,native(.9)])
 def target(t):return float(curve(np.clip(t,tt[0],tt[-1]))*maximum)if t<=.7 else float(join(t))if t<.9 else native(t)
 knots=np.unique(np.r_[.002,(hi-v[ids,0])*scale/LB,np.linspace(.002,.9,160),.9]);knots=knots[(knots>=.002)&(knots<=.9)];gain=np.array([target(float(t))/native(float(t))for t in knots]);gain[-1]=1;f=PchipInterpolator(np.r_[0,knots,1.3],np.r_[gain[0],gain,1]);tpos=(hi-v[:,0])*scale/LB;g=f(tpos);g[tpos>=.9]=1
 assert np.isfinite(g).all()and g.min()>.5 and g.max()<2.5,(g.min(),g.max())
 def measure(pos):return [{'t':float(t),'W_cm':float(np.ptp(section(pos,body,float(hi-t*LB/scale))[:,2])*scale)}for t in np.linspace(.002,.9,450)]
 proposed=v.copy();proposed[:,2]*=g;pre=measure(proposed);factor=maximum/max(q['W_cm']for q in pre)
 if abs(factor-1)>=.03:
  save(cp.with_suffix('.failure.validation.json'),{'ok':False,'reason':'Finite envelope maximum deviates from measured global anchor before normalization; inspect posterior joint.','target_max_cm':maximum,'actual_max':max(pre,key=lambda q:q['W_cm']),'factor':factor,'source_maximum':source[int(np.argmax(w))]});raise ValueError('Global preflight maximum mismatch; source/body joint must be inspected')
 u=np.clip((.9-tpos)/.2,0,1);blend=u*u*(3-2*u);g*=1+(factor-1)*blend;proposed=v.copy();proposed[:,2]*=g;newrows=measure(proposed);actual=max(q['W_cm']for q in newrows);assert abs(actual/maximum-1)<.005
 derivative=-f.derivative()(tpos)*scale/LB*(1+(factor-1)*blend)+f(tpos)*(factor-1)*np.where((tpos>.7)&(tpos<.9),-6*u*(1-u)/.2,0)*(-scale/LB);norm=n.astype(float).copy();norm[:,0]-=v[:,2]*derivative/g*n[:,2];norm[:,2]/=g;norm/=np.linalg.norm(norm,axis=1)[:,None];keep=tpos>=.9;proposed[keep]=v[keep];norm[keep]=n[keep]
 # A continuous Jacobian normal is not necessarily valid for finite triangles.
 # Enforce the actual body face hemisphere before authoring or human preview.
 triangles=body.reshape(-1,3);fn=np.cross(proposed[triangles[:,1]]-proposed[triangles[:,0]],proposed[triangles[:,2]]-proposed[triangles[:,0]]);fn/=np.maximum(np.linalg.norm(fn,axis=1)[:,None],1e-30);before_dots=(fn*norm[triangles].mean(1)).sum(1);normal_before=int((before_dots<=0).sum())
 for iteration in range(500):
  dots=(fn*norm[triangles].mean(1)).sum(1);bad=np.flatnonzero(dots<=1e-5)
  if not len(bad):break
  for fidx in bad:
   ids=triangles[fidx];delta=max(0,1e-4-float(norm[ids].mean(0)@fn[fidx]));norm[ids]+=delta*fn[fidx];norm[ids]/=np.linalg.norm(norm[ids],axis=1)[:,None]
 assert np.all((fn*norm[triangles].mean(1)).sum(1)>0),'Finite body normals still disagree with winding'
 audit={'ok':True,'species':c['species'],'samples':len(samples),'max_width_cm':maximum,'finite_normal_failures_before':normal_before,'finite_normal_failures_after':0,'gain_range':[float(g.min()),float(g.max())],'output':str(out),'dry_run':dry_run}
 if dry_run:return audit
 out.mkdir();image.save(out/'reference-marked.png');evidence={'kind':'measured_global_width_with_reference_local_ratios','species':c['species'],'inputs':c['inputs'],'finite_normal_check':audit,'supported_body_fraction':[float(tt.min()),.7],'samples':samples,'maximum_W_over_SL_scenario':ratio,'model_snout_tailbase_axis_cm':LB,'target_maximum_cm':maximum,'actual_proposed_maximum_cm':actual,'reference':c['inputs']['reference'],'reference_axis_pixels':[start,end],'source_maximum_px':wmax,'source_sections':source,'body_max_excludes_fins':True,'fin_root_trace_uncertainty_px':3,'source_scope':c['source_scope'],'limits':['Median of small preserved-specimen sample is a conditional scaling scenario, not population limits or adult allometry.','Generated reference local ratios are proposals, not real head measurements.','Model snout-to-tail-base axis is used as explicitly declared SL-like proxy; exact specimen SL endpoint correspondence is not established.','Posterior70-90% joins retained tail; fin/body full gates remain pending.'],'before':measure(v),'after':newrows,'formal_acceptance':False};ep=out/'reference.validation.json';save(ep,evidence)
 plan={'species':c['species'],'label':c['label'],'scientific_name':c['scientific_name'],'kind':'single_fish_transverse_width_trial','inputs':{k:old['inputs'][k]for k in ['model','blend','spec']},'evidence_grade':'D conditional width scenario anchored to same-species original measurements; reference shape remains provisional.','scope':'Whole anterior-body Z envelope only; preserve side XY, mouth, all parts, topology, UV/images, rig and clips.','model_scale':spec['viewer']['model_scale'],'runtime_bindings':{k:spec['motion'][k]for k in ['profile','runtime']},'display_TL_cm':L*scale,'head_focus':[float((hi-.12*L)*scale/100),0,0],'whole_width':L*scale/100*1.4,'head_width':L*scale/100*.42,'front_width':L*scale/100*.75,'motion_width':L*scale/100*1.5,'target_width_stations_cm':[[float(t*LB/(L*scale)),target(float(t))]for t in np.linspace(.01,.7,25)],'old_positions_gltf':v.tolist(),'new_positions_gltf':proposed.tolist(),'new_normals_gltf':norm.astype('float32').tolist(),'formal_acceptance':False};plan['inputs']['evidence']=ref(ep);trial=out/'trial';trial.mkdir();save(trial/'deformation.plan.json',plan);save(trial/'manifest.json',{'kind':'species_width_trial','species':c['species'],'status':'pending','next_action':'run','inputs':plan['inputs'],'formal_acceptance':False,'installed':False})
 return audit
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--config',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--dry-run',action='store_true');a=ap.parse_args();print(json.dumps(prepare(a.config,a.output,a.dry_run)))
