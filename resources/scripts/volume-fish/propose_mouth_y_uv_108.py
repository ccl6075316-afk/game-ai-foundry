#!/usr/bin/env python3
"""108Phase2d one CPU Y/UV proposal. Never writes model/UV/runtime assets."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from PIL import Image,ImageDraw,ImageFont
from probe_mouth_slit_stage1_108 import field,canvas,gate

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def envelope(v,faces,queries):
 lines=np.concatenate([v[faces[:,[0,1]]],v[faces[:,[1,2]]],v[faces[:,[2,0]]]]);q=canvas(lines.reshape(-1,3)).reshape(-1,2,2);valid=(q[:,:,0].max(1)>=1860)&(q[:,:,0].min(1)<=2019.5);q=q[valid];x0=q[:,0,0];dx=q[:,1,0]-x0;dy=q[:,1,1]-q[:,0,1];good=abs(dx)>1e-12;lo=[];hi=[]
 for start in range(0,len(queries),64):
  X=queries[start:start+64,None];t=np.divide(X-x0,dx,out=np.zeros((len(X),len(dx))),where=good);inside=good&(t>=-1e-12)&(t<=1+1e-12);Y=q[:,0,1]+t*dy;mn=np.where(inside,Y,np.inf).min(1);mx=np.where(inside,Y,-np.inf).max(1)
  for k,x in enumerate(X[:,0]):
   vertical=(~good)&(abs(x-x0)<1e-9)
   if vertical.any():mn[k]=min(mn[k],q[vertical,:,1].min());mx[k]=max(mx[k],q[vertical,:,1].max())
  lo.extend(mn);hi.extend(mx)
 return np.array(lo),np.array(hi)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parent;alignment=json.loads(a.input.read_text());paths=[b.parent/'eye-rollout-107/zander-mesh-rest.json',b/'zander-oral-rest.json'];data=[json.loads(p.read_text()) for p in paths];old=[np.array(d['rest_xyz']) for d in data];stage=[]
 for v in old:
  xy=canvas(v);mp,_=field(xy);out=v.copy();active=xy[:,0]>1988;out[active,0]=mp[active,0]/2024-.5;out[active,1]=(371-mp[active,1])/2024;stage.append(out)
 qs=[canvas(v) for v in stage];queries=np.unique(np.r_[*[q[q[:,0]>=1860,0] for q in qs],np.arange(1860.5,2019.5,.5),2019.5]);queries=queries[queries<=2019.5];skinfaces=np.array(data[0]['indices']).reshape(-1,3);sq=qs[0];sv=sq[:,1]-(452.62-1.02*742/2024*(sq[:,0]-1894.464));upper=skinfaces[sv[skinfaces].max(1)<0];lower=skinfaces[sv[skinfaces].max(1)>0];U,R=envelope(stage[0],upper,queries);L,B=envelope(stage[0],lower,queries)
 # Source cell-boundary rows. Lastuppercap is one representative role, not two competing targets.
 top=[[1920.5,349],[1940.5,356],[1960.5,365],[1980.5,376],[1995.5,381],[2005.5,385],[2010.5,391],[2015.5,395],[2018.5,397],[2019.5,401.5]]
 bottom=[[1860.5,499],[1870.5,494],[1894.5,487],[1900.5,487],[1906.5,484],[1920.5,480],[1940.5,475],[1960.5,467],[1980.5,458],[1995.5,452],[2005.5,448],[2010.5,443],[2015.5,438],[2019.5,436]]
 roof=[[2002.5,416],[2005.5,413],[2010.5,412],[2015.5,408],[2018.5,406],[2019.5,401.5]];lip=[[2002.5,418],[2005.5,419],[2010.5,419],[2015.5,423],[2018.5,425],[2019.5,425]]
 sourcecurves=[PchipInterpolator(*np.array(p).T,extrapolate=True) for p in [top,bottom,roof,lip]];protect=json.loads((b/'eye-protection-proposal.validation.json').read_text());maxEyeX=protect['front_x_gate_source_canvas_start']-2;maxEyeY=371-(-.0409841351211071)*2024;params={'status':'phase2d_first_cpu_proposal','accepted':False,'asset_written':False,'source_top_boundary_knots':top,'source_chin_boundary_knots':bottom,'source_front_roof_boundary_knots':roof,'source_front_lip_boundary_knots':lip,'source_pixel_centers':'nativeX,column+.5; Youter/lipcellboundaries. Endpointupper2019.5 iscollapsed401.5 only, not397/406 simultaneously.','upper_onset_x':[maxEyeX+2,1940.5],'front_lip_onset_x':[2000.5,2002.5],'chin_onset_x':[1860,1870.5],'chin_anchor_margin_pixels':2,'eye_max_canvas':[maxEyeX,maxEyeY],'eye_anchor_fade_x':[maxEyeX,maxEyeX+2],'stage1_and_upper97_cdt':'unchanged','interpolation':'PCHIP sparse source targets; actualenvelopesfromskintriangleedgeXplanes, tabulatedatallactualinputX+nativehalfgrid; PLbetweenmeasuredX. Noepsilonspanclamp.','UV':'CPUonly: source-opaque-center branchcoordinates, boundaryinwardhalf-pixel, blendedatlocalchartonsets; exacteyeUVpreserved. NoPNG/UVassetwrite.','input_hashes':{str(p):sha(p) for p in paths},'stage1_probe_sha256':sha(Path(__file__).with_name('probe_mouth_slit_stage1_108.py')),'probe_sha256':sha(Path(__file__))};a.output.mkdir(parents=True,exist_ok=True);frozen=a.output/'y-uv-proposal-frozen.validation.json';frozen.write_text(json.dumps(params,indent=2)+'\n')
 def table(c,x):return np.interp(x,queries,c)
 def change(q):
  X,Y=q.T;u=table(U,X);r=table(R,X);l=table(L,X);bb=table(B,X);V=Y-(452.62-1.02*742/2024*(X-1894.464));up=V<0;on=X>1860;h,_=gate(X,maxEyeX+2,1940.5);front,_=gate(X,2000.5,2002.5);post,_=gate(X,1860,1870.5);fade,_=gate(X,maxEyeX,maxEyeX+2);floor=457.174-1.02*742/2024*(X-1894.464);anchor=floor+2+np.maximum(maxEyeY+2-(floor+2),0)*(1-fade);srcU,srcB,srcR,srcL=[f(X) for f in sourcecurves];ut=u+h*(srcU-u);rt=r+front*(srcR-r);span=r-u;collapsed=(X==2019.5)&up;badup=up&on&(~collapsed)&((span<=0)|((rt-ut)<=0));badchin=(~up)&on&(front<1)&((bb-anchor)<=0)&(post>0);badlower=(~up)&on&(front>0)&(((bb-l)<=0)|((srcB-srcL)<=0))
  if badup.any() or badchin.any() or badlower.any():return None,{'bad_upper':np.flatnonzero(badup).tolist()[:16],'bad_chin':np.flatnonzero(badchin).tolist()[:16],'bad_lower':np.flatnonzero(badlower).tolist()[:16]},None
  out=q.copy();t=np.zeros(len(X));g=np.zeros(len(X));uvweight=np.zeros(len(X));desired=q.copy();use=up&on&(~collapsed);t[use]=(Y[use]-u[use])/span[use];out[use,1]=ut[use]+t[use]*(rt[use]-ut[use]);uvweight[use]=1-(1-h[use]*np.clip(1-t[use],0,1))*(1-front[use]);desired[use,1]=out[use,1]+.5-np.clip(t[use],0,1);out[collapsed,1]=401.5;uvweight[collapsed]=1;desired[collapsed,1]=401.5
  low=(~up)&on;validchin=low&(front<1);g[validchin]=gate(Y[validchin],anchor[validchin],bb[validchin])[0];chinY=Y+post*(srcB-bb)*g;affine=Y.copy();affine[low]=srcL[low]+(Y[low]-l[low])/(bb[low]-l[low])*(srcB[low]-srcL[low]);out[low,1]=(1-front[low])*chinY[low]+front[low]*affine[low];uvweight[low]=np.maximum(front[low],post[low]*g[low]);ratio=np.zeros(len(X));ratio[low]=(Y[low]-l[low])/(bb[low]-l[low]);desired[low,1]=out[low,1]+front[low]*(.5-np.clip(ratio[low],0,1))-(1-front[low])*.5*g[low];out[up&(h==0)&(front==0)]=q[up&(h==0)&(front==0)];return out,{'minimum_upper_oldspan':float(span[use].min()) if use.any() else None,'minimum_upper_targetspan':float((rt-ut)[use].min()) if use.any() else None,'minimum_lower_oldspan':float((bb-l)[low].min()) if low.any() else None,'minimum_chin_span_used':float((bb-anchor)[validchin].min()) if validchin.any() else None},(uvweight,desired)
 proposed=[];stats=[];uvstats=[];failed=[]
 for index,(q,d,v) in enumerate(zip(qs,data,stage)):
  mp,check,uv=change(q);stats.append(check)
  if mp is None:failed.append(index);proposed.append(v);continue
  out=v.copy();changed=mp[:,1]!=q[:,1];out[changed,1]=(371-mp[changed,1])/2024;proposed.append(out)
  if index==0:
   originalUV=np.array(d['source_uv'])*[2024,742];transported=originalUV+(mp-canvas(old[index]));weight,desired=uv;uvnew=transported+weight[:,None]*(desired-transported);eye=np.array(protect['surfaces'][index]['frozen_vertex_ids']);uvnew[eye]=originalUV[eye];uvstats.append({'skin_uv_in_memory_only':True,'max_delta_native_pixels':float(np.linalg.norm(uvnew-originalUV,axis=1).max()),'eye_uv_exact':bool(np.array_equal(uvnew[eye],originalUV[eye])),'skin_uv_written':False})
 # Sharedactualpoint equality, protectedX/Z and sparsechinwidth table.
 checks=[]
 for index,(v,out) in enumerate(zip(stage,proposed)):
  ids=np.array(protect['surfaces'][index]['frozen_vertex_ids']);checks.append({'surface':index,'protected_positions_exact':bool(np.array_equal(v[ids],out[ids])),'X_Z_unchanged':bool(np.array_equal(v[:,[0,2]],out[:,[0,2]]))})
 table_rows=[]
 for x in [1894.5,1900.5,1920.5,1940.5,1960.5,1980.5,2005.5,2010.5,2015.5,2019.5]:
  bb=table(B,np.array([x]))[0];ll=table(L,np.array([x]))[0];points=np.array([[x,ll],[x,bb]]);mapped,c,_=change(points);table_rows.append({'X':x,'old_stage1_lip_chin':[float(ll),float(bb)],'proposed_lip_chin':mapped[:,1].tolist() if mapped is not None else None,'source_chin_boundary':float(sourcecurves[1](x))})
 report={'status':'phase2d_cpu_proposal_only','accepted':False,'frozen_sha256':sha(frozen),'ordered_spans_failed_surfaces':failed,'span_checks':stats,'preservation_checks':checks,'uv_in_memory':uvstats,'chin_samples':table_rows,'scope':'CPUproposalonly; notPhase3/noFold/GPU/wholemouthaccepted. NoGLB/UV/runtimewritten.','limits':['Uppercollapsedpoint401.5 remainscaprepresentative. Lastnativecellboundaryerror mustbevisualized, notstrict9pxcapgeometry.','Onlyactualskinbranchused; loweroralrimdisappearanceusesactualskinlowerenvelope.','NoNORMALassetwritten; protectednormal/UVremainoriginal. CompleteanalyticJacobian/finiteactualtrianglesneedsindependentreview/Phase3.']};(a.output/'y-uv-proposal.validation.json').write_text(json.dumps(report,indent=2)+'\n')
 # Same-source canvas outlines: source, Stage1 geometry, proposedCPU geometry. Clip everypanel.
 src=Image.open(b.parent/'surface-mouth-audit-102/sources/zander/image-0.png').convert('RGBA');base=Image.new('RGBA',src.size,(30,43,48,255));base.alpha_composite(src);roi=(1850,315,2024,510);z=3;pw=(roi[2]-roi[0])*z;ph=(roi[3]-roi[1])*z;panels=[]
 for label,vtx in [('源图',None),('Stage1：只齐前尖',stage[0]),('Phase2d CPU提案（未安装）',proposed[0])]:
  im=base.convert('RGB').crop(roi).resize((pw,ph),Image.Resampling.NEAREST);draw=ImageDraw.Draw(im)
  if vtx is not None:
   qq=canvas(vtx)
   for branch in [upper,lower]:
    Xs=np.linspace(1860,2019.5,320);mn,mx=envelope(vtx,branch,Xs)
    for yy,color in [(mn,(255,70,210)),(mx,(0,255,120))]:
     valid=np.isfinite(yy);draw.line([((x-roi[0])*z,(y-roi[1])*z) for x,y in zip(Xs[valid],yy[valid])],fill=color,width=2)
  panels.append((label,im))
 board=Image.new('RGB',(pw*3,ph+90),(24,34,42));draw=ImageDraw.Draw(board);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',19)
 for i,(label,im) in enumerate(panels):board.paste(im,(pw*i,40));draw.text((pw*i+8,10),label,font=font,fill='white')
 draw.text((10,ph+52),'梭鲈｜同一源图坐标，粉：每支上缘；绿：每支下缘。轮廓/UV仅CPU提案，非资产验收。',font=font,fill='white');board.save(a.output/'source-y-uv-proposal.png');print(json.dumps({'span_failed_surfaces':failed,'span_checks':stats,'chin_samples':table_rows},indent=2))
if __name__=='__main__':main()
