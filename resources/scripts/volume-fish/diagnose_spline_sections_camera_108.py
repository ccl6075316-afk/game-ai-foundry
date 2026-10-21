#!/usr/bin/env python3
"""Approved bounded readonly fixed-field actual sections + old-camera scale. NO FIX."""
import json,math,hashlib
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from diagnostic_spline_ram_payload_108 import build_payload

FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def affine(t,points):a=np.asarray(t,float);return np.asarray(points)@a[:3]+a[3]
def project(camera,world):
 t=np.asarray(camera['camera_world_transform']);loc=np.linalg.solve(t[:3].T,(np.asarray(world)-t[3]).T).T;w,h=camera['render_viewport_size'];f=h/2/math.tan(math.radians(camera['camera_fov']/2));screen=np.c_[w/2+f*loc[:,0]/(-loc[:,2]),h/2-f*loc[:,1]/(-loc[:,2])];return screen,loc

def section(positions,faces,nativeX):
 xp=F(nativeX,2024)-F(1,2);x=float(xp);tri=positions[faces];selected=np.flatnonzero((tri[:,:,0].min(1)<=x)&(tri[:,:,0].max(1)>=x));segments=[]
 for faceid in selected:
  vv=[[F(float(c))for c in row]for row in tri[faceid]];points=set()
  for i,j in [(0,1),(1,2),(2,0)]:
   a,b=vv[i],vv[j];da=a[0]-xp;db=b[0]-xp
   if da==0:points.add((a[2]*2024,F(371)-a[1]*2024))
   if db==0:points.add((b[2]*2024,F(371)-b[1]*2024))
   if da*db<0:
    t=-da/(db-da);p=[a[k]+t*(b[k]-a[k])for k in range(3)];points.add((p[2]*2024,F(371)-p[1]*2024))
  pp=sorted(points)
  if len(pp)==2:segments.append(dict(face=int(faceid),vertices=faces[faceid].tolist(),ZY=[[float(z),float(y)]for z,y in pp]))
  elif len(pp)>2:
   # Truly coplanar triangle: retain all boundary edges; never discard the face.
   for i in range(len(pp)):segments.append(dict(face=int(faceid),vertices=faces[faceid].tolist(),ZY=[[float(v)for v in pp[i]],[float(v)for v in pp[(i+1)%len(pp)]]],coplanar_triangle=True))
 return segments

def hits(segments,z):
 out=[]
 for s in segments:
  (a,ya),(b,yb)=s['ZY']
  if a==b:
   if z==a:out.extend([ya,yb])
  elif min(a,b)<=z<=max(a,b):out.append(ya+(z-a)/(b-a)*(yb-ya))
 return sorted(set(out))
def extrema(segments,z):
 h=hits(segments,z);return dict(z=z,minY=min(h)if h else None,maxY=max(h)if h else None,all_Y=h)
def extent(p):return dict(min_xy=p.min(0).tolist(),max_xy=p.max(0).tolist(),extent_xy=(p.max(0)-p.min(0)).tolist())
def stats(old,new,camera,matrix):
 ow=affine(matrix,old);nw=affine(matrix,new);os,oc=project(camera,ow);ns,nc=project(camera,nw);d=np.linalg.norm(ns-os,axis=1);w,h=camera['render_viewport_size'];inside=(ns[:,0]>=0)&(ns[:,0]<=w)&(ns[:,1]>=0)&(ns[:,1]<=h)&(-nc[:,2]>=camera['camera_near']);return dict(point_count=len(old),baseline_screen_ROI=extent(os),candidate_screen_ROI=extent(ns),displacement_px=dict(min=float(d.min()),median=float(np.median(d)),p95=float(np.quantile(d,.95)),max=float(d.max()),max_index=int(d.argmax())),candidate_inside_viewport_count=int(inside.sum()),candidate_in_front_count=int((nc[:,2]<0).sum()),raw_screen_coordinates_not_visibility_or_GPU=True)

