"""RAM-only108 diagnostic geometry from stdout pipe. Never saves GLB/blend/JSON meshes."""
import bpy,subprocess,json,hashlib
from pathlib import Path
from mathutils import Vector
R=next(p for p in Path(__file__).resolve().parents if (p/'cli/gamefactory.py').exists());W=R/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108/original-skin-ram-grey';W.mkdir(exist_ok=True)
run=subprocess.run(['/Users/czl/.local/share/mise/installs/python/3.14.5/bin/python3',str(R/'resources/scripts/volume-fish/diagnostic_original_skin_ram_payload_108.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True);payload=json.loads(run.stdout);assert payload['status']=='RAM_diagnostic_only_CPU_failed'
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.22,.25,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5;scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
mat=bpy.data.materials.new('RAMdiagnosticGrey');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.5,.55,.58,1);bs.inputs['Roughness'].default_value=1;bs.inputs['Metallic'].default_value=0;bs.inputs['Specular IOR Level'].default_value=.15;records=[]
for name in ['baseline','original-skin-CPU-STOPPED']:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=payload['original_source']);imported=list(scene.objects)
 for obj in imported:
  if obj.animation_data:obj.animation_data_clear()
  if obj.type=='ARMATURE':obj.data.pose_position='REST'
  if obj.type=='MESH':
   obj.data.materials.clear();obj.data.materials.append(mat)
   for f in obj.data.polygons:f.material_index=0
 if name!='baseline':
  old=next(o for o in imported if o.type=='MESH'and o.name=='Closed_body');bpy.data.objects.remove(old,do_unlink=True)
  for i,surface in enumerate(payload['surfaces']):
   v=[(p[0],-p[2],p[1])for p in surface['POSITION']];n=[(p[0],-p[2],p[1])for p in surface['NORMAL']];ids=surface['indices'];ff=[ids[k:k+3]for k in range(0,len(ids),3)];mesh=bpy.data.meshes.new('RAMbody'+str(i));mesh.from_pydata(v,[],ff);mesh.update();obj=bpy.data.objects.new('RAMbody'+str(i),mesh);scene.collection.objects.link(obj);mesh.materials.append(mat)
   for face in mesh.polygons:face.use_smooth=True
   mesh.normals_split_custom_set_from_vertices(n)
 center=Vector((.445,0,-.005));bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=.205;cam.data.clip_start=.001;scene.camera=cam;bpy.ops.object.light_add(type='AREA',location=(.6,-.55,.7));light=bpy.context.object;light.data.energy=3;light.data.shape='DISK';light.data.size=.7;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
 for view,offset in [('side',(0,-.4,0)),('front',(.4,0,0)),('top',(0,0,.4)),('oblique',(.28,-.28,.12))]:
  cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();path=W/(name+'-'+view+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);records.append(dict(model=name,view=view,file=str(path),camera_position=list(cam.location),camera_rotation=list(cam.rotation_euler),ortho_scale=cam.data.ortho_scale))
receipt={k:v for k,v in payload.items()if k!='surfaces'};receipt.update(render_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),records=records,scope='NON-DELIVERY RAMgrey diagnostic. CPU stopped source1.099px>1pxgate. Readonly global diagnostic separately reported, no Phase3pass. No model/GLB/blend/UV/runtime write and no candidateaccepted.')
(W/'ram-render.validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
