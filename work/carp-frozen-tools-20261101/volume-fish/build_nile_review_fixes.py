"""A/B local material repair and B inward-jaw trim, from frozen round4 assets."""
import bpy,bmesh,json,hashlib,math,struct,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
repo=Path(__file__).resolve().parents[3];sys.path[:0]=[str(repo/'cli'),str(Path(__file__).parent)]
from oral_jaws import build_closed_oral_jaws
from volume_mouth import slit_v
trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial';old=trial/'round4-ab-textured';out=trial/'round5-user-review-fixes'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
plan=read(out/'repair.plan.validation.json')
for name,digest in plan['inputs'].items():assert sha(repo/name)==digest,'Frozen repair input changed: '+name
profile=read(repo/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json');sections=profile['body']['sections'];aspect=972/1961;scale=.402819722890854
def digest(ob):
 return hashlib.sha256(repr(([tuple(v.co) for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],[[tuple(ob.data.uv_layers.active.data[li].uv) for li in p.loop_indices] for p in ob.data.polygons],[[tuple((ob.vertex_groups[g.group].name,g.weight)) for g in v.groups] for v in ob.data.vertices])).encode()).hexdigest()
def material(name,path):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.node_tree.nodes.clear();n=m.node_tree.nodes;bs=n.new('ShaderNodeBsdfPrincipled');output=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
 bs.inputs['Roughness'].default_value=1.;bs.inputs['Specular IOR Level'].default_value=0.
 tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True);tex.image.pack();tex.interpolation='Closest';m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 return m
def interpolate(u,k):
 if u<=sections[0][0]:return sections[0][k]
 for a,b in zip(sections,sections[1:]):
  if u<=b[0]:return a[k]+(b[k]-a[k])*(u-a[0])/(b[0]-a[0])
 return sections[-1][k]
def body_uv(body):
 uv=body.data.uv_layers.new(name='UVMap')
 for face in body.data.polygons:
  face.use_smooth=True;values=[]
  for li in face.loop_indices:
   p=body.data.vertices[body.data.loops[li].vertex_index].co;u=p.x+.5;top,bottom,width=[interpolate(u,k) for k in [1,2,3]]
   center=(.5-(top+bottom)/2)*aspect;radius=(bottom-top)/2*aspect;angle=math.atan2(p.y/max(width,1e-6),(p.z-center)/max(radius,1e-6))%(2*math.pi)
   values.append((li,u,angle/(2*math.pi)))
  seam=max(v[2] for v in values)-min(v[2] for v in values)>.5
  for li,u,v in values:uv.data[li].uv=(u,1-(v+1 if seam and v<.5 else v))
