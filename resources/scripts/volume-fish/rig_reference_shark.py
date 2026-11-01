"""Own sparse reference-shark rig; body/fin/eye geometry and UV are unchanged.

Full actual basal caps inherit barycentric body skin. Independent fin motion
fades in by measured distance from that entire cap, not by shrinking the root.
"""
import bpy,json,hashlib,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();c=json.loads(cp.read_text());src=Path(c['baseline']);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(src/'fish.glb')==c['baseline_sha256'];bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));cfg=json.loads(Path(c['reference']).read_text());auth=json.loads((src/'fin-authoring.json').read_text());body=bpy.data.objects['Reference_head_body'];axis=cfg['reference_body_axis_m'];rows=cfg['body_stations'];all_meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
def geometry():return {o.name:hashlib.sha256(repr(([(tuple(v.co))for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],[tuple(v.uv)for v in o.data.uv_layers.active.data]if o.data.uv_layers.active else[])).encode()).hexdigest()for o in all_meshes}
before=geometry();assert not any(o.type=='ARMATURE'for o in bpy.context.scene.objects);arm=bpy.data.armatures.new('Scalloped_reference_skeleton');rig=bpy.data.objects.new('Scalloped_reference_rig',arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT');root=arm.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,0,.02);names=[];stations=c['spine_stations_t']
def center(t):return Vector((axis*(.5-t),0,float(np.interp(t,[r['t']for r in rows],[(r['top_z_m']+r['bottom_z_m'])/2 for r in rows]))))
for i,t in enumerate(stations):
    b=arm.edit_bones.new('body_%02d'%i);b.head=center(t);b.tail=center(stations[i+1]if i+1<len(stations)else t+.1);b.parent=arm.edit_bones[names[-1]]if names else root;names.append(b.name)
bpy.ops.object.mode_set(mode='OBJECT')
def axial(x):
    t=(axis/2-x)/axis
    if t<=stations[0]:return {names[0]:1.}
    if t>=stations[-1]:return {names[-1]:1.}
    for i,(a,b)in enumerate(zip(stations,stations[1:])):
        if a<=t<=b:g=(t-a)/(b-a);return {names[i]:1-g,names[i+1]:g}
weight_reductions=[]
def assign(ob,i,mix):
    total=sum(mix.values());assert total>0
    ordered=sorted(((name,w)for name,w in mix.items()if w>1e-8),key=lambda item:item[1],reverse=True)
    if len(ordered)>4:
        lost=sum(w for _,w in ordered[4:])/total
        weight_reductions.append(dict(mesh=ob.name,vertex=i,dropped_weight=lost))
        assert lost<.03,'Four-influence export would discard substantial skin weight'
        mix=dict(ordered[:4]);total=sum(mix.values())
    for name,w in mix.items():
        if w>1e-8:(ob.vertex_groups.get(name)or ob.vertex_groups.new(name=name)).add([i],w/total,'REPLACE')
for o in all_meshes:
    o.vertex_groups.clear();o.parent=rig;mod=o.modifiers.new('Native authored shark skin','ARMATURE');mod.object=rig
for v in body.data.vertices:assign(body,v.index,axial(v.co.x))
body.data.calc_loop_triangles();bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True)
def surface_mix(p):
    h,n,fi,d=tree.find_nearest(p);ids=bt[fi];beta=barycentric_transform(h,*[bv[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
    for i,gain in zip(ids,beta):
        for group in body.data.vertices[i].groups:name=body.vertex_groups[group.group].name;mix[name]=mix.get(name,0)+max(0,gain)*group.weight
    total=sum(mix.values());return {k:v/total for k,v in mix.items()if v>1e-8}
fin_motion=[];skin_report=[]
for row in auth['fins']:
    ob=bpy.data.objects[row['name']];me=ob.data;me.calc_loop_triangles();verts=[v.co.copy()for v in me.vertices];roots=set(row['root_ids']);cap=[tuple(t.vertices)for t in me.loop_triangles if all(i in roots for i in t.vertices)];assert cap and roots;rt=BVHTree.FromPolygons(verts,cap,all_triangles=True);p=np.array([tuple(verts[i])for i in roots]);anchor=Vector(tuple(p.mean(0)));name=row['name'];is_tail=name=='Caudal';bone_labels=['CaudalUpper_bone','CaudalLower_bone']if is_tail else[name+'_bone'];parent=max(surface_mix(anchor),key=surface_mix(anchor).get)
    for label in bone_labels:
        bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT');b=arm.edit_bones.new(label);b.head=anchor
        if is_tail:b.head=(axis*(.5-.70),0,float(center(.70).z));b.tail=b.head+Vector((-.045,0,.015 if'Upper'in label else-.04))
        else:
            side=-1 if name.endswith('_left')else 1;points=[v for i,v in enumerate(verts)if i not in roots];tip=max(points,key=lambda p:rt.find_nearest(p)[3]);b.tail=tip
            if(b.tail-b.head).length<.001:b.tail=b.head+Vector((0,0,.015))
        b.parent=arm.edit_bones[parent];bpy.ops.object.mode_set(mode='OBJECT');paired=row['paired'];side=-1 if name.endswith('_left')else 1;world_axis=Vector((side,0,0))if paired else Vector((0,0,1));amp=c['native_paired_fin_radians']if paired else c['native_median_fin_radians'];delay=c['fin_phases'].get(name,1.5);fin_motion.append(dict(bone=label,axis=list(world_axis),amplitude=amp,phase=delay+(.15 if'Lower'in label else 0)))
    gains=[]
    for vertex in me.vertices:
        dist=rt.find_nearest(vertex.co)[3];base=surface_mix(vertex.co);u=np.clip((dist-c['independent_fin_start_m'])/(c['independent_fin_full_m']-c['independent_fin_start_m']),0,1);gain=0 if vertex.index in roots else c['independent_fin_maximum_weight']*float(u*u*(3-2*u));mix={k:v*(1-gain)for k,v in base.items()}
        if gain:
            if is_tail:
                t=np.clip((vertex.co.z-center(.70).z+.005)/.010,0,1);mix[bone_labels[0]]=gain*float(t);mix[bone_labels[1]]=gain*float(1-t)
            else:mix[bone_labels[0]]=gain
        assign(ob,vertex.index,mix);gains.append(gain)
    skin_report.append(dict(name=name,full_cap_vertices=len(roots),full_cap_triangles=len(cap),maximum_independent_weight=max(gains),root_independent_weight=0,root_policy='Whole exact cap, barycentric finite body triangle weights. No root subsetting.'))
for o in all_meshes:
    if o.name.startswith('Eye_'):
        for v in o.data.vertices:assign(o,v.index,{names[0]:1.})
assert geometry()==before,'Rigging changed static geometry or UV';assert len(arm.bones)==18;bad=[(o.name,v.index)for o in all_meshes for v in o.data.vertices if abs(sum(g.weight for g in v.groups)-1)>1e-5];assert not bad
scene=bpy.context.scene;scene.render.fps=c['fps'];scene.frame_start=0;scene.frame_end=c['loop_frames'];rig.animation_data_create()
for frame in range(c['loop_frames']+1):
    phase=math.tau*(frame%c['loop_frames'])/c['loop_frames']
    for i,name in enumerate(names):
        pb=rig.pose.bones[name];pb.rotation_mode='QUATERNION';local_axis=pb.bone.matrix_local.to_3x3().inverted()@Vector((0,0,1));pb.rotation_quaternion=Quaternion(local_axis,c['native_body_radians'][i]*math.sin(phase-i*c['body_phase_step']));pb.keyframe_insert('rotation_quaternion',frame=frame,group=name)
    for item in fin_motion:
        pb=rig.pose.bones[item['bone']];pb.rotation_mode='QUATERNION';local_axis=pb.bone.matrix_local.to_3x3().inverted()@Vector(item['axis']);pb.rotation_quaternion=Quaternion(local_axis,item['amplitude']*math.sin(phase-item['phase']));pb.keyframe_insert('rotation_quaternion',frame=frame,group=item['bone'])
rig.animation_data.action.name='Swim';scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for o in all_meshes:o.select_set(True)
bpy.context.view_layer.objects.active=rig;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());r=dict(ok=True,kind='own_reference_shark_native_rig',model_sha256=sha(out/'fish.glb'),config_sha256=sha(cp),body_and_fins_and_eyes_geometry_uv_exact=True,static_geometry_fingerprints=before,bones=len(arm.bones),body_bones=names,fin_motion_bones=[r['bone']for r in fin_motion],skin=skin_report,explicit_four_influence_reductions=weight_reductions,maximum_discarded_skin_weight=max((r['dropped_weight']for r in weight_reductions),default=0),loop_seconds=c['loop_frames']/c['fps'],whole_triangles=auth['whole_triangles'],native_motion_basis=c['motion_basis'],motion_validation='pending',formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=True,bones=len(arm.bones),triangles=auth['whole_triangles'],loop_seconds=r['loop_seconds'])))
