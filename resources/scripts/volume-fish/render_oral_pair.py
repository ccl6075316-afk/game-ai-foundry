"""Read-only baseline/candidate review using one fixed native-space camera."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--baseline',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True)
p.add_argument('--target',nargs=3,type=float,default=[.44,0,-.045]);p.add_argument('--scale',type=float,default=.24)
p.add_argument('--inspect-separate-jaw',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
files={}
for label,path in [('before',a.baseline),('after',a.candidate)]:
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()));scene=bpy.context.scene;scene.frame_set(0)
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
    scene.render.resolution_x=900;scene.render.resolution_y=600;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
    world=bpy.data.worlds.new('Fixed comparison world');world.use_nodes=True;scene.world=world
    node=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');node.inputs[0].default_value=(.13,.16,.19,1);node.inputs[1].default_value=.75
    data=bpy.data.cameras.new('Fixed camera');camera=bpy.data.objects.new('Fixed camera',data);scene.collection.objects.link(camera);scene.camera=camera
    data.type='ORTHO';data.ortho_scale=a.scale
    lightdata=bpy.data.lights.new('Fixed light','AREA');lightdata.energy=35;lightdata.size=3
    light=bpy.data.objects.new('Fixed light',lightdata);scene.collection.objects.link(light);light.location=(0,-2,3)
    light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
    clay=bpy.data.materials.new('Fixed gray');clay.diffuse_color=(.5,.5,.5,1)
    for gray in [True,False]:
        scene.view_layers[0].material_override=clay if gray else None
        for view,direction in [('side',(0,-3,0)),('oblique',(2,-3,.65)),('front',(3,0,0))]:
            target=Vector(a.target);camera.location=target+Vector(direction)
            camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
            name=f'{label}_{"clay" if gray else "texture"}_{view}'
            scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True);files[name]=scene.render.filepath
    if label=='after' and a.inspect_separate_jaw:
        jaw=bpy.data.objects.get('Lower_jaw_separate')
        if jaw is None:raise ValueError('Separate-jaw inspection requested but no separate jaw exists')
        target=Vector(a.target);camera.location=target+Vector((2,-3,.65));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.view_layers[0].material_override=clay
        jaw.hide_render=True
        scene.render.filepath=str(out/'upper-only.png');bpy.ops.render.render(write_still=True);files['upper_only']=scene.render.filepath
        jaw.hide_render=False
        fish=[o for o in scene.objects if o.type=='MESH']
        for obj in fish:obj.hide_render=obj!=jaw
        camera.location=target+Vector((1.5,-2,2.5));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/'lower-only.png');bpy.ops.render.render(write_still=True);files['lower_only']=scene.render.filepath
        for obj in fish:obj.hide_render=False
        camera.location=target+Vector((2,-3,.65));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.view_layers[0].material_override=None
        upper=bpy.data.materials.new('Upper head study color');upper.diffuse_color=(.30,.43,.50,1)
        lower=bpy.data.materials.new('Independent jaw study color');lower.diffuse_color=(.70,.45,.12,1)
        for material in [upper,lower]:
            material.use_nodes=True
            bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            bsdf.inputs['Base Color'].default_value=material.diffuse_color;bsdf.inputs['Roughness'].default_value=1;bsdf.inputs['Specular IOR Level'].default_value=0
        for obj in fish:
            for i in range(len(obj.data.materials)):obj.data.materials[i]=lower if obj==jaw else upper
        scene.render.filepath=str(out/'parts-color.png');bpy.ops.render.render(write_still=True);files['parts_color']=scene.render.filepath
        jaw.location.z-=.05;target.z-=.02;data.ortho_scale=a.scale*1.2
        camera.location=target+Vector((2,-3,.65));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/'exploded.png');bpy.ops.render.render(write_still=True);files['exploded']=scene.render.filepath
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
(out/'comparison.validation.json').write_text(json.dumps({'scope':'Fixed camera, light and frame; qualitative morphology review, not anatomy acceptance. Optional exploded view translates jaw down0.05 native units in render memory only; model remains unchanged.','baseline_sha256':sha(a.baseline),'candidate_sha256':sha(a.candidate),'target':a.target,'orthographic_scale':a.scale,'frame':0,'files':files},indent=2),encoding='utf-8')