def export(target,rig):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['ARMATURE','MESH']:ob.select_set(True)
 bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_skins=True,export_materials='EXPORT')
 data=target.read_bytes();length,kind=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+length])
 for m in doc['materials']:
  fin=m.get('name','').startswith('fin_');m['alphaMode']='MASK' if fin else 'OPAQUE';m['doubleSided']=False
  if fin:m['alphaCutoff']=.5
 for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
 raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);tail=data[20+length:];target.write_bytes(struct.pack('<III',0x46546c67,2,20+len(raw)+len(tail))+struct.pack('<II',len(raw),kind)+raw+tail)
 return sum(doc['accessors'][p['indices']]['count']//3 for mesh in doc['meshes'] for p in mesh['primitives'])
def thickness(ob):
 vs=[v.co.copy() for v in ob.data.vertices];n=len(vs)//2;assert len(vs)%2==0
 pairs=[(vs[i]-vs[i+n]).length*scale*1000 for i in range(n)]
 front=[tuple(f.vertices) for f in ob.data.polygons if all(i<n for i in f.vertices)];back=[tuple(f.vertices) for f in ob.data.polygons if all(i>=n for i in f.vertices)]
 fb=BVHTree.FromPolygons(vs,front,all_triangles=True);bb=BVHTree.FromPolygons(vs,back,all_triangles=True)
 hits=[]
 for face in front:
  p=sum((vs[i] for i in face),Vector())/3;normal=(vs[face[1]]-vs[face[0]]).cross(vs[face[2]]-vs[face[0]]).normalized()
  hit,_,_,distance=bb.ray_cast(p-normal*1e-8,-normal,.05)
  if hit is None:hit,_,_,distance=bb.ray_cast(p+normal*1e-8,normal,.05)
  if hit is not None:hits.append(distance*scale*1000)
 return {'paired_surface_separation_mm':{'min':min(pairs),'median':sorted(pairs)[len(pairs)//2],'max':max(pairs)},'normal_ray_thickness_mm':{'samples':len(hits),'min':min(hits),'median':sorted(hits)[len(hits)//2],'max':max(hits)} if hits else None,'method':'Actual saved vertex-pair separation and triangle-center local-normal rays to the opposite fin skin, converted at40cm display scale. These are finite samples, not biological measurements.'}

for route in ['A','B']:
 target=out/(route+'-artifacts');target.mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(old/(route+'-artifacts/fish.blend')))
 rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE');body=next(ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.name.startswith('Closed_body'))
 fins=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob!=body];frozen_fins={ob.name:digest(ob) for ob in fins};old_body_digest=digest(body)
 thicknesses={ob.name:thickness(ob) for ob in fins}
 skin=material('body_skin',out/('body-atlas-clean-pectoral.png' if route=='A' else 'B-body-atlas-no-inward-outline.png'))
 oral_report=None
 if route=='A':body.data.materials[0]=skin
 else:
  bpy.data.objects.remove(body,do_unlink=True)
  cage=read(old/'B-artifacts/control-cage.validation.json');mesh=bpy.data.meshes.new('B trimmed integrated oral body');mesh.from_pydata(cage['vertices'],[],cage['faces']);mesh.update()
  body=bpy.data.objects.new('Closed_body_B',mesh);bpy.context.collection.objects.link(body);mesh.materials.append(skin)
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  ordered=sorted((row[0],f'body_{i:02d}') for i,row in enumerate(profile['rig']['spine']))
  def weights(u):
   if u<=ordered[0][0]:return {ordered[0][1]:1.}
   for a,b in zip(ordered,ordered[1:]):
    if u<=b[0]:
     t=(u-a[0])/(b[0]-a[0]);return {a[1]:1-t,b[1]:t}
   return {ordered[-1][1]:1.}
  gap_profile=[[.95,.0003],[.995,.010],[1.04,.012]]
  oral_report=build_closed_oral_jaws(body,profile['oral_jaws'],aspect,weights,gap_profile=gap_profile)
  mesh=body.data
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  body_uv(body)
  mesh.materials[1]=material('Inward jaw skin - no painted black rim',old/'shared/body-side.png')
  for face in mesh.polygons:
   if face.material_index==0:continue
   center=sum((mesh.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
   side='upper' if center.z>(.5-slit_v(profile['oral_jaws'],center.x+.5))*aspect else 'lower'
   x0,x1,y0,y1=plan['jaw_donor_domains_px'][side]
   for li in face.loop_indices:
    p=mesh.vertices[mesh.loops[li].vertex_index].co;t=max(0.,min(1.,(p.x+.5-.95)/.045));cross=max(0.,min(1.,abs(p.y)/max(interpolate(p.x+.5,3),1e-6)))
    mesh.uv_layers.active.data[li].uv=((x0+.5+(x1-x0-1)*t)/1961,1-(y0+.5+(y1-y0-1)*cross)/972)
  body.parent=rig;modifier=body.modifiers.new('Swim skin','ARMATURE');modifier.object=rig
 assert {ob.name:digest(ob) for ob in fins}==frozen_fins,'Existing fin or accepted tail changed'
 if route=='A':assert digest(body)==old_body_digest,'A geometry/UV/weights changed during texture repair'
 parts={ob.name:sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in bpy.context.scene.objects if ob.type=='MESH'};total=sum(parts.values());assert total<=2000
 bm=bmesh.new();bm.from_mesh(body.data);closed=all(e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-13 for f in bm.faces);bm.free()
 if route=='B':assert closed and zero==0
 bpy.context.scene.frame_set(0)
 bpy.ops.wm.save_as_mainfile(filepath=str(target/'fish.blend'),check_existing=False)
 actual=export(target/'fish.glb',rig);assert actual==total
 write(target/'validation.json',{'kind':'nile_local_review_repair','status':'experimental_requires_visual_review','formal_acceptance':False,'route':route,'triangles':total,'preferred_max':1500,'hard_max':2000,'parts':parts,'body_closed':closed,'body_zero_area':zero,'all_fin_geometry_uv_weights_unchanged':True,'tail_unchanged':True,'fins_before_and_after':frozen_fins,'fin_thickness':thicknesses,'oral_trim':oral_report,'A_body_geometry_uv_weights_unchanged':route=='A','hashes':{n:sha(target/n) for n in ['fish.blend','fish.glb']},'previous_fin_root_reports':'Old input hashes do not certify this re-export. Recheck after local visuals freeze.'})
 print(json.dumps({'ok':True,'route':route,'triangles':total,'closed':closed,'fin_thickness':{k:v['paired_surface_separation_mm'] for k,v in thicknesses.items()}}))
