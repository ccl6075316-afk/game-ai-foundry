"""Offline source repair: source-calibrated shoulder and real tapered fin volume.

Preserves source fin-outline identities, rig and animation; explicitly reallocates
free interior samples to finite basal support within the whole-fish budget. Thickness
is an explicit per-fin art construction, not a biological measurement. Tail roots
match the finite posterior body cross-section, never a centerline paper sheet.
"""
import argparse,hashlib,json,sys,math
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(Path(__file__).parent),str(ROOT/'cli')]
from closed_body_index140 import build as inside_index
from fish_budget import check_triangle_budget
from caudal_cross_section import rebuild as rebuild_caudal,junction_normals
from triangulate_export_mesh import triangulate_export_mesh
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot
from resample_median_root import resample as resample_median,add_crest

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def recalc(ob):
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update();ob.data.calc_loop_triangles()
def static(ob):return {'uv':[[list(x.uv)for x in l.data]for l in ob.data.uv_layers],'faces':[list(f.vertices)for f in ob.data.polygons]}
def vertex_uv(ob):
 rows=[[]for _ in ob.data.vertices]
 for l,uv in zip(ob.data.loops,ob.data.uv_layers.active.data):rows[l.vertex_index].append(np.array(uv.uv[:]))
 return [np.mean(q,axis=0)for q in rows]

def old_shell_median(ob):
 groups={}
 for i,q in enumerate(vertex_uv(ob)):groups.setdefault(tuple(np.round(q,7)),[]).append(i)
 values=[(ob.data.vertices[i].co-ob.data.vertices[j].co).length*scale*1000 for ids in groups.values()if len(ids)==2 for i,j in[ids]]
 assert values;return float(np.median(values))

