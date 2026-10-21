#!/usr/bin/env python3
"""Exact validation annotation only: untouched accepted source canvas + actual PL contours."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from diagnostic_spline_ram_payload_108 import build_payload
from build_stage1_cdt_candidate_108 import position_key

def main():
 root=Path(__file__).resolve().parents[3];b=root/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108';out=b/'continuous-spline-ram-grey';payload,e=build_payload();assert payload['production_solver_call_count']==0;ns=e['ns'];canvas=ns['canvas'];old=np.asarray(e['old'][0],np.float32).astype(float);cache={position_key(o):v for o,v in zip(e['raw'][0]['POSITION'],e['mapped'][0])};new=np.array([cache[position_key(o)]for o in e['old'][0]]);faces=np.array(e['actual'][0]['indices']).reshape(-1,3);stageq=canvas(e['stage'][0]);v=stageq[:,1]-(452.62-1.02*742/2024*(stageq[:,0]-1894.464));parts={'upper':faces[v[faces].max(1)<0],'lower':faces[v[faces].min(1)>0]};xs=np.arange(1900,2024.001,.25);curves={};font='/System/Library/Fonts/STHeiti Medium.ttc'
 for name,positions in [('原107',old),('本轮C2',new)]:
  for part,ff in parts.items():
   edges=positions[np.r_[ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]]];q=canvas(edges.reshape(-1,3)).reshape(-1,2,2);dx=q[:,1,0]-q[:,0,0];nonzero=dx!=0;points=[]
   for x in xs:
    t=np.zeros(len(dx));t[nonzero]=(x-q[nonzero,0,0])/dx[nonzero];on=nonzero&(t>=0)&(t<=1);ys=q[on,0,1]+t[on]*(q[on,1,1]-q[on,0,1]);vertical=(~nonzero)&(q[:,0,0]==x)
    if vertical.any():ys=np.r_[ys,q[vertical,:,1].ravel()]
    points.append([float(x),float(ys.max()if part=='upper'else ys.min())]if len(ys)else[x,None])
   curves[name+'_'+part]=points
 source=root/'projects/fish-082-zander/output/char_zander_082_nobg.png';sourceSHA=hashlib.sha256(source.read_bytes()).hexdigest();src=Image.open(source).convert('RGBA');assert src.size==(2024,742);base=Image.new('RGBA',src.size,(45,50,56,255));base.alpha_composite(src);overlay=Image.new('RGBA',src.size,(0,0,0,0));d=ImageDraw.Draw(overlay);colors={'原107':(255,70,180,240),'本轮C2':(15,240,255,240)}
 for key,points in curves.items():
  col=colors[key.split('_')[0]];run=[]
  for x,y in points:
   if y is None:
    if len(run)>1:d.line(run,fill=col,width=1)
    run=[];continue
   run.append((x,y))
  if len(run)>1:d.line(run,fill=col,width=1)
 d.rectangle((1972,350,2023,485),outline=(255,210,30,200),width=1);annotated=Image.alpha_composite(base,overlay).convert('RGB');full=Image.new('RGB',(2024,892),(26,32,36));full.paste(annotated,(0,0));draw=ImageDraw.Draw(full);f=ImageFont.truetype(font,24);draw.text((22,750),'梭鲈 Zander｜源画布2024×742未变形；actual f32有限面口缘侧投影',font=f,fill='white');draw.text((22,786),'紫：107旧上/下唇包络    青：本轮C2上/下唇包络    黄框：前口修改观察区',font=f,fill='white');draw.text((22,824),'CPU通过；视觉待审，非交付。曲线是原CPU同口径有限面投影，不是重绘源图或新解剖边。',font=f,fill='white');full.save(out/'zander-source-canvas-lip-overlay.png')
 cropbox=(1900,345,2024,490);zoom=annotated.crop(cropbox).resize((620,725),Image.Resampling.NEAREST);detail=Image.new('RGB',(920,875),(26,32,36));detail.paste(zoom,(0,105));draw=ImageDraw.Draw(detail);ff=ImageFont.truetype(font,21);draw.text((12,12),'梭鲈｜原源像素nearest ×5，只作验证标注',font=ff,fill='white');draw.text((12,43),'紫107旧｜青本轮C2｜CPU通过但视觉待审，非交付',font=ff,fill='white');draw.text((635,110),'source native',font=ff,fill='white');draw.text((635,145),'X1900..2024',font=ff,fill='white');draw.text((635,180),'Y345..490',font=ff,fill='white');draw.text((635,235),'上下唇各自包络',font=ff,fill='white');draw.text((635,280),'同画布 / 同静态姿态',font=ff,fill='white');draw.text((635,325),'源图不重绘、不变形',font=ff,fill='white');draw.text((12,840),'修改区：前上唇 / 口裂 / 下颌；材料明暗带不自动等同几何边',font=ff,fill='white');detail.save(out/'zander-source-lip-overlay-detail.png');assert hashlib.sha256(source.read_bytes()).hexdigest()==sourceSHA
 report=dict(status='source_canvas_validation_annotation_visual_pending_NOT_DELIVERY',fish='梭鲈 Zander',source=str(source),source_sha256=sourceSHA,source_size=[2024,742],source_file_unchanged=True,source_unwarped=True,detail_crop_native=cropbox,nearest_integer_zoom=5,geometry='Original actual/source and new frozenCPU exacthash positions; same existing upper/lower split, same native projection. Existing originalskin connectivity both.',projection='nativeX=(x+.5)*2024, nativeY=371-y*2024; upper=maxY and lower=minY at eachX per CPU finitePL definition; not a new anatomical boundary.',curve_samples_native_step=.25,curves=curves,production_solve_calls=0,CPU_point_hash_checks=payload['point_hash_checks'],CPU_completion_sha256=payload['CPU_completion_sha256'],factory_sha256=payload['payload_script_sha256'],annotation_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limitations=['Only orthographic native side projection; no transverse anatomy inference or visualacceptance.','Underlying source pixels copied unchanged before overlay marks; original source file remains exactSHA.','Nativecrop enlargement uses nearest, no smoothing or source image regeneration.']);(out/'source-overlay.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(sourceSHA=sourceSHA,pointchecks=payload['point_hash_checks'],solver_calls=0,files=['zander-source-canvas-lip-overlay.png','zander-source-lip-overlay-detail.png'])))
if __name__=='__main__':main()
