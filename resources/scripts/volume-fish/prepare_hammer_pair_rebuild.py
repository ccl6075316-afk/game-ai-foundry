"""Species-specific source plan for two hammerheads, using accepted native art.

Own side/top contours drive geometry; the library is a declared family foil
reference only. No previous fish mesh is copied, reduced or used as a donor.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator

ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def prepare(species,out):
 short=species.split('_')[0];base=ROOT/'projects/fishing-2d/experiments/hammer-pair-rebuild-20261105'/short
 profile=ROOT/'resources/volume-fish'/f'{short}-hammerhead-121.profile.json';p=json.loads(profile.read_text());old=ROOT/'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/accepted'/species/'accepted.handoff.json';h=json.loads(old.read_text());assert not out.exists();out.mkdir()
 src=base/'sources';sources={v:src/(v+'.png')for v in ['side','top','front','bottom']}
 for v,f in sources.items():assert sha(f)==h['source'if v=='side'else v+'_source']['sha256']
 W,H=Image.open(sources['side']).size;L=p['real_length_cm']/100;rear=.235 if short=='great'else .245;neck=.87;sections=np.array(p['body']['sections']);ratio=.26 if short=='great'else .275
 # Freeze posterior body from the same accepted pixels, replacing documented
 # old root landmarks. Do not fit the wrong author cap back into the source.
 side=np.array(Image.open(sources['side']).convert('RGBA'));posterior=[]
 for u in np.linspace(rear,rear+.06,6):
  y=np.where(side[:,int(round(u*(W-1))),3]>250)[0];assert len(y)>2;posterior.append([float(u),float(y.min()/H),float(y.max()/H),float(np.interp(u,sections[:,0],sections[:,3]))])
 sections=np.array(posterior+[r.tolist()for r in sections if r[0]>rear+.06]);eye=p['eyes']['center'];headmid=eye[1];head_rows=[[.965,headmid-.018,headmid+.018,.010],[1.,headmid-.014,headmid+.014,.001]]
 all_sections=np.vstack([sections,np.array(head_rows)]);all_sections=all_sections[np.argsort(all_sections[:,0])]
 # Width not visible in side art remains the explicitly inherited own-species
 # artistic section prior. Library does not provide a biological trunk width.
 top=np.array(Image.open(sources['top']).convert('RGBA'));TW,TH=top.shape[1],top.shape[0];yy,xx=np.mgrid[:TH,:TW];u=xx/(TW-1);hw=np.interp(u,all_sections[:,0],all_sections[:,3])*TW
 # A clipped head ROI must join an equally wide neck. The old artistic width
 # prior is much narrower than this fish's own top art near the gills, leaving
 # a rectangular shoulder ledge. Measure only the fin-free anterior top zone;
 # keep posterior artistic priors and blend across .74..78, not a hard step.
 hy,hx=np.where((top[:,:,3]>250)&(xx>=neck*TW));lateral_scale=ratio/((hy.max()-hy.min())/TW)
 original=all_sections.copy();anterior=[]
 for au in sorted(set(original[:,0])|{.74,.76,.78,.8,.82,.84,.86,.87}):
  values=[float(np.interp(au,original[:,0],original[:,k]))for k in range(1,4)]
  if au>=.78 and au<=neck:
   ay=np.where(top[:,int(round(au*(TW-1))),3]>250)[0];values[2]=float((ay.max()-ay.min())/2/TW*lateral_scale)
  elif .74<au<.78:
   ay=np.where(top[:,int(round(.78*(TW-1))),3]>250)[0];target=(ay.max()-ay.min())/2/TW*lateral_scale;values[2]=float(np.interp(au,[.74,.78],[np.interp(.74,original[:,0],original[:,3]),target]))
  anterior.append([float(au),*values])
 all_sections=np.array(anterior);hw=np.interp(u,all_sections[:,0],all_sections[:,3])*TW
 # Only keep the central body footprint posterior to the head for dorsal donors.
 center=TH/2;alpha=(top[:,:,3]>250)&((u>=neck)|((u>=rear)&(np.abs(yy-center)<hw)))
 clean=top.copy();clean[:,:,3]=np.where(alpha,255,0);Image.fromarray(clean).save(out/'top-body-owned.png')
 # Fin masks/root lines are the original own-species annotations in full canvas.
 roots={f['name']:np.array(f['source_baseline'])*[W,H]for f in p['fins']};rootlist={k:v.tolist()for k,v in roots.items()}
 for name in ['FirstDorsal','SecondDorsal']:
  rootlist[name]=sorted(rootlist[name],key=lambda q:q[0],reverse=True)
 for name in ['Pectoral','Pelvic','Anal']:
  rootlist[name]=sorted(rootlist[name],key=lambda q:q[0],reverse=True)
 # Caudal retains complete own-alpha endpoints of the same posterior body plane.
 cap=posterior[0];rootlist['Caudal']=[[rear*W,cap[1]*H],[rear*W,cap[2]*H]]
 # Own frontal outer-wing alpha strips measure generated-art t/span, not tissue.
 front=np.array(Image.open(sources['front']).convert('RGBA'));fy,fx=np.where(front[:,:,3]>250);lo,hi=int(fx.min()),int(fx.max());columns=[]
 for q in np.r_[np.linspace(.06,.24,12),np.linspace(.76,.94,12)]:
  x=int(lo+q*(hi-lo));ys=np.where(front[:,x,3]>250)[0];runs=np.split(ys,np.where(np.diff(ys)>1)[0]+1);run=max(runs,key=len);columns.append(dict(x=x,top=int(run.min()),bottom=int(run.max()),ratio=float((run.max()-run.min())/(hi-lo))))
 thickness=float(np.median([r['ratio']for r in columns]));assert .015<thickness<.16
 settings={}
 for f in p['fins']:
  a,b=np.array(f['source_baseline'])*[W,H];chord=float(np.linalg.norm(a-b))*L/W
  settings[f['name']]=dict(root_full_thickness_m=chord*(.075 if f['name']=='FirstDorsal'else .065),span_levels=[0,.08,.22,.45,.68,.88,.985],chord_levels=[0,.28,.72,1],roll_degrees=32 if f['paired']else 0)
 settings['Caudal']['root_full_thickness_m']=2*posterior[0][3]*L;settings['Caudal']['chord_levels']=[0,.28,.72,1];settings['Caudal']['boundary_cdt']=True
 c=dict(species=species,scientific_name='Sphyrna mokarran'if short=='great'else'Sphyrna zygaena',art_profile=str(profile),side=str(sources['side']),clean_top=str(out/'top-body-owned.png'),front=str(sources['front']),bottom=str(sources['bottom']),display_length_m=L,body_rear_u=rear,head_neck_u=neck,body_stations=49,head_rows=41,top_alpha_threshold=250,additional_side_sections=head_rows,body_sections_override=all_sections.tolist(),body_width_basis='historical_own_profile',target_head_span_over_length=ratio,head_projected_full_thickness_over_span=thickness,head_mid_z_from_side=False,fin_roots_px=rootlist,fin_settings=settings,edge_full_thickness_m=L*.00024,future_body_baseline=str(base/'body'),native_mouth_roi_uv=([.84,.94,.30,.70]if short=='great'else[.90,.975,.35,.65]),mouth=dict(full_width_over_head_span=.18,center_front_offset_over_head_depth=.66,corner_offset_over_head_depth=.84,maximum_gap_m=L*.0016,recess_depth_m=L*.0048))
 write(out/'config.json',c);write(out/'source-and-constraints.validation.json',dict(ok=True,kind='species_owned_hammerhead_rebuild_preparation',species=species,scientific_name=c['scientific_name'],accepted_source_handoff=dict(path=str(old),sha256=sha(old)),sources={k:dict(path=str(v),sha256=sha(v))for k,v in sources.items()},display_length_m=L,head_span_over_display_length=ratio,span_basis='Great retained FAO-derived23–27%TL design26%; smooth retained own artistic27.5%, not a same-species measured mean.',front_art_thickness_samples=columns,art_thickness_over_head_span=thickness,posterior_body_source_sections=posterior,body_width_basis='Own historical posterior artistic sections. Fin-free anterior u=.78..87 measured from own top alpha with the same lateral normalization as own head; .74..78 interpolates to the prior. Generated-art correspondence, not biological width.',anterior_top_lateral_scale=float(lateral_scale),family_foil_reference='resources/fish-database/evidence/hammerhead-fin-sections-20261104/sections.json',template_policy='Reuse sparse surface, closed foil, native lip transport and actual finite cap methods. No accepted scalloped vertices/faces/UV/pixels or biological dimensions copied.',pending=['Whole source-body profile vs native side silhouette','Actual shared head/neck transition','Integrated mouth/native pixels','All8complete fins, root support, taper and tail','Source cold export,490/072/077/motion/LOD/SOP','User appearance review']))
 return c
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--species',choices=['great_hammerhead','smooth_hammerhead'],required=True);a.add_argument('--output',type=Path,required=True);n=a.parse_args();c=prepare(n.species,n.output.resolve());print(json.dumps(dict(ok=True,species=c['species'],head_t_over_span=c['head_projected_full_thickness_over_span'])))
