"""Compare actual finite caudal/body side silhouettes to the native source alpha."""
import sys,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from shapely.geometry import Polygon,LineString,MultiLineString,box,Point
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).parent/'portable'));from glb_io import read_glb,arrays,sha

def lines_without_cut(polygon,cut):
 parts=[]
 for a,b in zip(polygon.exterior.coords,list(polygon.exterior.coords)[1:]):
  if a[0]>=cut-.01 and b[0]>=cut-.01:continue
  parts.append(LineString([a,b]))
 return unary_union(parts)

def samples(lines):
 geoms=list(lines.geoms)if hasattr(lines,'geoms')else[lines]
 return [g.interpolate(i/max(1,int(np.ceil(g.length))),normalized=True)for g in geoms for i in range(max(1,int(np.ceil(g.length)))+1)]

def actual(path,source_lines):
 d,b=read_glb(path);triangles=[]
 for n in d['nodes']:
  if n.get('name')not in['Caudal','CaudalUpper','CaudalLower','Closed_body']or'mesh'not in n:continue
  for p in d['meshes'][n['mesh']]['primitives']:
   v=arrays(d,b,p['attributes']['POSITION']);q=np.column_stack([(v[:,0]+.5)*1834,309-v[:,1]*1834])
   for t in arrays(d,b,p['indices']).reshape(-1,3):
    poly=Polygon(q[t])
    if poly.area>1e-10:triangles.append(poly)
 poly=unary_union(triangles).intersection(box(-100,-100,361,800)).buffer(0)
 assert poly.geom_type=='Polygon';line=lines_without_cut(poly,361)
 a=max(p.distance(line)for p in samples(source_lines));b=max(p.distance(source_lines)for p in samples(line))
 return dict(ok=max(a,b)<=5.0,model_sha256=sha(path),source_to_actual_max_px=a,actual_to_source_max_px=b,maximum_error_px=max(a,b))

if __name__=='__main__':
 source,current,negative,out=map(Path,sys.argv[1:]);alpha=np.array(Image.open(source).convert('RGBA'))[:,:,3];mask=(alpha>128).astype('uint8');mask[:,362:]=0;contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);poly=Polygon(max(contours,key=cv2.contourArea).reshape(-1,2));lines=lines_without_cut(poly,361)
 a=actual(current,lines);b=actual(negative,lines);r=dict(ok=a['ok']and not b['ok'],kind='native_alpha_to_actual_finite_caudal_side_outline',species='blacktip_reef_shark',source_sha256=sha(source),model_sha256=sha(current),current=a,rejected_original=b,alpha_threshold=128,anterior_cut_x_px=361,tolerance_px=5.0,tolerance_basis='Native traced pixel centers simplified at4.5px plus.5px pixel-boundary allowance; frozen before current finite measurement. No fitted output target or body/fin pose registration.',method='Union actual body and complete caudal finite triangles in orthographic source coordinates. Full native source tail component; artificial anterior cut line excluded from distance sampling. Both directed distances sampled at<=1pixel along edges.',limits='Native style/source silhouette only, not biological shape or thickness evidence; static rest pose.',checker_sha256=sha(Path(__file__)));assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(r));sys.exit(0 if r['ok']else 1)
