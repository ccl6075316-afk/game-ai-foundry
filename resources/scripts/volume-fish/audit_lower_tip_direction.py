"""Reject a down-hooked lower tip using the actual skinned side silhouette."""
import argparse,bpy,bmesh,math,json,hashlib,sys
from pathlib import Path
from mathutils import Matrix
p=argparse.ArgumentParser();p.add_argument('--blend',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);blend=Path(a.blend).resolve();bpy.ops.wm.open_mainfile(filepath=str(blend))
bpy.context.scene.frame_set(0);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
jaw=bpy.data.objects['Lower_jaw_separate'];rows=[]
for degrees in [0,6,12]:
    b=rig.pose.bones['jaw_lower'];b.rotation_mode='XYZ';b.rotation_euler=(0,math.radians(degrees),0);bpy.context.view_layer.update()
    posed=jaw.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=posed.to_mesh();bm=bmesh.new();bm.from_mesh(mesh)
    triangles=[[jaw.matrix_world@v.co for v in f.verts] for f in bm.faces];maxx=max(v.x for tri in triangles for v in tri);bm.free();posed.to_mesh_clear();points=[]
    for offset in [.003,.002,.001,.0005]:
        x=maxx-offset;hits=[]
        for tri in triangles:
            if min(v.x for v in tri)>x or max(v.x for v in tri)<x:continue
            for aa,bb in zip(tri,tri[1:]+tri[:1]):
                if (aa.x-x)*(bb.x-x)<=0 and abs(bb.x-aa.x)>1e-9:hits.append(aa.lerp(bb,(x-aa.x)/(bb.x-aa.x)).z)
        if not hits:raise ValueError('Missing jaw silhouette intersection')
        points.append([x,max(hits)])
    angle=math.degrees(math.atan2(points[-1][1]-points[0][1],points[-1][0]-points[0][0]))
    rows.append({'jaw_degrees':degrees,'terminal_upper_envelope_angle_degrees':angle,'points_xz':points,'ok':angle>0})
result={'ok':all(x['ok'] for x in rows),'blend_sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),'scope':'Head-right fish, body at rest, native+Z up. Exact projected jaw upper silhouette over lateralY; compare x_max-.003 tox_max-.0005 at0/6/12degrees. Reject downturned anterior upper edge. Rounded terminal cap excluded. Does not verify full occlusion or anatomy.','samples':rows}
Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));raise SystemExit(not result['ok'])
