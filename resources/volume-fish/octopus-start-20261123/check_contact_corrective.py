import bpy,json,math,hashlib,sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;O=R/'motion-r6';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(O/'octopus-actions.glb'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');skin=next(o for o in bpy.data.objects if o.type=='MESH'and o.data.name.startswith('Tight_coil_skin'));cups=next(o for o in bpy.data.objects if o.type=='MESH'and o.name.startswith('Paired_sucker_rows'));objects=[skin,cups]
ids=list(bpy.data.objects)+[o.data.shape_keys for o in objects if o.data.shape_keys]
tracks={}
for obj in ids:
 if not obj.animation_data:continue
 tracks[obj]=[(t.name,t.strips[0].action,t.strips[0].action_slot)for t in obj.animation_data.nla_tracks if t.strips]
 for t in obj.animation_data.nla_tracks:t.mute=True
 obj.animation_data.action=None
print('TRACKS',[(x.name,[(a,b.name)for a,b,c in tr])for x,tr in tracks.items()],flush=True)
def activate(clip):
 for obj,tt in tracks.items():
  matched=[(a,slot)for name,a,slot in tt if name==clip]
  if matched:obj.animation_data.action=matched[0][0];obj.animation_data.action_slot=matched[0][1]
  else:obj.animation_data.action=None
faces=[[list(f.vertices)for f in o.data.polygons]for o in objects];key=lambda v:tuple(round(x,5)for x in v);facekeys=[[set(key(o.data.vertices[i].co)for i in f)for f in ff]for o,ff in zip(objects,faces)];centers=[[sum((o.data.vertices[v].co for v in f),Vector())/len(f)for f in ff]for o,ff in zip(objects,faces)]
contact_planes=[(Vector(p['center']),Vector(p['normal']))for p in json.loads((O/'build.validation.json').read_text())['patches']]
# A genuine transverse surface crossing straddles both triangle planes; coplanar surface contact is counted separately.
def crossing(A,B,tol=2e-5):
 for c,n in contact_planes:
  da=[(p-c).dot(n)for p in A];db=[(p-c).dot(n)for p in B]
  if(max(da)<=2e-6 and min(db)>=-2e-6)or(max(db)<=2e-6 and min(da)>=-2e-6):return False
 na=(A[1]-A[0]).cross(A[2]-A[0]).normalized();nb=(B[1]-B[0]).cross(B[2]-B[0]).normalized();da=[(p-B[0]).dot(nb)for p in A];db=[(p-A[0]).dot(na)for p in B]
 return min(da)<-tol and max(da)>tol and min(db)<-tol and max(db)>tol
def overlap_area(A,B):
 planes=[(c,n)for c,n in contact_planes if max(abs((p-c).dot(n))for p in A+B)<2e-6]
 if not planes:return 0.
 c,n=planes[0]
 u=(A[1]-A[0]).normalized();v=n.cross(u);P=[np.array([(p-A[0]).dot(u),(p-A[0]).dot(v)])for p in A];Q=[np.array([(p-A[0]).dot(u),(p-A[0]).dot(v)])for p in B]
 cross=lambda a,b:a[0]*b[1]-a[1]*b[0]
 if cross(Q[1]-Q[0],Q[2]-Q[0])<0:Q.reverse()
 for q0,q1 in zip(Q,Q[1:]+Q[:1]):
  result=[]
  for a,b in zip(P,P[1:]+P[:1]):
   da=cross(q1-q0,a-q0);db=cross(q1-q0,b-q0)
   if da>=-1e-10:result.append(a)
   if (da>=0)!=(db>=0):result.append(a+(b-a)*(da/(da-db)))
  P=result
  if len(P)<3:return 0.
 return abs(sum(cross(a,b)for a,b in zip(P,P[1:]+P[:1])))*.5
reports=[];contact_counts=[];full_contact_area=0.;loop_positions={};loop_errors={}

clipframes=[('TightRoll',[0,15,30,35,40,45,48,60,135,222,230,235,240,300]),('ProbeTouch',[0,180,210]),('AlternatingTouch',[0,420])]
if '--full' in sys.argv:clipframes=[('TightRoll',sorted(set(range(0,301,5))|set(range(12,31))|set(range(240,259)))),('ProbeTouch',range(0,481,5)),('AlternatingTouch',range(0,481,5))]
for clip,ff in clipframes:
 activate(clip)
 for frame in ff:
  bpy.context.scene.frame_set(frame);dep=bpy.context.evaluated_depsgraph_get();verts=[];trees=[];areas=[]
  for ob,fac in zip(objects,faces):
   ev=ob.evaluated_get(dep);me=ev.to_mesh();v=[ev.matrix_world@x.co for x in me.vertices];verts.append(v);areas.append(min(p.area for p in me.polygons));trees.append(BVHTree.FromPolygons(v,fac,all_triangles=True));ev.to_mesh_clear()
  body=[(a,b)for a,b in trees[0].overlap(trees[0])if a<b and not facekeys[0][a].intersection(facekeys[0][b])]
  remote=[(a,b)for a,b in trees[0].overlap(trees[1])if(centers[0][a]-centers[1][b]).length>.15]
  bb=[(a,b)for a,b in body if crossing([verts[0][i]for i in faces[0][a]],[verts[0][i]for i in faces[0][b]])]
  cup_pairs=[(a,b)for a,b in trees[1].overlap(trees[1])if a<b and (centers[1][a]-centers[1][b]).length>.15]
  cc=[(a,b)for a,b in cup_pairs if crossing([verts[1][i]for i in faces[1][a]],[verts[1][i]for i in faces[1][b]])]
  bc=[(a,b)for a,b in remote if crossing([verts[0][i]for i in faces[0][a]],[verts[1][i]for i in faces[1][b]])]
  if frame==0:loop_positions[clip]=[[v.copy()for v in vv]for vv in verts]
  if frame==(300 if clip=='TightRoll'else 480):loop_errors[clip]=max((a-b).length for aa,bb in zip(loop_positions[clip],verts)for a,b in zip(aa,bb))
  if clip=='TightRoll'and frame==0:full_contact_area=sum(overlap_area([verts[0][i]for i in faces[0][a]],[verts[0][i]for i in faces[0][b]])for a,b in body)
  weights=[o.data.shape_keys.key_blocks['CoilContact_R_IV'].value for o in objects]
  row={'clip':clip,'frame':frame,'morph_weights':weights,'body_overlap_pairs':len(body),'body_transverse_crossings':len(bb),'cup_skin_overlap_pairs':len(remote),'cup_skin_transverse_crossings':len(bc),'cup_cup_transverse_crossings':len(cc),'body_examples':bb[:12],'cup_examples':bc[:12],'minimum_areas':areas,'minimum_ground_clearance':min(p.z for vv in verts for p in vv)+.25};reports.append(row)
  if bb or bc:print('BAD',json.dumps(row),flush=True)
  if clip=='TightRoll'and frame==0:
   patches=json.loads((O/'build.validation.json').read_text())['patches'];path=json.loads((R/'motion-r3/rest/gray-build.validation.json').read_text())['control_paths'][7];root=Vector(path[0]);dr=(Vector(path[-1])-root).normalized();L=(Vector(path[-1])-root).length
   for patch in patches:
    n=Vector(patch['normal']);axis=dr.cross(Vector((0,0,-1))).normalized();n=(n-axis*n.dot(axis)).normalized();c=Vector(patch['center']);hits=[]
    for k,v in enumerate(verts[0]):
     f=(skin.data.vertices[k].co-root).dot(dr)/L
     if (v-c).length<.09 and abs((v-c).dot(n))<2e-5:hits.append((k,f))
    a,b=patch['fractions'];flat_a=[];flat_b=[]
    for face in faces[0]:
     if max(abs((verts[0][j]-c).dot(n))for j in face)>2e-6:continue
     fraction=sum((skin.data.shape_keys.key_blocks['Basis'].data[j].co-root).dot(dr)/L for j in face)/3
     if abs(fraction-a)<abs(fraction-b):flat_a.append(face)
     else:flat_b.append(face)
    area=sum(overlap_area([verts[0][j]for j in aa],[verts[0][j]for j in bb])for aa in flat_a for bb in flat_b)
    full_contact_area+=area
    contact_counts.append({'center':list(c),'contact_area_ML_squared':area,'flat_faces_a':len(flat_a),'flat_faces_b':len(flat_b),'plane_vertices':len(hits),'side_a':sum(abs(f-a)<abs(f-b)for k,f in hits),'side_b':sum(abs(f-b)<abs(f-a)for k,f in hits)})
checks={'positive_contact_area':full_contact_area>1e-5,'sampled_floor_clearance':all(s['minimum_ground_clearance']>-2e-5 for s in reports),'loops_close':all(v<1e-4 for v in loop_errors.values()),'morph_applied_at_full_curl':reports[0]['morph_weights']==[1.,1.],'skin_contact_both_sides':sum(p['side_a']>=3 and p['side_b']>=3 for p in contact_counts)>=2,'no_transverse_body_crossings':all(s['body_transverse_crossings']==0 for s in reports),'no_transverse_nonlocal_cup_skin_crossings':all(s['cup_skin_transverse_crossings']==0 for s in reports),'no_nonlocal_cup_cup_crossings':all(s['cup_cup_transverse_crossings']==0 for s in reports),'released_at_extension_and_touch_clips':all(s['morph_weights']==[0.,0.]for s in reports if s['clip']!='TightRoll' or 60<=s['frame']<=210),'nondegenerate':all(min(s['minimum_areas'])>1e-12 for s in reports)}
checks={k:bool(v)for k,v in checks.items()};d={'kind':'contact_corrective_cold_glb','ok':all(checks.values()),'checks':checks,'model_sha256':hashlib.sha256((O/'octopus-actions.glb').read_bytes()).hexdigest(),'contact_area_ML_squared':full_contact_area,'loop_max_vertex_errors':loop_errors,'contact_patches':contact_counts,'samples':reports,'limits':['Known contact planes separate complete triangles within 0.000002 ML (2e-6); only these certified contacts excluded before transverse-crossing test at2e-5 ML','Not continuous-time or full soft-body validation']};(O/('contact-full.validation.json'if'--full'in sys.argv else'contact-local.validation.json')).write_text(json.dumps(d,indent=2)+'\n');print('RESULT',json.dumps(checks),flush=True)
