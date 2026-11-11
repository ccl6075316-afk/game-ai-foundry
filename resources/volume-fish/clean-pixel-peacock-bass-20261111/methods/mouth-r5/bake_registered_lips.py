from pathlib import Path
import sys,numpy as np
from PIL import Image
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W))
from bake import *
from bake_mouth import pose,project
out=Path(sys.argv[1]);out.mkdir(exist_ok=True)
model=out.parent/'fish.glb';d,b=read_glb(model);rows=list(parts(d,b));name,idx,f,tri=next(p for p in rows if p[0]==('Closed_body',0));node=next(n for n in d['nodes'] if n.get('name')=='Closed_body' and 'mesh' in n);prim=d['meshes'][node['mesh']]['primitives'][0];f=f|{'POSITION':pose(d,b,prim,f)}
orig=png(d,b,idx);dest=orig.copy();source=rgba(W/'body-side-v1.png')
# Independently registered real upper and lower edge stations, in actual18deg
# review pixels. Posterior opaque maxillary fold is a separate coordinate zone.
upper=np.array([[602,409],[620,405],[650,394],[680,378],[710,366],[740,358],[782,339],[805,335]])
lower=np.array([[602,418],[620,426],[650,439],[680,448],[710,452],[740,454],[780,460],[805,465]])
supper=np.array([[1310,548],[1320,542],[1340,531],[1360,519],[1380,507],[1387,504]])
slower=np.array([[1310,551],[1320,551],[1340,550],[1360,548],[1380,546],[1387,545]])
knots=np.array([[350,1180],[440,1220],[602,1310],[650,1330],[782,1380],[805,1387]])
def sample(p,n,x,y):
 tx,ty=project(p,True).T;u=np.interp(tx,knots[:,0],knots[:,1]);v=.5*ty+345
 top=np.interp(tx,upper[:,0],upper[:,1]);bot=np.interp(tx,lower[:,0],lower[:,1]);dt=np.interp(u,supper[:,0],supper[:,1]);db=np.interp(u,slower[:,0],slower[:,1]);isupper=ty<(top+bot)/2
 aligned=np.where(isupper,dt+.5*(ty-top),db+.5*(ty-bot));fac=smooth((tx-565)/60);v=v*(1-fac)+aligned*fac
 uu=np.clip(np.rint(u).astype(int),0,source.shape[1]-1);vv=np.clip(np.rint(v).astype(int),0,source.shape[0]-1);rgb=source[vv,uu,:3].astype(float)
 # Side owns maxillary relief and lateral lips; existing front center remains
 # independently authored. Never assign source background to exterior tissue.
 skin=(source[vv,uu,0]>source[vv,uu,2]+30)
 weight=smooth((tx-370)/55)*smooth((ty-280)/45)*(1-smooth((ty-535)/50))*smooth((np.abs(p[:,2])-.008)/.018)
 weight*=skin
 return orig[y,x,:3]*(1-weight[:,None])+rgb*weight[:,None]
raster(dest,f,tri,sample)
path=out/'mouth-exterior.png';Image.fromarray(dest).save(path)
oral=next(p for p in rows if p[0]==('Closed_body',1));oralidx=oral[1]
front=Image.open(W/'mouth-r3/front-donor.png').convert('RGBA');cavity=front.crop((627,564,883,720));cavity.save(out/'mouth-interior.png')
replace_images(d,b,{idx:path,oralidx:out/'mouth-interior.png'},out/'fish.glb')
save(out/'bake.validation.json',{'ok':True,'kind':'independent_maxillary_upper_lower_lip_registration','model_sha256':sha(model),'source_side':{'path':str(W/'body-side-v1.png'),'sha256':sha(W/'body-side-v1.png')},'source_oral':{'path':str(W/'mouth-r3/front-donor.png'),'sha256':sha(W/'mouth-r3/front-donor.png'),'crop':[627,564,883,720]},'images':{str(idx):{'path':str(path.resolve()),'sha256':sha(path)},str(oralidx):{'path':str((out/'mouth-interior.png').resolve()),'sha256':sha(out/'mouth-interior.png')}},'upper_target':upper.tolist(),'lower_target':lower.tolist(),'upper_source':supper.tolist(),'lower_source':slower.tolist(),'changed_exterior_rgb_texels':int(np.any(orig[:,:,:3]!=dest[:,:,:3],axis=2).sum()),'exterior_alpha_unchanged':bool(np.array_equal(orig[:,:,3],dest[:,:,3])),'geometry_unchanged':True,'status':'local_textured_candidate_for_operator_review'})
