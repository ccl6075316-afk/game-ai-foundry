#!/usr/bin/env python3
"""108 readonly existing Rt derivative/source-cluster diagnosis. No curve fitting/field generation."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from numpy.polynomial import Polynomial
from scipy.interpolate import CubicHermiteSpline
from PIL import Image,ImageDraw,ImageFont
from audit_mouth_refinement_108 import load_frozen_field

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();b=a.input.resolve().parent;a.output.mkdir(parents=True,exist_ok=True);p=json.loads(a.input.read_text());r=p['upper_R_target'];rt=CubicHermiteSpline(r['X'],r['Y'],r['derivatives']);ns=load_frozen_field(Path(__file__).with_name('probe_mouth_monotone_108.py'),b/'source-mouth-alignment.validation.json');segments=[]
 for i,(aa,bb,cc,dd) in enumerate(rt.c.T):
  h=r['X'][i+1]-r['X'][i];d=Polynomial([cc,2*bb,3*aa]);d2=d.deriv();d3=d2.deriv();times=[0.,h]
  if aa!=0:
   critical=-bb/(3*aa)
   if 0<critical<h:times.append(float(critical))
  slopes=[{'X':r['X'][i]+t,'slope':float(d(t))} for t in times];eq=d3*(Polynomial([1.])+d*d)-3*d*d2*d2;curvtimes=[0.,h]+[float(z.real) for z in eq.roots() if abs(z.imag)<1e-8 and 0<z.real<h];curv=[{'X':r['X'][i]+t,'signed_curvature_per_source_pixel':float(d2(t)/(1+d(t)**2)**1.5)} for t in curvtimes];segments.append({'X_interval':[r['X'][i],r['X'][i+1]],'Y_endpoints':[r['Y'][i],r['Y'][i+1]],'slope_extrema':slopes,'slope_min':min(t['slope'] for t in slopes),'slope_max':max(t['slope'] for t in slopes),'second_derivative_endpoints':[float(d2(0)),float(d2(h))],'max_abs_curvature':max(abs(t['signed_curvature_per_source_pixel']) for t in curv),'curvature_extrema':curv})
 oldR=ns['env'][1];known=[]
 for x,y in zip([1990.5,1995.5,2000.5,2005.5,2010.5],[413,413,407,407,407]):
  value=float(oldR(x));known.append({'X':x,'manual_gold_edge_Y':y,'old_Stage1_R_frozen_PCHIP_Y':value,'signed_old_minus_gold_sourcepx':value-y,'old_Stage1_R_derivative':float(oldR.derivative()(x))})
 source=b.parent/'surface-mouth-audit-102/sources/zander/image-0.png';im=Image.open(source).convert('RGBA');rgba=np.array(im);rgbtable=[]
 for x in [1990,1995,1997,1998,1999,2000,2005,2010,2015,2019]:rgbtable.append({'x':x,'RGBA_rows_405_414':{str(y):rgba[y,x].tolist() for y in range(405,415)}})
 facts=[{'region':'1980..1997, y407..412','observation':'Visible continuous cream/gold band spansroughly6PNGrows andmanycolumns; exactRGBvariesinsideband, not6identicalcopiedrows.','geometry_inference_limit':'Band visual edge413 ismanualmateriallandmark; no proof ofhorizontal anatomicalplateau.'},{'region':'x1997..2000, y407..413','observation':'1997y408RGB229214178,1998=197181145,1999=14713199; adjacent2columnstone transition,notonecategoricalpixeljump.','geometry_inference_limit':'Exactsubpixel lipedge/aliasing model unknown; supports uncertaintyinterval forreview, not automatically6pxlegalgeometryband.'},{'region':'x2000..2010,y400..406','observation':'Goldregion occupiesmultiplePNGrows; y406then407tonechangeisrepeatableinselectedcolumns.','geometry_inference_limit':'No measuredglobalpixelclustergrid, no assertion eachPNGpixelisthegamepixel.'},{'region':'2015/2019darktip','observation':'Darkopaqueend lacks reliablebright/darkskinsemanticdivide.','geometry_inference_limit':'Unknown retained; notdelete/snapendpointfromthreshold.'}]
 roi=(1978,395,2024,431);scale=15;pw=(roi[2]-roi[0])*scale;ph=(roi[3]-roi[1])*scale;bg=Image.new('RGBA',im.size,(30,43,48,255));bg.alpha_composite(im);board=Image.new('RGB',(pw*2,ph+125),(25,35,43));font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',17);dd=ImageDraw.Draw(board)
 for j in range(2):
  panel=bg.convert('RGB').crop(roi).resize((pw,ph),Image.Resampling.NEAREST);draw=ImageDraw.Draw(panel)
  def xy(x,y):return ((x-roi[0])*scale,(y-roi[1])*scale)
  for x in range(1980,2024,5):
   xx=xy(x,0)[0];draw.line((xx,0,xx,ph),fill=(60,95,100));draw.text((xx+1,0),str(x),font=font,fill=(255,230,150))
  for y in range(395,432,5):
   yy=xy(0,y)[1];draw.line((0,yy,pw,yy),fill=(60,95,100));draw.text((1,yy+1),str(y),font=font,fill=(255,230,150))
  draw.rectangle((*xy(1997,405),*xy(2000,414)),outline=(255,230,30),width=2)
  if j==1:
   xx=np.linspace(1985.5,2019.5,500);draw.line([xy(x,float(rt(x))) for x in xx],fill=(30,255,150),width=3);draw.line([xy(x,float(oldR(x))) for x in xx],fill=(255,70,210),width=2)
   for v in known:draw.ellipse((xy(v['X'],v['manual_gold_edge_Y'])[0]-4,xy(v['X'],v['manual_gold_edge_Y'])[1]-4,xy(v['X'],v['manual_gold_edge_Y'])[0]+4,xy(v['X'],v['manual_gold_edge_Y'])[1]+4),fill=(255,230,30))
  board.paste(panel,(j*pw,35));dd.text((j*pw+8,8),'梭鲈｜原图像素簇与1998–99过渡未知区' if j==0 else '梭鲈｜绿：当前Rt；粉：旧Stage1 R；黄：语义点',font=font,fill='white')
 for k,text in enumerate(['只分析既有曲线：6px/5px下降，端导均0，峰值斜率−1.8；C1不等于曲率连续。','原图亮带是多PNG像素色簇；黄框是语义/alias不确定区，不是已批准的宽容差。','旧R对语义点偏差最大约2.72sourcepx；不自动接受3px，不忽略真实材质收束，也不排除旧CDT影响。']):dd.text((8,ph+45+k*26),text,font=font,fill='white')
 board.save(a.output/'source-cluster-current-Rt-readonly.png');docs=[Path('projects/fishing-2d/docs/3d-fish/ORAL-JAWS.md'),Path('projects/fishing-2d/docs/3d-fish/2026-10-20-MOUTH-MATERIAL-REVIEW.md')];out={'status':'readonly_existing_Rt_sourcealias_diagnosis','third_field_fitted_or_run':False,'model_or_parameters_changed':False,'existing_Rt_segments':segments,'old_Stage1_R_known_point_residuals':known,'maximum_abs_old_R_residual':max(abs(t['signed_old_minus_gold_sourcepx']) for t in known),'source_RGB_columns':rgbtable,'observable_cluster_facts':facts,'limits':['Derivative/curvature areexisting1Dtargetcurve, notnew3Dfield or finitefacetnormals.','No aliasgeneratormodel/subpixel anatomicaltruthknown; cannotdeclareall6PNGpxacceptableband.','CurrentCDFconnectivityonnewmappedpointsisbeingcheckedseparately; noonly-causeclaim.','Source3pxautomaticacceptance notauthorized; preserveactualsource-definedlip meaning.'],'dependencies_sha256':{str(k):sha(k) for k in [a.input,source,Path(__file__),*docs,b/'attempt2-cpu/completion.validation.json']}};(a.output/'lip-alias-readonly.validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'segments':[{k:s[k] for k in ['X_interval','slope_min','slope_max','second_derivative_endpoints','max_abs_curvature']} for s in segments],'residuals':known},indent=2))
if __name__=='__main__':main()
