"""Blender-only single-fin candidates; never writes the installed fish.

Run with Blender -b --factory-startup --python this_file -- <trial-root> <a|b>.
"""
import bpy,bmesh,json,hashlib,sys,time,math
from pathlib import Path
from collections import defaultdict,Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE=Path(sys.argv[sys.argv.index('--')+1]).resolve()
ROUTE=sys.argv[sys.argv.index('--')+2]
assert BASE.name=='nile-dorsal-route-trial' and ROUTE in ['a','b']
P=json.loads((BASE/'trial-profile.json').read_text())
SOURCE=Path(P['source_blend'])
if not SOURCE.is_file():
 SOURCE=Path(__file__).resolve().parents[3]/'projects/fishing-2d/experiments/nile-tilapia-static-merge/nile_tilapia-static.blend'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==P['source_sha256']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def digest(obj):
 m=obj.data
 return hashlib.sha256(repr(([tuple(v.co) for v in m.vertices],[tuple(p.vertices) for p in m.polygons],
  [tuple(x.uv) for x in m.uv_layers.active.data] if m.uv_layers.active else [],
  [[(g.group,g.weight) for g in v.groups] for v in m.vertices])).encode()).hexdigest()

def get_source(obj):
 m=obj.data;by_vertex=defaultdict(set)
 for loop in m.loops:by_vertex[loop.vertex_index].add(tuple(round(x,7) for x in m.uv_layers.active.data[loop.index].uv))
 groups=defaultdict(list)
 for v in m.vertices:
  assert len(by_vertex[v.index])==1
  groups[next(iter(by_vertex[v.index]))].append(v.index)
 points=[];uvs=[];weights=[];normals=[];mapping={}
 for uv,ids in groups.items():
  assert len(ids)==2
  a,z=sorted((m.vertices[i] for i in ids),key=lambda v:v.co.y)
  for i in ids:mapping[i]=len(points)
  points.append((a.co+z.co)/2);uvs.append(uv);normals.append((z.co-a.co).normalized())
  weights.append({obj.vertex_groups[g.group].name:g.weight for g in a.groups if g.weight>0})
 triangles=set()
 for polygon in m.polygons:
  tri=tuple(mapping[i] for i in polygon.vertices)
  if len(set(tri))==3:triangles.add(tuple(sorted(tri)))
 triangles=list(triangles)
 # Geometry is parameterized by its physical XZ projection. Texture UV can
 # carry source-color transport and must not be mistaken for the physical domain.
 parameter_uvs=[(p.x,p.z*1961/972) for p in points]
 uv_tree=BVHTree.FromPolygons([Vector((u*1961,v*972,0)) for u,v in parameter_uvs],triangles,all_triangles=True)
 return {'points':points,'uvs':uvs,'parameter_uvs':parameter_uvs,'weights':weights,'normals':normals,'triangles':triangles,'uv_tree':uv_tree,
  'old_points':[v.co.copy() for v in m.vertices],'old_faces':[tuple(p.vertices) for p in m.polygons],
  'material':m.materials[0],'groups':[g.name for g in obj.vertex_groups]}

def sample(source,uv):
 hit,_,fi,distance=source['uv_tree'].find_nearest(Vector((uv[0]*1961,uv[1]*972,0)))
 assert fi is not None
 ids=source['triangles'][fi];a,b,c=[Vector((source['parameter_uvs'][i][0]*1961,source['parameter_uvs'][i][1]*972)) for i in ids]
 q=Vector((hit.x,hit.y));den=(b.y-c.y)*(a.x-c.x)+(c.x-b.x)*(a.y-c.y)
 assert abs(den)>1e-10
 wa=((b.y-c.y)*(q.x-c.x)+(c.x-b.x)*(q.y-c.y))/den
 wb=((c.y-a.y)*(q.x-c.x)+(a.x-c.x)*(q.y-c.y))/den;wc=1-wa-wb
 coeff=[max(0,wa),max(0,wb),max(0,wc)];total=sum(coeff);coeff=[v/total for v in coeff]
 point=sum((source['points'][i]*w for i,w in zip(ids,coeff)),Vector())
 point.x=uv[0];point.z=uv[1]*972/1961
 normal=sum((source['normals'][i]*w for i,w in zip(ids,coeff)),Vector()).normalized()
 weights=defaultdict(float)
 for i,w in zip(ids,coeff):
  for name,value in source['weights'][i].items():weights[name]+=value*w
 weights={k:v/sum(weights.values()) for k,v in weights.items() if v>1e-9}
 fin_weight=weights.get('Dorsal_2',0)
 thick_mm=P['thickness']['tip_mm']+(P['thickness']['root_mm']-P['thickness']['tip_mm'])*(1-fin_weight)**2
 color_uv=tuple(sum(source['uvs'][i][k]*w for i,w in zip(ids,coeff)) for k in range(2))
 return point,normal,weights,color_uv,thick_mm/(1000*P['runtime_scale']),distance

