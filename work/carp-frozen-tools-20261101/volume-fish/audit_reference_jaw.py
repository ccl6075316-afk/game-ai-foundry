"""Read-only regression for reference attributes, inverse binding and corner webs."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix
p=argparse.ArgumentParser();p.add_argument('--blend',required=True);p.add_argument('--profile',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);profile=json.loads(Path(a.profile).read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
degrees=profile['oral_jaws']['separate_lower']['reference_shape']['open_degrees']
rig.pose.bones['jaw_lower'].rotation_mode='XYZ';rig.pose.bones['jaw_lower'].rotation_euler=(0,math.radians(degrees),0)
bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();rows=[]
for name in ['Lower_jaw_separate','Oral_corner_web_left','Oral_corner_web_right']:
    obj=bpy.data.objects[name];expected=[v.value for v in obj.data.attributes['reference_jaw_weight'].data]
    jaw_group=obj.vertex_groups['jaw_lower'].index
    error=max(abs(sum(g.weight for g in v.groups if g.group==jaw_group)-expected[v.index]) for v in obj.data.vertices)
    projected={}
    for poly in obj.data.polygons:
        for li in poly.loop_indices:projected[obj.data.loops[li].vertex_index]=tuple(obj.data.uv_layers.active.data[li].uv)
    posed=obj.evaluated_get(graph).data
    uv_error=max(max(abs(v.co.x+.5-projected[v.index][0]),abs(v.co.z-(projected[v.index][1]-.5)/profile['source_aspect_ratio'])) for v in posed.vertices)
    rows.append({'object':name,'vertices':len(posed.vertices),'maximum_jaw_weight_error':error,'maximum_reference_projection_error_native':uv_error,'ok':error<1e-6 and uv_error<1e-6})
sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
result={'ok':all(q['ok'] for q in rows),'blend_sha256':sha(a.blend),'profile_sha256':sha(a.profile),'reference_pose_degrees':degrees,'objects':rows,'scope':'All jaw and commissure vertices must retain authored reference influence; posed X/Z must reconstruct original UV projection. Does not measure unknown depth or certify exact closed-lip contact.'}
Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));raise SystemExit(0 if result['ok'] else 1)
