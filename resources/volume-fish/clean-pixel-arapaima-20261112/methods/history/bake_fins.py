"""Independent complete fin image bake after frozen body checkpoint."""
from pathlib import Path
import sys,json
import numpy as np,cv2
from PIL import Image
ROOT=Path('/Users/czl/projects/game-ai-foundry');W=ROOT/'work/arapaima-jaw-20261112';D=W/'bake-r1'
sys.path[:0]=[str(ROOT/'resources/scripts/volume-fish/portable'),str(ROOT/'resources/scripts/volume-fish'),str(ROOT/'resources/volume-fish/clean-pixel-yellow-croaker-20261111/method')]
from bake_material import read_glb,read_parts,load_image_chart,raster,Donor,columns,sha,export_image_candidate
POLYS={'Dorsal':[(265,461),(267,442),(321,383),(388,349),(445,343),(500,355),(645,367),(598,377),(434,391),(334,436)],'Anal':[(273,590),(320,597),(462,587),(640,576),(604,608),(500,642),(400,648),(320,635),(280,618)],'Caudal':[(126,487),(148,461),(166,446),(185,449),(213,476),(215,581),(195,601),(177,612),(155,603),(126,567)],'Pectoral':[(1184,573),(1143,578),(1081,605),(1079,615),(1105,623),(1142,609)],'Pelvic':[(661,574),(640,579),(603,617),(602,623),(619,624),(643,602)]}
source=D/'body/fish.glb';doc,blob=read_glb(source);parts=read_parts(doc,blob);base={i:load_image_chart(doc,blob,i) for i in range(len(doc['images']))};result={i:q.copy() for i,q in base.items()};rank={i:np.zeros(q.shape[:2],np.float32) for i,q in base.items()};concept=np.array(Image.open(W/'material-concept-r1/arapaima-gray-green-concept.png').convert('RGBA'));written=set();rows=[]
for part in parts:
 name=part['node']
 if name=='Closed_body' or name.startswith('Eye_support'):continue
 kind=next(k for k in POLYS if name.startswith(k));mask=np.zeros(concept.shape[:2],np.uint8);cv2.fillPoly(mask,[np.array(POLYS[kind],np.int32)],1);donor=Donor(concept,mask.astype(bool),1)
 pos=part['pos'];project=pos[:,[0,1]].copy();project[:,1]*=-1
 # Full two-sided membranes use their own local projection; shared left/right
 # UV charts retain the exact original alpha and finite geometry.
 lo=project.min(0);span=np.maximum(np.ptp(project,axis=0),1e-7)
 coords=(project-lo)/span*[1200,400]+2;sil=np.zeros((405,1205),np.uint8)
 for face in part['faces']:cv2.fillConvexPoly(sil,np.rint(coords[face]).astype('int32'),1)
 l,r,upper,lower=columns(sil);dl,dr,du,dd=donor.bounds;i=part['image'];h,w=rank[i].shape;count=0
 for face in part['faces']:
  pix,bary,priority=raster(part['uv'][face],w,h,2.);x,y=pix.T;keep=priority>rank[i][y,x];x,y,bary,priority=x[keep],y[keep],bary[keep],priority[keep]
  if not len(x):continue
  q=bary@coords[face];ix=np.clip(np.rint(q[:,0]).astype(int),0,len(upper)-1);u=np.clip((q[:,0]-l)/max(r-l,1),0,1);v=np.clip((q[:,1]-upper[ix])/np.maximum(lower[ix]-upper[ix],1),0,1);sx=dl+u*(dr-dl);si=np.rint(sx).astype(int);sy=du[si]+(.025+.95*v)*(dd[si]-du[si]);color=donor.sample(sx,sy);result[i][y,x,:3]=np.rint(color).astype('uint8');rank[i][y,x]=priority;count+=len(x)
 written.add(i);rows.append({'fin':name,'image':i,'samples':count,'donor_roi':POLYS[kind],'fallback_samples':donor.fallback})
out=D/'final';out.mkdir(exist_ok=True);patches={}
for i in written:
 assert np.array_equal(base[i][:,:,3],result[i][:,:,3]);p=out/f'fin-{i}.png';Image.fromarray(result[i]).save(p);patches[i]=p
for part in parts:
 if part['node']=='Closed_body' or part['node'].startswith('Eye_support'):assert part['image'] not in written
export_image_candidate(doc,blob,out/'image-candidate.glb',patches)
report={'ok':True,'stage':'fins only','body_model_sha256':sha(source),'candidate_sha256':sha(out/'image-candidate.glb'),'patches':{str(i):{'path':str(p),'sha256':sha(p)} for i,p in patches.items()},'complete_fins':rows,'body_images_untouched':[p['image'] for p in parts if p['node']=='Closed_body'],'alpha_exact':True}
(out/'fin-bake.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