def build_closed_shell_collapse_rejected(obj,source,budget):
 bpy.context.view_layer.objects.active=obj;obj.select_set(True)
 modifier=obj.modifiers.new('Trial local collapse','DECIMATE');modifier.ratio=budget/18592;modifier.use_collapse_triangulate=True
 bpy.ops.object.modifier_move_up(modifier=modifier.name);bpy.ops.object.modifier_apply(modifier=modifier.name)
 m=obj.data;by_vertex=defaultdict(list)
 for loop in m.loops:by_vertex[loop.vertex_index].append(tuple(m.uv_layers.active.data[loop.index].uv))
 points=[];uvs=[];weights=[];clamps=[]
 for v in m.vertices:
  uv=tuple(sum(x[k] for x in by_vertex[v.index])/len(by_vertex[v.index]) for k in range(2))
  point,normal,w,uv,thick,distance=sample(source,uv)
  signed=(v.co-point).dot(normal)
  assert abs(signed)>1e-7,'Collapse merged opposite shell layers; route A rejected'
  points.append(point+normal*thick*.5*(1 if signed>0 else -1));uvs.append(uv);weights.append(w);clamps.append(distance)
 return points,[tuple(p.vertices) for p in m.polygons],uvs,weights,{'uv_projection_max_pixels':max(clamps),'method':'Collapse old closed shell, retain layer sign, reapply shared thickness and source fields'}

def shell(source,uvs,triangles,metrics):
 n=len(uvs);points=[];weights=[];used_uvs=[];clamps=[]
 for sign in [1,-1]:
  for uv in uvs:
   p,no,w,uv,thick,distance=sample(source,uv);points.append(p+no*thick*.5*sign);weights.append(w);used_uvs.append(uv);clamps.append(distance)
 front=[];counts=Counter()
 for a,b,c in triangles:
  if (points[b]-points[a]).cross(points[c]-points[a]).y<0:b,c=c,b
  front.append((a,b,c))
  for e in [(a,b),(b,c),(c,a)]:counts[tuple(sorted(e))]+=1
 faces=front+[(c+n,b+n,a+n) for a,b,c in front]
 for a,b,c in front:
  for x,y in [(a,b),(b,c),(c,a)]:
   if counts[tuple(sorted((x,y)))]==1:faces.extend([(x,x+n,y+n),(x,y+n,y)])
 metrics.update(uv_projection_max_pixels=max(clamps),method='Physical XZ-domain mesh, barycentric source-field transfer and direct closed shell')
 return points,faces,used_uvs,weights,metrics

def build_a(obj,source,budget):
 # Preserve the old mid-surface connectivity while simplifying; do not collapse
 # the two close shell layers against each other.
 mid=bpy.data.meshes.new('Old_mid_surface');mid.from_pydata(source['points'],[],source['triangles']);mid.update()
 layer=mid.uv_layers.new(name='UVMap')
 for loop in mid.loops:layer.data[loop.index].uv=source['parameter_uvs'][loop.vertex_index]
 temp=bpy.data.objects.new('Trial_collapse_mid',mid);bpy.context.collection.objects.link(temp)
 mod=temp.modifiers.new('Local_collapse','DECIMATE');mod.use_collapse_triangulate=True
 low,high=0.001,0.5;target=(budget+4)//4;chosen=None;delta=1e9
 for iteration in range(9):
  ratio=(low+high)/2;mod.ratio=ratio;bpy.context.view_layer.update()
  evaluated=temp.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
  used=sorted({vi for p in mesh.polygons for vi in p.vertices});nv=len(used);remap={old:new for new,old in enumerate(used)}
  if abs(nv-target)<delta:
   delta=abs(nv-target);by_vertex=defaultdict(list)
   for loop in mesh.loops:by_vertex[loop.vertex_index].append(tuple(mesh.uv_layers.active.data[loop.index].uv))
   uv=[tuple(sum(q[k] for q in by_vertex[i])/len(by_vertex[i]) for k in range(2)) for i in used]
   chosen=(uv,[tuple(remap[vi] for vi in p.vertices) for p in mesh.polygons],ratio)
  evaluated.to_mesh_clear()
  if nv>target:high=ratio
  else:low=ratio
 uvs,triangles,ratio=chosen;bpy.data.objects.remove(temp,do_unlink=True)
 result=shell(source,uvs,triangles,{'old_mid_surface_collapse_ratio':ratio,'target_mid_vertices':target})
 result[-1]['method']='Collapse existing mid-surface topology, then rebuild the same target thickness shell'
 return result

