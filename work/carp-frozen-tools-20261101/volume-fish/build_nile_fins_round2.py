"""Image-outline low-poly fins for the authorized Nile trial; never installs assets."""
import bpy,bmesh,json,sys,math,hashlib,numpy as np
from pathlib import Path
from collections import defaultdict,Counter
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
from mathutils.bvhtree import BVHTree

BASE=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert BASE.name=='round2' and BASE.parent.name=='nile-dorsal-route-trial'
P=json.loads((BASE.parent/'trial-profile.json').read_text())
F=json.loads((BASE/'fin-build.plan.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SOURCE=Path(P['source_blend'])
if not SOURCE.is_file():
 SOURCE=Path(__file__).resolve().parents[3]/'projects/fishing-2d/experiments/nile-tilapia-static-merge/nile_tilapia-static.blend'
assert sha(SOURCE)==P['source_sha256']
def smooth(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)
def nearline(q,line):
 best=(1e20,None)
 for a,b in zip(line,line[1:]):
  e=b-a;t=max(0.,min(1.,(q-a).dot(e)/max(e.length_squared,1e-12)));at=a+e*t
  if (q-at).length<best[0]:best=((q-at).length,at)
 return best
def inside(q,poly):
 odd=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a.y>q.y)!=(b.y>q.y) and q.x<(b.x-a.x)*(q.y-a.y)/(b.y-a.y)+a.x:odd=not odd
 return odd
def geometry_digest(ob):
 return hashlib.sha256(repr(([tuple(v.co) for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons])).encode()).hexdigest()
def texture_material(name,path):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;tree=mat.node_tree;bsdf=tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=1.;bsdf.inputs['Specular IOR Level'].default_value=0.
 image=bpy.data.images.load(str(path),check_existing=True);tex=tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);tree.links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha']);image.pack();return mat

bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
protected={o.name:geometry_digest(o) for o in bpy.data.objects if o.type=='MESH' and o.name not in [f['name'] for f in F['fins']]+['Closed_body']}
body=bpy.data.objects['Closed_body'];before=[v.co.copy() for v in body.data.vertices]
xmin=min(v.x for v in before);zcenter=(min(v.z for v in before if v.x<xmin+.002)+max(v.z for v in before if v.x<xmin+.002))/2
for v in body.data.vertices:
 amount=1-smooth((v.co.x-xmin)/F['tail']['blend_native'])
 v.co.y*=1-amount*(1-F['tail']['end_width_scale'])
 v.co.z=zcenter+(v.co.z-zcenter)*(1-amount*(1-F['tail']['end_height_scale']))
