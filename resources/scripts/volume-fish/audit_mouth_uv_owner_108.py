#!/usr/bin/env python3
"""108 CPU-only local UV/source ownership proposal; never writes UV or color assets."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from audit_mouth_refinement_108 import load_frozen_field

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parents[1];a.output.mkdir(parents=True,exist_ok=True);ns=load_frozen_field(Path(__file__).with_name('probe_mouth_monotone_108.py'),b/'source-mouth-alignment.validation.json');v=ns['st'][0];data=ns['data'][0];canvas=ns['canvas'];q=canvas(v);newq,dy,(w,desired)=ns['evaluate'](q,True);oldUV=np.array(data['source_uv'])*[2024,742];proposalUV=oldUV+w[:,None]*(desired-oldUV);skin=np.array(data['indices']).reshape(-1,3);inp=json.loads((b/'upper-skin-cdt-input-proposal.validation.json').read_text());cdt=json.loads(a.input.read_text());keep=np.ones(len(skin),bool);news=[]
 for sh,res in zip(inp['sheets'],cdt['sheets']):keep[sh['old_skin_triangle_ids']]=False;news.append(np.array([p['actual_vertex_id'] for p in sh['points']])[np.array(res['input_origin_faces'])])
 f=np.r_[skin[keep],*news];changed=np.any(proposalUV!=oldUV,axis=1);selected=f[changed[f].any(1)];weights=np.array([[1,0,0],[0,1,0],[0,0,1],[1/3]*3,[.5,.5,0],[0,.5,.5],[.5,0,.5]]);sample=np.einsum('sc,ncd->nsd',weights,proposalUV[selected]).reshape(-1,2);sampleold=np.einsum('sc,ncd->nsd',weights,oldUV[selected]).reshape(-1,2);sampleq=np.einsum('sc,ncd->nsd',weights,newq[selected]).reshape(-1,2);xyz=np.einsum('sc,ncd->nsd',weights,v[selected]).reshape(-1,3);source=b.parent/'surface-mouth-audit-102/sources/zander/image-0.png';im=Image.open(source).convert('RGBA');rgba=np.array(im);fallback=Path('projects/fish-107-zander-eye/game/assets/models/fish/motion/opaque-skin/fd2d0c154c140aca906201fcd7c7f80e043221827f4c97a14b714e24fa825b67.png');fb=np.array(Image.open(fallback).convert('RGBA'));pixels=np.floor(sample).astype(int);pixels[:,0]=np.clip(pixels[:,0],0,2023);pixels[:,1]=np.clip(pixels[:,1],0,741);color=rgba[pixels[:,1],pixels[:,0]];fbc=fb[pixels[:,1],pixels[:,0]];missing=color[:,3]<243;alpha=color[:,3:4]/255;effective=np.rint(color[:,:3]*alpha+fbc[:,:3]*(1-alpha)).astype(np.uint8);dark=(effective.max(1)<128);records=[];counts=Counter();outer={}
 for x in sorted(set(pixels[:,0])):
  ys=np.flatnonzero(rgba[280:550,x,3]>=243)+280;outer[x]=(int(ys[0]),int(ys[-1])) if len(ys) else None
 for j in np.flatnonzero(missing):
  x,y=map(int,pixels[j]);extent=outer[x];owner='unknown_internal_alpha'
  if extent is None:owner='outside_source_head'
  elif y<extent[0]:owner='above_source_outer_silhouette'
  elif y>extent[1]:owner='below_source_outer_silhouette'
  elif x>=2002:
   # Only identify a proven gap between disjoint accepted-source opaque runs.
   yy=np.flatnonzero(rgba[280:550,x,3]>=243)+280;groups=np.split(yy,np.flatnonzero(np.diff(yy)>1)+1)
   if any(groups[k][-1]<y<groups[k+1][0] for k in range(len(groups)-1)):owner='source_front_actual_alpha_gap'
  counts[owner]+=1;records.append({'sample_id':int(j),'proposedUV_native':sample[j].tolist(),'source_pixel':[x,y],'final_geometric_canvas':sampleq[j].tolist(),'stage1_rest_Z':float(xyz[j,2]),'sourceRGBA':color[j].tolist(),'fallbackRGBA':fbc[j].tolist(),'owner':owner})
 # Explicit candidate donor rectangles only; no palette extraction or generated pixels.
 donors=[{'id':'lower_jaw_cream_candidate','rect_xyxy':[1928,445,1940,456],'use':'only proposed new central chin exterior, not lateral lip/actual source dark tip'}, {'id':'upper_snout_gold_candidate','rect_xyxy':[1968,384,1980,392],'use':'only proposed new central upper exterior, not dorsal wholebody'}]
 for donor in donors:
  x0,y0,x1,y1=donor['rect_xyxy'];cc=rgba[y0:y1,x0:x1];donor['all_alpha255']=bool((cc[:,:,3]==255).all());donor['RGB_min']=cc[:,:,:3].reshape(-1,3).min(0).tolist();donor['RGB_max']=cc[:,:,:3].reshape(-1,3).max(0).tolist();donor['sample_native_center']=[(x0+x1)//2,(y0+y1)//2];donor['RGB_center']=rgba[(y0+y1)//2,(x0+x1)//2,:3].tolist();donor['review_status']='unapproved_visual_candidate_not_installed'
 known=['source_front_actual_alpha_gap'];ey=np.array(ns['eye']['surfaces'][0]['frozen_vertex_ids']);affected=np.flatnonzero(changed);roi=(1780,330,2024,530);scale=4;pw=(roi[2]-roi[0])*scale;ph=(roi[3]-roi[1])*scale;bg=Image.new('RGBA',im.size,(29,41,47,255));bg.alpha_composite(im);board=Image.new('RGB',(pw*2,ph+100),(25,35,43));font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',18);dd=ImageDraw.Draw(board);palette={'below_source_outer_silhouette':(255,70,170),'above_source_outer_silhouette':(255,160,30),'source_front_actual_alpha_gap':(50,220,255),'unknown_internal_alpha':(255,240,50),'outside_source_head':(200,60,255)}
 for k in range(2):
  panel=bg.convert('RGB').crop(roi).resize((pw,ph),Image.Resampling.NEAREST);draw=ImageDraw.Draw(panel)
  if k==0:
   for d in donors:
    x0,y0,x1,y1=d['rect_xyxy'];draw.rectangle(((x0-roi[0])*scale,(y0-roi[1])*scale,(x1-roi[0])*scale,(y1-roi[1])*scale),outline=(40,255,70),width=2)
  else:
   for r in records:
    x,y=r['proposedUV_native'];cx=(x-roi[0])*scale;cy=(y-roi[1])*scale;draw.ellipse((cx-2,cy-2,cx+2,cy+2),fill=palette[r['owner']])
  board.paste(panel,(k*pw,38));dd.text((k*pw+8,8),'梭鲈｜原图与待审供体框' if k==0 else '梭鲈｜UV透明采样归属（未改材质）',font=font,fill='white')
 dd.text((8,ph+46),'粉：下轮廓外；橙：上轮廓外；蓝：真实前口隙；黄：内部未知。源图暗唇/斑纹不自动删除。',font=font,fill='white');dd.text((8,ph+72),'绿框只是待审局部供体，未批准改色；本图不证明几何或shader验收。',font=font,fill='white');board.save(a.output/'source-owner-proposal.png')
 report={'status':'readonly_CPU_UV_owner_proposal','accepted':False,'UV_color_assets_written':False,'selected_changed_faces':len(selected),'samples_per_face':7,'sample_count':len(sample),'alpha_lt243':int(missing.sum()),'effective_RGBmax_lt128':int(dark.sum()),'alpha_missing_owner_counts':dict(counts),'source_alpha_missing_samples':records,'dark_diagnostic_not_removal_mask':{'count':int(dark.sum()),'note':'RGB threshold only counts; true lateral lip/source tip/organic marks must not be recolored from this count'},'UV_support':{'changed_vertex_count':len(affected),'changed_original_stage1_canvas_bbox':[q[affected].min(0).tolist(),q[affected].max(0).tolist()],'eye_UV_exact':bool(np.array_equal(proposalUV[ey],oldUV[ey])),'vertices_outside_analytic_weight_support_exact':bool(np.array_equal(proposalUV[w==0],oldUV[w==0])),'original_source_PNG_unchanged':True,'wholebody_palette_rebake':False},'candidate_donors':donors,'limits':['7 barycentric samples per actual final triangle, not all face interiors/GPU formalshader output.','Source/fallback CPU only;107 independent eye/head shader branches not modified.','Opaque donor is necessary not sufficient: actual lateral lip and outline ownership needs visual approval.','275 was previous topology 7point count, not retained as immutable expected count afterCDT.'],'inputs_sha256':{str(p):sha(p) for p in [a.input,Path(__file__),source,fallback,b/'upper-skin-cdt-input-proposal.validation.json',Path(__file__).with_name('probe_mouth_monotone_108.py')]}};(a.output/'uv-owner-proposal.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['selected_changed_faces','sample_count','alpha_lt243','alpha_missing_owner_counts','UV_support','candidate_donors']},indent=2))
if __name__=='__main__':main()