def build_b(obj,source,budget):
 # Rebuild a video-style low-density cage: longitudinal silhouette stations,
 # root-to-tip rows and direct thickness, using the old fish only as reference.
 points=source['points'];edges=Counter(tuple(sorted((t[i],t[(i+1)%3]))) for t in source['triangles'] for i in range(3))
 boundary=[e for e,c in edges.items() if c==1];outline=[points[i] for i in {v for e in boundary for v in e}]
 xmin=min(p.x for p in outline);xmax=max(p.x for p in outline)
 def span(x):
  values=[]
  for a,b in boundary:
   p,z=points[a],points[b]
   if min(p.x,z.x)-1e-9<=x<=max(p.x,z.x)+1e-9:
    if abs(z.x-p.x)<1e-12:values.extend([p.z,z.z])
    else:values.append(p.z+(z.z-p.z)*(x-p.x)/(z.x-p.x))
  assert values
  return min(values),max(values)
 max_stations=max(3,((budget+4)//4-2)//5+2)
 stations=[xmin,xmax]
 from functools import lru_cache
 span=lru_cache(maxsize=None)(span)
 def segment_distance(x,z,a,az,b,bz):
  dx,dz=b-a,bz-az;t=max(0.,min(1.,((x-a)*dx+(z-az)*dz)/max(dx*dx+dz*dz,1e-20)))
  return math.hypot(x-a-t*dx,z-az-t*dz)
 while len(stations)<max_stations:
  stations.sort();worst_error=-1.;worst_x=None
  for p in outline:
   if any(abs(p.x-x)<1e-6 for x in stations):continue
   at=next(i for i in range(len(stations)-1) if stations[i]<=p.x<=stations[i+1])
   a,z=stations[at:at+2];t=(p.x-a)/(z-a);sa,sz=span(a),span(z)
   error=min(segment_distance(p.x,p.z,a,sa[0],z,sz[0]),segment_distance(p.x,p.z,a,sa[1],z,sz[1]))
   if error>worst_error:worst_error=error;worst_x=p.x
  if worst_x is None:break
  stations.append(worst_x)
 stations.sort();uvs=[];rows=[]
 for ix,x in enumerate(stations):
  lo,hi=span(x)
  fractions=[.5] if ix in [0,len(stations)-1] else [0.,.05,.15,.4,1.]
  row=[]
  for t in fractions:row.append(len(uvs));uvs.append((x,(lo+(hi-lo)*t)*1961/972))
  rows.append(row)
 triangles=[]
 for a,z in zip(rows,rows[1:]):
  if len(a)==1:triangles.extend((a[0],z[k],z[k+1]) for k in range(len(z)-1))
  elif len(z)==1:triangles.extend((a[k],z[0],a[k+1]) for k in range(len(a)-1))
  else:
   for k in range(4):triangles.extend([(a[k],z[k],z[k+1]),(a[k],z[k+1],a[k+1])])
 result=shell(source,uvs,triangles,{'cage_stations':len(stations),'root_to_tip_rows':5,'new_mid_vertices':len(uvs),
  'station_native_x':stations,'method':'New low-density longitudinal cage fitted to old physical silhouette; root-biased rows, source UV/skin field transfer, direct variable thickness'})
 result[-1]['method']='Video-style newly built longitudinal cage; no old face connectivity retained'
 return result

def install_mesh(obj,source,result):
 points,faces,uvs,weights,metrics=result;m=bpy.data.meshes.new('Dorsal_trial_'+ROUTE);m.from_pydata(points,[],faces);m.materials.append(source['material']);m.update()
 layer=m.uv_layers.new(name='UVMap')
 for loop in m.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
 obj.data=m;obj.vertex_groups.clear()
 for polygon in m.polygons:polygon.use_smooth=True
 for name in source['groups']:obj.vertex_groups.new(name=name)
 for vi,row in enumerate(weights):
  for name,w in row.items():obj.vertex_groups[name].add([vi],w,'REPLACE')
 bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m)
 closed=all(e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=True)
 invalid_counts=Counter(len(e.link_faces) for e in bm.edges if not e.is_manifold);bm.free()
 if volume<0:
  bm=bmesh.new();bm.from_mesh(m);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
 assert closed,f'New shell not closed manifold: edge-face incidence {dict(invalid_counts)}, input faces {len(faces)}, imported faces {len(m.polygons)}'
 tree=BVHTree.FromPolygons([v.co for v in m.vertices],[p.vertices for p in m.polygons],all_triangles=True)
 # Compare to the same thickness target, rather than penalize the intentional thick-root design.
 source_target=[]
 for uv in source['parameter_uvs']:
  p,no,_,_,thick,_=sample(source,uv)
  source_target.extend([p+no*thick*.5,p-no*thick*.5])
 target_errors=[tree.find_nearest(p)[3]*P['runtime_scale']*1000 for p in source_target]
 target_tree=BVHTree.FromPolygons(source['old_points'],source['old_faces'],all_triangles=True)
 old_error=max(target_tree.find_nearest(v.co)[3] for v in m.vertices)*P['runtime_scale']*1000
 metrics.update(vertices=len(m.vertices),triangles=sum(len(p.vertices)-2 for p in m.polygons),closed_manifold=closed,
  target_surface_error_max_mm=max(target_errors),target_surface_error_p95_mm=sorted(target_errors)[int(len(target_errors)*.95)],
  distance_to_old_uniform_shell_max_mm=old_error,weight_sum_error=max(abs(sum(g.weight for g in v.groups)-1) for v in m.vertices))
 return metrics

def main():
 bpy.context.preferences.filepaths.save_version=0
 results=[]
 extra=sys.argv[sys.argv.index('--')+3:]
 for budget in ([int(x) for x in extra] if extra else P['budgets_triangles']):
  started=time.monotonic();destination=BASE/f'route-{ROUTE}-{budget}';destination.mkdir(exist_ok=True)
  try:
   bpy.ops.wm.open_mainfile(filepath=str(SOURCE));obj=bpy.data.objects[P['fin']]
   others={o.name:digest(o) for o in bpy.data.objects if o.type=='MESH' and o!=obj};source=get_source(obj)
   bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=obj;obj.select_set(True)
   result=(build_a if ROUTE=='a' else build_b)(obj,source,budget);metrics=install_mesh(obj,source,result)
   assert others=={o.name:digest(o) for o in bpy.data.objects if o.type=='MESH' and o!=obj},'Other fish objects changed'
   metrics['other_meshes_unchanged']=True
   bpy.ops.wm.save_as_mainfile(filepath=str(destination/'candidate.blend'))
   bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);obj.parent.select_set(True)
   from io_scene_gltf2.blender.exp.primitive_extract import PrimitiveCreator
   method=PrimitiveCreator._PrimitiveCreator__get_bone_data;code=method.__code__
   if code.co_consts.count(.0001)==1:method.__code__=code.replace(co_consts=tuple(0.0 if x==.0001 else x for x in code.co_consts))
   bpy.ops.export_scene.gltf(filepath=str(destination/'fin.glb'),export_format='GLB',use_selection=True,export_skins=True,export_animations=False,export_apply=False,export_yup=True)
   metrics.update(candidate_blend_sha256=sha(destination/'candidate.blend'),fin_glb_sha256=sha(destination/'fin.glb'))
   report={'ok':True,'route':ROUTE,'budget':budget,'metrics':metrics,'elapsed_seconds':round(time.monotonic()-started,3),'formal_acceptance':False}
  except Exception as exc:
   report={'ok':False,'route':ROUTE,'budget':budget,'error':str(exc),'elapsed_seconds':round(time.monotonic()-started,3),'formal_acceptance':False}
  save(destination/'build.validation.json',report);results.append(report);print('FIN_ROUTE '+json.dumps(report),flush=True)
 previous=BASE/f'route-{ROUTE}.validation.json'
 if previous.exists():
  budgets={x['budget'] for x in results};results=[x for x in json.loads(previous.read_text())['results'] if x['budget'] not in budgets]+results
 save(previous,{'route':ROUTE,'results':results,'source_sha256':P['source_sha256'],'profile_sha256':sha(BASE/'trial-profile.json')})

if __name__=='__main__':main()
