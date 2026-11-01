"""Explicit-plan finite contact cage conformity; local body projection, preserved source and append-only GLB. No acceptance claim."""
import bpy,json,sys,hashlib,copy,struct
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform
import argparse
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(Path(__file__).resolve().parent));config=json.loads(args.config.read_text());base=args.output.resolve();assert base.is_relative_to(repo)and any(x in ('work','output','experiments')for x in base.relative_to(repo).parts),'Output must be a repository work/output/experiment directory';assert not any((base/x).exists()for x in ('fish.glb','fish.blend')),'Refuse overwriting existing assets';base.mkdir(parents=True,exist_ok=True)
from patch_existing_fin_meshes import read,write
from repair_fin_clearance import values
from subdivide_fin_contact import midpoint,interpolate
import math
from closed_body_index140 import build
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads(args.plan.read_text());spec=next(x for x in plan['items']if x['species']==config['species']);assert spec['membrane_clearance']['root_collar_mm']==config['root_collar_mm']and spec['membrane_clearance']['penetration_tolerance_mm']==config['penetration_tolerance_mm'],'Frozen collision limits mismatch';source_blend=Path(spec['model']).with_suffix('.blend');d,b=read(spec['model']);original=bytes(b);stage=config['stages']['transition'];assert sha(spec['model'])==stage['input_model_sha256'];scale=config['runtime_length_cm']/100/spec['length_native'];out=base
body_node=next(n for n in d['nodes']if n.get('name')==config['body']and'mesh'in n);bv=[];bt=[];skin=[]
for pr in d['meshes'][body_node['mesh']]['primitives']:
 attrs={k:values(d,b,v)for k,v in pr['attributes'].items()};offset=len(bv);bv.extend(Vector(v)for v in attrs['POSITION']);ids=[v[0]for v in values(d,b,pr['indices'])];bt.extend(tuple(offset+j for j in ids[i:i+3])for i in range(0,len(ids),3));skin.extend(dict(zip(j,w))for j,w in zip(attrs['JOINTS_0'],attrs['WEIGHTS_0']))
if sum(bv[a].dot(bv[c].cross(bv[e]))for a,c,e in bt)<0:bt=[tuple(reversed(t))for t in bt]
tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);inside=build(np.array(bv),np.array(bt));records=[];patches={}
def signed(p):
 p=Vector(p);dist=tree.find_nearest(p)[3]*scale*1000;return -dist if inside(p)else dist
