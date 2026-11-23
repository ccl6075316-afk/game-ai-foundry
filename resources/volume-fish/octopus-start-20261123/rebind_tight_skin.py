import bpy,json,math,bisect,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;OUT=R/'motion-r3';REST=OUT/'rest';build=json.loads((REST/'gray-build.validation.json').read_text());paths=build['control_paths'];labels=build['arm_labels'];N=64
bpy.ops.wm.open_mainfile(filepath=str(OUT/'octopus-roll.blend'));ob=bpy.data.objects['Octopus_gray_skin'];rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');armdata=rig.data;coll=bpy.data.collections['GRAY_REVIEW'];old=ob.data
with bpy.data.libraries.load(str(REST/'octopus-gray.blend'),link=False) as (src,dst):dst.meshes=["Tight_coil_skin"]
ob.data=dst.meshes[0];bpy.data.meshes.remove(old)
roots=[Vector(p[0]) for p in paths];directions=[(Vector(p[-1])-Vector(p[0])).normalized() for p in paths];lengths=[(Vector(p[-1])-Vector(p[0])).length for p in paths];stations=[[lengths[i]*(1-(1-j/N)**1.6)for j in range(N+1)]for i in range(8)]
# Reuse the production weighting code against the unchanged rest skeleton.
s=(R/'build_tight_motion.py').read_text();a=s.index('def smooth(x):');b=s.index("rest={b.name",a);part=s[a:b];part=part.replace(" mod=ob.modifiers.new('Bend propagation skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False;ob.parent=rig",'')
meshes=[ob];exec(compile(part,str(R/'build_tight_motion.py'),'exec'))
bpy.context.scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT')
for x in coll.objects:x.select_set(True)
bpy.context.view_layer.objects.active=rig;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'octopus-roll.blend'),compress=True);bpy.ops.export_scene.gltf(filepath=str(OUT/'octopus-roll.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
p=OUT/'build.validation.json';d=json.loads(p.read_text());d['triangles']=sum(len(p.vertices)-2 for o in coll.objects if o.type=='MESH' for p in o.data.polygons);d['source_sha256']=hashlib.sha256((OUT/'octopus-roll.blend').read_bytes()).hexdigest();d['model_sha256']=hashlib.sha256((OUT/'octopus-roll.glb').read_bytes()).hexdigest();d['distal_refinement']=build['distal_refinement'];p.write_text(json.dumps(d,indent=2)+'\n');print('REBOUND',d['triangles'])
