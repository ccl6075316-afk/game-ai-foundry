"""Measure actual A projected mouth gap, not an invented slit-width preset."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
repo=Path(__file__).resolve().parents[3];trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial';out=trial/'round6-reference-repair';out.mkdir(exist_ok=True)
records={}
for route,folder in [('A','round4-ab-textured'),('B4','round4-ab-textured'),('B5','round5-user-review-fixes')]:
 source=trial/folder/('A-artifacts' if route=='A' else 'B-artifacts')/'fish.blend'
 if route=='B5' and not source.exists():continue # Rejected binaries are intentionally cleaned; A is the required reference.
 bpy.ops.wm.open_mainfile(filepath=str(source))
 body=next(ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.name.startswith('Closed_body'))
 vs=[v.co.copy() for v in body.data.vertices];fs=[list(f.vertices) for f in body.data.polygons];bvh=BVHTree.FromPolygons(vs,fs)
 samples=[]
 for u in sorted(set([.938,.94,.941,.942,.943,.944,.945,.95,.955,.96,.965,.97,.975,.98,.982,.985,.987,.989,.99,.9905,.991,.9915,.9925,.995,max(v.x for v in vs)+.5-.0001])):
  x=u-.5;line=(.5-(.552+(.502-.552)*(u-.95)/.045))*972/1961;step=.00015
  values=[]
  for j in range(-1000,1001):
   z=line+j*step;hit,_,_,_=bvh.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2);values.append(hit is not None)
  ranges=[];start=None
  for j,inside in enumerate(values+[False]):
   if inside and start is None:start=j
   if not inside and start is not None:ranges.append([line+(start-1000)*step,line+(j-1-1000)*step]);start=None
  internal=[]
  for a,b in zip(ranges,ranges[1:]):
   if a[1]<line+.02 and b[0]>line-.02:internal.append([a[1],b[0]])
  gap=min(internal,key=lambda r:abs(sum(r)/2-line)) if internal else None
  depths=[]
  for face in fs:
   for ia,ib in zip(face,face[1:]+face[:1]):
    a,b=vs[ia],vs[ib]
    if min(a.x,b.x)<=x<=max(a.x,b.x) and abs(a.x-b.x)>1e-10:
     t=(x-a.x)/(b.x-a.x);depths.append(a.y+(b.y-a.y)*t)
  samples.append({'u':u,'occupied_z_ranges':ranges,'mouth_gap_lower_upper_z':gap,'max_abs_depth':max(map(abs,depths)) if depths else None})
 records[route]={'max_u':max(v.x for v in vs)+.5,'samples':samples}
(out/'A-mouth-reference.validation.json').write_text(json.dumps({'kind':'actual_A_mouth_reference','method':'Actual saved rest mesh; side-projection rays at0.00015 native Z steps; gaps between projected lower/upper jaw occupied intervals, not a material darkness mask.','samples':records},indent=2),encoding='utf8')
print(json.dumps(records))
