"""Freeze this shark's complete source basal curves and sparse foil controls.

Requires Shapely for the two-dimensional source/body contour intersection.
All thickness and paired-fin dihedral choices are engineering candidates.
"""
import json,hashlib,sys
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,Point,LineString
ROOT=Path(__file__).resolve().parents[3]
def main():
 settings=json.loads((ROOT/sys.argv[1]).read_text(encoding='utf-8-sig'));p=json.loads((ROOT/settings['source_profile']).read_text());s=np.array(p['body']['sections']);body=Polygon(np.r_[s[:,:2],s[::-1][:,[0,2]]]);rows=[]
 for f in p['fins']:
  poly=Polygon(f['polygon']);paired=f['paired'];kind=f['name']
  if paired:
   ids=[9,10,0] if kind=='Pectoral' else[6,7,8,0];root=LineString([f['polygon'][i]for i in ids]);q=poly
  else:q=poly.difference(body);assert q.geom_type=='Polygon',kind;root=body.boundary
  contour=np.array(q.exterior.coords[:-1]);isroot=[root.distance(Point(v))<1e-7 for v in contour];assert sum(isroot)>=2,kind
  seeds=[]
  for v in np.linspace(contour[:,1].min(),contour[:,1].max(),6)[1:-1]:
   cross=q.intersection(LineString([[-1,v],[2,v]]))
   if cross.is_empty:continue
   if cross.geom_type=='MultiLineString':cross=max(cross.geoms,key=lambda g:g.length)
   for t in [.30,.65]:
    point=cross.interpolate(t,normalized=True)
    if q.contains(point)and root.distance(point)>.002:seeds.append(list(point.coords[0]))
  rows.append(dict(name=kind,paired=paired,contour=contour.tolist(),root=isroot,seeds=seeds,source=f,vertical_scale=.76 if kind=='SecondDorsal' else .38 if kind=='Pectoral' else .65 if kind=='Pelvic' else 1.,thickness_ratio=.14 if kind=='Pectoral' else .12 if kind=='CaudalUpper' else .10,maximum_half_thickness=.008 if kind=='Pectoral' else .006 if kind=='CaudalUpper' else .005,edge_half_thickness=.00035))
 out=ROOT/sys.argv[2];assert not out.exists();out.write_text(json.dumps(dict(kind='blacktip_source_fin_cages',rows=rows,scope='Complete original source basal interfaces; median source/body contour intersection, paired native full root curve. Geometry controls are engineering choices, not measured thickness.'),indent=2)+'\n');print(str(out))
if __name__=='__main__':main()
