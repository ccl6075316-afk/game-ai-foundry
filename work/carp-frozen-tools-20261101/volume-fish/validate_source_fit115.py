"""Frozen same-X envelope, complete confirmed lip/UV and emitted float32 surface gate."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from measure_lip_binding115 import measure
from freeze_surface_ownership import read_glb,accessor
from validate_oral_cdt_108 import crossing

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def section(xyz,x):
 result=[]
 for i,j in [(0,1),(1,2),(2,0)]:
  a=xyz[:,i];b=xyz[:,j];hit=((a[:,0]<=x)&(b[:,0]>=x)|(b[:,0]<=x)&(a[:,0]>=x))&(abs(a[:,0]-b[:,0])>1e-12);a=a[hit];b=b[hit];t=(x-a[:,0])/(b[:,0]-a[:,0]);result.extend(a+t[:,None]*(b-a))
 p=np.asarray(result);assert len(p)>2;return [float(p[:,1].max()),float(p[:,1].min()),float(abs(p[:,2]).max())]
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--confirmed',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_text());confirmed=json.loads(a.confirmed.read_text());rows=[]
 for item in plan['items']:
  sp=item['species'];line=next(x['lower_lip_source_px'] for x in confirmed['items'] if x['species']==sp);r=measure(Path(item['target']),Path(item['source_image']),line);w,h=r['source_size'];curve=PchipInterpolator(np.array(line)[:,0],np.array(line)[:,1],extrapolate=False)
  errors=[];path=np.asarray(r['ordered_lower_boundary_native']);covered=[]
  for x,y in zip(path,path[1:]):
   n=max(2,int(np.linalg.norm((y-x)[:2])*w*4)+1)
   for t in np.linspace(0,1,n):
    q=x*(1-t)+y*t;xx=(q[0]+.5)*w
    if line[0][0]-1e-5<=xx<=line[-1][0]+1e-5:
     xx=float(np.clip(xx,line[0][0],line[-1][0]));errors.append(abs(h*.5-q[1]*w-float(curve(xx))));covered.append(xx)
  doc,blob=read_glb(Path(item['target']));node=next(n for n in doc['nodes'] if n.get('name')=='Closed_body');pr=doc['meshes'][node['mesh']]['primitives'];parts=[{k:accessor(doc,blob,v).astype(float) for k,v in x['attributes'].items()} for x in pr];faces=[accessor(doc,blob,x['indices']).reshape(-1,3) for x in pr];v=np.concatenate([q['POSITION'] for q in parts]);f=np.concatenate([faces[0],faces[1]+len(parts[0]['POSITION'])]);xyz=v[f]
  envelope=[]
  for u,top,bottom,width in item['frozen_outer_sections115']:
   actual=section(xyz,u-.5);err=(np.array(actual)-[top,bottom,width])*w;envelope.append({'u':u,'errors_native_px':err.tolist()})
  cross=crossing(v,f,v[:,0]>=item['join_u']-.5-1e-7)
  uv_error=max(np.linalg.norm(np.array(uv)-row['screen_native_px']) for row in r['physical_lower_rim'] for uv in row['actual_skin_uv_px'])
  donors=[];image=np.asarray(Image.open(item['source_image']).convert('RGBA'))
  for kind,rect in item['front_cap_native_rects'].items():
   x,y,z,t=rect;q=image[y:t,x:z];uv=parts[0]['TEXCOORD_0']*[w,h];inside=((uv>=np.array([x,y])+.499)&(uv<=np.array([z,t])-.499)).all(1);cap=(parts[0]['POSITION'][faces[0],0].min(1)>.5*(item['end_u']+item['end_u'])-.5-1e-6)&inside[faces[0]].all(1)
   donors.append({'kind':kind,'rect':rect,'opaque':bool(q[:,:,3].min()==255),'known_outline_pixels':int((q[:,:,:3].max(2)<100).sum()),'interior_cap_triangles':int(cap.sum()),'decoded_rgba_sha256':hashlib.sha256(q.tobytes()).hexdigest()})
  maximum=max(max(abs(x) for x in row['errors_native_px']) for row in envelope);maximum_lip=max(errors);limits=plan['frozen_validation_limits115']
  ok=bool(maximum<=limits['same_x_outer_envelope_max_native_px'] and maximum_lip<=limits['whole_confirmed_lower_line_max_native_px'] and uv_error<.001 and cross['proper_crossings']==cross['coplanar_positive_area_overlap_pairs']==0 and all(x['opaque'] and x['known_outline_pixels']==0 and x['interior_cap_triangles']>10 for x in donors))
  rows.append({'species':sp,'ok':ok,'model_sha256':sha(item['target']),'complete_lower_curve_max_error_native_px':maximum_lip,'complete_lower_curve_samples':len(errors),'actual_lateral_rim_uv_vs_physical_max_native_px':float(uv_error),'same_x_envelope_max_error_native_px':maximum,'envelope':envelope,'float32_crossing':cross,'native_cap_donors':donors,'limits':limits});print(sp,ok,'lip',maximum_lip,'uv',uv_error,'envelope',maximum,'cross',cross['proper_crossings'],cross['coplanar_positive_area_overlap_pairs'],flush=True)
 ok=all(x['ok'] for x in rows);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({'ok':ok,'status':'done' if ok else 'failed','next_action':'human_review' if ok else 'fix_input','items':rows,'plan_sha256':sha(a.plan),'checker_sha256':sha(__file__),'crossing_checker_sha256':sha(Path(__file__).with_name('validate_oral_cdt_108.py')),'limits':'Emitted float32 base meshes and frozen source canvas only; actual import/LOD, GPU donors, multi-view art, fin roots/full membranes and continuous time remain separate.'},indent=2)+'\n');return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