p=argparse.ArgumentParser(description=__doc__)
for k in ['blend','config','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);source=a.blend.resolve();out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();assert sha(source)==cfg['input_blend_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(0);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.view_layer.update();body=bpy.data.objects[cfg['body']];profile=read(ROOT/cfg['profile']);oldprofile=read(ROOT/cfg['baseline_profile']);W,H=cfg['source_size'];aspect=H/W;scale=cfg['model_scale'];frozen={o.name:static(o)for o in bpy.data.objects if o.type=='MESH'}
rig_snapshot=rig_action_snapshot();actions=hashlib.sha256(json.dumps(rig_snapshot,sort_keys=True).encode()).hexdigest()
oldsec=np.array(oldprofile['body']['sections']);sec=np.array(profile['body']['sections']);head_changed=0
if cfg.get('head_join_interval'):
 lo,hi=cfg['head_join_interval']
 for v in body.data.vertices:
  u=v.co.x+.5
  if not lo-1e-7<=u<=hi+1e-7:continue
  ot,ob=[float(np.interp(u,oldsec[:,0],oldsec[:,i]))for i in [1,2]];nt,nb=[float(np.interp(u,sec[:,0],sec[:,i]))for i in [1,2]]
  z=(.5-v.co.z/aspect);target=nt+(z-ot)/(ob-ot)*(nb-nt);v.co.z=(.5-target)*aspect;head_changed+=1
recalc(body);bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);inside=inside_index(np.array(bv),np.array(bt));body_weights=[{body.vertex_groups[g.group].name:g.weight for g in v.groups}for v in body.data.vertices]
def skin_to_body(ob,i,hit,face):
 aa,bb,cc=bt[face];bary=barycentric_transform(hit,bv[aa],bv[bb],bv[cc],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
 for vi,g in zip((aa,bb,cc),bary):
  for bone,w in body_weights[vi].items():mix[bone]=mix.get(bone,0)+max(0,g)*w
 items=sorted(mix.items(),key=lambda x:-x[1])[:4];total=sum(v for _,v in items);assert total>0
 for g in list(ob.data.vertices[i].groups):ob.vertex_groups[g.group].remove([i])
 for bone,w in items:
  if w>0:(ob.vertex_groups.get(bone)or ob.vertex_groups.new(name=bone)).add([i],w/total,'REPLACE')
def tapered(t,root,mid,edge):
 # Monotone C1 segments; independent fin parameters are frozen in this case.
 if t<=.45:q=max(0.,min(1.,t/.45));return root+(mid-root)*(q*q*(3-2*q))
 q=max(0.,min(1.,(t-.45)/.55));return mid+(edge-mid)*(q*q*(3-2*q))

root_u=sec[0,0];root_x=root_u-.5;root_top,root_bottom,root_width=sec[0,1:];zmid=(.5-(root_top+root_bottom)/2)*aspect
cap_vertices=[q for q in bv if abs(q.x-root_x)<1e-6];assert len(cap_vertices)>=8
records=[];frozen_roots={}
def reallocate_interior_pair(ob,band):
 # Explicit case nomination only. Retain every boundary and complete basal
 # point; trade one redundant free interior UV-mate pair for root support.
 uv=vertex_uv(ob);groups={};ts=[v.value for v in ob.data.attributes['foundry_fin_source_t'].data]
 for i,q in enumerate(uv):groups.setdefault(tuple(np.round(q,7)),[]).append(i)
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();options=[];N=len(ob.data.vertices)//2
 for xy,ids in groups.items():
  if len(ids)!=2 or not all(.15<ts[i]<.9 for i in ids):continue
  # Two sides of a paired fin occupy the SAME body flank; Y sign is not a
  # layer identity. Native two-layer source indices distinguish closing walls.
  assert abs(ids[1]-ids[0])==N
  if all(all((v.index<N)==(i<N)for f in bm.verts[i].link_faces for v in f.verts)for i in ids):options.append((xy,ids))
 assert options,(ob.name,'No expendable free interior pair')
 xy,ids=options[0];before=len(ob.data.vertices);bmesh.ops.dissolve_verts(bm,verts=[bm.verts[i]for i in ids],use_face_split=False,use_boundary_tear=False);bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(ob.data);bm.free();recalc(ob)
 assert len(ob.data.vertices)==before-2
 return {'removed_interior_uv':xy,'removed_vertices':2,'original_outline_and_entire_root_band_retained':True}

def conform_basal_faces(ob,band):
 # Finite root faces must follow the same actual faceted body, not merely
 # touch at their vertices. Split only failing basal support edges; never
 # enlarge the collar or classify free membrane as root.
 triangulate_export_mesh(ob);history=[];added=[]
 for iteration in range(8):
  ob.data.calc_loop_triangles();ts=[v.value for v in ob.data.attributes['foundry_fin_source_t'].data];marked=[]
  for tri in ob.data.loop_triangles:
   ids=tuple(tri.vertices)
   if not all(ts[i]<=band+1e-7 for i in ids):continue
   pts=[ob.data.vertices[i].co.copy()for i in ids]
   probes=[sum(pts,Vector())/3]+[p.lerp(q,t)for p,q in zip(pts,pts[1:]+pts[:1])for t in [.25,.5,.75]]
   if any(inside(p)and tree.find_nearest(p)[3]*scale*1000>.48 for p in probes):
    edges=[(i,j)for i,j in zip(ids,ids[1:]+ids[:1])]
    marked.append(max(edges,key=lambda e:(ob.data.vertices[e[0]].co-ob.data.vertices[e[1]].co).length))
  marked=sorted({tuple(sorted(e))for e in marked});history.append({'round':iteration,'split_edges':len(marked)})
  if not marked:return {'added_vertices':len(added),'history':history}
  # The whole mesh budget is checked before saving; keep the experiment
  # bounded instead of silently adding an arbitrarily dense root layer.
  assert len(added)+len(marked)<=24,(ob.name,'Finite-root adaptation exceeded bounded local repair',history)
  bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();layer=bm.verts.layers.float['foundry_fin_source_t'];original=list(bm.verts);new=[]
  for i,j in marked:
   edge=bm.edges.get((original[i],original[j]));assert edge
   edge,vert=bmesh.utils.edge_split(edge,original[i],.5);hit,n,face,_=tree.find_nearest(vert.co);vert.co=hit-n*(cfg['root_inset_mm']/1000/scale);vert[layer]=(ts[i]+ts[j])/2;new.append((vert,hit,face))
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.index_update();indices=[(v.index,h,f)for v,h,f in new];bm.to_mesh(ob.data);bm.free()
  for i,hit,face in indices:skin_to_body(ob,i,hit,face);added.append(i)
  recalc(ob)
 raise AssertionError(ob.name+' finite root adaptation did not converge')

for fin in profile['fins']:
 for suffix in (['_left','_right']if fin['paired']else['']):
  name=fin['name']+suffix+'_mesh';ob=bpy.data.objects[name];settings=cfg['fins'][fin['name']];tail_rebuild=None;old_median=old_shell_median(ob)
  median_reallocation=resample_median(ob,fin,next(f for f in oldprofile['fins']if f['name']==fin['name']),bv,aspect,W,H,settings)if fin['name']in cfg.get('median_body_station_roots',[])else None
  allocation=reallocate_interior_pair(ob,fin['root_attachment']['root_band'])if fin['name']in cfg.get('reallocate_interior_fins',[])else None
  expected_static=static(ob)
  if fin['name']=='Caudal':tail_rebuild=rebuild_caudal(ob,fin,cap_vertices,root_x,zmid,aspect,W,H,scale,settings,cfg['tail_overlap_mm'],skin_to_body,tree,next(f for f in oldprofile['fins']if f['name']=='Caudal'))
  uv=vertex_uv(ob);groups={}
  for i,q in enumerate(uv):groups.setdefault(tuple(np.round(q,7)),[]).append(i)
  assert all(len(v)==2 for v in groups.values()),(name,'Every two-sided source point must have two UV mates',[(k,len(v))for k,v in groups.items()if len(v)!=2][:5])
  tattr=ob.data.attributes.get('foundry_fin_source_t');assert tattr;ts=np.array([v.value for v in tattr.data]);rootband=fin['root_attachment']['root_band'];roots=[i for i,t in enumerate(ts)if t<=rootband+1e-7];old=np.array([v.co[:]for v in ob.data.vertices]);new=old.copy();pairs=[]
  side=-1 if suffix=='_left'else 1
  flank_ids=[i for i,tri in enumerate(bt)if all(bv[j].y*side>=-1e-8 for j in tri)]if fin['paired']else[]
  flank=BVHTree.FromPolygons(bv,[bt[i]for i in flank_ids],all_triangles=True)if flank_ids else None
  for key,ids in groups.items():
   i,j=ids;t=float((ts[i]+ts[j])/2);center=(old[i]+old[j])/2;n=old[j]-old[i];length=np.linalg.norm(n);assert length>1e-9,(name,i,j,'Collapsed old shell');n/=length
   if tail_rebuild:
    pairs.append((i,j,t));continue
   # Preserve the accepted fin middle/shape. For median fins the anatomical
   # source plane is XZ; legacy cap-smoothed extrusion directions are not
   # the membrane normal and must not be scaled into a folded thick foil.
   if not fin['paired']:n=np.array([0.,1. if n[1]>=0 else-1.,0.])
   full=tapered(t,settings['root_mm'],settings['mid_mm'],settings['edge_mm']);half=full/2000/scale
   camber=settings.get('camber_mm',0)/1000/scale*math.sin(math.pi*max(0.,min(1.,t)))**2
   if fin['paired']:center+=n*camber*(1 if n[1]*(-1 if suffix=='_left'else 1)>0 else-1)
   proposed=[Vector(center+n*half*sign)for sign in[-1,1]]
   if i not in roots:
    # Translate the COMPLETE foil pair out of the body. Clamping each side
    # separately collapses the thickness and can fold the shell near its base.
    lift=0.;vertical=1 if fin['tip'][1]<fin['anchor'][1]else-1
    minimum=max(cfg['free_clearance_mm']/1000/scale,fin['root_attachment'].get('surface_clearance',0))
    for point in proposed:
     if fin['paired']:
      hit,normal,face,_=tree.ray_cast(Vector((point.x,side*2,point.z)),Vector((0,-side,0)),4)
      if hit is not None:lift=max(lift,side*(hit.y-point.y)+minimum)
     else:
      hit,normal,face,_=tree.ray_cast(Vector((point.x,point.y,vertical*2)),Vector((0,0,-vertical)),4)
      if hit is not None:lift=max(lift,vertical*(hit.z-point.z)+minimum)
    for point in proposed:
     if fin['paired']:point.y+=side*max(0,lift)
     else:point.z+=vertical*max(0,lift)
   for vi,sign in [(i,-1),(j,1)]:
    point=proposed[0 if sign==-1 else 1]
    if vi in roots:
     if not fin['paired']:
      direction=1 if fin['tip'][1]<fin['anchor'][1]else-1;hit,normal,face,_=tree.ray_cast(Vector((point.x,point.y,direction*2)),Vector((0,0,-direction)),4.)
      if hit is None:hit,normal,face,_=tree.find_nearest(point)
     else:
      hit,normal,face,_=flank.find_nearest(point);face=flank_ids[face]
     offset=cfg.get('paired_root_surface_offset_mm',-cfg['root_inset_mm'])if fin['paired']else cfg.get('root_surface_offset_mm',-cfg['root_inset_mm'])
     if median_reallocation:
      assert abs(normal.z)>.1;point=hit+Vector((0,0,(1 if fin['tip'][1]<fin['anchor'][1]else-1)*offset/1000/scale/abs(normal.z)))
     else:point=hit+normal*(offset/1000/scale)
     skin_to_body(ob,vi,hit,face)
    new[vi]=point
   pairs.append((i,j,t))
  for v,q in zip(ob.data.vertices,new):v.co=q
  recalc(ob)
  if not tail_rebuild:assert static(ob)==expected_static,name+' UV or topology changed'
  crest=add_crest(ob,fin,tree,scale,cfg['root_inset_mm'],skin_to_body)if median_reallocation else None
  adaptation=conform_basal_faces(ob,rootband)if fin['name']!='Caudal'else None
  ts=np.array([v.value for v in ob.data.attributes['foundry_fin_source_t'].data]);roots=[i for i,t in enumerate(ts)if t<=rootband+1e-7]
  # Use measured local two-surface separation, not AABB or requested parameters.
  distribution=[]
  for a0,b0,label in [(0,.15,'root'),(.15,.65,'middle'),(.65,1.001,'edge')]:
   values=[float(np.linalg.norm(new[i]-new[j])*scale*1000)for i,j,t in pairs if a0<=t<b0]
   distribution.append({'zone':label,'pairs':len(values),'measured_pair_distance_mm_min_median_max':np.percentile(values,[0,50,100]).tolist()if values else None})
  points=[ob.data.vertices[i].co for i in roots];frozen_roots[name]={'ids':roots,'rest_points_gltf':[[q.x,q.z,-q.y]for q in points],'vertices':len(ob.data.vertices),'rule':'Complete original persisted source_t basal band retained; tapered volume and current actual body support, no root selection shrink','source_baseline':fin['source_baseline'],'source_t_max':rootband}
  records.append({'name':name,'parameters_art_hypothesis':settings,'measurements':distribution,'geometry_changed':True,'native_uv_topology_unchanged':static(ob)==frozen[name],'source_quads_frozen_to_existing_export_triangles':True,'interior_reallocation':allocation,'caudal_section_rebuild':tail_rebuild,'median_root_reallocation':median_reallocation,'crest_support':crest,'finite_basal_adaptation':adaptation,'old_shell_mm_median':old_median})
assert static(body)==frozen[cfg['body']]
normal_repair=junction_normals(body,bpy.data.objects['Caudal_mesh'],root_x)
triangles=0
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();triangles+=len(ob.data.loop_triangles)
try:budget=check_triangle_budget(triangles,profile['real_length_cm'])
except ValueError as error:
 out.mkdir(parents=True);(out/'budget-failure.validation.json').write_text(json.dumps({'ok':False,'status':'failed','next_action':'fix_input','triangles':triangles,'error':str(error),'config_sha256':sha(a.config),'records':records,'scope':'Rejected before saving any model. Reallocate topology within the original complete fin/rig/body constraints; no increased budget.'},indent=2)+'\n',encoding='utf8');(out/'effective-config.json').write_bytes((json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode('utf8'));raise
assert rig_action_snapshot()==rig_snapshot,'Rig, actual keyframes or action bindings changed'
out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0;rig.data.pose_position='POSE';bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
allpoints=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH'for v in o.data.vertices];length=max(q.x for q in allpoints)-min(q.x for q in allpoints)
rootplan={'kind':'authored_fin_completion_plan','items':[{'species':profile['species'],'model':str(out/'fish.glb'),'model_sha256':sha(out/'fish.glb'),'body':cfg['body'],'body_bones':[f'body_{i:02d}'for i in range(len(profile['rig']['spine']))],'length_native':length,'scale_cm':profile['real_length_cm']/length,'fins':frozen_roots,'handoff':str(a.config.resolve()),'profile':str((ROOT/cfg['profile']).resolve()),'profile_sha256':sha(ROOT/cfg['profile']),'source_sha256':cfg['source_sha256']}]}
(out/'authored-roots.plan.json').write_text(json.dumps(rootplan,indent=2)+'\n',encoding='utf8')
report={'ok':True,'kind':'offline_full_fin_volume_and_source_join_repair','input_blend_sha256':sha(source),'config_sha256':sha(a.config),'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'head_vertices_changed':head_changed,'head_uses_frontal_reference':False,'mouth_geometry_intentionally_retained':True,'records':records,'triangle_budget':budget,'junction_normals':normal_repair,'root_count':{n:len(v['ids'])for n,v in frozen_roots.items()},'rig_actions_preserved_digest':actions,'scope':'Actual authored source candidate only; measured thickness/planform, tail cross-section continuity, full current posed contact/GPU and actual source/gray/material review remain mandatory. No user acceptance.'}
(out/'effective-config.json').write_bytes((json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
(out/'repair.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'head_vertices_changed':head_changed,'fins':len(records),'output':str(out)}))