body.data.update();body_changed=[i for i,(a,v) in enumerate(zip(before,body.data.vertices)) if (a-v.co).length>1e-10]
assert all(before[i].x<=xmin+F['tail']['blend_native'] for i in body_changed)
points=[v.co.copy() for v in body.data.vertices];faces=[tuple(p.vertices) for p in body.data.polygons]
bvh=BVHTree.FromPolygons(points,faces,all_triangles=True)
body_weights=[{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices]
def at_body(q,direction):
 hit,no,fi,_=bvh.ray_cast(q+direction*2,-direction,4.)
 if hit is None:hit,no,fi,_=bvh.find_nearest(q)
 if no.dot(direction)<0:no=-no
 return hit,no,fi
def sample_weights(point):
 hit,no,fi,_=bvh.find_nearest(point);ids=faces[fi]
 bary=barycentric_transform(hit,*[points[i] for i in ids[:3]],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
 d=defaultdict(float)
 for i,w in zip(ids,bary):
  for name,value in body_weights[i].items():d[name]+=max(0.,w)*value
 return d

records=[];roots={}
for spec in F['fins']:
 name=spec['name'];ob=bpy.data.objects[name];poly=[Vector(q) for q in spec['polygon_px']];base=[Vector(q) for q in spec['baseline_px']]
 # All topology is made from the independently isolated image and authored root.
 # The old fin mesh, UVs and weights are not queried.
 seed=poly[:]
 for a,z in zip(base,base[1:]):
  for i in range(max(1,math.ceil((z-a).length/18.))+1):
   q=a.lerp(z,i/max(1,math.ceil((z-a).length/18.)))
   if inside(q,poly):seed.append(q)
 minx,maxx=min(q.x for q in poly),max(q.x for q in poly);miny,maxy=min(q.y for q in poly),max(q.y for q in poly)
 for y in range(int(miny),int(maxy)+1,36):
  for x in range(int(minx),int(maxx)+1,36):
   q=Vector((x+.37,y+.23))
   if inside(q,poly):seed.append(q)
 dv,_,df,*_=delaunay_2d_cdt([q/1961 for q in seed],[(i,(i+1)%len(poly)) for i in range(len(poly))],[list(range(len(poly)))],1,1e-8)
 tri=[tuple(face) for face in df if len(face)==3]
 used=sorted({i for f in tri for i in f});remap={v:i for i,v in enumerate(used)};uvpx=[dv[i]*1961 for i in used];tri=[tuple(remap[i] for i in f) for f in tri]
 n=len(uvpx);dist=[nearline(q,base)[0] for q in uvpx];maxd=max(dist);paired=name.startswith(('Pectoral','Pelvic'));tail=name=='Caudal';side=-1 if name.endswith('_left') else 1
 direction=Vector((0,side,0)) if paired else Vector((-1,0,0)) if tail else Vector((0,0,1 if name=='Dorsal' else -1))
 vertices=[];weights=[];thickness=[];root_ids=[];geometric_t=[];locked_outline_errors=[]
 bone=name+'_2';assert ob.parent.data.bones.get(bone) is not None
 for i,(q,distance) in enumerate(zip(uvpx,dist)):
  basal=nearline(q,base)[1];bp=Vector(((basal.x-980.5)/1961,0.,(486-basal.y)/1961))
  if tail:bp.z=zcenter+(bp.z-zcenter)*F['tail']['end_height_scale']
  hit,no,fi=at_body(bp,direction)
  s=min(1.,distance/maxd);geometric_t.append(s);gain=1-smooth(distance/14.)
  point=Vector(((q.x-980.5)/1961,0.,(486-q.y)/1961))
  if paired:
   point.y=side*(abs(hit.y)+spec['spread_native']*smooth(s)+spec['camber_mm']/1000/P['runtime_scale']*math.sin(math.pi*s))
  elif tail:
   # Complete independent tail shape: only a single rigid placement shift.
   # Body fitting is confined to the narrow collar, never the free outline.
   point.x+=xmin+.00015-(base[0].x-980.5)/1961
   point.y=spec['camber_mm']/1000/P['runtime_scale']*math.sin(math.pi*s)
  else:point.z+=hit.z-bp.z;point.y=spec['camber_mm']/1000/P['runtime_scale']*math.sin(math.pi*s)
  # A finite root collar transports the source patch to the local body plane.
  delta=Vector(((q.x-basal.x)/1961,0.,-(q.y-basal.y)/1961));tangent_delta=delta-no*delta.dot(no)
  if paired:tangent_delta.y=side*abs(tangent_delta.y)
  root=hit+tangent_delta*.65-no*(.00015)
  if tail:root=Vector((xmin+.00015,0.,bp.z+tangent_delta.z*.65))
  point=point.lerp(root,gain)
  root_mm=spec['root_mm']
  if tail:
   sh,_,_,_=bvh.ray_cast(Vector((xmin+.0001,1.,point.z)),Vector((0,-1,0)),2.)
   root_mm=max(.4,2*abs(sh.y)*P['runtime_scale']*1000-.08) if sh is not None else .4
  t=spec['edge_mm']+(root_mm-spec['edge_mm'])*(1-s)**1.6;thickness.append(t/1000/P['runtime_scale'])
  if distance<=4.:root_ids.append(i)
  elif not tail:
   sh,nn,_,_=bvh.find_nearest(point);signed=(point-sh).dot(nn);clear=thickness[-1]*.5+.0003
   if signed<clear:point=sh+nn*clear
  if tail and distance>=14.:
   expected=Vector(((q.x-980.5)/1961+xmin+.00015-(base[0].x-980.5)/1961,0.,(486-q.y)/1961))
   locked_outline_errors.append(math.hypot(point.x-expected.x,point.z-expected.z)*P['runtime_scale']*1000)
  mix=sample_weights(point);fw=smooth((distance-5.)/max(10.,maxd*.65))*spec['fin_influence']
  mix={k:v*(1-fw) for k,v in mix.items()};mix[bone]=mix.get(bone,0.)+fw
  mix=dict(sorted(mix.items(),key=lambda v:-v[1])[:4]);total=sum(mix.values());mix={k:v/total for k,v in mix.items()}
  vertices.append(point);weights.append(mix)
 assert root_ids,(name,'No actual source root vertices')
 # Consistent layer normals, then explicit finite-thickness shell.
 mid=bpy.data.meshes.new(name+'_mid');mid.from_pydata(vertices,[],tri);mid.update();bm=bmesh.new();bm.from_mesh(mid);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mid);bm.free();tri=[tuple(p.vertices) for p in mid.polygons];normals=[v.normal.copy() for v in mid.vertices]
 solid=[p+normals[i]*thickness[i]*.5 for i,p in enumerate(vertices)]+[p-normals[i]*thickness[i]*.5 for i,p in enumerate(vertices)]
 allfaces=tri+[tuple(i+n for i in reversed(f)) for f in tri];counts=Counter(tuple(sorted((f[k],f[(k+1)%3]))) for f in tri for k in range(3));walls=[]
 for a,z,c in tri:
  for x,y in [(a,z),(z,c),(c,a)]:
   if counts[tuple(sorted((x,y)))]==1:walls.extend([(x,x+n,y+n),(x,y+n,y)])
 allfaces+=walls
 mesh=bpy.data.meshes.new(name+'_image_cage');mesh.from_pydata(solid,[],allfaces);mesh.update();ob.data=mesh;uvlayer=mesh.uv_layers.new(name='UVMap')
 safe=np.load(BASE/spec['wall_donor_field'])
 for face in mesh.polygons:
  face.material_index=int(face.index>=len(tri)*2);face.use_smooth=True
  for li in face.loop_indices:
   vi=mesh.loops[li].vertex_index%n;pixel=uvpx[vi]
   if face.material_index:
    # Per-source nearest safe interior pixels; no painted outline stretched
    # across the thickness, and no old fin mesh queried.
    x,y=map(lambda v:int(round(v)),uvpx[vi]);x=max(0,min(1960,x));y=max(0,min(971,y));pixel=Vector((float(safe['x'][y,x])+.5,float(safe['y'][y,x])+.5))
   uvlayer.data[li].uv=(pixel.x/1961,1-pixel.y/972)
 ob.vertex_groups.clear()
 for i,d in enumerate(weights+weights):
  for key,value in d.items():
   group=ob.vertex_groups.get(key) or ob.vertex_groups.new(name=key);group.add([i],value,'REPLACE')
 ob.data.materials.clear();mat=texture_material(name+'_source',BASE/spec['image']);ob.data.materials.append(mat);ob.data.materials.append(mat)
 source_t=mesh.attributes.new('foundry_fin_source_t','FLOAT','POINT')
 for i,v in enumerate(geometric_t+geometric_t):source_t.data[i].value=v
 bm=bmesh.new();bm.from_mesh(mesh);assert all(len(e.link_faces)==2 for e in bm.edges),(name,'Nonmanifold');assert all(f.calc_area()>1e-13 for f in bm.faces),(name,'Degenerate');bm.free()
 roots[name]={'ids':root_ids+[i+n for i in root_ids],'source_t_max':4./maxd,'vertices':len(solid),'rest_points_blender':[list(solid[i]) for i in root_ids+[i+n for i in root_ids]],'source_baseline':[[p.x/1961,p.y/972] for p in base]}
 records.append({'name':name,'triangles':len(allfaces),'vertices':len(solid),'root_vertices':len(root_ids)*2,'thickness_mm':[min(thickness)*P['runtime_scale']*1000,max(thickness)*P['runtime_scale']*1000],'camber_mm':spec['camber_mm'],'closed_manifold':True,'old_fin_mesh_read':False,'wall_outline_donors_excluded':True,'tail_free_mid_outline_locked_error_mm':max(locked_outline_errors) if locked_outline_errors else None})
 bpy.data.meshes.remove(mid)
assert protected=={o.name:geometry_digest(o) for o in bpy.data.objects if o.type=='MESH' and o.name in protected}
for image in bpy.data.images:
 if image.source=='FILE' and not image.packed_file:
  try:image.pack()
  except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'fins-candidate.blend'))
