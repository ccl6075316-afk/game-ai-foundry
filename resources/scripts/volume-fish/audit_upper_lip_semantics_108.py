#!/usr/bin/env python3
"""108 manual upper lip material-boundary evidence; no threshold cut or shape output."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parents[1];a.output.mkdir(parents=True,exist_ok=True);diag=json.loads(a.input.read_text());source=b.parent/'surface-mouth-audit-102/sources/zander/image-0.png';im=Image.open(source).convert('RGBA');rgba=np.array(im)
 # Manually curated visual candidate from requested column comparisons. Not a threshold-derived slit.
 candidate=[{'span':[[1980.5,413],[1997.5,413]],'status':'visible_cream_lower_edge_candidate','evidence':'rows412cream then413dark transition at1980/1985/1990/1995/1997'}, {'span':[[1997.5,413],[2000.5,407]],'status':'transition_1998_1999_uncertain_dashed','evidence':'1998mixedgold/cream;1999hasbrown below406, exact semantic joining unknown'}, {'span':[[2000.5,407],[2010.5,407]],'status':'visible_gold_lower_edge_candidate','evidence':'row406gold then407darker at2000/2005/2010'}];columns=[];alpha_line=[]
 for x in [1980,1985,1990,1995,1997,1998,1999,2000,2002,2005,2010,2015,2019]:
  ys=np.flatnonzero(rgba[350:500,x,3]>=243)+350;runs=np.split(ys,np.flatnonzero(np.diff(ys)>1)+1);runranges=[[int(g[0]),int(g[-1])+1] for g in runs];alpha_edge=int(runs[0][-1])+1 if len(runs)>1 else None;edge=413 if x<=1997 else 407 if 2000<=x<=2010 else None;rows=range(405,417) if edge==407 else range(410,416) if edge==413 else range(402,417);columns.append({'source_column_x':x,'candidate_gold_cream_lower_edge_y':edge,'candidate_is_cell_boundary_not_new_vertex':True,'alpha_upper_run_end_y':alpha_edge,'opaque_runs_y0_y1_exclusive':runranges,'RGBA_rows':{str(y):rgba[y,x].tolist() for y in rows},'semantic_status':'dark_tip_unknown' if x>=2015 else 'transition_unknown' if x in [1998,1999] else 'manual_visual_candidate_not_approved_cut'})
 for x in range(2002,2020):
  ys=np.flatnonzero(rgba[350:500,x,3]>=243)+350;runs=np.split(ys,np.flatnonzero(np.diff(ys)>1)+1)
  if len(runs)>1:alpha_line.append([x+.5,int(runs[0][-1])+1])
 roi=(1978,395,2024,431);scale=14;pw=(roi[2]-roi[0])*scale;ph=(roi[3]-roi[1])*scale;bg=Image.new('RGBA',im.size,(30,43,48,255));bg.alpha_composite(im);board=Image.new('RGB',(pw*2,ph+245),(25,35,43));font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',16);titlefont=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',18);draw=ImageDraw.Draw(board)
 def pos(p):return ((p[0]-roi[0])*scale,(p[1]-roi[1])*scale)
 for panelid in range(2):
  panel=bg.convert('RGB').crop(roi).resize((pw,ph),Image.Resampling.NEAREST);dd=ImageDraw.Draw(panel)
  for x in range(1980,2024,5):
   px=(x-roi[0])*scale;dd.line((px,0,px,ph),fill=(70,100,105),width=1);dd.text((px+1,0),str(x),font=font,fill=(255,235,160))
  for y in range(395,432,5):
   py=(y-roi[1])*scale;dd.line((0,py,pw,py),fill=(70,100,105),width=1);dd.text((1,py+1),str(y),font=font,fill=(255,235,160))
  if panelid==1:
   old=np.array(diag['rim']['native_old_actual_rim']);new=np.array(diag['rim']['native_rejected_fullY_rim'])
   for name,arr,color in [('old',old,(255,70,200)),('new',new,(255,75,65))]:
    for e in range(len(arr)//2):
     i=e*2;origin=old[i:i+2];vmean=(origin[:,1]-(452.62-1.02*742/2024*(origin[:,0]-1894.464))).mean()
     if vmean<0:dd.line([pos(p) for p in arr[i:i+2]],fill=color,width=4 if name=='old' else 2)
  dd.line([pos(p) for p in alpha_line],fill=(40,220,255),width=3)
  for line in candidate:
   aa,bb=map(np.array,line['span'])
   if line['status'].endswith('_dashed'):
    for lo in np.arange(0,1,.18):dd.line([pos(aa+(bb-aa)*lo),pos(aa+(bb-aa)*min(1,lo+.09))],fill=(255,230,30),width=3)
   else:dd.line([pos(aa),pos(bb)],fill=(255,230,30),width=3)
  for x in [2015.5,2019.5]:dd.text(pos([x,400]),'?',font=titlefont,fill=(255,230,30))
  board.paste(panel,(panelid*pw,38));draw.text((panelid*pw+8,8),'梭鲈｜材质候选边 ≠ alpha边' if panelid==0 else '梭鲈｜另叠旧/被拒fullY实体口缘',font=titlefont,fill='white')
 lines=['黄：金白亮带下缘候选；虚线：1998–1999语义连接未知；?：暗端2015/2019未知。','青：source alpha上run末边（仅真实分离列）；粉：原实体upper；红：被拒fullY upper。','1990: y412=[215,210,192] → y413=[110,108,97]；1995同类亮→暗。','2000: y406=[207,196,144] → y407=[153,140,102]（后续棕暗带仍opaque）。','2005: y406=[199,189,147] → y407=[106,100,85]；407–412暗带；alpha到413才断。','2010: y406=[156,146,114] → y407=[89,83,72]；alpha到412才断。','结论只支持重审“暗带全是实体外唇”的假设；不阈值挖嘴、不删暗端、不新建shape。']
 for j,line in enumerate(lines):draw.text((8,ph+48+j*26),line,font=font,fill='white')
 board.save(a.output/'gold-lip-alpha-entity-native-grid.png');report={'status':'manual_material_semantic_readonly','accepted':False,'shape_or_field_changed':False,'UV_or_color_assets_written':False,'manual_candidate_segments':candidate,'unknown_endpoints':[{'X':2015,'reason':'entire visible tip dark, no justified bright-to-dark boundary'},{'X':2019,'reason':'tip wholly dark, alphaedge405/406 does not by itself identify skin vslip/outline'}],'columns':columns,'alpha_boundary_role':'opaque pixelrun only, not biological skin/material boundary','interpretation':'At2005candidate gold edge407 versus alphaedge413 leaves6nativepixels ofopaque darkband. Treating all asadded exterior can create shieldlike downward material extension; this is evidence for review not an approved geometry target.','no_threshold_cut':True,'dependencies_sha256':{str(p):sha(p) for p in [a.input,source,Path(__file__)]}};(a.output/'gold-lip-semantic.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'candidate_segments':candidate,'columns':[{k:c[k] for k in ['source_column_x','candidate_gold_cream_lower_edge_y','alpha_upper_run_end_y','semantic_status']} for c in columns]},indent=2))
if __name__=='__main__':main()
