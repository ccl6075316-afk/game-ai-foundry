"""Read-only source-coordinate side renders for an authored open-reference jaw."""
import argparse,bpy,math,json,hashlib,sys
from pathlib import Path
from mathutils import Matrix
p=argparse.ArgumentParser();p.add_argument('--blend',required=True);p.add_argument('--profile',required=True);p.add_argument('--source',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);profile=json.loads(Path(a.profile).read_text(encoding='utf-8'))
degrees=profile['oral_jaws']['separate_lower']['reference_shape']['open_degrees'];out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()));scene=bpy.context.scene;scene.frame_set(0)
rig=next(o for o in scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
image=bpy.data.images.load(str(Path(a.source).resolve()),check_existing=True);w,h=image.size
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False
scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
world=bpy.data.worlds.new('Reference world');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.13,.16,.19,1);bg.inputs[1].default_value=.75
data=bpy.data.cameras.new('Source-coordinate camera');cam=bpy.data.objects.new('Source-coordinate camera',data);scene.collection.objects.link(cam);scene.camera=cam
data.type='ORTHO';data.ortho_scale=1.;cam.location=(0,-3,0);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.lights.new('Reference light','AREA');data.energy=35;data.size=3
light=bpy.data.objects.new('Reference light',data);scene.collection.objects.link(light);light.location=(0,-2,3);light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
clay=bpy.data.materials.new('Reference clay');clay.diffuse_color=(.5,.5,.5,1)
for angle in [0,degrees]:
    rig.pose.bones['jaw_lower'].rotation_mode='XYZ';rig.pose.bones['jaw_lower'].rotation_euler=(0,math.radians(angle),0)
    for gray in [False,True]:
        scene.view_layers[0].material_override=clay if gray else None
        scene.render.filepath=str(out/f'source-side-{angle:g}-{"clay" if gray else "texture"}.png');bpy.ops.render.render(write_still=True)
sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
(out/'render.validation.json').write_text(json.dumps({'blend_sha256':sha(a.blend),'profile_sha256':sha(a.profile),'source_sha256':sha(a.source),'reference_pose_degrees':degrees,'camera':{'width':1,'source_dimensions':[w,h],'location':[0,-3,0],'target':[0,0,0],'independent_alignment':False},'files':{q.name:sha(q) for q in out.glob('source-side-*.png')}},indent=2),encoding='utf-8')
