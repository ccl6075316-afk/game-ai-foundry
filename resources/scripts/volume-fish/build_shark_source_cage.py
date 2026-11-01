"""Source-calibrated low cage with a true subterminal oral recess.

Blender coordinates: X longitudinal, Y transverse, Z dorsal. This is an author
stage, never an installed model or an anatomical/visual acceptance decision.
"""
import bpy,bmesh,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 args=sys.argv[sys.argv.index('--')+1:];settings=read(args[0]);out=Path(args[1]).resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True)
 profile=read(ROOT/settings['source_profile']);aspect=1/profile['source_aspect_ratio'];src=ROOT/settings['side'];front=ROOT/settings['front'];source_blend=ROOT/settings['rig_source'];assert sha(src)==settings['side_sha256']and sha(front)==settings['front_sha256']
 bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(str(source_blend),link=False)as(a,b):b.objects=[name for name in a.objects if name.endswith('_Rig')]
 rigs=[o for o in b.objects if o and o.type=='ARMATURE'];assert len(rigs)==1;rig=rigs[0];bpy.context.collection.objects.link(rig);assert len(rig.data.bones)==18
 rig.location=(0,0,0);rig.rotation_euler=(0,0,0);rig.scale=(1,1,1)
 # Original accepted motion remains on its original armature. Mesh is authored
 # from explicit sparse stations, never imported from or decimated from old mesh.
 def image(path):im=bpy.data.images.load(str(path),check_existing=False);im.pack();return im
 def material(name,path):
  m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs=bs or next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=1;bs.inputs['Specular IOR Level'].default_value=0;t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=image(path);t.interpolation='Closest';t.extension='EXTEND';m.node_tree.links.new(t.outputs['Color'],bs.inputs['Base Color']);m.node_tree.links.new(t.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.35;return m
 charts=settings.get('native_charts');side_mat=material('Native source skin / opaque',ROOT/charts['side']if charts else src);front_mat=material('Native frontal skin / opaque',ROOT/charts['front']if charts else front);fin_mat=material('Original native fin and eye pixels / opaque padding',ROOT/charts['fin_eye'])if charts else side_mat
 inner=bpy.data.materials.new('Source oral shadow / cavity only');inner.diffuse_color=(.035,.031,.028,1);inner.use_nodes=True;next(n for n in inner.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.035,.031,.028,1)
 sec=np.array(profile['body']['sections']);
 for u,width in settings.get('head_half_width_controls',[]):sec[np.argmin(abs(sec[:,0]-u)),3]=width
 spine=profile['rig']['spine'];ordered=sorted((p[0],'body_%02d'%i)for i,p in enumerate(spine))
 def weights(u):
  if u<=ordered[0][0]:return {ordered[0][1]:1}
  if u>=ordered[-1][0]:return {ordered[-1][1]:1}
  for (a,na),(b,nb)in zip(ordered,ordered[1:]):
   if a<=u<=b:t=(u-a)/(b-a);return {na:1-t,nb:t}
 def surface(u,theta):
  top,bottom,depth=[float(np.interp(u,sec[:,0],sec[:,i]))for i in [1,2,3]];v=(top+bottom)/2-(bottom-top)/2*math.cos(theta);return Vector((u-.5,depth*math.sin(theta),(.5-v)*aspect))
 mouth=settings['mouth'];a0=mouth['theta_start_pi']*math.pi;a1=mouth['theta_end_pi']*math.pi
 angles=sorted(set([round(i*math.tau/12,10)for i in range(12)]+[round(a0+(a1-a0)*i/6,10)for i in range(7)]));N=len(angles);stations=settings['body_stations_before_mouth'];factor=settings.get('body_longitudinal_refinement',1);stations=[float(a+(b-a)*i/factor)for a,b in zip(stations,stations[1:])for i in range(factor)]+[stations[-1]];stages=stations+['back_lip','front_lip']+settings['body_stations_after_mouth'];back=stages.index('back_lip');faces=[];uvs=[];materials=[];verts=[]
 def appendface(ids,mat=0):
  faces.append(tuple(ids));materials.append(mat)
 def mouth_u(t):
  f=max(0,min(1,(t-a0)/(a1-a0)));s=math.sin(math.pi*f);return mouth['corner_u']+(mouth['anterior_u']-mouth['corner_u'])*s,s
 for stage in stages:
  for t in angles:
   if isinstance(stage,str):u,g=mouth_u(t);u+=(-1 if stage=='back_lip'else 1)*mouth['half_gap_u']*g
   else:u=stage
   verts.append(surface(u,t))
 for row in range(1,len(stages)):
  for j,t in enumerate(angles):
   k=(j+1)%N;tm=(t+(angles[k]if k else math.tau))/2
   if row==back+1 and a0-1e-8<=tm<=a1+1e-8:continue
   appendface([(row-1)*N+j,(row-1)*N+k,row*N+k,row*N+j])
 appendface(list(range(N-1,-1,-1)));appendface([(len(stages)-1)*N+j for j in range(N)])
 selected=[j for j,t in enumerate(angles)if a0-1e-8<=t<=a1+1e-8];boundary=[back*N+j for j in selected]+[(back+1)*N+j for j in reversed(selected)];inside=[]
 for i in boundary:
  inside.append(len(verts));p=verts[i].copy();p.z+=mouth['cavity_depth_native'];verts.append(p)
 center=sum((verts[i]for i in inside),Vector())/len(inside);center.z+=mouth['cavity_roof_arch_native'];ci=len(verts);verts.append(center)
 for j,p in enumerate(boundary):
  k=(j+1)%len(boundary)
  if (verts[p]-verts[boundary[k]]).length<1e-8:continue
  appendface([p,boundary[k],inside[k],inside[j]],2);appendface([inside[j],inside[k],ci],2)
 data=bpy.data.meshes.new('Sparse body and integrated subterminal cavity');data.from_pydata(verts,[],faces);data.update();obj=bpy.data.objects.new('Closed_body',data);bpy.context.collection.objects.link(obj);obj.parent=rig
 for m in [side_mat,front_mat,inner]:data.materials.append(m)
 layer=data.uv_layers.new(name='NativeSourceUV');cap=profile['head_projection'];body_patch=profile['body_uv_patches'][0]
 def insidepoly(point,poly):
  x,y=point;inside=False
  for a,b in zip(poly,poly[1:]+poly[:1]):
   if (a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
  return inside
 for poly,mi in zip(data.polygons,materials):
  poly.use_smooth=True;poly.material_index=mi;is_front=mi!=2 and poly.center.x+.5>.985 and abs(poly.normal.x)>cap['normal_threshold']and abs(poly.normal.y)<cap['side_limit'] and poly.center.z>-.023
  if is_front:poly.material_index=1
  for li in poly.loop_indices:
   p=data.vertices[data.loops[li].vertex_index].co;u=p.x+.5;v=.5-p.z/aspect
   if is_front:
    dr=cap['model_depth_range'];vr=cap['model_v_range'];rect=cap['source_rect'];tu=rect[0]+np.clip((p.y-dr[0])/(dr[1]-dr[0]),0,1)*(rect[2]-rect[0]);tv=rect[1]+np.clip((v-vr[0])/(vr[1]-vr[0]),0,1)*(rect[3]-rect[1]);layer.data[li].uv=(float(tu),float(1-tv))
   elif mi==2:layer.data[li].uv=(.93,1-.63)
   else:
    if charts:pass
    elif u>.868 and v>.553:u=.81+(u-.868)*.15;v=.60+(v-.553)*.35
    elif insidepoly([u,v],profile['body_uv_patches'][1]['polygon']):u+=profile['body_uv_patches'][1]['offset'][0]
    elif .599<=u<=.743:
     oldtop,oldbottom=np.interp(u,sec[:,0],sec[:,1]),np.interp(u,sec[:,0],sec[:,2]);r=(v-oldtop)/(oldbottom-oldtop);u=.49+(u-.599)*.50;v=np.interp(u,sec[:,0],sec[:,1])+(np.interp(u,sec[:,0],sec[:,2])-np.interp(u,sec[:,0],sec[:,1]))*r
    layer.data[li].uv=(u,1-v)
 bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges),'Body/inner cavity not closed'
 for f in bm.faces:
  if f.material_index==2:f.smooth=False
 bm.to_mesh(data);bm.free();data.update()
 for i,p in enumerate(data.vertices):
  for name,gain in weights(p.co.x+.5).items():
   if gain>1e-7:(obj.vertex_groups.get(name)or obj.vertex_groups.new(name=name)).add([i],gain,'REPLACE')
 mod=obj.modifiers.new('Original native swim skin','ARMATURE');mod.object=rig
 fins=[];fin_records=[]
 if settings.get('fin_cages'):
  sys.path.insert(0,str(HERE));from shark_fin_cages import build
  proof=read(ROOT/settings['mouth_operator_review']);assert proof['mouth_local_geometry_review']=='pass' and proof['whole_fish_acceptance'] is False
  fins,fin_records=build(read(ROOT/settings['fin_cages']),obj,rig,fin_mat,aspect,weights)
  # Small closed native-source eye caps: preserve the painted eye footprint
  # without the old 528-triangle sphere per eye.
  assert settings.get('eyes_in_native_body_skin',False),'Rejected eye-cap trial is not a production branch; use accepted native body eye pixels'
 for mesh in [obj,*fins]:mesh.data.calc_loop_triangles()
 total_triangles=sum(len(mesh.data.loop_triangles)for mesh in[obj,*fins]);hard=settings.get('triangle_budget',{}).get('hard',2000);save(out/'budget.validation.json',dict(ok=total_triangles<=hard,triangles=total_triangles,hard=hard,preferred=settings.get('triangle_budget',{}).get('preferred',1500),scope='All authored body, integrated mouth, eyes and finite fin sides/walls.'))
 assert total_triangles<=hard,'Whole fish exceeds current triangle contract'
 rig.select_set(True);obj.select_set(True);bpy.context.view_layer.objects.active=rig
 scene=bpy.context.scene;scene.frame_set(0);scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('Review world');scene.world.use_nodes=True
 bg=scene.world.node_tree.nodes.new('ShaderNodeBackground');wo=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.12,.16,.18,1);bg.inputs[1].default_value=.8
 bpy.ops.object.light_add(type='AREA',location=(1,-2,3));light=bpy.context.object;light.data.energy=350;light.data.shape='DISK';light.data.size=4
 bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO';scene.view_settings.view_transform='Standard';review=out/'review';review.mkdir()
 for name,direction,focus,size in [('whole-side',(0,-1,0),(0,0,0),1.12),('head-side',(0,-1,0),(.43,0,-.02),.28),('head-front',(1,0,0),(.43,0,-.02),.28),('mouth-bottom',(0,0,-1),(.43,0,-.02),.24),('head-oblique',(1,-1,-.4),(.43,0,-.02),.30),('head-top',(0,0,1),(.43,0,0),.30)]:
  target=Vector(focus);camera.location=target+Vector(direction).normalized()*2;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=size;scene.render.filepath=str(review/(name+'.png'));bpy.ops.render.render(write_still=True)
 original_mats=list(data.materials);gray=bpy.data.materials.new('Geometry review only');gray.diffuse_color=(.55,.57,.60,1)
 for i in range(len(data.materials)):data.materials[i]=gray
 for name,direction in [('gray-mouth-bottom',(0,0,-1)),('gray-head-oblique',(1,-1,-.4))]:
  target=Vector((.43,0,-.02));camera.location=target+Vector(direction).normalized()*2;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.3;scene.render.filepath=str(review/(name+'.png'));bpy.ops.render.render(write_still=True)
 for i,m in enumerate(original_mats):data.materials[i]=m
 # Save only the authored model/armature, while retaining review camera/lights
 # in the editable source. GLB never includes review furniture or old meshes.
 bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);obj.select_set(True)
 for fin in fins:fin.select_set(True)
 bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=True,export_def_bones=False)
 if fins:save(out/'fin-authoring.json',{'fins':fin_records,'body_triangles':len(data.loop_triangles),'whole_triangles':len(data.loop_triangles)+sum(f['triangles']for f in fin_records),'operator_visual_acceptance':False})
 data.calc_loop_triangles();report={'ok':True,'kind':'shark_mouth_first_source_cage','scope':('Full source-cage construction candidate; no whole-fish acceptance.'if fins else'Body/mouth operator study only; fins not built.'),'triangles':total_triangles,'body_triangles':len(data.loop_triangles),'vertices':len(data.vertices),'bones':len(rig.data.bones),'mouth_boundary':[[float(v)for v in verts[i]]for i in boundary],'settings':settings,'body_closed_with_integrated_recess':True,'old_mesh_geometry_reused':False,'rig_source_sha256':sha(source_blend),'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'source_sha256':sha(src),'front_source_sha256':sha(front)};save(out/'validation.json',report);print(json.dumps({k:report[k]for k in ['ok','triangles','vertices','bones','model_sha256']}))
if __name__=='__main__':main()