def main():
 root=Path(__file__).resolve().parents[3];b=root/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108';out=b/'continuous-spline-sections-camera-readonly';out.mkdir(exist_ok=True);payload,e=build_payload();assert payload['production_solver_call_count']==0;receiptpath=b/'attempt2-cpu/actual-camera-projection.validation.json';receipt=json.loads(receiptpath.read_text());mesh=receipt['mesh_global_transform'];bone1=receipt['skin_bind_endpoint_data'][0]['binding'][0]['skin_world_transform'];assert receipt['skin_bind_endpoint_data'][1]['binding'][0]['skin_world_transform']==bone1
 # First replay all existing camera receipts; same axes and fov formula.
 repro=[]
 for ci,c in enumerate(receipt['camera_projections']):
  for rp,cp in zip(receipt['point_pairs'],c['point_pairs']):
   for kind,rkey,wkey in [('actual','rest_actual','world_actual'),('target','rest_target_sameXZ','world_target')]:
    expected=np.array(cp[kind]['screen_subviewport']);world=np.asarray(rp[wkey]);sp,_=project(c,world[None]);mp,_=project(c,affine(mesh,np.array([rp[rkey]])));bp,_=project(c,affine(bone1,np.array([rp[rkey]])));repro.append(dict(camera_index=ci,role=rp['role'],point_kind=kind,expected_screen=expected.tolist(),world_replay_error_px=float(np.linalg.norm(sp[0]-expected)),meshrest_replay_error_px=float(np.linalg.norm(mp[0]-expected)),known_joint1_replay_error_px=float(np.linalg.norm(bp[0]-expected))))
 maxrepro=max(x['world_replay_error_px']for x in repro);assert maxrepro<.01,'Camera convention reproduction failed (sanity only, not geometry tolerance)'
 # Whole requested domain, original rest-frame X/Y; L explicitly is frozen old
 # Stage1-envelope function evaluated at ORIGINAL native X, not silently reselected.
 oldall=[];newall=[];known=[];identities=[];selections=[];ns=e['ns'];allbody=[]
 for surface in range(2):
  r=e['raw'][surface];q=ns['canvas'](r['POSITION']);allbody.append(q);L=ns['env'][2](q[:,0]);on=(q[:,0]>=1920)&(q[:,0]<=2015)&(q[:,1]>=L);ids=np.flatnonzero(on);unit1=(np.sum(np.where(r['JOINTS_0']==1,r['WEIGHTS_0'],0),axis=1)==1)&(np.sum(np.where(r['JOINTS_0']!=1,r['WEIGHTS_0'],0),axis=1)==0);selections.append(dict(surface=surface,selected_raw_attribute_count=len(ids),raw_ids=ids.tolist(),unit_joint1_attribute_count=int(unit1[ids].sum()),mixed_or_other_attribute_count=int((~unit1[ids]).sum()),used_bind_slots=sorted(set(r['JOINTS_0'][ids][r['WEIGHTS_0'][ids]>0].tolist())),baseline_body_native_XY_extent=extent(q)))
  for i in ids:oldall.append(r['POSITION'][i]);newall.append(e['mapped'][surface][i]);known.append(bool(unit1[i]));identities.append([surface,int(i)])
 oldall=np.array(oldall);newall=np.array(newall);known=np.array(known);groups={}
 for i,p in enumerate(oldall):
  key=(tuple(p),known[i])
  if key not in groups:groups[key]=i
 unique=np.array(list(groups.values()));old=oldall[unique];new=newall[unique];k=known[unique];ids=[identities[i]for i in unique];cameras=[]
 for ci,c in enumerate(receipt['camera_projections']):
  if c['view']!='front':continue
  row=dict(camera_index=ci,preset=c['preset'],viewport_case=c['viewport_case'],viewport_size=c['render_viewport_size'],mouth_pan=c['pan_to_mouth_perpendicular_only'],distance=c['distance'],matrix_source='same actual OLD baseline camera transform, no candidate bbox normalization',groups={})
  row['groups']['unit_joint1_receipt_skin_matrix']=stats(old[k],new[k],c,bone1);row['groups']['unit_joint1_receipt_skin_matrix']['scope']='Exact supplied old joint1 skin matrix applied to same rest/material points; float64 projection, no newGPU.'
  row['groups']['mixed_meshrest_affine_only']=stats(old[~k],new[~k],c,mesh);row['groups']['mixed_meshrest_affine_only']['scope']='Approximate rest-affine mathematical scale ONLY: receipt has no joint2 skin matrix. Not exact mixed skin displacement or GPU.'
  row['groups']['complete_ROI_meshrest_affine_only']=stats(old,new,c,mesh);row['groups']['complete_ROI_meshrest_affine_only']['scope']='Complete geometric selection, common old mesh-rest affine only. Its maximum is NOT claimed as all-point exact weighted skin maximum.';cameras.append(row)
 cameraout=dict(status='readonly_old_actual_baseline_camera_math_NOT_GPU_or_acceptance',CPU_completion_sha256=payload['CPU_completion_sha256'],camera_receipt=str(receiptpath),camera_receipt_sha256=sha(receiptpath),axis_convention='Transform arrays are basis columns+origin; world=rest@basis_columns+origin; camera inverse then verticalfov42 perspective h/(2tan21deg); default viewport378h,720h is old formula upper-response case, not actual host720 screenshot.',reproduction=dict(all_existing_pairs=repro,max_known_world_camera_error_px=maxrepro,max_meshrest_error_px=max(x['meshrest_replay_error_px']for x in repro),max_known_joint1_error_px=max(x['known_joint1_replay_error_px']for x in repro),sanity_threshold_px=.01,threshold_not_geometry_tolerance=True),selection=dict(definition='Original raw native X inclusive[1920,2015] and original raw nativeY>= frozen original Stage1 lower-envelope L(originalrawX). Never changed selection after projection; complete skin+oral selected and bindings disclosed.',coordinate_caveat='Frozen L lives in Stage1 chart; this requested original-frame evaluation is explicit. No assertion that it is a measured anatomical ROI. All baseline body ranges preserved below.',per_surface=selections,total_attribute_points=len(oldall),canonical_physical_plus_binding_points=len(old),unique_unit_joint1=int(k.sum()),unique_mixed_or_other=int((~k).sum()),canonical_point_representatives_raw_surface_id=ids),cameras=cameras,mesh_global_transform=mesh,known_joint1_world_transform=bone1,limits=['No new model import/GPU/normal/UV/runtime/boundsnormalize or real screenshot claim.','Unit-joint1 subset and mixed restaffine group never conflated.','Restpose math only, not continuous animation/skinning acceptance; section shapes independent of this pixel-scale calculation.','Screenextent may include off-viewport points and mathematical unoccluded surfaces; visibility cannot be inferred.']);(out/'camera-scale.validation.json').write_text(json.dumps(cameraout,indent=2)+'\n')
 # Full actual triangles, both skin and oral. Baseline oral is original GLB;
 # candidate oral97 connection inherited from the already approved CPU.
 sectionrows=[]
 for X in [1920,1950,1980,1995,2005,2015]:
  row=dict(native_X=X,models={})
  for model,positions,faces in [('baseline',[r['POSITION']for r in e['raw']],e['rawfaces']),('current',[np.array(s['POSITION'])for s in payload['surfaces']],[np.array(s['indices']).reshape(-1,3)for s in payload['surfaces']])]:
   row['models'][model]={}
   for surface in range(2):
    seg=section(positions[surface],faces[surface],X);profiles=[extrema(seg,z)for z in [-10,-5,0,5,10]];centre=next(x for x in profiles if x['z']==0);sides=[x['maxY']for x in profiles if abs(x['z'])==5 and x['maxY']is not None];ridge=centre['maxY']-sum(sides)/len(sides)if len(sides)==2 and centre['maxY']is not None else None;row['models'][model][['skin','oral'][surface]]=dict(segments=seg,profiles=profiles,centre_lower_minus_mean_side_Z5_native_px=ridge,note='Profile sampleZ=0,+/-5,+/-10 is engineering localization only, no calibrated biological width.')
  sectionrows.append(row)
 # Common equal native Y/Z scale across all six panels, no per-panel stretch.
 allp=[p for r in sectionrows for m in r['models'].values()for s in m.values()for seg in s['segments']for p in seg['ZY']];a=np.array(allp);zmax=max(10,math.ceil(abs(a[:,0]).max()/10)*10);ymin=math.floor(a[:,1].min()/10)*10;ymax=math.ceil(a[:,1].max()/10)*10;W,H=1500,1280;image=Image.new('RGB',(W,H),(28,34,39));d=ImageDraw.Draw(image);font=ImageFont.truetype(FONT,21);d.text((18,12),'梭鲈 Zander｜真实三角平面交线｜统一 native单位 Y向下 / 横轴Z×2024｜只读、非交付',font=font,fill='white');colors={('baseline','skin'):(255,90,190),('baseline','oral'):(255,170,70),('current','skin'):(0,235,255),('current','oral'):(110,240,100)}
 for i,row in enumerate(sectionrows):
  col=i%3;rr=i//3;left=col*500+45;top=rr*570+90;pw,ph=410,490;scl=min(pw/(2*zmax),ph/(ymax-ymin));cx=left+pw/2;py=lambda y:top+(y-ymin)*scl;px=lambda z:cx+z*scl;d.text((left,top-35),f"nativeX={row['native_X']}",font=font,fill='white')
  for yy in range(ymin,ymax+1,20):d.line((px(-zmax),py(yy),px(zmax),py(yy)),fill=(55,61,65));d.text((left-38,py(yy)-8),str(yy),font=ImageFont.truetype(FONT,15),fill=(200,200,200))
  d.line((px(0),py(ymin),px(0),py(ymax)),fill=(130,130,130))
  for model in ['baseline','current']:
   for surface in ['skin','oral']:
    for seg in row['models'][model][surface]['segments']:d.line([(px(z),py(y))for z,y in seg['ZY']],fill=colors[model,surface],width=2 if model=='current'else 1)
  for z in range(-zmax,zmax+1,10):d.text((px(z)-10,py(ymax)+4),str(z),font=ImageFont.truetype(FONT,15),fill=(220,220,220))
 d.text((20,1230),'紫=原外皮 橙=原口内  青=本轮外皮 绿=本轮口内；截面不是生物宽度测量，禁止据此补新几何',font=font,fill='white');image.save(out/'zander-six-sections-equal-scale.png')
 # Project fixed section midline role points too; these are same-plane geometric
 # correspondences, not material-ID correspondences and use old mesh-rest affine.
 sectionprojections=[]
 for row in sectionrows:
  for role in ['minY','maxY']:
   oldp=row['models']['baseline']['skin']['profiles'][2][role];newp=row['models']['current']['skin']['profiles'][2][role]
   if oldp is None or newp is None:continue
   op=np.array([[row['native_X']/2024-.5,(371-oldp)/2024,0.]]);npnt=np.array([[row['native_X']/2024-.5,(371-newp)/2024,0.]])
   for ci,c in enumerate(receipt['camera_projections']):
    if c['view']=='front':sectionprojections.append(dict(native_X=row['native_X'],role='skin_upper_centre'if role=='minY'else'skin_lower_centre',baseline_native_Y=oldp,current_native_Y=newp,camera_index=ci,viewport=c['render_viewport_size'],preset=c['preset'],math_meshrest_only=stats(op,npnt,c,mesh)))
 (out/'sections.validation.json').write_text(json.dumps(dict(status='readonly_full_triangle_sections_NOT_fix_or_biological_width',CPU_completion_sha256=payload['CPU_completion_sha256'],CPU_f32_hash_checks=payload['point_hash_checks'],planes=[1920,1950,1980,1995,2005,2015],intersection='Exact Fraction of input actualfloat32 vertices and planeX=nativeX/2024-.5, all intersecting triangles; no epsilon, nearest or newgeometry.',plot_axes=dict(horizontal='Z*2024',vertical='371-Y*2024 increasing down',equal_native_scale=True,common_Z_bounds=[-zmax,zmax],common_Y_bounds=[ymin,ymax]),sections=sectionrows,section_midline_old_camera_projections=sectionprojections,limitations=['Midline min/max are geometric role correspondence, not same material IDs. Projected with actual old meshrest affine; not full weighted GPU.','All oral/skin triangle plane intersections retained; different originaloral vs approvedoral97 reported, no badpieces omitted.','No calibrated species transverse width or acceptance; no newfield/solver/normal/UV/lighting/model or fourthattempt.']),indent=2)+'\n')
 print(json.dumps(dict(replay_max_world_px=maxrepro,geometry_attributes=len(oldall),unique_points=len(old),unit_joint1=int(k.sum()),mixed=int((~k).sum()),sections=[dict(X=r['native_X'],baseline_lower_centre_vs_Z5=r['models']['baseline']['skin']['centre_lower_minus_mean_side_Z5_native_px'],current_lower_centre_vs_Z5=r['models']['current']['skin']['centre_lower_minus_mean_side_Z5_native_px'])for r in sectionrows],camera_rows=[dict(preset=c['preset'],h=c['viewport_size'][1],pan=c['mouth_pan'],joint1_max_px=c['groups']['unit_joint1_receipt_skin_matrix']['displacement_px']['max'])for c in cameras])))
if __name__=='__main__':main()