bpy.ops.object.select_all(action='DESELECT')
for spec in F['fins']:bpy.data.objects[spec['name']].select_set(True)
bpy.data.objects[F['rig']].select_set(True)
from io_scene_gltf2.blender.exp.primitive_extract import PrimitiveCreator
method=PrimitiveCreator._PrimitiveCreator__get_bone_data;code=method.__code__
if code.co_consts.count(.0001)==1:method.__code__=code.replace(co_consts=tuple(0. if x==.0001 else x for x in code.co_consts))
bpy.ops.export_scene.gltf(filepath=str(BASE/'fins.glb'),export_format='GLB',use_selection=True,export_skins=True,export_animations=False)
(BASE/'root-selection.json').write_text(json.dumps(roots,indent=2)+'\n')
report={'ok':True,'formal_acceptance':False,'source_sha256':P['source_sha256'],'records':records,'body_change':{'only_posterior':True,'vertices':len(body_changed),'max_displacement_mm':max((a-v.co).length for a,v in zip(before,body.data.vertices))*P['runtime_scale']*1000,'preserved_before_x':xmin+F['tail']['blend_native']},'protected_meshes_unchanged':True,'blend_sha256':sha(BASE/'fins-candidate.blend'),'glb_sha256':sha(BASE/'fins.glb'),'note':'Build only. Independent roots/free surfaces, actual motion and material transfer pending.'}
(BASE/'fin-build.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