def project(row):
 hit,n,fi,_=tree.find_nearest(Vector(row['POSITION']));row['POSITION']=tuple(hit+n*((-config['root_inset_mm']if row['root']else config['new_point_clearance_mm'])/1000/scale));ids=bt[fi];bary=barycentric_transform(hit,*[bv[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix=defaultdict(float)
 for i,amount in zip(ids,bary):
  for j,w in skin[i].items():mix[j]+=max(0,amount)*w
 items=sorted(mix.items(),key=lambda q:-q[1])[:4]
 while len(items)<4:items.append((0,0.))
 total=sum(w for _,w in items);row['JOINTS_0']=tuple(j for j,_ in items);row['WEIGHTS_0']=tuple(w/total for _,w in items)
def put(idx,rows):
 a=copy.deepcopy(d['accessors'][idx]);fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']];b.extend(b'\0'*(-len(b)%4));off=len(b)
 for row in rows:b.extend(struct.pack('<'+fmt*len(row),*row))
 a.update(bufferView=len(d['bufferViews']),byteOffset=0,count=len(rows));a.pop('min',None);a.pop('max',None)
 if a['type']=='VEC3':a.update(min=[min(q[k]for q in rows)for k in range(3)],max=[max(q[k]for q in rows)for k in range(3)])
 d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(b)-off});d['accessors'].append(a);return len(d['accessors'])-1
for name in stage['targets']:
 node=next(n for n in d['nodes']if n.get('name')==name and'mesh'in n);pr=d['meshes'][node['mesh']]['primitives'][0];attrs={k:values(d,b,v)for k,v in pr['attributes'].items()};roots=[Vector(p)for p in spec['fins'][name]['rest_points_gltf']];rows=[{**{k:v[i]for k,v in attrs.items()},'root':any((Vector(q)-r).length<2e-6 for r in roots)}for i,q in enumerate(attrs['POSITION'])];ids=[v[0]for v in values(d,b,pr['indices'])];tri=[tuple(ids[k:k+3])for k in range(0,len(ids),3)];old_count=len(rows);history=[]
 for i in stage['lateral_vertex_ids']:
  p=list(rows[i]['POSITION']);p[2]+=(1 if name.endswith('_left')else -1)*stage['physical_lateral_shift_mm']/1000/scale;rows[i]['POSITION']=tuple(p)
 def key(i):return tuple(round(v,7)for v in rows[i]['POSITION'])
 # Human-reviewed feasibility: reject a root whose required normal gap already exceeds the internal edge ceiling.
 preflight=[]
 for i,row in enumerate(rows):
  if not row['root']:continue
  sd=signed(row['POSITION']);gap=abs(config['new_point_clearance_mm']-sd);assert gap<stage['transition_edge_mm'],(name,i,'infeasible normalgap',gap)
  preflight.append({'vertex':i,'root_signed_mm':sd,'normal_gap_mm':gap,'tangent_budget_mm':math.sqrt(stage['transition_edge_mm']**2-gap**2)})
 for iteration in range(9):
  marked=set();bad=0;worst=0.
  for t in tri:
   for a,c in zip(t,t[1:]+t[:1]):
    if rows[a]['root']!=rows[c]['root'] and(Vector(rows[a]['POSITION'])-Vector(rows[c]['POSITION'])).length*scale*1000>stage['transition_edge_mm']:marked.add(tuple(sorted((a,c))))
  if iteration==0:marked.update(map(tuple,stage['posed_collision_edges']))
  rootfaces=[t for t in tri if all(rows[i]['root']for i in t)];rootbvh=BVHTree.FromPolygons([r['POSITION']for r in rows],rootfaces,all_triangles=True)if rootfaces else None
  rooted={tuple(sorted((a,c)))for t in tri for a,c in zip(t,t[1:]+t[:1])if rows[a]['root']and rows[c]['root']};rootpts=[Vector(r['POSITION'])for r in rows if r['root']]+[Vector(rows[a]['POSITION']).lerp(Vector(rows[c]['POSITION']),k/8)for a,c in rooted for k in range(1,8)];kd=KDTree(len(rootpts))
  for i,q in enumerate(rootpts):kd.insert(q,i)
  kd.balance()
  def badpoint(q):
   sd=signed(q);rd=kd.find(q)[2]
   if rootbvh:rd=min(rd,rootbvh.find_nearest(q)[3])
   return not(rd*scale*1000<=config['root_collar_mm']and sd>=config['static_refinement_min_signed_mm'])and sd<config['static_free_target_mm']
  for t in tri:
   if not any(rows[i]['root']or i>=old_count for i in t):continue
   pts=[Vector(rows[i]['POSITION'])for i in t];allroot=all(rows[i]['root']for i in t);limit=-.30 if allroot else -.005;failed=[]
   for k,(aa,bb)in enumerate(zip(pts,pts[1:]+pts[:1])):
    if any(badpoint(aa.lerp(bb,f))for f in [.25,.5,.75]):failed.append(tuple(sorted((t[k],t[(k+1)%3]))))
   probes=[sum(pts,Vector())/3]+[pts[j]*.6+pts[(j+1)%3]*.2+pts[(j+2)%3]*.2 for j in range(3)]
   distance=min(signed(q)for q in probes);worst=min(worst,distance)
   if failed or any(badpoint(q)for q in probes):
    bad+=1
    if not failed:failed=[max([tuple(sorted((a,c)))for a,c in zip(t,t[1:]+t[:1])],key=lambda e:(Vector(rows[e[0]]['POSITION'])-Vector(rows[e[1]]['POSITION'])).length)]
    marked.update(failed)
  history.append({'round':iteration,'failing_contact_faces':bad,'worst_mm':worst,'marked_edges':len(marked)})
  if not marked:break
  # UV-split duplicate edges get identical geometry points and conforming splits.
  edge_keys={tuple(sorted((key(a),key(c))))for a,c in marked};all_edges={tuple(sorted((a,c)))for t in tri for a,c in zip(t,t[1:]+t[:1])};marked={e for e in all_edges if tuple(sorted((key(e[0]),key(e[1]))))in edge_keys};added={}
  for edge in sorted(marked):
   a,c=edge
   if rows[a]['root']!=rows[c]['root']:
    root,free=(a,c)if rows[a]['root']else(c,a);rp=Vector(rows[root]['POSITION'])
    def support(t):
     value=interpolate([rows[root],rows[free]],[1-t,t]);value['root']=False;project(value);return value
    zero=support(0.);assert(Vector(zero['POSITION'])-rp).length*scale*1000<stage['transition_edge_mm'],(name,'infeasible actual facet transition')
    row=support(.5)
    if(Vector(row['POSITION'])-rp).length*scale*1000>stage['transition_edge_mm']-.0005:
     lo,hi=0.,.5
     for _ in range(28):
      mid=(lo+hi)/2;candidate=support(mid)
      if(Vector(candidate['POSITION'])-rp).length*scale*1000<=stage['transition_edge_mm']-.0005:lo=mid
      else:hi=mid
     row=support(lo)
    assert(Vector(row['POSITION'])-rp).length*scale*1000<=stage['transition_edge_mm']
   else:row=midpoint(rows[a],rows[c]);project(row)
   added[edge]=len(rows);rows.append(row)
  rebuilt=[]
  for t in tri:
   pieces=[t]
   for a,c in zip(t,t[1:]+t[:1]):
    mid=added.get(tuple(sorted((a,c))))
    if mid is None:continue
    split=[]
    for piece in pieces:
     if a not in piece or c not in piece:split.append(piece);continue
     for k in range(3):
      x,y,z=piece[k],piece[(k+1)%3],piece[(k+2)%3]
      if{x,y}=={a,c}:split.extend([(x,mid,z),(mid,y,z)]);break
    pieces=split
   rebuilt.extend(pieces)
  tri=rebuilt
  assert len(tri)<config['max_triangles_per_fin'],'bounded per-fin triangle stop'
 assert not marked,(name,'did not converge',history)
 normals=[Vector()for _ in rows]
 for a,c,e in tri:
  n=(Vector(rows[c]['POSITION'])-Vector(rows[a]['POSITION'])).cross(Vector(rows[e]['POSITION'])-Vector(rows[a]['POSITION']))
  for i in(a,c,e):normals[i]+=n
 for i,row in enumerate(rows):
  if normals[i].length>1e-12:row['NORMAL']=tuple(normals[i].normalized())
 for k,idx in list(pr['attributes'].items()):pr['attributes'][k]=put(idx,[r[k]for r in rows])
 pr['indices']=put(pr['indices'],[(j,)for t in tri for j in t]);spec['fins'][name]['rest_points_gltf']=[list(r['POSITION'])for r in rows if r['root']];patches[name]=(rows,tri,node);records.append({'fin':name,'old_vertices':old_count,'added_vertices':len(rows)-old_count,'triangles':len(tri),'history':history,'feasibility':preflight})
assert bytes(b[:len(original)])==original;model=out/'fish.glb';write(model,d,b);spec.update(model=str(model),model_sha256=sha(model));plan['scope']='R9 bounded finite near-basal refinement; complete all7 roots; unchanged frozen .5mm collar/.02mm tolerance.';plan.pop('transfer_proof',None);(out/'fin-gate.plan.json').write_text(json.dumps(plan,indent=2))
# Keep original editable scene, replacing only the repaired four mesh datablocks.
bpy.ops.wm.open_mainfile(filepath=str(source_blend))
for name,(rows,tri,node)in patches.items():
 ob=bpy.data.objects[name];old=ob.data;merged={};points=[];skinrows=[];remap=[]
 for row in rows:
  k=tuple(round(v,8)for v in row['POSITION'])+tuple(row['JOINTS_0'])+tuple(round(w,7)for w in row['WEIGHTS_0'])
  if k not in merged:merged[k]=len(points);p=row['POSITION'];points.append((p[0],-p[2],p[1]));skinrows.append(row)
  remap.append(merged[k])
 mesh=bpy.data.meshes.new(name+'_finite_contact_R9');mesh.from_pydata(points,[],[tuple(remap[i]for i in t)for t in tri]);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
 for face,t in zip(mesh.polygons,tri):
  face.use_smooth=True
  for li,i in zip(face.loop_indices,t):u,v=rows[i]['TEXCOORD_0'];uv.data[li].uv=(u,1-v)
 for mat in old.materials:mesh.materials.append(mat)
 ob.data=mesh
 for group in list(ob.vertex_groups):ob.vertex_groups.remove(group)
 jointnames=[d['nodes'][j]['name']for j in d['skins'][node['skin']]['joints']]
 for i,row in enumerate(skinrows):
  for j,w in zip(row['JOINTS_0'],row['WEIGHTS_0']):
   if w<=0:continue
   namej=jointnames[j];group=ob.vertex_groups.get(namej)or ob.vertex_groups.new(name=namej);group.add([i],w,'REPLACE')
from restore_fin_source_normals import apply_frozen_normals;source_normal_records=apply_frozen_normals(out/'fish.glb',stage['targets']);bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
count=sum(d['accessors'][pr['indices']]['count']//3 for mesh in d['meshes']for pr in mesh['primitives']);assert count<=config['whole_fish_triangle_limit'],count
report={'ok':True,'model_sha256':sha(model),'blend_sha256':sha(out/'fish.blend'),'whole_fish_triangles':count,'original_bin_prefix_sha256':hashlib.sha256(original).hexdigest(),'original_bin_bytes':len(original),'basal_new_point_inset_mm':config['root_inset_mm'],'mixed_new_point_clearance_mm':config['new_point_clearance_mm'],'original_positions_change_scope':{'Pectoral_left':[38,39,40,41],'Pectoral_right':[38,39,40,41]},'original_UVs_weights_unchanged':True,'original_chest_lateral_shift_physical_mm':stage['physical_lateral_shift_mm'],'root_transition_edge_limit_mm':stage['transition_edge_mm'],'construction':'Human approved direct feasible root-to-exterior support; sourceUV interpolation follows solved edge parameter','source_UV_interpolation':'per-original-edge linear; original texture images and material accessors untouched','root_rule':'only both-root edge midpoint inherits root; mixed points remain non-root','records':records,'status':'local rest adaptation only, fresh actual posed validation required'};(base/'human-approved-repair.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
