#!/usr/bin/env python3
"""108 read-only Phase1 anchor/complete-eye footprint/rim diagnosis; no correction or assets."""
import argparse,json,hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from audit_mouth_refinement_108 import load_frozen_field

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def polyclip(poly,axis,value,keepgreater):
 out=[]
 if not len(poly):return np.empty((0,np.asarray(poly).shape[-1] if np.asarray(poly).ndim==2 else 3))
 for aa,bb in zip(poly,np.roll(poly,-1,axis=0)):
  da=(aa[axis]-value)*(1 if keepgreater else -1);db=(bb[axis]-value)*(1 if keepgreater else -1);ia=da>=0;ib=db>=0
  if ia!=ib:out.append(aa+(bb-aa)*da/(da-db))
  if ib:out.append(bb)
 return np.array(out)
def area(poly):return abs(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1)))/2 if len(poly)>=3 else 0

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parent;a.output.mkdir(parents=True,exist_ok=True);ns=load_frozen_field(Path(__file__).with_name('probe_mouth_monotone_108.py'),a.input);v=ns['old'][0];st=ns['st'][0];q=ns['canvas'](st);f=np.array(ns['data'][0]['indices']).reshape(-1,3);eyeX=ns['eyeX'];eyeY=ns['eyeY'];ev=ns['evaluate'];records=[]
 for x in [1918.,1919.,1920.,eyeX,1920.5,1921.,1921.5,1922.,eyeX+2,1922.5,1923.,1924.]:
  U,R,L,B=[float(c(x)) for c in ns['env']];fade=1-ns['gate'](np.array([x]),eyeX,eyeX+2)[0][0];floor=457.174-1.02*742/2024*(x-1894.464);a0=floor+2;b0=a0+fade*(eyeY+2-a0);anchor=float(np.logaddexp(a0,b0));ys=np.array([anchor,(anchor+B)/2,B]);qq=np.c_[np.full(3,x),ys];new,dy,_=ev(qq);eps=1e-4;dx=(ev(qq+[eps,0])[0][:,1]-ev(qq-[eps,0])[0][:,1])/(2*eps);records.append({'X':x,'old_actual_bottom_B':B,'target_chin':float(ns['chin'](x)),'old_floor':floor,'eye_fade':float(fade),'anchor':anchor,'remaining_source_span_B_minus_anchor':B-anchor,'samples':[{'oldY':float(y),'newY':float(y1),'dYdY':float(j),'dYdX_FD':float(jx)} for y,y1,j,jx in zip(ys,new[:,1],dy,dx)]})
 near=(q[:,0]>=1918)&(q[:,0]<=1924)&(q[:,1]>445);ids=np.flatnonzero(near);new,dy,_=ev(q[ids]);eps=1e-4;dx=(ev(q[ids]+[eps,0])[0][:,1]-ev(q[ids]-[eps,0])[0][:,1])/(2*eps);ranking=sorted(range(len(ids)),key=lambda i:abs(dx[i]),reverse=True);actual=[{'actual_vertex_id':int(ids[i]),'stage1_nativeXY':q[ids[i]].tolist(),'mapped_nativeXY':new[i].tolist(),'Z_rest':float(st[ids[i],2]),'dYdY':float(dy[i]),'dYdX_FD':float(dx[i])} for i in ranking[:24]]
 # Complete current107 eye layer pixel cells, projected exactly as the shader (no pupil-only proxy).
 eyeprofile=Path('projects/fish-107-zander-eye/game/assets/models/fish/motion/eye-107/eye-ownership-107.json');profile=json.loads(eyeprofile.read_text())['profiles']['zander'];proj=profile['projection'];maskpath=eyeprofile.parent/'eye-layer-mask.png';sourcepath=eyeprofile.parent/'source-runtime.png';mask=np.array(Image.open(maskpath).convert('RGBA'))[:,:,0]>=128;src=np.array(Image.open(sourcepath).convert('RGBA'));mask&=src[:,:,3]>0;yy,xx=np.nonzero(mask);anchor=np.array(proj['anchor_rest_xy']);pixel=np.array(proj['pixel_native_xy']);pupil=np.array(proj['source_pupil_px']);anchor[1]-=proj['downshift_native_pixels']*pixel[1];gap=proj['central_gap_abs_z'];runs=[]
 for y in sorted(set(yy)):
  xs=np.flatnonzero(mask[y]);groups=np.split(xs,np.flatnonzero(np.diff(xs)>1)+1)
  for group in groups:runs.append((int(group[0]),int(group[-1])+1,int(y),int(y)+1))
 def source_xy(poly):return pupil+np.c_[(poly[:,0]-anchor[0])/pixel[0],-(poly[:,1]-anchor[1])/pixel[1]]
 # Exact union-of-pixelcell rectangles intersects clipped actual rest triangles; no raster center shortcuts.
 supports=[]
 for label,sign in [('left',1),('right',-1)]:
  tri_ids=[];clippedcount=0
  for tid,face in enumerate(f):
   tri=v[face].copy();tri[:,2]*=sign
   if tri[:,2].max()<=gap:continue
   p=polyclip(tri,2,gap,True)
   if len(p)<3:continue
   xy=source_xy(p);xmin,ymin=xy.min(0);xmax,ymax=xy.max(0)
   if xmax<xx.min() or xmin>xx.max()+1 or ymax<yy.min() or ymin>yy.max()+1:continue
   for x0,x1,y0,y1 in runs:
    if xmax<x0 or xmin>x1 or ymax<y0 or ymin>y1:continue
    clipped=xy.copy()
    for ax,val,greater in [(0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)]:
     if not len(clipped):break
     clipped=polyclip(clipped,ax,val,greater)
    if area(clipped)>0:tri_ids.append(tid);break
  vertices=set(map(int,np.unique(f[tri_ids])));poskeys={tuple(v[i]) for i in vertices};duplicateids={i for i,p in enumerate(v) if tuple(p) in poskeys};normalfaces=np.flatnonzero(np.isin(f,list(duplicateids)).any(1));ring=set(map(int,np.unique(f[normalfaces])));oldprotect=set(ns['eye']['surfaces'][0]['frozen_vertex_ids']);native=ns['canvas'](v);supports.append({'side':label,'feature_triangles':tri_ids,'feature_triangle_count':len(tri_ids),'feature_vertices':sorted(vertices),'feature_vertex_count':len(vertices),'exact_position_and_original_normal_attribute_support_vertices':sorted(duplicateids),'normal_support_count':len(duplicateids),'conservative_normal_incident_faces':normalfaces.tolist(),'conservative_normal_incident_vertices':sorted(ring),'conservative_normal_incident_vertex_count':len(ring),'feature_support_native_bbox':[native[list(duplicateids)].min(0).tolist(),native[list(duplicateids)].max(0).tolist()],'normal_incident_geometry_native_bbox':[native[list(ring)].min(0).tolist(),native[list(ring)].max(0).tolist()],'old659_intersection_count':len(oldprotect&duplicateids),'old659_extra_over_direct_feature_count':len(oldprotect-duplicateids),'feature_outside_old659_count':len(duplicateids-oldprotect),'scope':'direct triangles preserve full fragment rest+normal interpolation; incident ring is separate conservative geometry dependency if normals recomputed, not automatically required UV region'})
 source=b.parent/'surface-mouth-audit-102/sources/zander/image-0.png';im=Image.open(source).convert('RGBA');bg=Image.new('RGBA',im.size,(30,43,48,255));bg.alpha_composite(im);roi=(1880,380,2024,490);scale=6;pw=(roi[2]-roi[0])*scale;ph=(roi[3]-roi[1])*scale;board=Image.new('RGB',(pw*2,ph+100),(25,35,43));font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',18);draw=ImageDraw.Draw(board);alignment=ns['alignment'];rim=np.array([p for e in alignment['actual_interface'] for p in e['rest_xyz']]);oldrim=ns['canvas'](rim);stageR=ns['stage1'](oldrim)[0];newrim=ev(stageR)[0]
 for panelid in range(2):
  panel=bg.convert('RGB').crop(roi).resize((pw,ph),Image.Resampling.NEAREST);dd=ImageDraw.Draw(panel)
  for x in range(1880,2025,10):
   cx=(x-roi[0])*scale;dd.line((cx,0,cx,ph),fill=(65,100,105),width=1);dd.text((cx+2,0),str(x),font=font,fill=(255,230,150))
  for y in range(380,491,10):
   cy=(y-roi[1])*scale;dd.line((0,cy,pw,cy),fill=(65,100,105),width=1);dd.text((1,cy+2),str(y),font=font,fill=(255,230,150))
  coords=oldrim if panelid==0 else newrim
  for e in range(len(coords)//2):
   line=coords[e*2:e*2+2];xmean=line[:,0].mean();vmean=(oldrim[e*2:e*2+2,1]-(452.62-1.02*742/2024*(oldrim[e*2:e*2+2,0]-1894.464))).mean();color=(255,70,200) if vmean<0 else (50,220,255);dd.line([((x-roi[0])*scale,(y-roi[1])*scale) for x,y in line],fill=color,width=2)
  board.paste(panel,(panelid*pw,38));draw.text((panelid*pw+8,8),'梭鲈｜源图+原实际口缘' if panelid==0 else '梭鲈｜源图+fullY口缘（已视觉拒绝）',font=font,fill='white')
 draw.text((8,ph+46),'native XY同画布；粉：原upper分支口缘；蓝：原lower分支口缘。两暗band含义仍需目视辨认。',font=font,fill='white');draw.text((8,ph+72),'未知后唇冻结与2000.5→2002.5过渡均原样记录，不靠dark阈值切口；未改几何/UV。',font=font,fill='white');board.save(a.output/'native-mouth-grid-old-fullY-rim.png')
 eyeunion=set(k for s in supports for k in s['exact_position_and_original_normal_attribute_support_vertices']);oldset=set(ns['eye']['surfaces'][0]['frozen_vertex_ids']);report={'status':'read_only_after_visual_rejection_phase1','fix_executed':False,'UV_assets_written':False,'field_changed':False,'chin_anchor_rows':records,'actual_fold_vertex_samples':actual,'eye_complete_mask':{'mask_pixels':int(mask.sum()),'source_mask_bbox_xyxy':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'native_downshift':proj['downshift_native_pixels'],'z_owner_nonzero_gap':gap,'rectangle_run_count':len(runs),'projection':proj,'side_supports':supports,'union_feature_vertex_count':len(eyeunion),'old659_extra_over_union_feature_count':len(oldset-eyeunion),'feature_outside_old659_count':len(eyeunion-oldset),'old659_native_bbox':[ns['canvas'](v)[list(oldset)].min(0).tolist(),ns['canvas'](v)[list(oldset)].max(0).tolist()],'limits':'full6039 pixelcell footprint with sourcealpha and owner clip; current actual base mesh only, oldLOD5 remains failed; this is evidence not permission to shrink protection. Oral surface1 has no independenteye material, its shared geometry coupling still needs review.'},'rim':{'original397_interface_edges':len(oldrim)//2,'unknown_rear_cutoff':2000.5,'front_blend':[2000.5,2002.5],'native_old_actual_rim':oldrim.tolist(),'native_stage1_rim':stageR.tolist(),'native_rejected_fullY_rim':newrim.tolist(),'semantic_unknown':'Originalsource two darkbands may include maxillaryplate boundary and true slit; do not automatically cut all darkpixels.'},'dependencies_sha256':{str(p):sha(p) for p in [a.input,Path(__file__),Path(__file__).with_name('probe_mouth_monotone_108.py'),eyeprofile,maskpath,sourcepath,source]}};(a.output/'readonly-failure-diagnosis.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'chin':records,'actual_fold_top3':actual[:3],'eye':[{'side':s['side'],'tri':s['feature_triangle_count'],'verts':s['feature_vertex_count'],'bbox':s['feature_support_native_bbox'],'normal_incident_bbox':s['normal_incident_geometry_native_bbox']} for s in supports],'union':len(eyeunion),'old659extra':len(oldset-eyeunion),'outsideold':len(eyeunion-oldset)},indent=2))
if __name__=='__main__':main()
