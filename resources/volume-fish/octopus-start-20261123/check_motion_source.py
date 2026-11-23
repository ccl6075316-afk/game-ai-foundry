import bpy,json,hashlib
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-r1'
def snapshot():
 result={}
 for ob in bpy.data.collections['GRAY_REVIEW'].objects:
  if ob.type!='MESH':continue
  result[ob.name]={'vertices':[list(ob.matrix_world@v.co) for v in ob.data.vertices],'faces':[list(p.vertices) for p in ob.data.polygons]}
 return result
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'motion-r1/rest/octopus-gray.blend'));baseline=snapshot()
bpy.ops.wm.open_mainfile(filepath=str(OUT/'octopus-motion.blend'));current=snapshot()
skin_name='Octopus_gray_skin'
b=baseline[skin_name];c=current[skin_name]
tree=BVHTree.FromPolygons([Vector(v) for v in b['vertices']],b['faces'])
rest_surface_error=max(tree.find_nearest(Vector(v))[3] for v in c['vertices'])
other_exact=all(v==current[n] for n,v in baseline.items() if n!=skin_name)
assert rest_surface_error<1e-6 and other_exact,'Bound membrane clearance repair and preserve accessories'
coll=bpy.data.collections['GRAY_REVIEW'];rig=next(o for o in coll.objects if o.type=='ARMATURE')
checks={'motion_rest_geometry_preserved':rest_surface_error<1e-6,'accessories_geometry_exact':other_exact,'all_vertices_weighted':all(len(v.groups)>0 for o in coll.objects if o.type=='MESH' for v in o.data.vertices),'weights_normalized':all(abs(sum(g.weight for g in v.groups)-1)<1e-5 for o in coll.objects if o.type=='MESH' for v in o.data.vertices),'maximum_four_weights':all(len(v.groups)<=4 for o in coll.objects if o.type=='MESH' for v in o.data.vertices)}
bpy.ops.object.select_all(action='DESELECT')
for o in coll.objects:o.select_set(True)
bpy.context.view_layer.objects.active=rig
cold=OUT/'octopus-motion.cold.glb'
bpy.ops.export_scene.gltf(filepath=str(cold),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks['source_cold_export_identical']=sha(cold)==sha(OUT/'octopus-motion.glb')
report={'rest_surface_max_vertex_distance':rest_surface_error,'skin_topology_changed_for_web_deformation':True,'kind':'octopus_motion_source_cold_export','checks':checks,'ok':all(checks.values()),'source_sha256':sha(OUT/'octopus-motion.blend'),'model_sha256':sha(OUT/'octopus-motion.glb'),'cold_sha256':sha(cold),'baseline_sha256':sha(ROOT/'motion-r1/rest/octopus-gray.blend')}
(OUT/'source.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
