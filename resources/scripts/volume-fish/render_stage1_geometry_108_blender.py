"""Background Blender grey comparison. No runtime project changes."""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
R=next(p for p in Path(__file__).resolve().parents if (p/'cli/gamefactory.py').exists());W=R/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108/geometry-candidate-stage1'
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world.color=(.075,.095,.105);scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.22,.25,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
mat=bpy.data.materials.new('DiagnosticGrey');mat.diffuse_color=(.5,.55,.58,1);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.5,.55,.58,1);bs.inputs['Roughness'].default_value=1.;bs.inputs['Metallic'].default_value=0.;bs.inputs['Specular IOR Level'].default_value=.15
records=[]
for name,path in [('baseline',R/'projects/fish-107-zander-eye/game/assets/models/fish/zander.glb'),('stage1',W/'zander.glb')]:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(path));imported=list(scene.objects)
 for obj in imported:
  if obj.animation_data:obj.animation_data_clear()
  if obj.type=='ARMATURE':obj.data.pose_position='REST'
  if obj.type=='MESH':
   obj.data.materials.clear();obj.data.materials.append(mat)
   for p in obj.data.polygons:p.material_index=0
 # World glTF(x,y,z) -> Blender(x,-z,y), no per-model registration.
 center=Vector((.445,0,-.005));bpy.ops.object.camera_add(location=(0,-.3,0));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=.205;cam.data.lens=50;cam.data.clip_start=.001;cam.data.clip_end=100;scene.camera=cam
 bpy.ops.object.light_add(type='AREA',location=(.6,-.55,.7));light=bpy.context.object;light.data.energy=3;light.data.shape='DISK';light.data.size=.7;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
 for view,offset in [('side',(0,-.4,0)),('front',(.4,0,0)),('top',(0,0,.4)),('oblique',(.28,-.28,.12))]:
  cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();target=W/(name+'-'+view+'-grey.png');scene.render.filepath=str(target);bpy.ops.render.render(write_still=True);records.append(dict(model=name,view=view,file=str(target),camera_position=list(cam.location),camera_rotation=list(cam.rotation_euler),ortho_scale=cam.data.ortho_scale,center=list(center)))
(W/'grey-render.validation.json').write_text(json.dumps(dict(ok=True,scope='Native GLB rest-pose fixed cameras/lighting. Stage1 only, chin/front-lipY/UV unfinished. No runtime/LOD acceptance.',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_sha256=hashlib.sha256((R/'projects/fish-107-zander-eye/game/assets/models/fish/zander.glb').read_bytes()).hexdigest(),model_sha256=hashlib.sha256((W/'zander.glb').read_bytes()).hexdigest(),records=records),indent=2))
